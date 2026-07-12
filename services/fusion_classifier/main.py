import os
from typing import Dict, Any, List
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import joblib
import pandas as pd

app = FastAPI(
    title="PRAHARI Fusion Classifier Service",
    description="Microservice hosting the LightGBM/scikit-learn joint correlation model",
    version="1.0.0"
)

# Request schema
class FeatureRequest(BaseModel):
    identity_id: str
    features: Dict[str, Any]

# Response schema
class ScorerResponse(BaseModel):
    fusion_score: float
    severity: str
    contributing_signals: List[str]

# Global model container
model = None
MODEL_PATH = os.getenv("MODEL_PATH", "fusion_model.joblib")

@app.on_event("startup")
def load_model():
    global model
    if not os.path.exists(MODEL_PATH):
        print(f"[warning] Model file not found at {MODEL_PATH}, using dummy rules mode")
        model = None
        return
        
    try:
        model = joblib.load(MODEL_PATH)
        print(f"[init] Successfully loaded Fusion Classifier model from {MODEL_PATH}")
        print(f"[init] Model expects features: {getattr(model, 'feature_names_in_', 'N/A')}")
    except Exception as e:
        print(f"[error] Failed to load model: {e}")
        model = None

@app.post("/internal/fusion/score", response_model=ScorerResponse)
async def score_features(req: FeatureRequest):
    """
    Score the feature vector using LightGBM model.
    Falls back to a robust rule-based scorer if the model fails to load.
    """
    features_dict = req.features
    
    # Extract features matching the model's exact expected names and order
    expected_features = [
        'hour_of_day', 'txn_amount_zscore', 'beneficiary_is_new', 'txn_velocity_1h',
        'off_hours_txn_flag', 'cross_border_flag', 'new_device_flag',
        'impossible_travel_flag', 'failed_auth_count_1h', 'privileged_cmd_count_1h',
        'endpoint_alert_count_1h', 'joint_window_overlap_flag'
    ]

    # Calculate contributing signals list for visibility
    contributing = []
    if features_dict.get("impossible_travel_flag"):
        contributing.append("impossible_travel")
    if features_dict.get("new_device_flag"):
        contributing.append("new_device")
    if features_dict.get("beneficiary_is_new"):
        contributing.append("new_beneficiary")
    if features_dict.get("cross_border_flag"):
        contributing.append("cross_border_transaction")
    if features_dict.get("off_hours_txn_flag"):
        contributing.append("off_hours_transaction")
    if features_dict.get("txn_velocity_1h", 0) > 3:
        contributing.append("high_transaction_velocity")
    if features_dict.get("failed_auth_count_1h", 0) > 0:
        contributing.append(f"failed_logins_count_{features_dict['failed_auth_count_1h']}")
    if features_dict.get("privileged_cmd_count_1h", 0) > 0:
        contributing.append("privileged_commands_executed")
    if features_dict.get("endpoint_alert_count_1h", 0) > 0:
        contributing.append("endpoint_security_alerts")

    # If the loaded model is available, use it
    if model is not None:
        try:
            # Build input DataFrame
            input_df = pd.DataFrame([{f: features_dict.get(f, 0) for f in expected_features}])
            
            # Predict probabilities
            probabilities = model.predict_proba(input_df)
            fusion_score = float(probabilities[0][1]) # Class 1 probability
        except Exception as e:
            print(f"[scorer-err] Model prediction failed: {e}. Falling back to rule-based.")
            fusion_score = None
    else:
        fusion_score = None

    # Fallback/Interim scorer (Section 6 contract)
    if fusion_score is None:
        score = 0.0
        if features_dict.get("impossible_travel_flag"):
            score += 0.35
        if features_dict.get("new_device_flag"):
            score += 0.20
        if features_dict.get("beneficiary_is_new"):
            score += 0.25
        if float(features_dict.get("txn_amount_zscore", 0)) > 2.0:
            score += 0.15
        elif float(features_dict.get("txn_amount_zscore", 0)) > 4.0:
            score += 0.30
            
        score += min(int(features_dict.get("failed_auth_count_1h", 0)) * 0.10, 0.30)
        score += min(int(features_dict.get("privileged_cmd_count_1h", 0)) * 0.15, 0.30)
        score += min(int(features_dict.get("endpoint_alert_count_1h", 0)) * 0.15, 0.30)
        
        # Joint window overlap boost
        if features_dict.get("joint_window_overlap_flag"):
            score = score * 1.4
            
        fusion_score = min(max(score, 0.0), 1.0)

    # Determine severity
    if fusion_score >= 0.85:
        severity = "critical"
    elif fusion_score >= 0.65:
        severity = "high"
    elif fusion_score >= 0.35:
        severity = "medium"
    else:
        severity = "low"

    return ScorerResponse(
        fusion_score=fusion_score,
        severity=severity,
        contributing_signals=contributing
    )
