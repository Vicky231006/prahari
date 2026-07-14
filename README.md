# PRAHARI: Security Sentinel
> AI-Driven Correlation of Cybersecurity Telemetry & Transactional Behaviour

## Overview
PRAHARI (Hindi for sentinel/watchman) is a real-time detection pipeline that fuses identity-linked cybersecurity events (e.g., logins, endpoint alerts) with transactional behaviour to generate high-confidence security alerts. It directly tackles the problem of siloed SOC and fraud teams by reducing false positives through multi-channel correlation.

Additionally, it includes a deterministic Crypto Inventory module to track Post-Quantum Cryptography (PQC) readiness and flag Harvest-Now-Decrypt-Later (HNDL) exposure risks on TLS handshakes.

All anomaly explanations are generated using a local semantic RAG layer referencing the **RBI Cyber Security Framework** baseline controls.

## Architecture
- **Streaming Pipeline**: Kafka → Fusion Job (Python) → Redis (Feature Store) → PostgreSQL
- **Machine Learning**: LightGBM fusion classifier with rule-based fallback
- **API & Persistence**: FastAPI gateway, PostgreSQL (SQLAlchemy async), Redis KPI cache
- **RAG Layer**: ChromaDB (Vector store), Gemini 1.5 Flash — streaming SSE explanation
- **Frontend UI**: React + Vite, Dual-theme engine (Aero & Brutalist), `react-query`

## Key Features

### Investigation Workspace
Clicking any alert in the Fusion Alerts table opens a full **Investigation Workspace** (960 px drawer) with three tabs:
- **Explanation** — RAG-streamed analysis of the fused alert against RBI controls, with contributing signals
- **Risk Profile** — Rich customer identity panel (18+ fields) from the synthetic banking dataset: KYC, balance, devices, beneficiaries, fraud history, device trust score
- **Timeline** — Chronological event sequence from account opening → security events → transactions → alert generation → case creation → analyst actions

### SOC Workflow Actions
Two fully functional workflow buttons in the workspace footer:
- **Escalate to Tier 2** — `POST /api/alerts/{id}/escalate` — creates/updates a linked Case and writes an immutable ESCALATE audit entry
- **Dismiss False Positive** — `POST /api/alerts/{id}/dismiss` — prompts for analyst reason, writes a DISMISS audit entry

### Extended Synthetic Banking Dataset
200 synthetic identities with realistic banking metadata:
- Customer type (Retail / SME / Corporate), KYC status, account age, primary branch, region
- Balance, average daily volume, monthly transaction count
- Known devices (with trust scores), known beneficiaries, fraud history

### Investigation Timeline API
`GET /api/alerts/{id}/timeline` — backend endpoint that joins four data sources and returns a normalized, chronologically sorted event list. Raw security and transaction events are now persisted in the `alerts.raw_events` column directly from the Kafka payload so the timeline reflects actual events rather than derived signals.

## Pre-Requisites
- **Docker & Docker Compose**: To run the entire infrastructure stack (Kafka, Redis, Postgres, ChromaDB).
- **Python 3.12+**: For running services locally if not using full Docker profiles.
- **Node.js 20+**: For frontend development.
- **Gemini API Key**: Placed in `.env` for the RAG explanation service.

## Environment Setup
1. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```
2. Open `.env` and fill in your `GEMINI_API_KEY`.
3. Start the full stack:
   ```bash
   docker compose up -d
   ```

## Testing & Demo
PRAHARI includes an embedded **Scenario Runner** (when `DEMO_MODE=true` in `.env`). This allows you to inject 4 synthetic attack scenarios directly into the Kafka pipeline from the frontend UI:
1. **Account Takeover (ATO)**
2. **Insider Collusion**
3. **Credential Stuffing → ATO**
4. **HNDL Exposure**

Run the backend test suite:
```bash
pytest tests/
```
