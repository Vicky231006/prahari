"""
Main entry point for PRAHARI synthetic data generators.

Runs all three event generators (security-telemetry, transaction-events,
tls-handshake) and the scenario injector concurrently as threads.

Usage:
  python -m data.synthetic.generators.run_generators

Environment:
  KAFKA_BOOTSTRAP_SERVERS  — Kafka broker address (default: localhost:9094)
"""
import json
import os
import signal
import sys
import threading
import time

from .base import IDENTITY_POOL, IdentityState, make_producer
from .scenario_injector import run_scenario_injector
from .security_telemetry_gen import run_security_generator
from .tls_handshake_gen import run_tls_generator
from .transaction_gen import run_transaction_generator


def main():
    print("=" * 60)
    print("PRAHARI Synthetic Data Generators")
    print("=" * 60)

    # Build shared identity state pool
    print(f"[init] Building identity state for {len(IDENTITY_POOL)} identities...")
    identity_states: dict[str, IdentityState] = {}
    for iid in IDENTITY_POOL:
        identity_states[iid] = IdentityState(iid)

    # Link some identities for insider-collusion scenarios (Section 3 scenario 2)
    for i in range(0, 50, 2):
        id_a = IDENTITY_POOL[i]
        id_b = IDENTITY_POOL[50 + i] if (50 + i) < len(IDENTITY_POOL) else IDENTITY_POOL[i + 1]
        identity_states[id_a].linked_identities.append(id_b)
        identity_states[id_b].linked_identities.append(id_a)

    print("[init] Seeding identity profiles to Redis and Postgres...")
    try:
        import redis
        import httpx
        
        # 1. Seed Redis
        redis_host = os.environ.get("REDIS_HOST", "localhost")
        redis_port = int(os.environ.get("REDIS_PORT", "6379"))
        r = redis.Redis(host=redis_host, port=redis_port, decode_responses=True)
        
        profiles = [state.get_profile_dict() for state in identity_states.values()]
        
        for p in profiles:
            r.setex(f"profile:{p['identity_id']}", 86400, json.dumps(p))
        print(f"[init] Seeded {len(profiles)} profiles to Redis.")
        
        # 2. Seed Postgres via Gateway API
        # The API might take a few seconds to boot, retry loop
        gateway_url = os.environ.get("GATEWAY_URL", "http://gateway:8080")
        sync_url = f"{gateway_url}/api/internal/identities/sync"
        
        for attempt in range(10):
            try:
                resp = httpx.post(sync_url, json=profiles, timeout=5)
                if resp.status_code == 200:
                    print(f"[init] Successfully synced {len(profiles)} profiles to Postgres via Gateway API.")
                    break
                else:
                    print(f"[init] Gateway API returned {resp.status_code}: {resp.text}")
            except httpx.RequestError as e:
                print(f"[init] Waiting for Gateway API to be ready (attempt {attempt+1}/10)...")
                time.sleep(5)
    except Exception as e:
        print(f"[init] Failed to seed identity profiles: {e}")

    # Create Kafka producer
    producer = make_producer()
    print(f"[init] Kafka producer created")

    # Graceful shutdown
    stop_event = threading.Event()

    def shutdown_handler(signum, frame):
        print("\n[shutdown] Stopping all generators...")
        stop_event.set()

    signal.signal(signal.SIGINT, shutdown_handler)
    signal.signal(signal.SIGTERM, shutdown_handler)

    # Start generator threads
    threads = [
        threading.Thread(
            target=run_security_generator,
            args=(identity_states, producer),
            kwargs={"events_per_second": 10.0, "stop_event": stop_event},
            name="security-telemetry-gen",
            daemon=True,
        ),
        threading.Thread(
            target=run_transaction_generator,
            args=(identity_states, producer),
            kwargs={"events_per_second": 8.0, "stop_event": stop_event},
            name="transaction-gen",
            daemon=True,
        ),
        threading.Thread(
            target=run_tls_generator,
            args=(producer,),
            kwargs={"events_per_second": 5.0, "stop_event": stop_event},
            name="tls-handshake-gen",
            daemon=True,
        ),
        threading.Thread(
            target=run_scenario_injector,
            args=(identity_states, producer),
            kwargs={"injection_interval_seconds": 30.0, "stop_event": stop_event},
            name="scenario-injector",
            daemon=True,
        ),
    ]

    for t in threads:
        t.start()
        print(f"[init] Started thread: {t.name}")

    print("[init] All generators running. Press Ctrl+C to stop.")
    print("=" * 60)

    # Wait for stop signal
    try:
        while not stop_event.is_set():
            time.sleep(1)
    except KeyboardInterrupt:
        stop_event.set()

    # Flush remaining messages
    print("[shutdown] Flushing Kafka producer...")
    producer.flush(timeout=10)
    print("[shutdown] Done.")
    sys.exit(0)


if __name__ == "__main__":
    main()
