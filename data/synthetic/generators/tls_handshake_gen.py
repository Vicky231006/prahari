"""
TLS handshake event generator.

Produces events to the `tls-handshake` Kafka topic matching the schema
defined in PROMPT.md Section 3:
  { session_id, timestamp, key_exchange, signature_algo,
    data_sensitivity, bytes_transferred, destination }

Normal events (~90%): routine data over modern but still-legacy crypto (ECDHE-P256),
with a small fraction already on PQC (ML-KEM-768) to show inventory spread.
HNDL-exposed events are injected by scenario_injector.
"""
import random
import time

from .base import (
    DATA_SENSITIVITY_LEVELS,
    LEGACY_KEY_EXCHANGES,
    LEGACY_SIGNATURE_ALGOS,
    PQC_KEY_EXCHANGES,
    PQC_SIGNATURE_ALGOS,
    jittered_now,
    new_uuid,
    produce_event,
)


def generate_normal_tls_event() -> dict:
    """Generate a single normal tls-handshake event."""
    # Most sessions still use legacy crypto (realistic for Indian banking in 2026)
    # ~15% have migrated to PQC or hybrid
    if random.random() < 0.15:
        key_exchange = random.choice(PQC_KEY_EXCHANGES)
        signature_algo = random.choice(PQC_SIGNATURE_ALGOS)
    else:
        key_exchange = random.choice(LEGACY_KEY_EXCHANGES)
        signature_algo = random.choice(LEGACY_SIGNATURE_ALGOS)

    # Most sessions carry routine data
    data_sensitivity = random.choices(
        DATA_SENSITIVITY_LEVELS,
        weights=[0.10, 0.05, 0.85],  # kyc=10%, credit_history=5%, routine=85%
        k=1,
    )[0]

    return {
        "session_id": f"sess-{new_uuid()[:8]}",
        "timestamp": jittered_now(),
        "key_exchange": key_exchange,
        "signature_algo": signature_algo,
        "data_sensitivity": data_sensitivity,
        "bytes_transferred": random.randint(512, 65536),
        "destination": random.choices(
            ["internal", "external"],
            weights=[0.80, 0.20],
            k=1,
        )[0],
    }


def run_tls_generator(
    producer,
    events_per_second: float = 5.0,
    stop_event=None,
):
    """Continuously produce normal tls-handshake events."""
    topic = "tls-handshake"
    interval = 1.0 / events_per_second
    count = 0

    print(f"[tls-handshake-gen] Starting at ~{events_per_second} events/sec")

    while stop_event is None or not stop_event.is_set():
        event = generate_normal_tls_event()
        produce_event(producer, topic, event, key=event["session_id"])
        count += 1

        if count % 500 == 0:
            producer.flush()
            print(f"[tls-handshake-gen] Produced {count} events")

        time.sleep(interval + random.uniform(-interval * 0.3, interval * 0.3))
