"""
Transaction event generator.

Produces events to the `transaction-events` Kafka topic matching the schema
defined in PROMPT.md Section 3:
  { txn_id, identity_id, timestamp, amount, currency, channel,
    beneficiary_id, beneficiary_is_new, session_id, is_cross_border }

Normal events: log-normal amounts, known beneficiaries, INR, domestic.
"""
import random
import time

from .base import (
    CHANNELS,
    IDENTITY_POOL,
    IdentityState,
    jittered_now,
    lognormal_amount,
    new_uuid,
    produce_event,
)


def generate_normal_transaction(state: IdentityState) -> dict:
    """Generate a single normal (benign) transaction-events event."""
    channel = random.choices(
        CHANNELS,
        weights=[0.55, 0.20, 0.05, 0.20],  # UPI dominates Indian retail
        k=1,
    )[0]

    # Normal transactions: known beneficiaries, domestic, reasonable amounts
    amount = lognormal_amount()
    # Clip to channel limits (approximate RBI limits)
    if channel == "UPI":
        amount = min(amount, 100000)
    elif channel == "IMPS":
        amount = min(amount, 500000)

    return {
        "txn_id": new_uuid(),
        "identity_id": state.identity_id,
        "timestamp": jittered_now(),
        "amount": amount,
        "currency": "INR",
        "channel": channel,
        "beneficiary_id": state.known_beneficiary(),
        "beneficiary_is_new": False,
        "session_id": f"sess-{new_uuid()[:8]}",
        "is_cross_border": False,
    }


def run_transaction_generator(
    identity_states: dict[str, IdentityState],
    producer,
    events_per_second: float = 8.0,
    stop_event=None,
):
    """Continuously produce normal transaction-events."""
    topic = "transaction-events"
    interval = 1.0 / events_per_second
    count = 0

    print(f"[transaction-gen] Starting at ~{events_per_second} events/sec")

    while stop_event is None or not stop_event.is_set():
        identity_id = random.choice(IDENTITY_POOL)
        state = identity_states[identity_id]
        event = generate_normal_transaction(state)
        produce_event(producer, topic, event, key=identity_id)
        count += 1

        if count % 500 == 0:
            producer.flush()
            print(f"[transaction-gen] Produced {count} events")

        time.sleep(interval + random.uniform(-interval * 0.3, interval * 0.3))
