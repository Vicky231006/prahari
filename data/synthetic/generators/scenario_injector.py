"""
Scenario injector — generates the four labeled attack scenarios defined in
PROMPT.md Section 3.

Each scenario produces a coordinated sequence of events across multiple Kafka
topics with correct temporal relationships. Every injected event carries:
  - scenario_type: one of "ato", "insider_collusion", "credential_stuffing_ato", "hndl_exposure"
  - is_synthetic_positive: true

These labels provide ground truth for the fusion model and enable the
Scenario Runner (Section 9) to trigger exact sequences on demand.

Scenario specifications (verbatim from Section 3):
  1. ATO: new device + impossible travel + high-value transfer to new beneficiary within 15 min.
  2. Insider collusion: privileged account unusual data access, correlated within 10 min with a
     transaction from an associated/linked identity to a shared or new beneficiary.
  3. Credential stuffing → ATO: burst of failed logins across many identities from few source IPs,
     followed by one success and an immediate transaction.
  4. HNDL exposure: session carrying kyc or credit_history sensitivity data negotiated over legacy
     (RSA-2048/ECDHE-P256) key exchange.
"""
import random
import time
from datetime import datetime, timedelta, timezone

from .base import (
    FOREIGN_GEO_POOL,
    IDENTITY_POOL,
    IdentityState,
    jittered_now,
    lognormal_amount,
    new_uuid,
    produce_event,
)


def inject_ato_scenario(
    identity_states: dict[str, IdentityState],
    producer,
) -> list[dict]:
    """
    Scenario 1 — Account Takeover (ATO):
    New device + impossible travel + high-value transfer to a new beneficiary within 15 minutes.
    """
    identity_id = random.choice(IDENTITY_POOL)
    state = identity_states[identity_id]
    session_id = f"sess-ato-{new_uuid()[:8]}"
    foreign_geo = random.choice(FOREIGN_GEO_POOL)
    new_device = state.new_device()
    now = datetime.now(timezone.utc)
    events = []

    # Step 1: Login from a new device at a foreign location (impossible travel)
    login_event = {
        "event_id": new_uuid(),
        "identity_id": identity_id,
        "timestamp": now.isoformat(),
        "event_type": "login",
        "source_ip": f"185.{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}",
        "geo": {k: v for k, v in foreign_geo.items() if k != "city"},
        "device_fingerprint": new_device,
        "is_new_device": True,
        "session_id": session_id,
        "risk_flags": ["impossible_travel", "new_device"],
        "scenario_type": "ato",
        "is_synthetic_positive": True,
    }
    produce_event(producer, "security-telemetry", login_event, key=identity_id)
    events.append(login_event)

    # Step 2: Geo change alert (2 minutes later)
    geo_event = {
        "event_id": new_uuid(),
        "identity_id": identity_id,
        "timestamp": (now + timedelta(minutes=2)).isoformat(),
        "event_type": "geo_change",
        "source_ip": login_event["source_ip"],
        "geo": {k: v for k, v in foreign_geo.items() if k != "city"},
        "device_fingerprint": new_device,
        "is_new_device": True,
        "session_id": session_id,
        "risk_flags": ["impossible_travel"],
        "scenario_type": "ato",
        "is_synthetic_positive": True,
    }
    produce_event(producer, "security-telemetry", geo_event, key=identity_id)
    events.append(geo_event)

    # Step 3: High-value transfer to a new beneficiary (within 15 min window)
    txn_event = {
        "txn_id": new_uuid(),
        "identity_id": identity_id,
        "timestamp": (now + timedelta(minutes=random.randint(5, 14))).isoformat(),
        "amount": round(random.uniform(200000, 1000000), 2),  # High-value: ₹2L–₹10L
        "currency": "INR",
        "channel": random.choice(["NEFT", "RTGS", "IMPS"]),
        "beneficiary_id": state.new_beneficiary(),
        "beneficiary_is_new": True,
        "session_id": session_id,
        "is_cross_border": False,
        "scenario_type": "ato",
        "is_synthetic_positive": True,
    }
    produce_event(producer, "transaction-events", txn_event, key=identity_id)
    events.append(txn_event)

    print(f"[scenario] ATO injected for {identity_id}")
    return events


def inject_insider_collusion_scenario(
    identity_states: dict[str, IdentityState],
    producer,
) -> list[dict]:
    """
    Scenario 2 — Insider Collusion:
    Privileged account performs unusual data access, correlated within 10 min
    with a transaction from an associated/linked identity to a shared or new beneficiary.
    """
    # Pick two identities and link them
    insider_id = random.choice(IDENTITY_POOL[:50])  # First 50 are "privileged"
    linked_id = random.choice(IDENTITY_POOL[50:])
    insider_state = identity_states[insider_id]
    linked_state = identity_states[linked_id]
    now = datetime.now(timezone.utc)
    shared_beneficiary = f"BEN-shared-{new_uuid()[:6]}"
    events = []

    # Step 1: Privileged command (unusual data access) by the insider
    priv_event = {
        "event_id": new_uuid(),
        "identity_id": insider_id,
        "timestamp": now.isoformat(),
        "event_type": "privileged_cmd",
        "source_ip": insider_state.known_ip(),
        "geo": {k: v for k, v in insider_state.home_geo.items() if k != "city"},
        "device_fingerprint": insider_state.known_device(),
        "is_new_device": False,
        "session_id": f"sess-insider-{new_uuid()[:8]}",
        "risk_flags": ["unusual_data_access", "privileged_account"],
        "scenario_type": "insider_collusion",
        "is_synthetic_positive": True,
    }
    produce_event(producer, "security-telemetry", priv_event, key=insider_id)
    events.append(priv_event)

    # Step 2: Transaction from the linked identity to the shared beneficiary (within 10 min)
    txn_event = {
        "txn_id": new_uuid(),
        "identity_id": linked_id,
        "timestamp": (now + timedelta(minutes=random.randint(3, 9))).isoformat(),
        "amount": round(random.uniform(50000, 500000), 2),
        "currency": "INR",
        "channel": random.choice(["NEFT", "IMPS"]),
        "beneficiary_id": shared_beneficiary,
        "beneficiary_is_new": True,
        "session_id": f"sess-linked-{new_uuid()[:8]}",
        "is_cross_border": False,
        "scenario_type": "insider_collusion",
        "is_synthetic_positive": True,
        "linked_insider_id": insider_id,  # Extra field for traceability
    }
    produce_event(producer, "transaction-events", txn_event, key=linked_id)
    events.append(txn_event)

    print(f"[scenario] Insider collusion injected: {insider_id} → {linked_id}")
    return events


def inject_credential_stuffing_ato_scenario(
    identity_states: dict[str, IdentityState],
    producer,
) -> list[dict]:
    """
    Scenario 3 — Credential Stuffing → ATO:
    Burst of failed logins across many identities from few source IPs,
    followed by one success and an immediate transaction.
    """
    # Few attacker IPs
    attacker_ips = [
        f"45.{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}"
        for _ in range(random.randint(2, 4))
    ]
    target_identities = random.sample(IDENTITY_POOL, k=min(20, len(IDENTITY_POOL)))
    victim_id = target_identities[0]
    victim_state = identity_states[victim_id]
    now = datetime.now(timezone.utc)
    events = []

    # Step 1: Burst of failed logins across many identities
    for i, tid in enumerate(target_identities):
        failed_event = {
            "event_id": new_uuid(),
            "identity_id": tid,
            "timestamp": (now + timedelta(seconds=i * 2)).isoformat(),
            "event_type": "login",
            "source_ip": random.choice(attacker_ips),
            "geo": {"lat": 0, "lon": 0, "country": "XX"},  # Unknown/anonymized
            "device_fingerprint": f"fp-attacker-{new_uuid()[:6]}",
            "is_new_device": True,
            "session_id": f"sess-stuffing-{new_uuid()[:8]}",
            "risk_flags": ["failed_login", "credential_stuffing"],
            "scenario_type": "credential_stuffing_ato",
            "is_synthetic_positive": True,
        }
        produce_event(producer, "security-telemetry", failed_event, key=tid)
        events.append(failed_event)

    # Step 2: One successful login for the victim
    success_session = f"sess-victim-{new_uuid()[:8]}"
    success_event = {
        "event_id": new_uuid(),
        "identity_id": victim_id,
        "timestamp": (now + timedelta(seconds=len(target_identities) * 2 + 5)).isoformat(),
        "event_type": "login",
        "source_ip": random.choice(attacker_ips),
        "geo": {"lat": 0, "lon": 0, "country": "XX"},
        "device_fingerprint": f"fp-attacker-{new_uuid()[:6]}",
        "is_new_device": True,
        "session_id": success_session,
        "risk_flags": ["new_device", "suspicious_ip_cluster"],
        "scenario_type": "credential_stuffing_ato",
        "is_synthetic_positive": True,
    }
    produce_event(producer, "security-telemetry", success_event, key=victim_id)
    events.append(success_event)

    # Step 3: Immediate transaction from the victim
    txn_event = {
        "txn_id": new_uuid(),
        "identity_id": victim_id,
        "timestamp": (now + timedelta(seconds=len(target_identities) * 2 + 30)).isoformat(),
        "amount": round(random.uniform(100000, 500000), 2),
        "currency": "INR",
        "channel": "IMPS",
        "beneficiary_id": victim_state.new_beneficiary(),
        "beneficiary_is_new": True,
        "session_id": success_session,
        "is_cross_border": False,
        "scenario_type": "credential_stuffing_ato",
        "is_synthetic_positive": True,
    }
    produce_event(producer, "transaction-events", txn_event, key=victim_id)
    events.append(txn_event)

    print(f"[scenario] Credential stuffing→ATO injected: {len(target_identities)} targets, victim={victim_id}")
    return events


def inject_hndl_exposure_scenario(producer) -> list[dict]:
    """
    Scenario 4 — HNDL Exposure:
    A session carrying kyc or credit_history sensitivity data negotiated over
    legacy (RSA-2048 / ECDHE-P256) key exchange.
    """
    now = datetime.now(timezone.utc)
    events = []

    # Generate 3-5 HNDL-exposed sessions for visibility
    for _ in range(random.randint(3, 5)):
        event = {
            "session_id": f"sess-hndl-{new_uuid()[:8]}",
            "timestamp": (now + timedelta(seconds=random.randint(0, 60))).isoformat(),
            "key_exchange": random.choice(["RSA-2048", "ECDHE-P256"]),
            "signature_algo": random.choice(["RSA", "ECDSA"]),
            "data_sensitivity": random.choice(["kyc", "credit_history"]),
            "bytes_transferred": random.randint(10000, 500000),
            "destination": random.choice(["internal", "external"]),
            "scenario_type": "hndl_exposure",
            "is_synthetic_positive": True,
        }
        produce_event(producer, "tls-handshake", event, key=event["session_id"])
        events.append(event)

    print(f"[scenario] HNDL exposure injected: {len(events)} sessions")
    return events


def run_scenario_injector(
    identity_states: dict[str, IdentityState],
    producer,
    injection_interval_seconds: float = 30.0,
    stop_event=None,
):
    """
    Periodically inject attack scenarios at a known rate (~5% of total traffic).
    Cycles through all four scenario types.
    """
    scenarios = [
        ("ato", lambda: inject_ato_scenario(identity_states, producer)),
        ("insider_collusion", lambda: inject_insider_collusion_scenario(identity_states, producer)),
        ("credential_stuffing_ato", lambda: inject_credential_stuffing_ato_scenario(identity_states, producer)),
        ("hndl_exposure", lambda: inject_hndl_exposure_scenario(producer)),
    ]
    cycle_idx = 0

    print(f"[scenario-injector] Starting, injecting every ~{injection_interval_seconds}s")

    while stop_event is None or not stop_event.is_set():
        name, inject_fn = scenarios[cycle_idx % len(scenarios)]
        try:
            inject_fn()
            producer.flush()
        except Exception as e:
            print(f"[scenario-injector] Error injecting {name}: {e}")

        cycle_idx += 1
        time.sleep(injection_interval_seconds + random.uniform(-5, 5))
