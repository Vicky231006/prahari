import pytest
from streaming.detection.rules import DetectionRules

def test_detection_rules(sample_security_event):
    # Test normal event
    signals = DetectionRules.evaluate_all(sample_security_event, redis_client=None)
    assert signals == set()

    # Test brute force (credential stuffing)
    cs_event = sample_security_event.copy()
    cs_event["risk_flags"] = ["credential_stuffing"]
    signals = DetectionRules.evaluate_all(cs_event, redis_client=None)
    assert "brute_force_detected" in signals

    # Test brute force (failed login flag)
    fl_event = sample_security_event.copy()
    fl_event["risk_flags"] = ["failed_login"]
    signals = DetectionRules.evaluate_all(fl_event, redis_client=None)
    assert "brute_force_detected" in signals

    # Test port scan
    ps_event = sample_security_event.copy()
    ps_event["risk_flags"] = ["port_scan"]
    signals = DetectionRules.evaluate_all(ps_event, redis_client=None)
    assert "port_scan_detected" in signals

    # Test exfiltration
    ex_event = sample_security_event.copy()
    ex_event["risk_flags"] = ["exfiltration"]
    signals = DetectionRules.evaluate_all(ex_event, redis_client=None)
    assert "exfiltration_detected" in signals

    # Test lateral movement
    lm_event = sample_security_event.copy()
    lm_event["risk_flags"] = ["lateral_movement"]
    signals = DetectionRules.evaluate_all(lm_event, redis_client=None)
    assert "lateral_movement_detected" in signals

    # Test lateral movement via privileged command with unusual data access
    pc_event = sample_security_event.copy()
    pc_event["event_type"] = "privileged_cmd"
    pc_event["risk_flags"] = ["unusual_data_access"]
    signals = DetectionRules.evaluate_all(pc_event, redis_client=None)
    assert "lateral_movement_detected" in signals

    # Test C2 beaconing
    c2_event = sample_security_event.copy()
    c2_event["risk_flags"] = ["c2_beaconing"]
    signals = DetectionRules.evaluate_all(c2_event, redis_client=None)
    assert "c2_beaconing_detected" in signals
