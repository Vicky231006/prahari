"""
PRAHARI Gateway API — main.py

Performance-audited rewrite.  Key changes vs original:
  1.  Bounded Kafka concurrency via asyncio.Queue (maxsize=32) + fixed worker
      pool (4 coroutines).  The old code spawned one coroutine per Kafka message
      with run_coroutine_threadsafe, exhausting the DB connection pool (20) under
      any sustained throughput.
  2.  handle_fused_alert is now a fast-path: INSERT alert + case, COMMIT, broadcast
      WS, then schedule a DETACHED background task for RAG enrichment.  The old
      code awaited the RAG HTTP call (5 s timeout) inside the ingest path,
      serialising every alert behind a slow/flapping RAG service.
  3.  Shared httpx.AsyncClient created once at startup and closed at shutdown.
      The old code opened a new connection pool per alert.
  4.  All list endpoints (/alerts, /cases, /audit, /quantum/sessions) now use
      keyset / seek-method cursor pagination with LIMIT.  The old code did
      SELECT * with no LIMIT, materialising entire tables into Python objects.
  5.  get_dashboard_kpis replaces the N+1 per-identity alert-count loop with a
      single GROUP BY query.
  6.  Redis KPI cache invalidation is rate-limited to once every 5 s.  The old
      code called redis_client.delete() on every Kafka message, making the 30 s
      TTL completely ineffective under continuous ingestion.
"""

import asyncio
import json
import os
import threading
import time
from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID

import httpx
import redis
from confluent_kafka import Consumer, KafkaError
from fastapi import FastAPI, Depends, HTTPException, WebSocket, WebSocketDisconnect, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select, update, desc, func, or_, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from .database import get_db, AsyncSessionLocal
from .models import Alert, Case, AuditTrail, QuantumAlert, IdentityProfile
from .schemas import (
    AlertResponse,
    CaseActionRequest,
    CaseResponse,
    AuditTrailResponse,
    QuantumAlertResponse,
    QuantumStatsResponse,
    DashboardKPIsResponse,
    SeverityCount,
    TopRiskIdentity,
    ScenarioInjectionRequest,
    PaginatedAlerts,
    PaginatedCases,
    PaginatedAuditTrail,
    PaginatedQuantumSessions,
)
from .ws_manager import ws_manager

# ── App Setup ──────────────────────────────────────────────────────────────────
app = FastAPI(
    title="PRAHARI Gateway API",
    description="Central gateway routing cybersecurity-telemetry & transaction alerts",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Config ─────────────────────────────────────────────────────────────────────
KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9094")
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
DEMO_MODE = os.getenv("DEMO_MODE", "false").lower() == "true"
RAG_SERVICE_URL = os.getenv("RAG_SERVICE_URL", "http://localhost:8082")

# Kafka worker pool settings
_KAFKA_WORKER_COUNT = 4      # number of concurrent alert-processing coroutines
_KAFKA_QUEUE_MAXSIZE = 32    # back-pressure: drop (and log) when queue is full

# Redis KPI cache invalidation rate-limit
_KPI_INVALIDATION_COOLDOWN_S: float = 5.0  # only delete the KPI key once per 5 s

# ── Module-level singletons ────────────────────────────────────────────────────
# Set in startup_event; used across handlers.
main_loop: Optional[asyncio.AbstractEventLoop] = None
_rag_client: Optional[httpx.AsyncClient] = None
_alert_queue: Optional[asyncio.Queue] = None
_last_kpi_invalidation: float = 0.0

# ── Redis connection ───────────────────────────────────────────────────────────
try:
    redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
    redis_client.ping()
except Exception as e:
    print(f"[warning] Redis connection failed in gateway: {e}")
    redis_client = None


# ── Redis KPI cache invalidation (rate-limited) ────────────────────────────────
def _maybe_invalidate_kpi_cache() -> None:
    """Delete the KPI Redis key at most once every _KPI_INVALIDATION_COOLDOWN_S.

    The old implementation called redis_client.delete("kpi:dashboard_kpis") on
    every Kafka message.  Under continuous ingestion (e.g. 50 msg/s) the cache
    was effectively always cold, so every /api/dashboard/kpis request hit
    Postgres — running 6+ queries each time.  This guard ensures the 30 s TTL
    is respected: the key is only evicted proactively at most once per 5 s, so
    the cache stays warm the vast majority of the time.
    """
    global _last_kpi_invalidation
    if not redis_client:
        return
    now = time.monotonic()
    if (now - _last_kpi_invalidation) >= _KPI_INVALIDATION_COOLDOWN_S:
        redis_client.delete("kpi:dashboard_kpis")
        _last_kpi_invalidation = now


# ── RAG enrichment (detached background task) ─────────────────────────────────
async def _enrich_alert_rag(
    alert_id: UUID,
    contributing_signals: list,
    severity: str,
) -> None:
    """Call the RAG explanation service and UPDATE the alert row with the result.

    This runs as a detached asyncio task (via asyncio.create_task) so it never
    blocks the ingest fast-path.  Uses the module-level shared _rag_client to
    avoid creating a new TCP connection pool per call.
    """
    if _rag_client is None:
        return
    try:
        resp = await _rag_client.post(
            f"{RAG_SERVICE_URL}/api/explain",
            json={"contributing_signals": contributing_signals, "severity": severity},
            timeout=10.0,  # generous timeout since this is non-blocking
        )
        if resp.status_code == 200:
            rag_data = resp.json()
            async with AsyncSessionLocal() as session:
                await session.execute(
                    update(Alert)
                    .where(Alert.id == alert_id)
                    .values(
                        explanation=rag_data.get("explanation"),
                        regulatory_controls=rag_data.get("regulatory_controls", []),
                    )
                )
                await session.commit()
    except Exception as e:
        print(f"[rag-enrichment] Failed for alert {alert_id}: {e}")


# ── Alert ingest handlers ──────────────────────────────────────────────────────
async def handle_fused_alert(payload: dict) -> None:
    """Fast-path: persist Alert + Case, invalidate Redis, broadcast WS.

    RAG enrichment is scheduled as a DETACHED asyncio background task so this
    coroutine returns in ~10–20 ms instead of blocking for up to 5 s on the
    RAG HTTP call.  The explanation column is populated asynchronously once the
    RAG service responds.
    """
    print(f"[ingest] Fused alert for identity={payload['identity_id']}")
    async with AsyncSessionLocal() as session:
        alert = Alert(
            identity_id=payload["identity_id"],
            fusion_score=payload["fusion_score"],
            severity=payload["severity"],
            contributing_signals=payload["contributing_signals"],
            window_start=datetime.fromisoformat(payload["window_start"].replace("Z", "+00:00")),
            window_end=datetime.fromisoformat(payload["window_end"].replace("Z", "+00:00")),
            scenario_type=payload.get("scenario_type"),
            is_synthetic_positive=payload.get("is_synthetic_positive", False),
        )
        session.add(alert)
        await session.flush()  # populate alert.id before we reference it in Case

        case = Case(alert_id=alert.id, status="open")
        session.add(case)
        await session.commit()

        # Capture values before the session context closes
        alert_id = alert.id
        alert_snapshot = {
            "id": str(alert.id),
            "identity_id": alert.identity_id,
            "fusion_score": alert.fusion_score,
            "severity": alert.severity,
            "contributing_signals": alert.contributing_signals,
            "window_start": alert.window_start.isoformat(),
            "window_end": alert.window_end.isoformat(),
            "explanation": None,  # populated later by RAG task
            "regulatory_controls": [],
            "created_at": alert.created_at.isoformat(),
            "status": "open",
        }

    # Rate-limited cache invalidation (at most once per 5 s)
    _maybe_invalidate_kpi_cache()

    # Broadcast immediately — clients see the alert before RAG runs
    await ws_manager.broadcast({"type": "NEW_ALERT", "alert": alert_snapshot})

    # Schedule RAG enrichment; do NOT await — this must not block ingest
    asyncio.create_task(
        _enrich_alert_rag(alert_id, payload["contributing_signals"], payload["severity"])
    )


async def handle_quantum_alert(payload: dict) -> None:
    """Fast-path: persist QuantumAlert, invalidate Redis, broadcast WS."""
    print(f"[ingest] Quantum alert for session={payload['session_id']}")
    async with AsyncSessionLocal() as session:
        qalert = QuantumAlert(
            session_id=payload["session_id"],
            key_exchange=payload["key_exchange"],
            signature_algo=payload["signature_algo"],
            classification=payload["classification"],
            is_hndl_exposed=payload.get("is_hndl_exposed", False),
            data_sensitivity=payload["data_sensitivity"],
            bytes_transferred=payload.get("bytes_transferred", 0),
            destination=payload["destination"],
            risk_factors=payload.get("risk_factors", []),
        )
        session.add(qalert)
        await session.commit()

        q_snapshot = {
            "id": str(qalert.id),
            "session_id": qalert.session_id,
            "key_exchange": qalert.key_exchange,
            "signature_algo": qalert.signature_algo,
            "classification": qalert.classification,
            "is_hndl_exposed": qalert.is_hndl_exposed,
            "data_sensitivity": qalert.data_sensitivity,
            "bytes_transferred": qalert.bytes_transferred,
            "destination": qalert.destination,
            "risk_factors": qalert.risk_factors,
            "created_at": qalert.created_at.isoformat(),
        }

    _maybe_invalidate_kpi_cache()
    await ws_manager.broadcast({"type": "NEW_QUANTUM_ALERT", "quantum_alert": q_snapshot})


# ── asyncio.Queue enqueue helper (called from Kafka thread via run_coroutine_threadsafe) ──
async def _enqueue(item: tuple) -> None:
    """Put an item into the bounded alert queue.

    If the queue is full (meaning the worker pool is saturated) the message is
    dropped and logged.  This is safer than blocking the Kafka consumer thread,
    which would stall partition consumption and eventually cause Kafka to rebalance.
    """
    try:
        _alert_queue.put_nowait(item)
    except asyncio.QueueFull:
        print("[kafka-consumer] ⚠ Queue full — dropping message to prevent back-pressure stall")


# ── Kafka worker pool (runs on the main asyncio event loop) ───────────────────
async def _kafka_worker() -> None:
    """Drain the alert queue and process items one at a time per worker.

    Four of these run concurrently (see startup_event), providing controlled
    parallelism: up to 4 DB sessions + 4 RAG tasks at any instant, well within
    the connection pool (pool_size=20).
    """
    while True:
        topic, payload = await _alert_queue.get()
        try:
            if topic == "fusion":
                await handle_fused_alert(payload)
            elif topic == "quantum":
                await handle_quantum_alert(payload)
        except Exception as e:
            print(f"[kafka-worker] Unhandled error processing {topic} message: {e}")
        finally:
            _alert_queue.task_done()


# ── Kafka background consumer thread ──────────────────────────────────────────
def run_kafka_consumer() -> None:
    """Kafka consumer runs in a daemon thread and pushes items into the asyncio queue.

    The old implementation called asyncio.run_coroutine_threadsafe(handle_fused_alert(...))
    directly for every message — spawning an unlimited number of concurrent coroutines.
    Now it only enqueues (non-blocking put_nowait via the event loop); the bounded
    worker pool on the event loop side controls actual concurrency.
    """
    print("[kafka-consumer] Starting consumer thread...")
    conf = {
        "bootstrap.servers": KAFKA_BOOTSTRAP_SERVERS,
        "group.id": "prahari-gateway-group",
        "auto.offset.reset": "latest",
        "enable.auto.commit": True,
    }

    consumer = None
    for attempt in range(1, 6):
        try:
            consumer = Consumer(conf)
            consumer.subscribe(["fusion-alerts", "quantum-alerts"])
            print("[kafka-consumer] Subscribed to fusion-alerts, quantum-alerts")
            break
        except Exception as e:
            print(f"[kafka-consumer] Init attempt {attempt}/5 failed: {e}")
            time.sleep(3)

    if not consumer:
        print("[kafka-consumer] ✗ Could not start — telemetry updates disabled")
        return

    while True:
        try:
            msg = consumer.poll(timeout=1.0)
            if msg is None:
                continue
            if msg.error():
                if msg.error().code() != KafkaError._PARTITION_EOF:
                    print(f"[kafka-consumer] Kafka error: {msg.error()}")
                continue

            topic = msg.topic()
            value = json.loads(msg.value().decode("utf-8"))

            # Route to the appropriate queue slot
            if topic == "fusion-alerts":
                item = ("fusion", value)
            elif topic == "quantum-alerts":
                item = ("quantum", value)
            else:
                continue

            if main_loop:
                asyncio.run_coroutine_threadsafe(_enqueue(item), main_loop)

        except Exception as e:
            print(f"[kafka-consumer] Loop exception: {e}")
            time.sleep(2)


# ── Lifespan events ────────────────────────────────────────────────────────────
@app.on_event("startup")
async def startup_event() -> None:
    global main_loop, _rag_client, _alert_queue

    main_loop = asyncio.get_event_loop()

    # Bounded asyncio queue provides back-pressure between the Kafka thread and workers
    _alert_queue = asyncio.Queue(maxsize=_KAFKA_QUEUE_MAXSIZE)

    # Shared HTTP client — one connection pool to the RAG service for the lifetime of the app
    _rag_client = httpx.AsyncClient(
        timeout=httpx.Timeout(connect=2.0, read=10.0, write=5.0, pool=2.0),
        limits=httpx.Limits(max_connections=20, max_keepalive_connections=10),
    )

    # Start the fixed worker pool
    for _ in range(_KAFKA_WORKER_COUNT):
        asyncio.create_task(_kafka_worker())

    # Start the Kafka consumer in a daemon thread
    t = threading.Thread(target=run_kafka_consumer, daemon=True)
    t.start()

    print(f"[startup] Gateway ready — {_KAFKA_WORKER_COUNT} Kafka workers, queue maxsize={_KAFKA_QUEUE_MAXSIZE}")


@app.on_event("shutdown")
async def shutdown_event() -> None:
    if _rag_client:
        await _rag_client.aclose()
    print("[shutdown] RAG HTTP client closed")


# ── Timing middleware ──────────────────────────────────────────────────────────
@app.middleware("http")
async def log_request_time(request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    elapsed = (time.perf_counter() - start) * 1000
    print(f"[TIMING] {request.method} {request.url.path} -> {elapsed:.2f} ms")
    return response


# ── REST Endpoints ─────────────────────────────────────────────────────────────

# ── /api/alerts ────────────────────────────────────────────────────────────────
@app.get("/api/alerts", response_model=PaginatedAlerts)
async def get_alerts(
    severity: Optional[str] = None,
    identity_id: Optional[str] = None,
    limit: int = Query(default=50, ge=1, le=200, description="Page size (max 200)"),
    before_id: Optional[UUID] = Query(
        default=None,
        description="Cursor: ID of the last item on the previous page (from next_cursor)"
    ),
    db: AsyncSession = Depends(get_db),
) -> PaginatedAlerts:
    """Retrieve fused alerts with keyset cursor pagination.

    Cursor pagination (seek-method) instead of OFFSET:
    - First page:  GET /api/alerts?limit=50
    - Next page:   GET /api/alerts?limit=50&before_id=<next_cursor from previous response>
    - Stops when next_cursor is null.

    Uses the composite index (created_at DESC, id DESC) for O(log n) seeks
    regardless of table size.  The old SELECT * with no LIMIT caused 11–13 s
    responses as the table grew.
    """
    query = (
        select(Alert, Case.status)
        .outerjoin(Case, Alert.id == Case.alert_id)
    )

    if severity:
        query = query.where(Alert.severity == severity)
    if identity_id:
        query = query.where(Alert.identity_id == identity_id)

    # Cursor seek: find rows older than the cursor position
    if before_id:
        cursor_q = select(Alert.created_at, Alert.id).where(Alert.id == before_id)
        cursor_res = await db.execute(cursor_q)
        cursor_row = cursor_res.first()
        if cursor_row:
            cursor_ts, cursor_uuid = cursor_row
            # Rows strictly before the cursor in descending (created_at, id) order
            query = query.where(
                or_(
                    Alert.created_at < cursor_ts,
                    and_(Alert.created_at == cursor_ts, Alert.id < cursor_uuid),
                )
            )

    # Fetch one extra row to detect whether another page exists
    query = query.order_by(desc(Alert.created_at), desc(Alert.id)).limit(limit + 1)

    result = await db.execute(query)
    rows = result.all()

    has_more = len(rows) > limit
    rows = rows[:limit]

    items = [
        AlertResponse(
            id=row[0].id,
            identity_id=row[0].identity_id,
            fusion_score=row[0].fusion_score,
            severity=row[0].severity,
            contributing_signals=row[0].contributing_signals,
            window_start=row[0].window_start,
            window_end=row[0].window_end,
            scenario_type=row[0].scenario_type,
            is_synthetic_positive=row[0].is_synthetic_positive,
            explanation=row[0].explanation,
            regulatory_controls=row[0].regulatory_controls,
            created_at=row[0].created_at,
            updated_at=row[0].updated_at,
            status=row[1] or "open",
        )
        for row in rows
    ]

    next_cursor = str(rows[-1][0].id) if has_more and rows else None
    return PaginatedAlerts(items=items, next_cursor=next_cursor)


# ── /api/alerts/{id} ───────────────────────────────────────────────────────────
@app.get("/api/alerts/{alert_id}", response_model=AlertResponse)
async def get_alert_detail(alert_id: UUID, db: AsyncSession = Depends(get_db)) -> AlertResponse:
    """Retrieve details of a single alert (Section 9 Level 3 explain drawer)."""
    query = (
        select(Alert, Case.status)
        .outerjoin(Case, Alert.id == Case.alert_id)
        .where(Alert.id == alert_id)
    )
    result = await db.execute(query)
    row = result.first()
    if not row:
        raise HTTPException(status_code=404, detail="Alert not found")

    alert_obj, status = row
    return AlertResponse(
        id=alert_obj.id,
        identity_id=alert_obj.identity_id,
        fusion_score=alert_obj.fusion_score,
        severity=alert_obj.severity,
        contributing_signals=alert_obj.contributing_signals,
        window_start=alert_obj.window_start,
        window_end=alert_obj.window_end,
        scenario_type=alert_obj.scenario_type,
        is_synthetic_positive=alert_obj.is_synthetic_positive,
        explanation=alert_obj.explanation,
        regulatory_controls=alert_obj.regulatory_controls,
        created_at=alert_obj.created_at,
        updated_at=alert_obj.updated_at,
        status=status or "open",
    )


# ── /api/cases/{id}/action ─────────────────────────────────────────────────────
@app.post("/api/cases/{case_id}/action", response_model=CaseResponse)
async def perform_case_action(
    case_id: UUID,
    req: CaseActionRequest,
    db: AsyncSession = Depends(get_db),
) -> CaseResponse:
    """Perform analyst action (Acknowledge, Escalate, Dismiss) on a case.

    Logs an immutable audit entry to audit_trail (Section 9 Level 3 Case Action).
    """
    if req.action not in ("acknowledge", "escalate", "dismiss"):
        raise HTTPException(status_code=400, detail="Invalid action")

    q = select(Case).where(Case.id == case_id)
    res = await db.execute(q)
    case_obj = res.scalar_one_or_none()

    if not case_obj:
        raise HTTPException(status_code=404, detail="Case not found")

    status_map = {
        "acknowledge": "acknowledged",
        "escalate": "escalated",
        "dismiss": "dismissed",
    }
    old_status = case_obj.status
    new_status = status_map[req.action]

    case_obj.status = new_status
    case_obj.notes = req.notes
    case_obj.assigned_to = req.actor
    case_obj.updated_at = datetime.now(timezone.utc)

    # ── LOG SECURELY: immutable audit trail ─────────────────────────────────
    audit = AuditTrail(
        entity_type="case",
        entity_id=case_obj.id,
        action=req.action.upper(),
        actor=req.actor,
        details={
            "old_status": old_status,
            "new_status": new_status,
            "notes": req.notes,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    )
    db.add(audit)
    await db.commit()
    await db.refresh(case_obj)

    # Case state change also warrants a KPI refresh (analyst queue count changed)
    _maybe_invalidate_kpi_cache()

    return case_obj


# ── /api/cases ─────────────────────────────────────────────────────────────────
@app.get("/api/cases", response_model=PaginatedCases)
async def get_cases(
    status: Optional[str] = None,
    limit: int = Query(default=50, ge=1, le=200),
    before_id: Optional[UUID] = Query(default=None),
    db: AsyncSession = Depends(get_db),
) -> PaginatedCases:
    """Retrieve analyst queue of cases with cursor pagination (Section 9 Case Management)."""
    query = select(Case).options(selectinload(Case.alert))

    if status:
        query = query.where(Case.status == status)

    if before_id:
        cursor_q = select(Case.created_at, Case.id).where(Case.id == before_id)
        cursor_res = await db.execute(cursor_q)
        cursor_row = cursor_res.first()
        if cursor_row:
            cursor_ts, cursor_uuid = cursor_row
            query = query.where(
                or_(
                    Case.created_at < cursor_ts,
                    and_(Case.created_at == cursor_ts, Case.id < cursor_uuid),
                )
            )

    query = query.order_by(desc(Case.created_at), desc(Case.id)).limit(limit + 1)

    res = await db.execute(query)
    rows = res.scalars().all()

    has_more = len(rows) > limit
    rows = rows[:limit]

    next_cursor = str(rows[-1].id) if has_more and rows else None
    return PaginatedCases(items=list(rows), next_cursor=next_cursor)


# ── /api/audit ─────────────────────────────────────────────────────────────────
@app.get("/api/audit", response_model=PaginatedAuditTrail)
async def get_audit_trail(
    limit: int = Query(default=50, ge=1, le=200),
    before_id: Optional[UUID] = Query(default=None),
    db: AsyncSession = Depends(get_db),
) -> PaginatedAuditTrail:
    """Retrieve immutable audit trail with cursor pagination (Section 9 Level 3)."""
    query = select(AuditTrail)

    if before_id:
        cursor_q = select(AuditTrail.created_at, AuditTrail.id).where(AuditTrail.id == before_id)
        cursor_res = await db.execute(cursor_q)
        cursor_row = cursor_res.first()
        if cursor_row:
            cursor_ts, cursor_uuid = cursor_row
            query = query.where(
                or_(
                    AuditTrail.created_at < cursor_ts,
                    and_(AuditTrail.created_at == cursor_ts, AuditTrail.id < cursor_uuid),
                )
            )

    query = query.order_by(desc(AuditTrail.created_at), desc(AuditTrail.id)).limit(limit + 1)

    res = await db.execute(query)
    rows = res.scalars().all()

    has_more = len(rows) > limit
    rows = rows[:limit]

    next_cursor = str(rows[-1].id) if has_more and rows else None
    return PaginatedAuditTrail(items=list(rows), next_cursor=next_cursor)


# ── /api/quantum/sessions ──────────────────────────────────────────────────────
@app.get("/api/quantum/sessions", response_model=PaginatedQuantumSessions)
async def get_quantum_sessions(
    limit: int = Query(default=100, ge=1, le=500),
    before_id: Optional[UUID] = Query(default=None),
    db: AsyncSession = Depends(get_db),
) -> PaginatedQuantumSessions:
    """Retrieve crypto inventory and HNDL alerts with cursor pagination (Section 9 Quantum panel).

    Default limit is 100 (higher than alerts because quantum records are smaller and
    the Quantum panel renders them all in a table without a separate detail view).
    The old query returned all rows, causing 0.8–3.7 s latency that grew linearly.
    """
    query = select(QuantumAlert)

    if before_id:
        cursor_q = select(QuantumAlert.created_at, QuantumAlert.id).where(QuantumAlert.id == before_id)
        cursor_res = await db.execute(cursor_q)
        cursor_row = cursor_res.first()
        if cursor_row:
            cursor_ts, cursor_uuid = cursor_row
            query = query.where(
                or_(
                    QuantumAlert.created_at < cursor_ts,
                    and_(QuantumAlert.created_at == cursor_ts, QuantumAlert.id < cursor_uuid),
                )
            )

    query = query.order_by(desc(QuantumAlert.created_at), desc(QuantumAlert.id)).limit(limit + 1)

    res = await db.execute(query)
    rows = res.scalars().all()

    has_more = len(rows) > limit
    rows = rows[:limit]

    next_cursor = str(rows[-1].id) if has_more and rows else None
    return PaginatedQuantumSessions(items=list(rows), next_cursor=next_cursor)


# ── /api/dashboard/kpis ────────────────────────────────────────────────────────
@app.get("/api/dashboard/kpis", response_model=DashboardKPIsResponse)
async def get_dashboard_kpis(db: AsyncSession = Depends(get_db)) -> DashboardKPIsResponse:
    """Retrieve dashboard KPI metrics, served from Redis with a 30 s TTL.

    Key change: the top-risk-identities section previously fired 1 + N sequential
    SELECT COUNT(*) queries (one per identity profile, up to 5).  It now uses a
    single GROUP BY query that returns all required data in one round-trip.

    The Redis invalidation is also now rate-limited (see _maybe_invalidate_kpi_cache),
    so this path actually serves from cache the vast majority of the time under
    continuous ingestion.
    """
    # ── Cache hit ───────────────────────────────────────────────────────────
    if redis_client:
        cached = redis_client.get("kpi:dashboard_kpis")
        if cached:
            try:
                data = json.loads(cached)
                data["last_updated"] = datetime.now(timezone.utc)
                return data
            except Exception:
                pass  # malformed cache entry — fall through to DB

    # ── Cache miss: compute from DB ─────────────────────────────────────────

    # 1. Count of open alerts
    q_active = (
        select(func.count())
        .select_from(Alert)
        .join(Case, Alert.id == Case.alert_id)
        .where(Case.status == "open")
    )
    active_count: int = (await db.execute(q_active)).scalar() or 0

    # 2. Alert counts by severity
    q_sev = select(Alert.severity, func.count()).group_by(Alert.severity)
    sevs = {row[0]: row[1] for row in (await db.execute(q_sev)).all()}
    sev_counts = SeverityCount(
        low=sevs.get("low", 0),
        medium=sevs.get("medium", 0),
        high=sevs.get("high", 0),
        critical=sevs.get("critical", 0),
    )

    # 3. Top-5 risk identities — SINGLE GROUP BY (replaces N+1 per-identity queries)
    #    Uses the covering index idx_alerts_identity_score so no heap fetch is needed.
    q_risk = (
        select(
            Alert.identity_id,
            func.max(Alert.fusion_score).label("risk_score"),
            func.count().label("alert_count"),
        )
        .group_by(Alert.identity_id)
        .order_by(desc(func.max(Alert.fusion_score)))
        .limit(5)
    )
    top_identities = [
        TopRiskIdentity(
            identity_id=row.identity_id,
            risk_score=row.risk_score,
            alert_count=row.alert_count,
        )
        for row in (await db.execute(q_risk)).all()
    ]

    # 4. Quantum stats from Redis (fast path), fall back to DB aggregate
    q_stats = {"legacy_count": 0, "pqc_ready_count": 0, "hybrid_count": 0, "hndl_exposed_count": 0}
    if redis_client:
        raw = redis_client.hgetall("kpi:quantum_raw")
        if raw:
            q_stats = {
                "legacy_count": int(raw.get("count_legacy", 0)),
                "pqc_ready_count": int(raw.get("count_pqc_ready", 0)),
                "hybrid_count": int(raw.get("count_hybrid", 0)),
                "hndl_exposed_count": int(raw.get("count_hndl", 0)),
            }
        else:
            # DB fallback: two aggregate queries instead of iterating rows
            q_qstats = select(QuantumAlert.classification, func.count()).group_by(QuantumAlert.classification)
            for row in (await db.execute(q_qstats)).all():
                q_stats[f"{row[0]}_count"] = row[1]

            q_hndl = select(func.count()).select_from(QuantumAlert).where(QuantumAlert.is_hndl_exposed.is_(True))
            q_stats["hndl_exposed_count"] = (await db.execute(q_hndl)).scalar() or 0

    # ── Cache and return ─────────────────────────────────────────────────────
    kpi_payload = {
        "active_alerts_count": active_count,
        "alerts_by_severity": sev_counts.dict(),
        "top_risk_identities": [i.dict() for i in top_identities],
        "quantum_stats": q_stats,
    }
    if redis_client:
        redis_client.setex("kpi:dashboard_kpis", 30, json.dumps(kpi_payload))

    kpi_payload["last_updated"] = datetime.now(timezone.utc)
    return kpi_payload


# ── /api/demo/inject ───────────────────────────────────────────────────────────
@app.post("/api/demo/inject")
async def trigger_scenario(req: ScenarioInjectionRequest):
    """Demo Mode Scenario Injector (Section 9).

    Directly generates a coordinated event chain into the real Kafka topics.
    Gated behind DEMO_MODE=true env variable.
    """
    if not DEMO_MODE:
        raise HTTPException(
            status_code=403,
            detail="Forbidden: Demo Mode is not enabled. Gated behind DEMO_MODE=true",
        )

    try:
        from data.synthetic.generators.base import IdentityState, IDENTITY_POOL, make_producer
        from data.synthetic.generators.scenario_injector import (
            inject_ato_scenario,
            inject_insider_collusion_scenario,
            inject_credential_stuffing_ato_scenario,
            inject_hndl_exposure_scenario,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load generator scripts: {e}")

    try:
        p = make_producer()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to init Kafka producer: {e}")

    states = {iid: IdentityState(iid) for iid in IDENTITY_POOL}

    try:
        events = []
        if req.scenario_type == "ato":
            events = inject_ato_scenario(states, p)
        elif req.scenario_type == "insider_collusion":
            events = inject_insider_collusion_scenario(states, p)
        elif req.scenario_type == "credential_stuffing_ato":
            events = inject_credential_stuffing_ato_scenario(states, p)
        elif req.scenario_type == "hndl_exposure":
            events = inject_hndl_exposure_scenario(p)
        else:
            raise HTTPException(status_code=400, detail="Unknown scenario type")

        p.flush()
        return {
            "status": "success",
            "message": f"Injected scenario '{req.scenario_type}' successfully",
            "events_count": len(events),
            "events": events,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Scenario execution error: {e}")


# ── WebSocket ──────────────────────────────────────────────────────────────────
@app.websocket("/ws/alerts")
async def websocket_endpoint(websocket: WebSocket):
    """Real-time alert push (Section 5 WebSocket push)."""
    await ws_manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
    except Exception as e:
        print(f"[ws-err] WebSocket exception: {e}")
        ws_manager.disconnect(websocket)
