import pytest
from streaming.fusion.features import extract_features

def test_extract_features(sample_security_event, sample_transaction_event):
    # Setup test baseline profile
    profile = {
        "avg_txn_amount": 5000.0,
        "known_beneficiaries": ["BEN-001"],
        "known_devices": ["fp-abcdef123456"]
    }

    # Test benign scenario (no alerts, existing device, existing beneficiary, standard transaction)
    features = extract_features(
        identity_id="ID-TEST-001",
        security_events=[sample_security_event],
        transaction_events=[sample_transaction_event],
        profile=profile
    )

    # Assert correct keys are returned
    expected_keys = {
        "hour_of_day", "txn_amount_zscore", "beneficiary_is_new", "txn_velocity_1h",
        "off_hours_txn_flag", "cross_border_flag", "new_device_flag", "impossible_travel_flag",
        "failed_auth_count_1h", "privileged_cmd_count_1h", "endpoint_alert_count_1h",
        "joint_window_overlap_flag"
    }
    assert set(features.keys()) == expected_keys

    # Assert specific feature values for standard benign flow
    assert features["beneficiary_is_new"] == 0
    assert features["txn_velocity_1h"] == 1
    assert features["new_device_flag"] == 0
    assert features["impossible_travel_flag"] == 0
    assert features["failed_auth_count_1h"] == 0
    assert features["privileged_cmd_count_1h"] == 0
    assert features["endpoint_alert_count_1h"] == 0
    assert features["joint_window_overlap_flag"] == 1

    # Test anomalous scenario (ATO characteristics)
    ato_sec = sample_security_event.copy()
    ato_sec["risk_flags"] = ["impossible_travel", "new_device"]
    ato_sec["is_new_device"] = True

    ato_txn = sample_transaction_event.copy()
    ato_txn["amount"] = 50000.0  # High z-score
    ato_txn["beneficiary_id"] = "BEN-ATO-VICTIM"
    ato_txn["beneficiary_is_new"] = True

    features_ato = extract_features(
        identity_id="ID-TEST-001",
        security_events=[ato_sec],
        transaction_events=[ato_txn],
        profile=profile
    )

    assert features_ato["new_device_flag"] == 1
    assert features_ato["impossible_travel_flag"] == 1
    assert features_ato["beneficiary_is_new"] == 1
    assert features_ato["txn_amount_zscore"] > 2.0  # (50k - 5k) / 2.5k = 18.0
    assert features_ato["joint_window_overlap_flag"] == 1
