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
    GEO_POOL,
    FOREIGN_GEO_POOL,
)


def generate_normal_transaction(state: IdentityState) -> dict:
    """Generate a single normal (benign) transaction-events event."""
    
    # Base amounts and channels on customer type
    if state.customer_type == "Retail":
        channels = ["UPI", "IMPS", "ATM Withdrawal", "POS", "Merchant Payment"]
        weights = [0.60, 0.15, 0.05, 0.10, 0.10]
        base_amount = state.avg_txn_amount * random.uniform(0.1, 1.5)
    elif state.customer_type == "SME":
        channels = ["NEFT", "RTGS", "IMPS", "Cash Deposit", "Merchant Payment"]
        weights = [0.40, 0.20, 0.20, 0.10, 0.10]
        base_amount = state.avg_txn_amount * random.uniform(0.5, 2.5)
    else:  # Corporate
        channels = ["RTGS", "NEFT", "Salary Credit"]
        weights = [0.60, 0.30, 0.10]
        base_amount = state.avg_txn_amount * random.uniform(1.0, 5.0)

    channel = random.choices(channels, weights=weights, k=1)[0]
    
    amount = base_amount
    if channel == "UPI":
        amount = min(amount, 100000)
    elif channel == "IMPS":
        amount = min(amount, 500000)
        
    merchant_name = None
    location = state.home_geo
    
    if channel in ["POS", "Merchant Payment", "UPI"]:
        merchants = ["Amazon", "Flipkart", "Swiggy", "Zomato", "Uber", "Ola", "Reliance Fresh", "D-Mart", "Starbucks", "Indian Oil"]
        merchant_name = random.choice(merchants)
        if random.random() < 0.2:  # Sometimes out of town
            location = random.choice([g for g in GEO_POOL if g["city"] != state.home_geo["city"]] or [state.home_geo])
            
    is_cross_border = False
    if state.vip_flag and random.random() < 0.05:
        is_cross_border = True
        location = random.choice(FOREIGN_GEO_POOL)

    # Use a rich beneficiary object instead of just string if available
    beneficiary = random.choice(state.rich_beneficiaries) if state.rich_beneficiaries else {"beneficiary_id": state.known_beneficiary()}

    return {
        "txn_id": new_uuid(),
        "identity_id": state.identity_id,
        "timestamp": jittered_now(),
        "amount": round(amount, 2),
        "currency": "INR" if not is_cross_border else random.choice(["USD", "EUR", "GBP"]),
        "channel": channel,
        "merchant_name": merchant_name,
        "location": location,
        "beneficiary_id": beneficiary["beneficiary_id"],
        "beneficiary_is_new": False,
        "session_id": f"sess-{new_uuid()[:8]}",
        "is_cross_border": is_cross_border,
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
