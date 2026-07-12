"""
Base utilities shared across all PRAHARI synthetic data generators.

Provides identity pools, timestamp generation with business-hours weighting,
geo-coordinate pools for Indian cities, and a common Kafka producer factory.
"""
import json
import os
import random
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from confluent_kafka import Producer

# ── Indian metro cities with realistic coordinates ──
GEO_POOL = [
    {"lat": 19.076, "lon": 72.877, "country": "IN", "city": "Mumbai"},
    {"lat": 28.614, "lon": 77.209, "country": "IN", "city": "Delhi"},
    {"lat": 12.972, "lon": 77.595, "country": "IN", "city": "Bengaluru"},
    {"lat": 13.083, "lon": 80.271, "country": "IN", "city": "Chennai"},
    {"lat": 22.572, "lon": 88.364, "country": "IN", "city": "Kolkata"},
    {"lat": 17.385, "lon": 78.487, "country": "IN", "city": "Hyderabad"},
    {"lat": 18.520, "lon": 73.857, "country": "IN", "city": "Pune"},
    {"lat": 23.023, "lon": 72.571, "country": "IN", "city": "Ahmedabad"},
    {"lat": 26.912, "lon": 75.787, "country": "IN", "city": "Jaipur"},
    {"lat": 21.146, "lon": 79.089, "country": "IN", "city": "Nagpur"},
]

# Foreign cities for impossible-travel scenarios
FOREIGN_GEO_POOL = [
    {"lat": 51.507, "lon": -0.128, "country": "GB", "city": "London"},
    {"lat": 40.713, "lon": -74.006, "country": "US", "city": "New York"},
    {"lat": 1.352, "lon": 103.820, "country": "SG", "city": "Singapore"},
    {"lat": 25.276, "lon": 55.296, "country": "AE", "city": "Dubai"},
]

# UPI channels per Section 3 schema
CHANNELS = ["UPI", "NEFT", "RTGS", "IMPS"]

# Security event types per Section 3
SEC_EVENT_TYPES = ["login", "privileged_cmd", "endpoint_alert", "geo_change"]

# TLS key exchange and signature algorithms
LEGACY_KEY_EXCHANGES = ["RSA-2048", "ECDHE-P256"]
PQC_KEY_EXCHANGES = ["ML-KEM-768", "hybrid"]
LEGACY_SIGNATURE_ALGOS = ["RSA", "ECDSA"]
PQC_SIGNATURE_ALGOS = ["ML-DSA"]
DATA_SENSITIVITY_LEVELS = ["kyc", "credit_history", "routine"]

# ── How many synthetic identities to maintain ──
NUM_IDENTITIES = 200
IDENTITY_POOL = [f"ID-{str(i).zfill(5)}" for i in range(1, NUM_IDENTITIES + 1)]


def make_producer() -> Producer:
    """Create a confluent-kafka Producer from environment config."""
    bootstrap = os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "localhost:9094")
    return Producer({
        "bootstrap.servers": bootstrap,
        "linger.ms": 50,
        "batch.num.messages": 200,
        "compression.type": "lz4",
        "acks": "all",
    })


def delivery_report(err, msg):
    """Kafka delivery callback — logs failures only."""
    if err is not None:
        print(f"[KAFKA-ERR] Delivery failed for {msg.topic()}: {err}")


def produce_event(producer: Producer, topic: str, event: dict, key: str | None = None):
    """Serialize and send a single event to Kafka."""
    producer.produce(
        topic=topic,
        key=key.encode("utf-8") if key else None,
        value=json.dumps(event, default=str).encode("utf-8"),
        callback=delivery_report,
    )


def new_uuid() -> str:
    return str(uuid.uuid4())


def business_hours_timestamp(base: datetime | None = None) -> datetime:
    """
    Generate a timestamp weighted toward Indian business hours (09:00–18:00 IST).
    ~70% of events fall within business hours, ~30% outside.
    This matches realistic banking transaction patterns.
    """
    if base is None:
        base = datetime.now(timezone.utc)

    ist_offset = timedelta(hours=5, minutes=30)
    ist_hour = (base + ist_offset).hour

    # Weight toward business hours
    if random.random() < 0.7:
        # Business hours: 09:00 - 18:00 IST
        hour = random.randint(9, 17)
        minute = random.randint(0, 59)
        second = random.randint(0, 59)
        result = base.replace(hour=(hour - 5) % 24, minute=minute, second=second,
                              microsecond=random.randint(0, 999999))
    else:
        # Off-hours
        hour = random.choice(list(range(0, 9)) + list(range(18, 24)))
        minute = random.randint(0, 59)
        second = random.randint(0, 59)
        result = base.replace(hour=(hour - 5) % 24, minute=minute, second=second,
                              microsecond=random.randint(0, 999999))
    return result


def jittered_now(max_jitter_seconds: int = 5) -> str:
    """Current UTC time with slight random jitter, ISO-8601 formatted."""
    dt = datetime.now(timezone.utc) + timedelta(seconds=random.uniform(0, max_jitter_seconds))
    return dt.isoformat()


def lognormal_amount(mean: float = 8.5, sigma: float = 1.5, min_val: float = 100) -> float:
    """
    Log-normal distribution for transaction amounts (INR).
    mean=8.5, sigma=1.5 gives a realistic spread: median ~₹4,900, 95th pctl ~₹150K.
    """
    amount = random.lognormvariate(mean, sigma)
    return round(max(amount, min_val), 2)


def random_device_fingerprint() -> str:
    return f"fp-{uuid.uuid4().hex[:16]}"


class IdentityState:
    """
    Tracks per-identity state so generators produce coherent sequences:
    known devices, known beneficiaries, usual geo, etc.
    """

    def __init__(self, identity_id: str):
        self.identity_id = identity_id
        self.known_devices = [random_device_fingerprint() for _ in range(random.randint(1, 3))]
        self.known_beneficiaries = [f"BEN-{uuid.uuid4().hex[:8]}" for _ in range(random.randint(2, 8))]
        self.home_geo = random.choice(GEO_POOL)
        self.usual_ips = [f"103.{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}"
                          for _ in range(random.randint(1, 3))]
        self.avg_txn_amount = lognormal_amount(mean=8.0, sigma=1.0)
        self.linked_identities: list[str] = []  # populated for insider-collusion scenario

    def known_device(self) -> str:
        return random.choice(self.known_devices)

    def known_ip(self) -> str:
        return random.choice(self.usual_ips)

    def known_beneficiary(self) -> str:
        return random.choice(self.known_beneficiaries)

    def new_beneficiary(self) -> str:
        b = f"BEN-{uuid.uuid4().hex[:8]}"
        return b

    def new_device(self) -> str:
        return random_device_fingerprint()
