import pytest
from streaming.quantum.job import CryptoInventoryJob

class MockProducer:
    def __init__(self):
        self.emitted = []
    def produce(self, topic, key, value):
        self.emitted.append((topic, key, value))
    def flush(self, timeout=None):
        pass

def test_crypto_classification():
    job = CryptoInventoryJob(redis_client=None, kafka_producer=MockProducer())
    
    # ML-KEM + ML-DSA -> pqc_ready
    assert job.classify_session("ML-KEM-768", "ML-DSA-65") == "pqc_ready"
    assert job.classify_session("ML-KEM-1024", "ML-DSA") == "pqc_ready"
    
    # Hybrid key-exchange -> hybrid
    assert job.classify_session("hybrid", "ECDSA") == "hybrid"
    assert job.classify_session("X25519-MLKEM768", "RSA") == "hybrid"
    
    # Legacy + Legacy -> legacy
    assert job.classify_session("RSA-2048", "RSA") == "legacy"
    assert job.classify_session("ECDHE-P256", "ECDSA") == "legacy"
    
    # Unknown/missing -> legacy (fail-secure fallback)
    assert job.classify_session("unknown", "unknown") == "legacy"
