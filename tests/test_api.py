import pytest
import pytest_asyncio
from uuid import uuid4
from datetime import datetime, timezone
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from services.gateway.main import app, get_db
from services.gateway.database import Base
from services.gateway.models import Alert, Case, AuditTrail, QuantumAlert, IdentityProfile

# ── Use in-memory SQLite for testing ──
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

engine = create_async_engine(TEST_DATABASE_URL, echo=False)
TestingSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)

@pytest_asyncio.fixture(scope="function", autouse=True)
async def setup_test_db():
    """Create a fresh database structure in-memory before each test."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

async def override_get_db():
    """Dependency override to yield testing session."""
    async with TestingSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

app.dependency_overrides[get_db] = override_get_db


@pytest.mark.asyncio
async def test_gateway_endpoints():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        # ── Test 1: Empty alerts list ──
        resp = await client.get("/api/alerts")
        assert resp.status_code == 200
        assert resp.json() == []

        # Seed an alert via the testing database session directly
        async with TestingSessionLocal() as session:
            alert = Alert(
                id=uuid4(),
                identity_id="ID-00123",
                fusion_score=0.92,
                severity="critical",
                contributing_signals=["impossible_travel", "new_device"],
                window_start=datetime.now(timezone.utc),
                window_end=datetime.now(timezone.utc)
            )
            session.add(alert)
            await session.flush()
            
            case = Case(alert_id=alert.id, status="open")
            session.add(case)
            
            qalert = QuantumAlert(
                session_id="sess-q-test",
                key_exchange="ECDHE-P256",
                signature_algo="ECDSA",
                classification="legacy",
                is_hndl_exposed=True,
                data_sensitivity="kyc",
                bytes_transferred=2048,
                destination="external"
            )
            session.add(qalert)
            
            profile = IdentityProfile(
                identity_id="ID-00123",
                risk_score=0.92,
                avg_txn_amount=6200.0,
                txn_count=4
            )
            session.add(profile)
            
            await session.commit()
            alert_id = alert.id
            case_id = case.id

        # ── Test 2: Fetch populated alerts list ──
        resp = await client.get("/api/alerts")
        assert resp.status_code == 200
        alerts = resp.json()
        assert len(alerts) == 1
        assert alerts[0]["identity_id"] == "ID-00123"
        assert alerts[0]["severity"] == "critical"
        assert alerts[0]["status"] == "open"

        # ── Test 3: Fetch detail for single alert ──
        resp = await client.get(f"/api/alerts/{alert_id}")
        assert resp.status_code == 200
        assert resp.json()["identity_id"] == "ID-00123"

        # ── Test 4: Perform case action ──
        action_payload = {
            "action": "acknowledge",
            "actor": "analyst_vicky",
            "notes": "Acknowledged critical alert. Starting investigation."
        }
        resp = await client.post(f"/api/cases/{case_id}/action", json=action_payload)
        assert resp.status_code == 200
        case_data = resp.json()
        assert case_data["status"] == "acknowledged"
        assert case_data["assigned_to"] == "analyst_vicky"

        # ── Test 5: Verify Audit log contains action ──
        resp = await client.get("/api/audit")
        assert resp.status_code == 200
        audit_trail = resp.json()
        assert len(audit_trail) == 1
        assert audit_trail[0]["action"] == "ACKNOWLEDGE"
        assert audit_trail[0]["actor"] == "analyst_vicky"

        # ── Test 6: Fetch quantum inventory sessions ──
        resp = await client.get("/api/quantum/sessions")
        assert resp.status_code == 200
        q_sessions = resp.json()
        assert len(q_sessions) == 1
        assert q_sessions[0]["session_id"] == "sess-q-test"
        assert q_sessions[0]["classification"] == "legacy"
        assert q_sessions[0]["is_hndl_exposed"] is True

        # ── Test 7: Fetch dashboard KPIs ──
        resp = await client.get("/api/dashboard/kpis")
        assert resp.status_code == 200
        kpis = resp.json()
        assert "active_alerts_count" in kpis
        assert "alerts_by_severity" in kpis
        assert "top_risk_identities" in kpis
