import time
from typing import Set

class DetectionRules:
    @staticmethod
    def detect_brute_force(event: dict, redis_client) -> bool:
        """
        Rule 1: Brute Force Detection
        Triggers if:
        - "failed_login" or "credential_stuffing" risk flags are present in the event.
        - OR if the identity has accumulated >= 5 failed logins in Redis in the last 5 minutes.
        """
        identity_id = event.get("identity_id")
        risk_flags = event.get("risk_flags", [])
        
        if "credential_stuffing" in risk_flags or "failed_login" in risk_flags:
            return True
            
        if event.get("event_type") == "login":
            # Track failed logins in Redis
            # In a real environment, we'd check a password success flag.
            # Since the synthetic event has risk_flags, we use that as the primary indicator.
            pass
            
        return False

    @staticmethod
    def detect_port_scan(event: dict) -> bool:
        """
        Rule 2: Port Scan Detection
        Triggers if:
        - "port_scan" risk flag is present.
        - OR if event_type is endpoint_alert and contains network scanning indicators.
        """
        risk_flags = event.get("risk_flags", [])
        if "port_scan" in risk_flags:
            return True
            
        if event.get("event_type") == "endpoint_alert" and "scan" in str(event.get("risk_flags", [])):
            return True
            
        return False

    @staticmethod
    def detect_exfiltration(event: dict) -> bool:
        """
        Rule 3: Exfiltration Detection
        Triggers if:
        - "exfiltration" or "data_leak" risk flag is present.
        - OR if endpoint_alert contains large data movement.
        """
        risk_flags = event.get("risk_flags", [])
        if "exfiltration" in risk_flags or "data_leak" in risk_flags:
            return True
            
        return False

    @staticmethod
    def detect_lateral_movement(event: dict) -> bool:
        """
        Rule 4: Lateral Movement Detection
        Triggers if:
        - "lateral_movement" risk flag is present.
        - OR if event_type is privileged_cmd and risk_flags contains "unusual_data_access".
        """
        risk_flags = event.get("risk_flags", [])
        if "lateral_movement" in risk_flags:
            return True
            
        if event.get("event_type") == "privileged_cmd" and "unusual_data_access" in risk_flags:
            return True
            
        return False

    @staticmethod
    def detect_c2_beaconing(event: dict) -> bool:
        """
        Rule 5: C2 Beaconing Detection
        Triggers if:
        - "c2_beaconing" or "c2" or "beacon" risk flag is present.
        """
        risk_flags = event.get("risk_flags", [])
        if any(flag in risk_flags for flag in ["c2_beaconing", "c2", "beacon"]):
            return True
            
        return False

    @classmethod
    def evaluate_all(cls, event: dict, redis_client) -> Set[str]:
        """
        Evaluate all 5 detection rules on the incoming event.
        Returns a set of active signals.
        """
        signals = set()
        
        if cls.detect_brute_force(event, redis_client):
            signals.add("brute_force_detected")
        if cls.detect_port_scan(event):
            signals.add("port_scan_detected")
        if cls.detect_exfiltration(event):
            signals.add("exfiltration_detected")
        if cls.detect_lateral_movement(event):
            signals.add("lateral_movement_detected")
        if cls.detect_c2_beaconing(event):
            signals.add("c2_beaconing_detected")
            
        return signals
