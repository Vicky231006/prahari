"""
Shared pytest fixtures for PRAHARI test suite.
Provides configured test clients, mock Kafka producers, and database sessions.
"""
import os
import pytest

# Force test-safe defaults so tests never touch production infra
os.environ.setdefault("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
os.environ.setdefault("REDIS_HOST", "localhost")
os.environ.setdefault("REDIS_PORT", "6379")
os.environ.setdefault("POSTGRES_HOST", "localhost")
os.environ.setdefault("POSTGRES_PORT", "5432")
os.environ.setdefault("POSTGRES_DB", "prahari_test")
os.environ.setdefault("POSTGRES_USER", "prahari")
os.environ.setdefault("POSTGRES_PASSWORD", "prahari_dev_pw")
os.environ.setdefault("DEMO_MODE", "true")
os.environ.setdefault("GEMINI_API_KEY", "test-key-not-real")
os.environ.setdefault("JWT_SECRET", "test-jwt-secret")


@pytest.fixture
def sample_security_event():
    """A single well-formed security-telemetry event for unit tests."""
    return {
        "event_id": "evt-test-001",
        "identity_id": "ID-TEST-001",
        "timestamp": "2026-07-12T12:00:00Z",
        "event_type": "login",
        "source_ip": "203.0.113.10",
        "geo": {"lat": 19.076, "lon": 72.877, "country": "IN"},
        "device_fingerprint": "fp-abcdef123456",
        "is_new_device": False,
        "session_id": "sess-test-001",
        "risk_flags": [],
    }


@pytest.fixture
def sample_transaction_event():
    """A single well-formed transaction-events event for unit tests."""
    return {
        "txn_id": "txn-test-001",
        "identity_id": "ID-TEST-001",
        "timestamp": "2026-07-12T12:01:00Z",
        "amount": 5000.0,
        "currency": "INR",
        "channel": "UPI",
        "beneficiary_id": "BEN-001",
        "beneficiary_is_new": False,
        "session_id": "sess-test-001",
        "is_cross_border": False,
    }


@pytest.fixture
def sample_tls_event():
    """A single well-formed tls-handshake event for unit tests."""
    return {
        "session_id": "sess-test-001",
        "timestamp": "2026-07-12T12:00:00Z",
        "key_exchange": "ECDHE-P256",
        "signature_algo": "ECDSA",
        "data_sensitivity": "routine",
        "bytes_transferred": 4096,
        "destination": "internal",
    }
