from pydantic import BaseModel, Field
from datetime import datetime
from typing import List, Optional, Dict, Any
from uuid import UUID


# ── Alert Schemas ──────────────────────────────────────────────────────────────
class AlertBase(BaseModel):
    identity_id: str
    fusion_score: float
    severity: str
    contributing_signals: List[str]
    window_start: datetime
    window_end: datetime
    scenario_type: Optional[str] = None
    is_synthetic_positive: bool = False


class AlertCreate(AlertBase):
    id: Optional[UUID] = None
    explanation: Optional[str] = None
    regulatory_controls: Optional[List[Dict[str, Any]]] = None


class AlertResponse(AlertBase):
    id: UUID
    explanation: Optional[str] = None
    regulatory_controls: Optional[List[Dict[str, Any]]] = None
    created_at: datetime
    updated_at: datetime
    status: Optional[str] = "open"  # Joined from Case

    class Config:
        from_attributes = True


class PaginatedAlerts(BaseModel):
    """Paginated wrapper for /api/alerts.

    `next_cursor` is the `id` of the last item in `items`.  Pass it as
    `before_id` on the next request to get the following page.  When
    `next_cursor` is null there are no more pages.
    """
    items: List[AlertResponse]
    next_cursor: Optional[str] = None


# ── Case Schemas ───────────────────────────────────────────────────────────────
class CaseActionRequest(BaseModel):
    action: str = Field(..., description="Action to perform: acknowledge, escalate, dismiss")
    actor: str = Field("analyst", description="Username or role of the analyst")
    notes: Optional[str] = Field(None, description="Optional notes explaining the action")


class CaseResponse(BaseModel):
    id: UUID
    alert_id: UUID
    status: str
    assigned_to: Optional[str] = None
    notes: Optional[str] = None
    alert: Optional[AlertBase] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PaginatedCases(BaseModel):
    """Paginated wrapper for /api/cases."""
    items: List[CaseResponse]
    next_cursor: Optional[str] = None


# ── Audit Trail Schemas ────────────────────────────────────────────────────────
class AuditTrailResponse(BaseModel):
    id: UUID
    entity_type: str
    entity_id: UUID
    action: str
    actor: str
    details: Dict[str, Any]
    created_at: datetime

    class Config:
        from_attributes = True


class PaginatedAuditTrail(BaseModel):
    """Paginated wrapper for /api/audit."""
    items: List[AuditTrailResponse]
    next_cursor: Optional[str] = None


# ── Quantum / TLS Schemas ──────────────────────────────────────────────────────
class QuantumAlertResponse(BaseModel):
    id: UUID
    session_id: str
    key_exchange: str
    signature_algo: str
    classification: str
    is_hndl_exposed: bool
    data_sensitivity: str
    bytes_transferred: int
    destination: str
    risk_factors: List[str]
    created_at: datetime

    class Config:
        from_attributes = True


class QuantumStatsResponse(BaseModel):
    legacy_count: int
    pqc_ready_count: int
    hybrid_count: int
    hndl_exposed_count: int


class PaginatedQuantumSessions(BaseModel):
    """Paginated wrapper for /api/quantum/sessions."""
    items: List[QuantumAlertResponse]
    next_cursor: Optional[str] = None


# ── Dashboard KPI Schemas ──────────────────────────────────────────────────────
class SeverityCount(BaseModel):
    low: int = 0
    medium: int = 0
    high: int = 0
    critical: int = 0


class TopRiskIdentity(BaseModel):
    identity_id: str
    risk_score: float
    alert_count: int


class DashboardKPIsResponse(BaseModel):
    active_alerts_count: int
    alerts_by_severity: SeverityCount
    top_risk_identities: List[TopRiskIdentity]
    quantum_stats: QuantumStatsResponse
    last_updated: datetime


# ── Scenario Injection Schema ──────────────────────────────────────────────────
class ScenarioInjectionRequest(BaseModel):
    scenario_type: str = Field(
        ...,
        description="Type of scenario to run: ato, insider_collusion, credential_stuffing_ato, hndl_exposure"
    )
