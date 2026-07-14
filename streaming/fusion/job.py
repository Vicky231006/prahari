import json
import time
import requests
from datetime import datetime, timezone
from confluent_kafka import Producer
from ..redis_client import RedisClient
from ..config import settings
from .features import extract_features
from ..detection.rules import DetectionRules

class IdentityFusionJob:
    def __init__(self, redis_client: RedisClient, kafka_producer: Producer):
        self.redis_client = redis_client
        self.kafka_producer = kafka_producer
        self.classifier_url = "http://localhost:8081/internal/fusion/score" # Local default, overridden in docker env

    def process_security_event(self, event: dict):
        """Process incoming security telemetry event."""
        identity_id = event.get("identity_id")
        if not identity_id:
            return

        # Run 5 detection rules to extract active signals
        active_signals = DetectionRules.evaluate_all(event, self.redis_client)
        if active_signals:
            event["risk_flags"] = list(set(event.get("risk_flags", []) + list(active_signals)))

        # Update Redis sliding window
        self.redis_client.add_security_event(identity_id, event, settings.FUSION_WINDOW_SECONDS)

        # Update identity profile with IP and device
        profile = self.redis_client.get_identity_profile(identity_id)
        if event.get("device_fingerprint") and event["device_fingerprint"] not in profile.get("known_devices", []):
            profile["known_devices"].append(event["device_fingerprint"])
        if event.get("source_ip") and event["source_ip"] not in profile.get("usual_ips", []):
            profile["usual_ips"].append(event["source_ip"])
        self.redis_client.save_identity_profile(identity_id, profile)

        # Evaluate fusion window
        self.evaluate_fusion(identity_id)

    def process_transaction_event(self, event: dict):
        """Process incoming transaction event."""
        identity_id = event.get("identity_id")
        if not identity_id:
            return

        # Update Redis sliding window
        self.redis_client.add_transaction_event(identity_id, event, settings.FUSION_WINDOW_SECONDS)

        # Update identity profile baseline
        profile = self.redis_client.get_identity_profile(identity_id)
        
        # Recalculate average transaction amount
        amount = float(event.get("amount", 0.0))
        txn_count = int(profile.get("txn_count", 0)) + 1
        old_avg = float(profile.get("avg_txn_amount", 5000.0))
        new_avg = ((old_avg * (txn_count - 1)) + amount) / txn_count
        
        profile["avg_txn_amount"] = new_avg
        profile["txn_count"] = txn_count
        
        beneficiary_id = event.get("beneficiary_id")
        if beneficiary_id and beneficiary_id not in profile.get("known_beneficiaries", []):
            profile["known_beneficiaries"].append(beneficiary_id)
            
        self.redis_client.save_identity_profile(identity_id, profile)

        # Evaluate fusion window
        self.evaluate_fusion(identity_id)

    def evaluate_fusion(self, identity_id: str):
        """Perform joint window correlation and call classifier."""
        # Retrieve window events
        security_events, transaction_events = self.redis_client.get_window_events(
            identity_id, settings.FUSION_WINDOW_SECONDS
        )

        # Don't evaluate if window is completely empty
        if not security_events and not transaction_events:
            return

        # Fetch profile baseline
        profile = self.redis_client.get_identity_profile(identity_id)

        # Extract feature vector
        features = extract_features(identity_id, security_events, transaction_events, profile)

        # Run scoring logic (try classifier microservice first; fall back to local rule-based)
        fusion_score, severity, contributing_signals = self.get_fusion_score(identity_id, features, security_events, transaction_events)

        # Check if we should emit alert
        # Trigger condition (Section 4): Both security and txn signals fire in same window, OR fusion_score crosses threshold (e.g. >= 0.35)
        has_security = len(security_events) > 0
        has_txn = len(transaction_events) > 0
        both_channels_fired = has_security and has_txn
        
        # Continuous score threshold
        score_threshold = 0.35

        if both_channels_fired or fusion_score >= score_threshold:
            # Aggregate contributing signals
            all_signals = list(set(contributing_signals))
            
            # Formulate alert payload
            alert_id = f"alert-{int(time.time())}-{identity_id}"
            
            # Find scenario labels if they exist (for Synthetic training/audit)
            scenario_type = None
            is_synthetic_positive = False
            for ev in security_events + transaction_events:
                if ev.get("is_synthetic_positive"):
                    is_synthetic_positive = True
                    scenario_type = ev.get("scenario_type")
                    break

            alert = {
                "alert_id": alert_id,
                "identity_id": identity_id,
                "fusion_score": float(fusion_score),
                "severity": severity,
                "contributing_signals": all_signals,
                "features": features,
                "raw_events": {
                    "security": security_events,
                    "transactions": transaction_events,
                },
                "window_start": min(
                    [ev.get("timestamp") for ev in security_events + transaction_events if ev.get("timestamp")] or [datetime.now(timezone.utc).isoformat()]
                ),
                "window_end": max(
                    [ev.get("timestamp") for ev in security_events + transaction_events if ev.get("timestamp")] or [datetime.now(timezone.utc).isoformat()]
                ),
                "scenario_type": scenario_type,
                "is_synthetic_positive": is_synthetic_positive,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

            # Emit to fusion-alerts topic
            self.kafka_producer.produce(
                topic=settings.TOPIC_FUSION_ALERTS,
                key=identity_id.encode("utf-8"),
                value=json.dumps(alert).encode("utf-8")
            )
            self.kafka_producer.flush()
            print(f"[fusion-job] Emitted Fused Alert for {identity_id} (Score: {fusion_score:.2f}, Severity: {severity})")

    def get_fusion_score(
        self,
        identity_id: str,
        features: dict,
        security_events: list,
        transaction_events: list
    ) -> tuple[float, str, list[str]]:
        """
        Calculates fusion score. Attempts to contact fusion-classifier FastAPI endpoint first,
        otherwise falls back to rule-based evaluation.
        """
        # Collect contributing signals
        contributing_signals = []
        for sec in security_events:
            contributing_signals.extend(sec.get("risk_flags", []))
            if sec.get("event_type") == "login":
                contributing_signals.append("login_activity")
            elif sec.get("event_type") == "privileged_cmd":
                contributing_signals.append("privileged_cmd_exec")
                
        for txn in transaction_events:
            contributing_signals.append(f"txn_{txn.get('channel')}")
            if txn.get("beneficiary_is_new"):
                contributing_signals.append("new_beneficiary_txn")
            if txn.get("is_cross_border"):
                contributing_signals.append("cross_border_txn")

        # Try to call the fusion-classifier service
        try:
            # Timeout quick so we don't block streaming pipeline
            resp = requests.post(
                self.classifier_url,
                json={"identity_id": identity_id, "features": features},
                timeout=0.5
            )
            if resp.status_code == 200:
                data = resp.json()
                return (
                    float(data["fusion_score"]),
                    data["severity"],
                    list(set(contributing_signals + data.get("contributing_signals", [])))
                )
        except Exception:
            # Fall back to rule-based scoring (Section 6 contract)
            pass

        # ── Rule-Based Scorer (Interim Scorer) ──
        # Base score from features
        score = 0.0
        
        # Accumulate weights
        if features["impossible_travel_flag"]:
            score += 0.35
        if features["new_device_flag"]:
            score += 0.20
        if features["beneficiary_is_new"]:
            score += 0.25
        if features["txn_amount_zscore"] > 2.0:
            score += 0.15
        elif features["txn_amount_zscore"] > 4.0:
            score += 0.30
            
        score += min(features["failed_auth_count_1h"] * 0.10, 0.30)
        score += min(features["privileged_cmd_count_1h"] * 0.15, 0.30)
        score += min(features["endpoint_alert_count_1h"] * 0.15, 0.30)
        
        # Joint window overlap boost (Section 4: Fused signals get boosted confidence)
        if features["joint_window_overlap_flag"]:
            score = score * 1.4
            
        # Bound score
        score = min(max(score, 0.0), 1.0)

        # Map score to severity
        if score >= 0.85:
            severity = "critical"
        elif score >= 0.65:
            severity = "high"
        elif score >= 0.35:
            severity = "medium"
        else:
            severity = "low"

        return score, severity, contributing_signals
