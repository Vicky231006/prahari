# ⚠️ System Limitations & Known Constraints

As a prototype built for demonstration and evaluation purposes, **PRAHARI** contains design tradeoffs and simplified modules. What follows is an honest engineering assessment of the current system's limitations and known constraints.

---

## 1. Machine Learning Fusion Classifier (Active Fallback)
The pipeline is designed to extract a 12-dimensional feature vector from Redis sliding windows and query the Fusion Classifier Service.
- **The Limitation**: The endpoint (`POST /internal/fusion/score` in `services/fusion_classifier/main.py`) loads a pre-trained LightGBM model (`fusion_model.joblib`). However, due to version skew during environment setups, the service may issue an `InconsistentVersionWarning`. 
- **The Constraint**: If the classifier encounters issues loading the joblib file, it gracefully falls back to a deterministic, weighted scoring engine. In production, this requires maintaining strict Python packaging parity and model registry pipelines (e.g., MLflow).

---

## 2. Authentication & Security Middleware
While JWT verification variables (`JWT_SECRET`) are configured in `.env`, the FastAPI gateway endpoints do not enforce strict auth tokens.
- **The Limitation**: Endpoints such as `POST /api/alerts/{id}/escalate` and `POST /api/alerts/{id}/dismiss` are open to facilitate testing.
- **The Constraint**: Security tokens are bypassed to allow the judging panel to execute scenarios and interact with UI action buttons without configuring OAuth2/OIDC providers locally. Production versions must enforce OAuth2/JWT middleware blocks on all REST/WebSocket routes.

---

## 3. Synthetic Data Coverage
The system uses realistic, mathematically derived synthetic transactions and events.
- **The Limitation**: The normal banking telemetry runs on log-normal distributions (median ~₹4,900) biased toward business hours.
- **The Constraint**: Real-world transactions exhibit higher noise, extreme outliers, complex seasonal fluctuations, and high rates of legitimate cross-border travel. The rule thresholds and LGBM model would need to be retrained on anonymized real production data to avoid high false-positive rates in a real banking environment.

---

## 4. Single-Node Sandbox Deployment
The system architecture runs inside a docker-compose sandbox.

> [!WARNING]
> The default configuration is optimized for single-machine demonstration, not production scale:
> *   **Kafka**: Runs in single-node KRaft mode. Production requires multi-broker replication with ZooKeeper/KRaft controller clusters.
> *   **Redis**: Single-node instance with LRU cache eviction. Production requires Redis Sentinel or Redis Cluster for failover.
> *   **PostgreSQL**: Single database instance. Production demands high-availability replication (e.g., AWS Aurora or PGPool-II).
> *   **Flink/Streaming Processing**: Implemented as local Python consumer loops rather than a distributed Apache Flink Cluster.

---

## 5. ChromaDB & Gemini RAG Fallbacks
The Explanation Drawer streams AI analyses citing regional compliance guidelines.
- **The Limitation**: If a `GEMINI_API_KEY` is not provided in `.env`, the RAG explanation service dynamically falls back to a template-based explanation parser.
- **The Constraint**: Vector lookups to ChromaDB are still executed, but the final text output is structured statically based on the contributing signals rather than dynamically generated.