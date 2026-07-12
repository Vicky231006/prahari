import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Float, Boolean, Integer, DateTime, JSON, ForeignKey, Uuid
from sqlalchemy.orm import relationship
from .database import Base

class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    identity_id = Column(String(64), nullable=False)
    fusion_score = Column(Float, nullable=False)
    severity = Column(String(10), nullable=False)
    contributing_signals = Column(JSON, nullable=False, default=list)
    explanation = Column(String, nullable=True)
    regulatory_controls = Column(JSON, nullable=True, default=list)
    window_start = Column(DateTime(timezone=True), nullable=False)
    window_end = Column(DateTime(timezone=True), nullable=False)
    scenario_type = Column(String(50), nullable=True)
    is_synthetic_positive = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    case = relationship("Case", back_populates="alert", uselist=False, cascade="all, delete-orphan")

class Case(Base):
    __tablename__ = "cases"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    alert_id = Column(Uuid, ForeignKey("alerts.id", ondelete="CASCADE"), nullable=False)
    status = Column(String(20), nullable=False, default="open")
    assigned_to = Column(String(128), nullable=True)
    notes = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    alert = relationship("Alert", back_populates="case")

class AuditTrail(Base):
    __tablename__ = "audit_trail"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    entity_type = Column(String(32), nullable=False)
    entity_id = Column(Uuid, nullable=False)
    action = Column(String(32), nullable=False)
    actor = Column(String(128), nullable=False, default="system")
    details = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

class QuantumAlert(Base):
    __tablename__ = "quantum_alerts"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    session_id = Column(String(64), nullable=False)
    key_exchange = Column(String(32), nullable=False)
    signature_algo = Column(String(32), nullable=False)
    classification = Column(String(16), nullable=False)
    is_hndl_exposed = Column(Boolean, default=False)
    data_sensitivity = Column(String(32), nullable=False)
    bytes_transferred = Column(Integer, default=0)
    destination = Column(String(16), nullable=False)
    risk_factors = Column(JSON, nullable=False, default=list)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

class IdentityProfile(Base):
    __tablename__ = "identity_profiles"

    identity_id = Column(String(64), primary_key=True)
    known_devices = Column(JSON, default=list)
    known_beneficiaries = Column(JSON, default=list)
    known_ips = Column(JSON, default=list)
    avg_txn_amount = Column(Float, default=0.0)
    txn_count = Column(Integer, default=0)
    login_time_distribution = Column(JSON, default=dict)
    risk_score = Column(Float, default=0.0)
    last_seen_geo = Column(JSON, default=dict)
    last_updated = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

