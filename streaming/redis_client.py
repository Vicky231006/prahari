import json
import redis
from .config import settings

class RedisClient:
    def __init__(self):
        self.client = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            decode_responses=True
        )

    def get_identity_profile(self, identity_id: str) -> dict:
        """
        Retrieve identity rolling behavioural baseline from Redis (Section 5).
        Returns a dict with avg_txn_amount, login_time_distribution, known_devices, known_beneficiaries.
        If missing, returns default baseline state.
        """
        profile_json = self.client.get(f"profile:{identity_id}")
        if profile_json:
            try:
                return json.loads(profile_json)
            except json.JSONDecodeError:
                pass
        
        # Default baseline
        return {
            "identity_id": identity_id,
            "avg_txn_amount": 5000.0,
            "txn_count": 1,
            "known_devices": [],
            "known_beneficiaries": [],
            "usual_ips": [],
            "login_time_distribution": {},
            "risk_score": 0.0
        }

    def save_identity_profile(self, identity_id: str, profile: dict, ttl: int = 86400):
        """Save identity baseline to Redis with a TTL."""
        self.client.setex(f"profile:{identity_id}", ttl, json.dumps(profile))

    def add_security_event(self, identity_id: str, event: dict, window_seconds: int = 900):
        """
        Add security event to the identity's sliding window in Redis.
        Uses sorted sets where score is timestamp.
        """
        event_str = json.dumps(event)
        timestamp = float(event.get("timestamp_epoch", 0.0))
        if timestamp == 0.0:
            # Parse ISO string if epoch is not present
            from datetime import datetime
            try:
                dt = datetime.fromisoformat(event["timestamp"].replace("Z", "+00:00"))
                timestamp = dt.timestamp()
            except Exception:
                import time
                timestamp = time.time()

        key = f"window:security:{identity_id}"
        self.client.zadd(key, {event_str: timestamp})
        
        # Remove events older than window
        cutoff = timestamp - window_seconds
        self.client.zremrangebyscore(key, "-inf", cutoff)
        # Set expiry for the key itself to prevent memory leaks
        self.client.expire(key, window_seconds * 2)

    def add_transaction_event(self, identity_id: str, event: dict, window_seconds: int = 900):
        """
        Add transaction event to the identity's sliding window in Redis.
        Uses sorted sets where score is timestamp.
        """
        event_str = json.dumps(event)
        timestamp = float(event.get("timestamp_epoch", 0.0))
        if timestamp == 0.0:
            from datetime import datetime
            try:
                dt = datetime.fromisoformat(event["timestamp"].replace("Z", "+00:00"))
                timestamp = dt.timestamp()
            except Exception:
                import time
                timestamp = time.time()

        key = f"window:transactions:{identity_id}"
        self.client.zadd(key, {event_str: timestamp})
        
        # Remove events older than window
        cutoff = timestamp - window_seconds
        self.client.zremrangebyscore(key, "-inf", cutoff)
        self.client.expire(key, window_seconds * 2)

    def get_window_events(self, identity_id: str, window_seconds: int = 900) -> tuple[list[dict], list[dict]]:
        """
        Retrieve all security and transaction events in the active sliding window.
        Returns (security_events, transaction_events) sorted by timestamp.
        """
        import time
        now = time.time()
        cutoff = now - window_seconds

        # Fetch security events
        sec_key = f"window:security:{identity_id}"
        self.client.zremrangebyscore(sec_key, "-inf", cutoff)
        sec_raw = self.client.zrange(sec_key, 0, -1)
        security_events = []
        for r in sec_raw:
            try:
                security_events.append(json.loads(r))
            except Exception:
                pass

        # Fetch txn events
        txn_key = f"window:transactions:{identity_id}"
        self.client.zremrangebyscore(txn_key, "-inf", cutoff)
        txn_raw = self.client.zrange(txn_key, 0, -1)
        transaction_events = []
        for r in txn_raw:
            try:
                transaction_events.append(json.loads(r))
            except Exception:
                pass

        return security_events, transaction_events

    def get_quantum_stats(self) -> dict:
        """Get summarized counts for quantum inventory (legacy vs pqc_ready sessions)."""
        stats_json = self.client.get("kpi:quantum_stats")
        if stats_json:
            try:
                return json.loads(stats_json)
            except Exception:
                pass
        return {"legacy_count": 0, "pqc_ready_count": 0, "hybrid_count": 0, "hndl_exposed_count": 0}

    def set_quantum_stats(self, stats: dict):
        """Set summarized counts for quantum inventory with 60s TTL."""
        self.client.setex("kpi:quantum_stats", 60, json.dumps(stats))

    def update_quantum_counts(self, classification: str, is_hndl: bool):
        """Atomically increment quantum session counters in Redis."""
        key = "kpi:quantum_raw"
        self.client.hincrby(key, f"count_{classification}", 1)
        if is_hndl:
            self.client.hincrby(key, "count_hndl", 1)
        
        # Refresh the cached kpi:quantum_stats
        raw = self.client.hgetall(key)
        stats = {
            "legacy_count": int(raw.get("count_legacy", 0)),
            "pqc_ready_count": int(raw.get("count_pqc_ready", 0)),
            "hybrid_count": int(raw.get("count_hybrid", 0)),
            "hndl_exposed_count": int(raw.get("count_hndl", 0))
        }
        self.set_quantum_stats(stats)
