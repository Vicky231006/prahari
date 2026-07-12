# PRAHARI: Security Sentinel
> AI-Driven Correlation of Cybersecurity Telemetry & Transactional Behaviour

## Overview
PRAHARI (Hindi for sentinel/watchman) is a real-time detection pipeline that fuses identity-linked cybersecurity events (e.g., logins, endpoint alerts) with transactional behaviour to generate high-confidence security alerts. It directly tackles the problem of siloed SOC and fraud teams by reducing false positives through multi-channel correlation. 

Additionally, it includes a deterministic Crypto Inventory module to track Post-Quantum Cryptography (PQC) readiness and flag Harvest-Now-Decrypt-Later (HNDL) exposure risks on TLS handshakes.

All anomaly explanations are generated using a local semantic RAG layer referencing the **RBI Cyber Security Framework** baseline controls.

## Architecture
- **Streaming Pipeline**: Kafka → PyFlink (Correlation & Aggregation) → Redis (Feature Store)
- **Machine Learning**: LightGBM fusion classifier
- **API & Persistence**: FastAPI, PostgreSQL, SQLAlchemy
- **RAG Layer**: ChromaDB (Vector store), Gemini 1.5 Flash
- **Frontend UI**: React + Vite, Dual-theme engine (Aero & Brutalist)

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
3. Start the infrastructure layer:
   ```bash
   docker compose up -d
   ```
4. Start the application services:
   ```bash
   docker compose --profile full up -d
   ```
   *(Alternatively, run the python services via `uvicorn` and the frontend via `npm run dev`)*

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
