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

## Phase 11: Documentation Pass (Complete ✅)

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

... (file continues with same content)