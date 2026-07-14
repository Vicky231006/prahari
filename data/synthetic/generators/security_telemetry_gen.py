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

    ip_obj = random.choice(state.rich_ips) if state.rich_ips else {"ip_address": state.known_ip()}
    device_obj = random.choice(state.rich_devices) if state.rich_devices else {"device_id": state.known_device()}
    
    geo = state.home_geo.copy()
    if ip_obj.get("city") and ip_obj.get("country"):
        geo = {"lat": geo["lat"], "lon": geo["lon"], "country": ip_obj["country"], "city": ip_obj["city"]}

    risk_flags = []
    if ip_obj.get("vpn_flag"):
        risk_flags.append("VPN_DETECTED")
    if ip_obj.get("tor_flag"):
        risk_flags.append("TOR_NODE")
    if not device_obj.get("trusted_flag", True):
        risk_flags.append("UNTRUSTED_DEVICE")

    return {
        "event_id": new_uuid(),
        "identity_id": state.identity_id,
        "timestamp": jittered_now(),
        "event_type": event_type,
        "source_ip": ip_obj["ip_address"],
        "geo": geo,
        "device_fingerprint": device_obj["device_id"],
        "is_new_device": False,
        "session_id": f"sess-{new_uuid()[:8]}",
        "risk_flags": risk_flags,
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
