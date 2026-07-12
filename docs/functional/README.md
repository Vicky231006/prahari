# Functional Documentation

## User Flow
1. **Analyst Dashboard**: The analyst logs into the dashboard (Progressive Disclosure Level 1). They see high-level KPIs, avoiding alert fatigue.
2. **Alert Drill-down**: The analyst clicks the "Total Active Anomalies" card to view the alert queue (Level 2).
3. **Investigation**: Clicking a specific alert opens the Explanation Drawer (Level 3).
4. **Resolution**: The analyst reads the RAG-generated explanation (citing RBI controls) and uses the Case Action bar to Escalate or Dismiss the alert. This is logged to the immutable Audit Trail.

## Logic Flow (Streaming Pipeline)
1. **Ingestion**: Raw telemetry arrives on three Kafka topics: `security-telemetry`, `transaction-events`, and `tls-handshake`.
2. **State Management**: `redis_client.py` maintains a rolling behavioural baseline for each identity and a sliding 15-minute event buffer.
3. **Fusion Correlation**: Flink jobs monitor the 15-minute buffers. If an anomaly is detected, a 12-feature vector is extracted and sent to the Fusion Classifier Service.
4. **Classification**: The LightGBM model outputs a continuous probability score. High scores emit an alert to the `fusion-alerts` topic.
5. **Gateway Processing**: The FastAPI gateway consumes the alert, persists it to Postgres, invalidates Redis KPI caches, triggers the RAG service, and broadcasts the alert via WebSocket to the React UI.
