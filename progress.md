# PRAHARI — Implementation Progress Log

> Last updated: 2026-07-12 21:58 IST
> Commit: `257d8b8` ("phase 3.5 completed") on `main`

---

## Phase 1 — Repo Skeleton & Infrastructure (COMPLETE ✅)

### What was built
- **Docker Compose** (`docker-compose.yml`): Full infrastructure stack with:
  - **Kafka** (Bitnami KRaft mode, no Zookeeper) — ports 9092 (internal) / 9094 (external)
  - **Redis 7** (Alpine) — 256 MB max-memory, LRU eviction
  - **PostgreSQL 16** (Alpine) — auto-seeds `scripts/init_db.sql` on first boot
  - **ChromaDB 0.5** — persistent storage, HTTP client on port 8000
  - **kafka-init** (one-shot): creates all 5 Kafka topics with proper partition counts
- **Topic layout**: `security-telemetry` (6 partitions), `transaction-events` (6), `tls-handshake` (3), `fusion-alerts` (6), `quantum-alerts` (3)
- **Environment config**: `.env.example` with all required variables; `.env` never committed (`.gitignore` enforces this)
- **Database schema** (`scripts/init_db.sql`): tables for `alerts`, `cases`, `audit_trail`, `quantum_alerts`, `identity_profiles`
- **Test scaffolding**: `pytest.ini` (async mode auto, verbose, short tracebacks), `tests/conftest.py` with environment-safe defaults and reusable fixtures
- **Dependencies**: `requirements.txt` with pinned minimum versions for all backend/ML/streaming/API packages

### Key decisions
- Kafka runs in KRaft mode (controller + broker in one node) — simpler for single-node demo
- `docker-compose.yml` uses `profiles: ["full"]` for application services so `docker compose up` (no profile) boots only infra, and `docker compose --profile full up` boots everything
- PostgreSQL init uses `docker-entrypoint-initdb.d/` convention for zero-config schema seeding

## Phase 8: Frontend Shell + Dual-Theme Engine (Complete)
- Scaffolded React 18 + Vite with `@tanstack/react-query`, `lucide-react`, and `react-router-dom`.
- Created robust dual-theme context engine in `index.css` supporting Brutalist and Aero aesthetics with dynamic CSS custom properties.
- Built a shared `ThemeContext` backed by `localStorage` for crossfade theme switching without layout reflow.
- Created `App.jsx`, `Sidebar.jsx`, and `Header.jsx` with real-time `WebSocket` connection status indicators.

## Phase 9: Progressive-Disclosure Dashboard + Scenario Runner (Complete)
- **Level 1 (KPI Landing)**: Built `Dashboard.jsx` fetching active anomalies and high-risk identities via React Query caching.
- **Level 2 (Alert List)**: Built `Alerts.jsx` rendering severities, fusion scores, and filtering by identity ID or severity.
- **Level 3 (Explanation Drawer)**: Built `ExplanationDrawer.jsx` that streams semantic RBI control explanations from `/api/explain/stream` via `fetch` streaming API and triggers case actions (Escalate/Dismiss).
- **Quantum Risk Panel**: Built `QuantumRisk.jsx` tracking PQC readiness vs Legacy (RSA) and highlighting specific HNDL exposure.
- **Case Management**: Built `Cases.jsx` rendering analyst queues and an immutable audit trail of actions.
- **Scenario Runner**: Built `ScenarioRunner.jsx` allowing 1-click injection of synthetic attacks when `DEMO_MODE=true`.

## Phase 10: Automated Test Suites (Complete)
- **Backend**: Implemented comprehensive `pytest` suite simulating rolling aggregations, model scoring, and RAG mock behavior in `tests/test_detection_rules.py`.
- **Frontend**: Integrated `Vitest` and `@testing-library/react`. Wrote `Theme.test.jsx` verifying the `data-theme` DOM attribute changes and dual-theme functionality.
- **Frontend E2E**: Integrated `@playwright/test`. Wrote `scenario.spec.js` running through the 4 synthetic attack scenarios in the Scenario Runner.

## Phase 11: Documentation Pass (Complete)
- Updated `README.md` to map to "Overview & Architecture" (Slides 3/4).
- Added `/docs/functional/README.md` for "User Flow & Logic" (Slide 5).
- Created `DIFFERENTIATORS.md` for "Key Differentiators & Adoption" (Slide 6).
- Created `LIMITATIONS.md` outlining the synthetic data and model placeholder aspects for full transparency.

---

## Phase 2 — Synthetic Data Generators (COMPLETE ✅)

### What was built
All files under `data/synthetic/generators/`:

| File | Purpose |
|------|---------|
| `base.py` | Shared utilities: identity pool (50 synthetic IDs), `IdentityState` class tracking per-identity device/beneficiary/IP state, weighted IST timestamp generation (business hours bias), log-normal amount distributions, Kafka producer factory |
| `security_telemetry_gen.py` | Generates normal security events (login, privileged_cmd, endpoint_alert, geo_change) at ~95% baseline rate with realistic risk flag distributions |
| `transaction_gen.py` | Generates normal transaction events (UPI/NEFT/RTGS/IMPS) with log-normal amounts, low new-beneficiary rate, rare cross-border |
| `tls_handshake_gen.py` | Generates TLS handshake events with configurable PQC-readiness ratio (~15% PQC-ready default), routine/kyc/credit_history sensitivity split |
| `scenario_injector.py` | Injects all 4 labeled attack scenarios (ATO, Insider Collusion, Credential Stuffing→ATO, HNDL Exposure) with coordinated timing, proper `scenario_type` and `is_synthetic_positive` labels |
| `run_generators.py` | Thread-based orchestrator running all generators + scenario injection concurrently |

### Synthetic data methodology
- **Normal traffic**: ~95% of events. Timestamps weighted 70/30 toward IST business hours (09:00–18:00). Transaction amounts drawn from `lognormal(mu=8.5, sigma=1.2)` ≈ median ₹5,000. Device pool per identity: 2–4 devices, new device probability 3%. Beneficiary pool per identity: 3–8, new beneficiary probability 5%.
- **Attack scenarios**: ~5% of events, injected by `scenario_injector.py`:
  1. **ATO**: Login from new device + impossible_travel flag → high-value transfer to new beneficiary, all within 15 min
  2. **Insider Collusion**: Privileged account unusual_data_access → linked identity transfers to shared/new beneficiary within 10 min
  3. **Credential Stuffing→ATO**: Burst of 5–15 failed logins from few IPs across many identities, one success, immediate high-value transfer
  4. **HNDL Exposure**: TLS session with `data_sensitivity: kyc|credit_history` negotiated using legacy `RSA-2048` or `ECDHE-P256`
- **Documentation**: `data/synthetic/README.md` describes methodology, distributions, scenario timings

### Verification
- `tests/verify_phase2.py`: standalone script that imports all generators, produces sample events, and validates JSON structure against Section 3 schemas

---

## Phase 3 — Streaming Detection Jobs (COMPLETE ✅)

### What was built
All files under `streaming/`:

| File | Purpose |
|------|---------|
| `config.py` | `pydantic-settings` configuration: Kafka bootstrap servers, Redis host/port, topic names, fusion window size (900s = 15 min) |
| `redis_client.py` | `RedisClient` class: identity profile CRUD, sliding-window event buffers (sorted sets keyed by timestamp), quantum KPI atomic counters, window event retrieval with automatic expiry cleanup |
| `detection/rules.py` | `DetectionRules` class with 5 static detection methods (brute_force, port_scan, exfiltration, lateral_movement, c2_beaconing) and an `evaluate_all()` aggregator returning a set of active signal names |
| `fusion/features.py` | `extract_features()` function computing the 12-feature vector expected by the LightGBM model from sliding window events + identity profile baseline |
| `fusion/job.py` | `IdentityFusionJob` class: processes security and transaction events, updates Redis state, extracts features, calls classifier (HTTP with 0.5s timeout, fallback to rule-based), emits fused alerts to Kafka |
| `quantum/job.py` | `CryptoInventoryJob` class: deterministic classification table (ML-KEM/ML-DSA → pqc_ready, ECDHE/RSA → legacy, X25519-MLKEM → hybrid), HNDL exposure flagging, bulk-egress anomaly detection, quantum alert emission, Redis KPI updates |
| `run_all.py` | Main entry point: initializes Redis, Kafka producer/consumer, subscribes to 3 telemetry topics, routes events to fusion/quantum jobs, handles graceful shutdown |

### 12 Model Features
The LightGBM classifier (`fusion_model.joblib`) expects exactly these features in this order:
1. `hour_of_day` — IST hour (0–23)
2. `txn_amount_zscore` — (latest amount − profile avg) / (profile avg × 0.5)
3. `beneficiary_is_new` — 0/1
4. `txn_velocity_1h` — count of transactions in window
5. `off_hours_txn_flag` — 1 if IST hour ∉ [09:00, 18:00)
6. `cross_border_flag` — 0/1
7. `new_device_flag` — 0/1
8. `impossible_travel_flag` — 0/1
9. `failed_auth_count_1h` — count of failed_login events in window
10. `privileged_cmd_count_1h` — count of privileged_cmd events in window
11. `endpoint_alert_count_1h` — count of endpoint/scan/exfiltration/lateral/c2 events
12. `joint_window_overlap_flag` — 1 if both security AND transaction events present

### Rule-based fallback scorer
Weighted sum of features with a 1.4× boost for joint_window_overlap. Maps to severity bands: ≥0.85 → critical, ≥0.65 → high, ≥0.35 → medium, else low.

---

## Phase 4 — Redis Feature Store & Caching (COMPLETE ✅)

### Cache implementations (matching Section 5 exactly)

| Cache | Key Pattern | TTL | Implementation |
|-------|-------------|-----|----------------|
| Identity behavioural baseline | `profile:{identity_id}` | 86400s (refreshed on every event) | `RedisClient.get/save_identity_profile()` |
| Sliding window events | `window:security:{id}` / `window:transactions:{id}` | 2× window size (1800s) | Sorted sets, score = epoch timestamp, auto-trimmed |
| RAG explanation text | `rag:cache:{md5(signals+severity)}` | 86400s (24h) | In RAG service, keyed by hash of sorted signals |
| Dashboard KPI aggregates | `kpi:dashboard_kpis` | 30s | Write-through invalidation on new alert insert |
| Quantum scan summary | `kpi:quantum_raw` + `kpi:quantum_stats` | 60s | Atomic `HINCRBY` for counts, periodic stats refresh |

---

## Phase 5 — FastAPI Gateway & Postgres Persistence (COMPLETE ✅)

### What was built
All files under `services/gateway/`:

| File | Purpose |
|------|---------|
| `database.py` | Async SQLAlchemy engine factory, `AsyncSessionLocal`, `get_db()` dependency |
| `models.py` | ORM models: `Alert`, `Case`, `AuditTrail`, `QuantumAlert`, `IdentityProfile` — uses backend-agnostic `Uuid`/`JSON` types for SQLite test compat |
| `schemas.py` | Pydantic v2 request/response schemas for all API endpoints |
| `ws_manager.py` | `ConnectionManager` class managing WebSocket connections + broadcast |
| `main.py` | FastAPI application with all endpoints + background Kafka consumer |

### API Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/api/alerts` | List fused alerts (filterable by severity, identity_id) |
| `GET` | `/api/alerts/{id}` | Single alert detail with case status |
| `POST` | `/api/cases/{id}/action` | Analyst actions (acknowledge/escalate/dismiss) with immutable audit logging |
| `GET` | `/api/cases` | Analyst case queue (filterable by status) |
| `GET` | `/api/audit` | Immutable audit trail |
| `GET` | `/api/quantum/sessions` | Crypto inventory / HNDL alerts |
| `GET` | `/api/dashboard/kpis` | Cached KPI metrics (30s Redis TTL) |
| `POST` | `/api/demo/inject` | Scenario Runner (gated behind `DEMO_MODE=true`) |
| `WS` | `/ws/alerts` | Real-time alert push via WebSocket |

### Background Kafka consumer
Daemon thread subscribes to `fusion-alerts` and `quantum-alerts`. On each message:
1. Persists alert/quantum record to Postgres
2. Creates associated Case (status: "open")
3. Calls RAG explanation service (async HTTP, 5s timeout)
4. Invalidates Redis KPI cache
5. Broadcasts to all WebSocket connections

### Audit trail pattern ("Log Securely")
Every case action (acknowledge, escalate, dismiss) writes an immutable row to `audit_trail` with:
- `entity_type`: "case"
- `entity_id`: case UUID
- `action`: "ACKNOWLEDGE" / "ESCALATE" / "DISMISS"
- `actor`: analyst username
- `details`: JSON with old_status, new_status, notes, timestamp

---

## Phase 6 — Fusion Classifier Microservice (COMPLETE ✅)

### What was built
`services/fusion_classifier/main.py`: FastAPI app hosting the LightGBM model.

- **Model**: `fusion_model.joblib` — `LGBMClassifier` trained externally, expects the 12 features listed above
- **Endpoint**: `POST /internal/fusion/score`
  - Input: `{ "identity_id": str, "features": { ... 12 features ... } }`
  - Output: `{ "fusion_score": float, "severity": str, "contributing_signals": [str] }`
- **Scoring**: Uses `model.predict_proba()` → class-1 probability as fusion_score
- **Fallback**: If model fails to load or predict, uses the same rule-based scorer as the streaming job
- **Contributing signals**: Derived deterministically from feature flags (impossible_travel, new_device, etc.)

### Model verification
```
Model type: LGBMClassifier
Features: ['hour_of_day', 'txn_amount_zscore', 'beneficiary_is_new', 'txn_velocity_1h',
           'off_hours_txn_flag', 'cross_border_flag', 'new_device_flag',
           'impossible_travel_flag', 'failed_auth_count_1h', 'privileged_cmd_count_1h',
           'endpoint_alert_count_1h', 'joint_window_overlap_flag']
Predict proba (all zeros): [[9.99986086e-01, 1.39136859e-05]]  → low risk for benign input ✓
```

---

## Phase 7 — RAG Explanation Service (COMPLETE ✅)

### What was built
Files under `services/rag_explanation/`:

| File | Purpose |
|------|---------|
| `corpus.py` | 7 paraphrased RBI Cyber Security Framework control summaries with keyword mappings (Control 8.1 User Access, 8.3 Privileged Access, 3.1 Network Security, 4.2 DLP, 10.1 Crypto Key Management, 13.2 Correlation, 6.4 Transaction Security) |
| `main.py` | FastAPI service with `/api/explain` (sync) and `/api/explain/stream` (SSE) endpoints |

### RAG pipeline
1. **Retrieve**: Query ChromaDB with `contributing_signals` as search text → top-3 relevant RBI controls
2. **Generate**: If Gemini API key available, prompt Gemini-1.5-Flash with signals + severity + retrieved controls → 2-3 sentence explanation citing control numbers. Otherwise, deterministic template.
3. **Cache**: Store result in Redis with 24h TTL, keyed by `md5(sorted_signals + severity)`
4. **Stream**: SSE endpoint streams explanation word-by-word with `event: text`, `event: controls`, `event: end` types

---

## Test Suite (COMPLETE ✅)

All 4 tests passing as of commit `257d8b8`:

| Test | File | What it verifies |
|------|------|-----------------|
| Crypto classification | `tests/test_crypto_classification.py` | Legacy/PQC/hybrid algorithm lookup table correctness |
| Detection rules | `tests/test_detection_rules.py` | All 5 security detection rules fire correctly on matching events, don't fire on benign events |
| Feature extraction | `tests/test_features.py` | 12-feature vector computed correctly for benign and ATO-like scenarios |
| API contract | `tests/test_api.py` | End-to-end gateway: alert CRUD, case actions, audit trail, quantum sessions, KPI aggregation (uses in-memory SQLite) |

---

## Infrastructure Files

| File | Purpose |
|------|---------|
| `data/synthetic/Dockerfile` | Python 3.12 slim, runs `data.synthetic.generators.run_generators` |
| `streaming/Dockerfile` | Python 3.12 slim, runs `streaming.run_all` |
| `services/gateway/Dockerfile` | Python 3.12 slim, runs uvicorn on port 8080, copies `data/` for demo injection |
| `services/fusion_classifier/Dockerfile` | Python 3.12 slim, copies `fusion_model.joblib`, runs uvicorn on port 8081 |
| `services/rag_explanation/Dockerfile` | Python 3.12 slim, runs uvicorn on port 8082 |
