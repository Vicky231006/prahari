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
    Now enhanced with rich banking metadata.
    """

    def __init__(self, identity_id: str):
        self.identity_id = identity_id
        
        # 1. Base Metadata
        first_names = ["Aarav", "Vihaan", "Aditya", "Arjun", "Sai", "Riya", "Aanya", "Diya", "Isha", "Neha", "Rahul", "Karan", "Priya", "Anjali", "Vikram"]
        last_names = ["Sharma", "Patel", "Singh", "Kumar", "Gupta", "Deshmukh", "Joshi", "Reddy", "Nair", "Iyer"]
        self.customer_name = f"{random.choice(first_names)} {random.choice(last_names)}"
        
        self.customer_type = random.choices(["Retail", "SME", "Corporate"], weights=[0.8, 0.15, 0.05])[0]
        
        if self.customer_type == "Retail":
            self.customer_segment = random.choices(["Standard", "Premium", "HNI"], weights=[0.7, 0.25, 0.05])[0]
            self.avg_txn_amount = lognormal_amount(mean=7.0, sigma=1.0)
        elif self.customer_type == "SME":
            self.customer_segment = random.choices(["Standard", "Premium"], weights=[0.6, 0.4])[0]
            self.customer_name = f"{self.customer_name} Enterprises"
            self.avg_txn_amount = lognormal_amount(mean=10.0, sigma=1.2)
        else:
            self.customer_segment = "Corporate"
            self.customer_name = f"{self.customer_name} Corp Ltd."
            self.avg_txn_amount = lognormal_amount(mean=12.0, sigma=1.5)
            
        self.kyc_status = random.choices(["Verified", "Pending", "Restricted"], weights=[0.9, 0.08, 0.02])[0]
        self.account_age_days = random.randint(10, 3650)
        
        # Derive customer_since
        base = datetime.now(timezone.utc)
        since_date = base - timedelta(days=self.account_age_days)
        self.customer_since = since_date.strftime("%Y-%m-%d")
        
        self.home_geo = random.choice(GEO_POOL)
        self.primary_branch = f"Branch - {self.home_geo['city']}"
        self.region = self.home_geo['city']
        
        # Risk & VIP
        self.risk_tier = random.choices(["Low", "Medium", "High"], weights=[0.8, 0.15, 0.05])[0]
        self.vip_flag = (self.customer_segment in ["HNI", "Premium"]) or (self.customer_type == "Corporate")
        
        # Financials
        self.current_balance = self.avg_txn_amount * random.uniform(10.0, 100.0)
        self.average_daily_volume = self.avg_txn_amount * random.uniform(1.0, 5.0)
        self.monthly_txn_count = random.randint(5, 100) if self.customer_type == "Retail" else random.randint(50, 500)
        self.dormant_account_flag = (random.random() < 0.02)
        
        # History
        self.previous_alerts_count = random.randint(0, 5) if self.risk_tier == "Low" else random.randint(2, 20)
        self.previous_cases_count = max(0, self.previous_alerts_count - random.randint(1, 5))
        self.fraud_history_count = random.choices([0, 1, 2], weights=[0.95, 0.04, 0.01])[0]
        
        self.preferred_payment_method = random.choice(CHANNELS)
        self.device_trust_score = random.uniform(0.6, 1.0)
        
        # 2. Rich Devices
        self.rich_devices = []
        self.known_devices = []
        for _ in range(random.randint(1, 3)):
            fp = random_device_fingerprint()
            self.known_devices.append(fp)
            self.rich_devices.append({
                "device_id": fp,
                "os": random.choice(["Windows 10", "macOS", "iOS", "Android"]),
                "browser": random.choice(["Chrome", "Safari", "Firefox", "Edge"]),
                "fingerprint": fp,
                "first_seen": (base - timedelta(days=random.randint(10, 300))).isoformat(),
                "last_seen": (base - timedelta(days=random.randint(0, 10))).isoformat(),
                "times_used": random.randint(10, 1000),
                "trusted_flag": random.random() > 0.1,
                "risk_score": random.uniform(0.0, 0.3)
            })
            
        # 3. Rich Beneficiaries
        self.rich_beneficiaries = []
        self.known_beneficiaries = []
        for _ in range(random.randint(2, 8)):
            bid = f"BEN-{uuid.uuid4().hex[:8]}"
            self.known_beneficiaries.append(bid)
            self.rich_beneficiaries.append({
                "beneficiary_id": bid,
                "name": f"{random.choice(first_names)} {random.choice(last_names)}",
                "bank": random.choice(["HDFC", "SBI", "ICICI", "Axis", "Kotak"]),
                "ifsc": f"BANK000{random.randint(1000, 9999)}",
                "relationship": random.choice(["Family", "Friend", "Merchant", "Vendor", "Employee"]),
                "first_added": (base - timedelta(days=random.randint(5, 300))).isoformat(),
                "times_used": random.randint(1, 50),
                "total_amount_received": self.avg_txn_amount * random.randint(1, 10),
                "risk_score": random.uniform(0.0, 0.2)
            })
            
        # 4. Rich IPs
        self.rich_ips = []
        self.usual_ips = []
        for _ in range(random.randint(1, 3)):
            ip = f"103.{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}"
            self.usual_ips.append(ip)
            self.rich_ips.append({
                "ip_address": ip,
                "country": "IN",
                "city": self.region,
                "asn": f"AS{random.randint(1000, 9999)}",
                "isp": random.choice(["Jio", "Airtel", "Vi", "BSNL"]),
                "vpn_flag": random.random() < 0.05,
                "tor_flag": random.random() < 0.01,
                "known_malicious_flag": False,
                "times_seen": random.randint(50, 500)
            })

        self.linked_identities: list[str] = []

    def get_profile_dict(self) -> dict:
        """Return the rich profile dictionary compatible with IdentityProfileSyncRequest."""
        return {
            "identity_id": self.identity_id,
            "customer_name": self.customer_name,
            "customer_type": self.customer_type,
            "customer_segment": self.customer_segment,
            "kyc_status": self.kyc_status,
            "account_age_days": self.account_age_days,
            "customer_since": self.customer_since,
            "primary_branch": self.primary_branch,
            "region": self.region,
            "risk_tier": self.risk_tier,
            "current_balance": self.current_balance,
            "average_daily_volume": self.average_daily_volume,
            "monthly_txn_count": self.monthly_txn_count,
            "dormant_account_flag": self.dormant_account_flag,
            "vip_flag": self.vip_flag,
            "previous_alerts_count": self.previous_alerts_count,
            "previous_cases_count": self.previous_cases_count,
            "fraud_history_count": self.fraud_history_count,
            "typical_login_hours": [9, 10, 11, 14, 15, 18],
            "typical_countries": ["IN"],
            "typical_channels": CHANNELS,
            "preferred_payment_method": self.preferred_payment_method,
            "device_trust_score": self.device_trust_score,
            "known_devices": self.rich_devices,
            "known_beneficiaries": self.rich_beneficiaries,
            "known_ips": self.rich_ips,
            "avg_txn_amount": self.avg_txn_amount,
            "txn_count": self.monthly_txn_count,
            "login_time_distribution": {"morning": 0.4, "afternoon": 0.4, "evening": 0.2},
            "risk_score": 0.5 if self.risk_tier == "High" else (0.2 if self.risk_tier == "Medium" else 0.05),
            "last_seen_geo": self.home_geo
        }

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
