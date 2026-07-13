import asyncio
import json
import os
import threading
import time
from datetime import datetime, timezone, timedelta
from typing import List, Optional
from uuid import UUID

import httpx
import redis
from confluent_kafka import Consumer, Producer, KafkaError
from fastapi import FastAPI, Depends, HTTPException, WebSocket, WebSocketDisconnect, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select, update, desc, func
from sqlalchemy.ext.asyncio import AsyncSession

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
    ScenarioInjectionRequest
)
from .ws_manager import ws_manager

# ── Lifespan & App Setup ──
app = FastAPI(
    title="PRAHARI Gateway API",
    description="Central gateway routing cybersecurity-telemetry & transaction alerts",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configs
KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9094")
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
DEMO_MODE = os.getenv("DEMO_MODE", "false").lower() == "true"
RAG_SERVICE_URL = os.getenv("RAG_SERVICE_URL", "http://localhost:8082")

# Redis connection
try:
    redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
    redis_client.ping()
except Exception as e:
    print(f"[warning] Redis connection failed in gateway: {e}")
    redis_client = None


# ── Kafka Background Consumer ──
# Consumes fusion-alerts and quantum-alerts, persists to DB, triggers websocket broadcasts
def run_kafka_consumer():
    print("[background-consumer] Starting Kafka consumer thread...")
    conf = {
        "bootstrap.servers": KAFKA_BOOTSTRAP_SERVERS,
        "group.id": "prahari-gateway-group",
        "auto.offset.reset": "latest",
        "enable.auto.commit": True
    }
    
    # Try initializing consumer with retries
    consumer = None
    retries = 5
    while retries > 0:
        try:
            consumer = Consumer(conf)
            consumer.subscribe(["fusion-alerts", "quantum-alerts"])
            print("[background-consumer] Successfully subscribed to fusion-alerts and quantum-alerts")
            break
        except Exception as e:
            print(f"[background-consumer] Failed to init consumer, retrying... ({e})")
            retries -= 1
            time.sleep(3)

    if not consumer:
        print("[background-consumer] Critical: Kafka consumer could not start. Telemetry updates will not work.")
        return

    while True:
        try:
            msg = consumer.poll(timeout=1.0)
            if msg is None:
                continue
            if msg.error():
                if msg.error().code() != KafkaError._PARTITION_EOF:
                    print(f"[background-consumer-err] Kafka error: {msg.error()}")
                continue

            topic = msg.topic()
            value = json.loads(msg.value().decode("utf-8"))

            if topic == "fusion-alerts":
                if main_loop:
                    asyncio.run_coroutine_threadsafe(handle_fused_alert(value), main_loop)
            elif topic == "quantum-alerts":
                if main_loop:
                    asyncio.run_coroutine_threadsafe(handle_quantum_alert(value), main_loop)

        except Exception as e:
            print(f"[background-consumer-err] Loop exception: {e}")
            time.sleep(2)


async def handle_fused_alert(payload: dict):
    """Save alert to PG, create Case, fetch RAG details, broadcast to WebSocket."""
    print(f"[background-consumer] Processing fused alert for {payload['identity_id']}")
    async with AsyncSessionLocal() as session:
        # Create Alert model
        alert = Alert(
            identity_id=payload["identity_id"],
            fusion_score=payload["fusion_score"],
            severity=payload["severity"],
            contributing_signals=payload["contributing_signals"],
            window_start=datetime.fromisoformat(payload["window_start"].replace("Z", "+00:00")),
            window_end=datetime.fromisoformat(payload["window_end"].replace("Z", "+00:00")),
            scenario_type=payload.get("scenario_type"),
            is_synthetic_positive=payload.get("is_synthetic_positive", False)
        )
        
        session.add(alert)
        await session.flush()  # populate ID

        # Create associated Case (Section 9 Level 3 Case Management queue)
        case = Case(alert_id=alert.id, status="open")
        session.add(case)
        await session.commit()

        # Call RAG explanation service asynchronously
        try:
            async with httpx.AsyncClient() as client:
                # Section 7 Contract: fetch explanation
                rag_resp = await client.post(
                    f"{RAG_SERVICE_URL}/api/explain",
                    json={
                        "contributing_signals": alert.contributing_signals,
                        "severity": alert.severity
                    },
                    timeout=5.0
                )
                if rag_resp.status_code == 200:
                    rag_data = rag_resp.json()
                    # Re-bind session and update explanation
                    await session.execute(
                        update(Alert)
                        .where(Alert.id == alert.id)
                        .values(
                            explanation=rag_data.get("explanation"),
                            regulatory_controls=rag_data.get("regulatory_controls", [])
                        )
                    )
                    await session.commit()
                    alert.explanation = rag_data.get("explanation")
                    alert.regulatory_controls = rag_data.get("regulatory_controls", [])
        except Exception as e:
            print(f"[background-consumer] RAG generation failed on ingest: {e}")

        # Invalidate KPIs cache in Redis (Section 5 write-through invalidation)
        if redis_client:
            redis_client.delete("kpi:dashboard_kpis")

        # Broadcast via WebSockets to all dashboard UIs
        alert_dict = {
            "type": "NEW_ALERT",
            "alert": {
                "id": str(alert.id),
                "identity_id": alert.identity_id,
                "fusion_score": alert.fusion_score,
                "severity": alert.severity,
                "contributing_signals": alert.contributing_signals,
                "window_start": alert.window_start.isoformat(),
                "window_end": alert.window_end.isoformat(),
                "explanation": alert.explanation,
                "regulatory_controls": alert.regulatory_controls,
                "created_at": alert.created_at.isoformat(),
                "status": "open"
            }
        }
        await ws_manager.broadcast(alert_dict)


async def handle_quantum_alert(payload: dict):
    """Save quantum/HNDL session alert, broadcast to WebSocket."""
    print(f"[background-consumer] Processing quantum/HNDL alert for session {payload['session_id']}")
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
            risk_factors=payload.get("risk_factors", [])
        )
        session.add(qalert)
        await session.commit()

        # Invalidate dashboard KPIs in Redis (Section 5)
        if redis_client:
            redis_client.delete("kpi:dashboard_kpis")

        await ws_manager.broadcast({
            "type": "NEW_QUANTUM_ALERT",
            "quantum_alert": {
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
                "created_at": qalert.created_at.isoformat()
            }
        })


main_loop = None

@app.on_event("startup")
def startup_event():
    global main_loop
    main_loop = asyncio.get_event_loop()
    # Run consumer in daemon thread so it exits with main thread
    t = threading.Thread(target=run_kafka_consumer, daemon=True)
    t.start()


# ── REST API Endpoints ──

@app.get("/api/alerts", response_model=List[AlertResponse])
async def get_alerts(
    severity: Optional[str] = None,
    identity_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """Retrieve fused alerts with optional filtering (Section 9 Level 2/3)."""
    # Join with cases to get current status
    query = select(Alert, Case.status).outerjoin(Case, Alert.id == Case.alert_id)
    
    if severity:
        query = query.where(Alert.severity == severity)
    if identity_id:
        query = query.where(Alert.identity_id == identity_id)
        
    query = query.order_by(desc(Alert.created_at))
    
    result = await db.execute(query)
    alerts = []
    for row in result.all():
        alert_obj = row[0]
        status = row[1]
        
        # Build response manually
        alerts.append(AlertResponse(
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
            status=status or "open"
        ))
    return alerts


@app.get("/api/alerts/{alert_id}", response_model=AlertResponse)
async def get_alert_detail(alert_id: UUID, db: AsyncSession = Depends(get_db)):
    """Retrieve details of a single alert (Section 9 Level 3 explain drawer)."""
    query = select(Alert, Case.status).outerjoin(Case, Alert.id == Case.alert_id).where(Alert.id == alert_id)
    result = await db.execute(query)
    row = result.first()
    if not row:
        raise HTTPException(status_code=404, detail="Alert not found")
        
    alert_obj = row[0]
    status = row[1]
    
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
        status=status or "open"
    )


@app.post("/api/cases/{case_id}/action", response_model=CaseResponse)
async def perform_case_action(
    case_id: UUID,
    req: CaseActionRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Perform analyst action (Acknowledge, Escalate, Dismiss) on a case.
    Logs an immutable audit entry to audit_trail (Section 9 Level 3 Case Action).
    """
    if req.action not in ["acknowledge", "escalate", "dismiss"]:
        raise HTTPException(status_code=400, detail="Invalid action")

    # Find the case
    q = select(Case).where(Case.id == case_id)
    res = await db.execute(q)
    case_obj = res.scalar_one_or_none()
    
    if not case_obj:
        raise HTTPException(status_code=404, detail="Case not found")

    status_map = {
        "acknowledge": "acknowledged",
        "escalate": "escalated",
        "dismiss": "dismissed"
    }
    
    new_status = status_map[req.action]
    old_status = case_obj.status

    # Update case status
    case_obj.status = new_status
    case_obj.notes = req.notes
    case_obj.assigned_to = req.actor
    case_obj.updated_at = datetime.now(timezone.utc)
    
    # ── LOG SECURELY (Immutable audit trail pattern built from scratch) ──
    audit = AuditTrail(
        entity_type="case",
        entity_id=case_obj.id,
        action=req.action.upper(),
        actor=req.actor,
        details={
            "old_status": old_status,
            "new_status": new_status,
            "notes": req.notes,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    )
    
    db.add(audit)
    await db.commit()
    await db.refresh(case_obj)
    
    # Invalidate KPIs since case counts changed
    if redis_client:
        redis_client.delete("kpi:dashboard_kpis")
        
    return case_obj


@app.get("/api/quantum/sessions", response_model=List[QuantumAlertResponse])
async def get_quantum_sessions(db: AsyncSession = Depends(get_db)):
    """Retrieve crypto inventory and HNDL alerts (Section 9 Quantum panel)."""
    q = select(QuantumAlert).order_by(desc(QuantumAlert.created_at))
    res = await db.execute(q)
    return res.scalars().all()


@app.get("/api/dashboard/kpis", response_model=DashboardKPIsResponse)
async def get_dashboard_kpis(db: AsyncSession = Depends(get_db)):
    """
    Retrieve dashboard KPI metrics.
    Caches results in Redis with 30s TTL to prevent heavy PG queries (Section 5).
    """
    if redis_client:
        cached = redis_client.get("kpi:dashboard_kpis")
        if cached:
            try:
                # Add current timezone-aware timestamp to the response
                data = json.loads(cached)
                data["last_updated"] = datetime.now(timezone.utc)
                return data
            except Exception:
                pass

    # Recompute from DB
    # 1. Active alerts (where case status is open)
    q_active = select(func.count()).select_from(Alert).join(Case, Alert.id == Case.alert_id).where(Case.status == "open")
    res_active = await db.execute(q_active)
    active_count = res_active.scalar() or 0

    # 2. Count by severity
    q_sev = select(Alert.severity, func.count()).group_by(Alert.severity)
    res_sev = await db.execute(q_sev)
    sevs = {row[0]: row[1] for row in res_sev.all()}
    sev_counts = SeverityCount(
        low=sevs.get("low", 0),
        medium=sevs.get("medium", 0),
        high=sevs.get("high", 0),
        critical=sevs.get("critical", 0)
    )

    # 3. Top-10 risk identities (Section 5)
    # Join profiles and select top
    q_risk = select(IdentityProfile).order_by(desc(IdentityProfile.risk_score)).limit(5)
    res_risk = await db.execute(q_risk)
    profiles = res_risk.scalars().all()
    
    top_identities = []
    for p in profiles:
        # get alert counts
        q_cnt = select(func.count()).select_from(Alert).where(Alert.identity_id == p.identity_id)
        res_cnt = await db.execute(q_cnt)
        alert_cnt = res_cnt.scalar() or 0
        top_identities.append(TopRiskIdentity(
            identity_id=p.identity_id,
            risk_score=p.risk_score,
            alert_count=alert_cnt
        ))

    # If profiles are empty (e.g. fresh DB), get top alert generators instead
    if not top_identities:
        q_alt = select(Alert.identity_id, func.max(Alert.fusion_score), func.count()).group_by(Alert.identity_id).order_by(desc(func.max(Alert.fusion_score))).limit(5)
        res_alt = await db.execute(q_alt)
        for row in res_alt.all():
            top_identities.append(TopRiskIdentity(
                identity_id=row[0],
                risk_score=row[1],
                alert_count=row[2]
            ))

    # 4. Quantum counts from Redis
    q_stats = {"legacy_count": 0, "pqc_ready_count": 0, "hybrid_count": 0, "hndl_exposed_count": 0}
    if redis_client:
        raw = redis_client.hgetall("kpi:quantum_raw")
        if raw:
            q_stats = {
                "legacy_count": int(raw.get("count_legacy", 0)),
                "pqc_ready_count": int(raw.get("count_pqc_ready", 0)),
                "hybrid_count": int(raw.get("count_hybrid", 0)),
                "hndl_exposed_count": int(raw.get("count_hndl", 0))
            }
        else:
            # Fall back to DB
            q_qstats = select(QuantumAlert.classification, func.count()).group_by(QuantumAlert.classification)
            res_qstats = await db.execute(q_qstats)
            for row in res_qstats.all():
                q_stats[f"{row[0]}_count"] = row[1]
                
            q_hndl = select(func.count()).select_from(QuantumAlert).where(QuantumAlert.is_hndl_exposed == True)
            res_hndl = await db.execute(q_hndl)
            q_stats["hndl_exposed_count"] = res_hndl.scalar() or 0

    kpi_payload = {
        "active_alerts_count": active_count,
        "alerts_by_severity": sev_counts.dict(),
        "top_risk_identities": [i.dict() for i in top_identities],
        "quantum_stats": q_stats,
    }

    # Save to cache with 30s TTL
    if redis_client:
        redis_client.setex("kpi:dashboard_kpis", 30, json.dumps(kpi_payload))

    kpi_payload["last_updated"] = datetime.now(timezone.utc)
    return kpi_payload


@app.get("/api/cases", response_model=List[CaseResponse])
async def get_cases(status: Optional[str] = None, db: AsyncSession = Depends(get_db)):
    """Retrieve analyst queue of cases (Section 9 Case Management)."""
    from sqlalchemy.orm import selectinload
    q = select(Case).options(selectinload(Case.alert))
    if status:
        q = q.where(Case.status == status)
    q = q.order_by(desc(Case.created_at))
    res = await db.execute(q)
    return res.scalars().all()


@app.get("/api/audit", response_model=List[AuditTrailResponse])
async def get_audit_trail(db: AsyncSession = Depends(get_db)):
    """Retrieve immutable audit trail (Section 9 Level 3 audit log)."""
    q = select(AuditTrail).order_by(desc(AuditTrail.created_at))
    res = await db.execute(q)
    return res.scalars().all()


# ── Scenario Runner (Gated behind DEMO_MODE=true, Section 9) ──
@app.post("/api/demo/inject")
async def trigger_scenario(req: ScenarioInjectionRequest):
    """
    Demo Mode Scenario Injector (Section 9).
    Directly generates and writes a coordinated event chain into the Kafka topics.
    Gated behind DEMO_MODE=true env variable.
    """
    if not DEMO_MODE:
        raise HTTPException(
            status_code=403,
            detail="Forbidden: Demo Mode is not enabled. Gated behind DEMO_MODE=true"
        )

    # Lazily import generator modules to prevent circular dependencies
    try:
        from data.synthetic.generators.base import IdentityState, IDENTITY_POOL, make_producer
        from data.synthetic.generators.scenario_injector import (
            inject_ato_scenario,
            inject_insider_collusion_scenario,
            inject_credential_stuffing_ato_scenario,
            inject_hndl_exposure_scenario
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to load synthetic generator scripts: {e}"
        )

    # Initialize a localized Producer
    try:
        p = make_producer()
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to initialize Kafka producer for demo mode: {e}"
        )

    # Create dummy identity states for all identities so random.choice doesn't throw KeyError
    states = {}
    for iid in IDENTITY_POOL:
        states[iid] = IdentityState(iid)

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
            "events": events
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Scenario execution error: {e}")


# ── WebSockets endpoint (Section 5 dashboard WebSocket push) ──
@app.websocket("/ws/alerts")
async def websocket_endpoint(websocket: WebSocket):
    await ws_manager.connect(websocket)
    try:
        while True:
            # Maintain connection, handle ping/pong implicitly
            await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
    except Exception as e:
        print(f"[ws-err] WebSocket connection exception: {e}")
        ws_manager.disconnect(websocket)
