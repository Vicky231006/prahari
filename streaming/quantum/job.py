import json
import time
from datetime import datetime, timezone
from confluent_kafka import Producer
from ..redis_client import RedisClient
from ..config import settings

# ── Cryptographic Algorithms Classification Lookup Table ──
# Matches NIST FIPS 203/204/205 guidance
CRYPTO_CLASSIFICATION = {
    "key_exchange": {
        "ML-KEM-768": "pqc_ready",
        "ML-KEM-1024": "pqc_ready",
        "ML-KEM-512": "pqc_ready",
        "hybrid": "hybrid",
        "X25519-MLKEM768": "hybrid",
        "ECDHE-P256": "legacy",
        "ECDHE-P384": "legacy",
        "RSA-2048": "legacy",
        "RSA-4096": "legacy"
    },
    "signature_algo": {
        "ML-DSA-65": "pqc_ready",
        "ML-DSA-87": "pqc_ready",
        "ML-DSA-44": "pqc_ready",
        "ML-DSA": "pqc_ready",
        "ECDSA": "legacy",
        "RSA": "legacy"
    }
}

class CryptoInventoryJob:
    def __init__(self, redis_client: RedisClient, kafka_producer: Producer):
        self.redis_client = redis_client
        self.kafka_producer = kafka_producer

    def classify_session(self, key_exchange: str, signature_algo: str) -> str:
        """Classify session cryptography as legacy, pqc_ready, or hybrid."""
        kx_type = CRYPTO_CLASSIFICATION["key_exchange"].get(key_exchange, "legacy")
        sig_type = CRYPTO_CLASSIFICATION["signature_algo"].get(signature_algo, "legacy")

        if kx_type == "pqc_ready" and sig_type == "pqc_ready":
            return "pqc_ready"
        elif kx_type == "hybrid" or sig_type == "hybrid":
            return "hybrid"
        else:
            return "legacy"

    def process_tls_event(self, event: dict):
        """Process incoming tls-handshake event and evaluate quantum risk."""
        session_id = event.get("session_id")
        if not session_id:
            return

        key_exchange = event.get("key_exchange", "unknown")
        signature_algo = event.get("signature_algo", "unknown")
        data_sensitivity = event.get("data_sensitivity", "routine")
        bytes_transferred = int(event.get("bytes_transferred", 0))
        destination = event.get("destination", "internal")

        # Classify algorithms
        classification = self.classify_session(key_exchange, signature_algo)

        # Flag 1: HNDL Exposure
        # Target: sensitive data (KYC, credit history) over legacy crypto
        is_hndl_exposed = False
        risk_factors = []
        
        if data_sensitivity != "routine" and classification == "legacy":
            is_hndl_exposed = True
            risk_factors.append("legacy_crypto_sensitive_data")

        # Flag 2: Bulk Egress Anomaly (Harvesting indicator)
        # Threshold-based rule: large byte transfer to external destination
        is_bulk_egress_anomaly = False
        if bytes_transferred > 100000 and destination == "external":
            is_bulk_egress_anomaly = True
            risk_factors.append("bulk_external_egress")

        # If HNDL exposed or bulk egress anomalous, form alert
        if is_hndl_exposed or is_bulk_egress_anomaly:
            alert = {
                "alert_id": f"qalert-{int(time.time())}-{session_id}",
                "session_id": session_id,
                "timestamp": event.get("timestamp") or datetime.now(timezone.utc).isoformat(),
                "key_exchange": key_exchange,
                "signature_algo": signature_algo,
                "classification": classification,
                "is_hndl_exposed": is_hndl_exposed,
                "data_sensitivity": data_sensitivity,
                "bytes_transferred": bytes_transferred,
                "destination": destination,
                "risk_factors": risk_factors
            }

            # Emit to quantum-alerts topic
            self.kafka_producer.produce(
                topic=settings.TOPIC_QUANTUM_ALERTS,
                key=session_id.encode("utf-8"),
                value=json.dumps(alert).encode("utf-8")
            )
            self.kafka_producer.flush()
            print(f"[crypto-job] Emitted Crypto Alert for {session_id} (HNDL: {is_hndl_exposed}, Egress: {is_bulk_egress_anomaly})")

        # Update Redis stats atomically (Section 5 quantum scan summary count cache)
        self.redis_client.update_quantum_counts(classification, is_hndl_exposed)
