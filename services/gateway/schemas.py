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

    class Config:
        from_attributes = True


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


# ── Alert Workflow Action Schema ───────────────────────────────────────────────
class AlertActionRequest(BaseModel):
    """Request body for POST /api/alerts/{id}/escalate and /api/alerts/{id}/dismiss.

    The action itself is expressed in the URL path, so only the actor name and
    optional notes are needed here.
    """
    actor: str = Field("Tier 1 Analyst", description="Username or role performing the action")
    notes: Optional[str] = Field(None, description="Optional notes, e.g. dismiss reason")


# ── Scenario Injection Schema ──────────────────────────────────────────────────
class ScenarioInjectionRequest(BaseModel):
    scenario_type: str = Field(
        ...,
        description="Type of scenario to run: ato, insider_collusion, credential_stuffing_ato, hndl_exposure"
    )

# ── Identity Profile Schemas ───────────────────────────────────────────────────
class IdentityProfileBase(BaseModel):
    identity_id: str
    customer_name: Optional[str] = None
    customer_type: Optional[str] = None
    customer_segment: Optional[str] = None
    kyc_status: Optional[str] = None
    account_age_days: int = 0
    customer_since: Optional[str] = None
    primary_branch: Optional[str] = None
    region: Optional[str] = None
    risk_tier: Optional[str] = None
    current_balance: float = 0.0
    average_daily_volume: float = 0.0
    monthly_txn_count: int = 0
    dormant_account_flag: bool = False
    vip_flag: bool = False
    previous_alerts_count: int = 0
    previous_cases_count: int = 0
    fraud_history_count: int = 0
    typical_login_hours: List[Any] = Field(default_factory=list)
    typical_countries: List[Any] = Field(default_factory=list)
    typical_channels: List[Any] = Field(default_factory=list)
    preferred_payment_method: Optional[str] = None
    device_trust_score: float = 0.0
    known_devices: List[Any] = Field(default_factory=list)
    known_beneficiaries: List[Any] = Field(default_factory=list)
    known_ips: List[Any] = Field(default_factory=list)
    avg_txn_amount: float = 0.0
    txn_count: int = 0
    login_time_distribution: Dict[str, Any] = Field(default_factory=dict)
    risk_score: float = 0.0
    last_seen_geo: Dict[str, Any] = Field(default_factory=dict)

class IdentityProfileResponse(IdentityProfileBase):
    last_updated: datetime

    class Config:
        from_attributes = True

class IdentityProfileSyncRequest(IdentityProfileBase):
    pass


# ── Alert Timeline Schemas ─────────────────────────────────────────────────────
class AlertTimelineEvent(BaseModel):
    timestamp: str
    type: str
    icon: str
    severity: str
    title: str
    description: str
    entity_id: Optional[str] = None
    entity_type: Optional[str] = None


class AlertTimelineResponse(BaseModel):
    alert_id: str
    identity_id: str
    events: List[AlertTimelineEvent]


# ── Investigation Graph Schemas ────────────────────────────────────────────────
class GraphNode(BaseModel):
    id: str
    type: str          # identity | device | ip | beneficiary | transaction | alert | case
    label: str
    sublabel: Optional[str] = None
    risk: str = "low"  # low | medium | high | critical
    data: Dict[str, Any] = Field(default_factory=dict)


class GraphEdge(BaseModel):
    id: str
    source: str
    target: str
    type: str          # uses_device | logged_in_from | transferred_to | added_beneficiary | triggered_alert | case_link | same_ip | same_device
    label: str
    risk: str = "low"  # low | medium | high
    data: Dict[str, Any] = Field(default_factory=dict)


class GraphResponse(BaseModel):
    identity_id: str
    nodes: List[GraphNode]
    edges: List[GraphEdge]
