"""
Security telemetry event generator.

Produces events to the `security-telemetry` Kafka topic matching the schema
defined in PROMPT.md Section 3:
  { event_id, identity_id, timestamp, event_type, source_ip, geo,
    device_fingerprint, is_new_device, session_id, risk_flags }

Normal events (~95%): logins from known devices/IPs/geos with no risk flags.
Anomalous events are injected by the scenario_injector module, not here.
"""
import random
import time

from .base import (
    IDENTITY_POOL,
    SEC_EVENT_TYPES,
    IdentityState,
    jittered_now,
    new_uuid,
    produce_event,
)


def generate_normal_security_event(state: IdentityState) -> dict:
    """Generate a single normal (benign) security-telemetry event."""
    event_type = random.choices(
        SEC_EVENT_TYPES,
        weights=[0.60, 0.10, 0.05, 0.25],  # logins are most common
        k=1,
    )[0]

    return {
        "event_id": new_uuid(),
        "identity_id": state.identity_id,
        "timestamp": jittered_now(),
        "event_type": event_type,
        "source_ip": state.known_ip(),
        "geo": {k: v for k, v in state.home_geo.items() if k != "city"},
        "device_fingerprint": state.known_device(),
        "is_new_device": False,
        "session_id": f"sess-{new_uuid()[:8]}",
        "risk_flags": [],
    }


def run_security_generator(
    identity_states: dict[str, IdentityState],
    producer,
    events_per_second: float = 10.0,
    stop_event=None,
):
    """
    Continuously produce normal security-telemetry events.
    Anomalous/scenario events are injected separately by scenario_injector.
    """
    topic = "security-telemetry"
    interval = 1.0 / events_per_second
    count = 0

    print(f"[security-telemetry-gen] Starting at ~{events_per_second} events/sec")

    while stop_event is None or not stop_event.is_set():
        identity_id = random.choice(IDENTITY_POOL)
        state = identity_states[identity_id]
        event = generate_normal_security_event(state)
        produce_event(producer, topic, event, key=identity_id)
        count += 1

        if count % 500 == 0:
            producer.flush()
            print(f"[security-telemetry-gen] Produced {count} events")

        time.sleep(interval + random.uniform(-interval * 0.3, interval * 0.3))
