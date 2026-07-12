import time
from datetime import datetime, timezone, timedelta

def extract_features(
    identity_id: str,
    security_events: list[dict],
    transaction_events: list[dict],
    profile: dict
) -> dict:
    """
    Extract the 12 feature values expected by the LightGBM fusion model.
    
    Expected features:
    - hour_of_day
    - txn_amount_zscore
    - beneficiary_is_new
    - txn_velocity_1h
    - off_hours_txn_flag
    - cross_border_flag
    - new_device_flag
    - impossible_travel_flag
    - failed_auth_count_1h
    - privileged_cmd_count_1h
    - endpoint_alert_count_1h
    - joint_window_overlap_flag
    """
    # 1. Hour of day (IST is UTC + 5:30)
    now_ist = datetime.now(timezone.utc) + timedelta(hours=5, minutes=30)
    hour_of_day = now_ist.hour

    # 2. Transaction features
    avg_txn = float(profile.get("avg_txn_amount", 5000.0))
    # We estimate standard deviation as 50% of the average transaction amount
    std_txn = max(avg_txn * 0.5, 1.0)
    
    txn_amount_zscore = 0.0
    beneficiary_is_new = 0
    txn_velocity_1h = len(transaction_events)
    off_hours_txn_flag = 0
    cross_border_flag = 0

    if transaction_events:
        # Get the latest transaction in the window
        latest_txn = sorted(transaction_events, key=lambda x: x.get("timestamp", ""))[-1]
        amount = float(latest_txn.get("amount", 0.0))
        txn_amount_zscore = (amount - avg_txn) / std_txn
        
        # Check beneficiary
        beneficiary_id = latest_txn.get("beneficiary_id")
        known_beneficiaries = profile.get("known_beneficiaries", [])
        if latest_txn.get("beneficiary_is_new") or (beneficiary_id and beneficiary_id not in known_beneficiaries):
            beneficiary_is_new = 1
            
        # Off hours txn flag (18:00 to 09:00 IST)
        try:
            dt = datetime.fromisoformat(latest_txn["timestamp"].replace("Z", "+00:00"))
            dt_ist = dt + timedelta(hours=5, minutes=30)
            if dt_ist.hour >= 18 or dt_ist.hour < 9:
                off_hours_txn_flag = 1
        except Exception:
            if hour_of_day >= 18 or hour_of_day < 9:
                off_hours_txn_flag = 1
                
        # Cross border flag
        if latest_txn.get("is_cross_border"):
            cross_border_flag = 1

    # 3. Security features
    new_device_flag = 0
    impossible_travel_flag = 0
    failed_auth_count_1h = 0
    privileged_cmd_count_1h = 0
    endpoint_alert_count_1h = 0

    for sec in security_events:
        risk_flags = sec.get("risk_flags", [])
        event_type = sec.get("event_type")
        
        if sec.get("is_new_device") or "new_device" in risk_flags:
            new_device_flag = 1
            
        if "impossible_travel" in risk_flags:
            impossible_travel_flag = 1
            
        if "failed_login" in risk_flags:
            failed_auth_count_1h += 1
            
        if event_type == "privileged_cmd":
            privileged_cmd_count_1h += 1
            
        if event_type == "endpoint_alert" or any(flag in risk_flags for flag in ["port_scan", "exfiltration", "lateral_movement", "c2_beaconing"]):
            endpoint_alert_count_1h += 1

    # 4. Joint overlap flag
    joint_window_overlap_flag = 1 if (len(security_events) > 0 and len(transaction_events) > 0) else 0

    return {
        "hour_of_day": int(hour_of_day),
        "txn_amount_zscore": float(txn_amount_zscore),
        "beneficiary_is_new": int(beneficiary_is_new),
        "txn_velocity_1h": int(txn_velocity_1h),
        "off_hours_txn_flag": int(off_hours_txn_flag),
        "cross_border_flag": int(cross_border_flag),
        "new_device_flag": int(new_device_flag),
        "impossible_travel_flag": int(impossible_travel_flag),
        "failed_auth_count_1h": int(failed_auth_count_1h),
        "privileged_cmd_count_1h": int(privileged_cmd_count_1h),
        "endpoint_alert_count_1h": int(endpoint_alert_count_1h),
        "joint_window_overlap_flag": int(joint_window_overlap_flag)
    }
