# MASTER BUILD PROMPT — Project PRAHARI
### AI-Driven Correlation of Cybersecurity Telemetry & Transactional Behaviour
### FinSpark'26 (Bank of Maharashtra) — Problem Statement 2

> Working codename: **PRAHARI** (Hindi: sentinel/watchman). Rename freely — this is a real naming choice, not a placeholder, so it's fine to keep or swap.

---

## 0. ROLE AND OPERATING RULES FOR THE BUILD AGENT

You are the lead engineer building a working, demoable prototype for a national banking cybersecurity hackathon. The submission is judged on: **Business Potential & Relevance (40%), Security Considerations (30%), Uniqueness of Approach (15%), User Experience (5%), Scalability (5%), Ease of Development & Maintenance (5%)**. Every architectural decision below is already made with this weighting in mind — do not re-derive priorities, implement what's specified.

**Non-negotiable rules:**

1. **No placeholders, no stubs, no `TODO`, no lorem ipsum, no hardcoded fake "success" responses.** If a feature genuinely cannot be fully implemented in scope, implement a smaller *real* version of it and write exactly what's missing in `LIMITATIONS.md`. A silently faked feature is worse than an honestly incomplete one.
2. **Every dataset is either (a) real public reference data, cited, or (b) explicitly labeled synthetic data with a documented generation methodology.** Section 3 specifies exactly which is which. Never let synthetic data pass as real, and never let it go undocumented — judges will ask "is this real data?" and the honest, well-documented answer is a strength, not a weakness, if it's presented that way.
3. **This is a 4-day build.** Depth over breadth: the fusion engine, the RAG explanation layer, and the quantum module are the scored core (70% of the rubric). The dual-theme frontend is real but must not consume time disproportionate to its 5% UX weight — build it as a token-swap system (Section 8), not two parallel codebases.
4. **Dogfood security.** This submission is *about* security — any hardcoded secret, exposed key, or disabled auth in the repo is a credibility failure a judge will notice immediately. Use `.env` + `.env.example`, never commit real credentials, and gate any demo/testing endpoints behind an explicit non-production flag (Section 9).
5. Build in the phase order given in Section 11. Do not skip ahead to frontend polish before the pipeline moves real events end-to-end.

---

## 1. WHAT THIS SYSTEM DOES

Banks run fraud detection and cybersecurity monitoring (SOC/UEBA) as separate systems with separate teams and, in India, separate regulatory reporting tracks — RBI's Master Direction on Frauds routes to the Central Fraud Registry while the Cyber Security Framework routes incidents to RBI's cybersecurity cell on a 2–6 hour window, run in parallel rather than unified. PRAHARI correlates **identity-linked security telemetry** with **identity-linked transaction behaviour** in real time, so a security anomaly and a transaction anomaly on the same identity in the same time window are surfaced as one higher-confidence fused alert instead of two separate low-confidence ones — directly reducing false positives, which is a named expected outcome of PS2.

It also runs a **quantum-risk / harvest-now-decrypt-later (HNDL) monitoring module**: a cryptographic inventory scanner that classifies live sessions as legacy (RSA/ECC) or PQC-ready (ML-KEM/ML-DSA, NIST FIPS 203/204) and flags sessions carrying long-shelf-life sensitive data (KYC, credit history) over legacy crypto as HNDL-exposed. This is deliberately framed as *detection and inventory*, not "we implemented post-quantum cryptography" — inventory-first is the actual first step every real PQC migration roadmap (G7 CEG, EU DORA, NIST) specifies, so this is both more honest and more buildable in 4 days than retrofitting a crypto vault.

Every alert carries a **RAG-generated explanation** that cites which specific behavioural signals fired and which RBI baseline control they map to — this is the "explainable AI-driven threat intelligence" outcome, and it's also your strongest defense against a judge asking "why should I trust this AI's call."

---

## 2. SYSTEM ARCHITECTURE (TEXT DIAGRAM)

```
[Synthetic Event Generators] ──▶ Kafka topics ──▶ Flink jobs ──▶ Redis (feature store + cache)
   security-telemetry-gen           │                  │                    │
   transaction-gen                  │                  ├─ existing 5 detection jobs (reuse)
   tls-handshake-gen                │                  ├─ NEW: Identity Fusion Job
                                    │                  └─ NEW: Crypto Inventory Job
                                    ▼                         │
                            fusion-alerts topic ◀─────────────┘
                                    │
                                    ▼
                        Fusion Classifier Service (FastAPI + model)
                                    │
                                    ▼
                    Alert persisted (Postgres) + RAG Explanation Service
                        (Gemini + ChromaDB corpus of RBI control summaries)
                                    │
                                    ▼
                     FastAPI Gateway ──▶ WebSocket push ──▶ React Frontend
                     (REST + WS)         + REST polling        (dual-theme, progressive disclosure)
```

Build a real Mermaid or draw.io version of this for the PPT architecture slide (Section 10) once the pipeline is working — don't hand-wave it as text in the final deliverable.

---

## 3. DATA LAYER — SCHEMAS AND SYNTHETIC DATA POLICY

All three event types below are **synthetic, generated by scripts you write, documented in `/data/synthetic/README.md`** with the exact injection rules used. This is stated openly in the submission, not hidden.

**`security-telemetry` event:**
```json
{ "event_id": "uuid", "identity_id": "string", "timestamp": "iso8601",
  "event_type": "login|privileged_cmd|endpoint_alert|geo_change",
  "source_ip": "string", "geo": {"lat":0,"lon":0,"country":"IN"},
  "device_fingerprint": "string", "is_new_device": false,
  "session_id": "string", "risk_flags": ["impossible_travel","new_device"] }
```

**`transaction-events` event:**
```json
{ "txn_id": "uuid", "identity_id": "string", "timestamp": "iso8601",
  "amount": 0.0, "currency": "INR", "channel": "UPI|NEFT|RTGS|IMPS",
  "beneficiary_id": "string", "beneficiary_is_new": false,
  "session_id": "string", "is_cross_border": false }
```

**`tls-handshake` event (for the quantum module):**
```json
{ "session_id": "string", "timestamp": "iso8601", "key_exchange": "RSA-2048|ECDHE-P256|ML-KEM-768|hybrid",
  "signature_algo": "RSA|ECDSA|ML-DSA", "data_sensitivity": "kyc|credit_history|routine",
  "bytes_transferred": 0, "destination": "internal|external" }
```

**Generation methodology (put this in the README, verbatim in spirit):** generate a background of ~95% "normal" identity behaviour using realistic distributions (log-normal transaction amounts, business-hours-weighted timestamps, low new-device/new-beneficiary rates), then inject four labeled scenario types at a known rate for supervised training and demo:

1. **Account takeover (ATO):** new device + impossible travel + high-value transfer to a new beneficiary within 15 minutes.
2. **Insider collusion:** privileged account performs an unusual data access, correlated within 10 minutes with a transaction from an associated/linked identity to a shared or new beneficiary.
3. **Credential stuffing → ATO:** burst of failed logins across many identities from few source IPs, followed by one success and an immediate transaction.
4. **HNDL exposure:** a session carrying `kyc` or `credit_history` sensitivity data negotiated over legacy (`RSA-2048`/`ECDHE-P256`) key exchange.

Label every injected event with `scenario_type` and `is_synthetic_positive: true` so the fusion model has ground truth and the Scenario Runner (Section 9) can trigger these exact sequences on demand.

---

## 4. STREAMING & PROCESSING LAYER

- **Kafka topics:** `security-telemetry`, `transaction-events`, `tls-handshake`, `fusion-alerts`, `quantum-alerts`.
- **Reuse the 5 existing Flink detection jobs** (brute force, port scan, exfiltration, lateral movement, C2 beaconing) unchanged — they still feed `security-telemetry`-derived signals into the fusion job.
- **NEW — Identity Fusion Job (PyFlink):** keyed by `identity_id`, sliding window (default 15 min, configurable). Computes per-window feature vector (Section 5) from both streams and emits to `fusion-alerts` whenever both a security-side and a transaction-side signal fire in the same window for the same identity, OR the fusion model's continuous score crosses a threshold (don't require *both* channels to fire — a strong single-channel signal should still surface, just at lower confidence; that's the whole point of "reduces false positives" — fused signals get boosted confidence, not gated existence).
- **NEW — Crypto Inventory Job (PyFlink):** consumes `tls-handshake`, classifies key-exchange/signature algorithm against a maintained lookup table (legacy vs PQC-ready per NIST FIPS 203/204/205), flags HNDL exposure when `data_sensitivity != routine` and algorithm is legacy, flags bulk-egress anomalies (`bytes_transferred` z-score outlier + `destination: external`) as a secondary harvesting indicator. **This does not require a trained ML model** — it's a deterministic classification table plus a threshold rule. Don't over-engineer this into an ML problem it isn't.

---

## 5. FEATURE STORE AND CACHING (REDIS) — BE EXPLICIT ABOUT WHY EACH CACHE EXISTS

Don't cache generically — every cache below solves a specific latency or cost problem. Implement exactly these, with these patterns:

| What | Pattern | TTL | Why |
|---|---|---|---|
| Identity rolling behavioural baseline (avg txn amount, login time distribution, known beneficiaries, known devices) | Cache-aside, written by Flink, read by Fusion Classifier Service at inference time | 60s refresh from Flink state | Every fusion inference needs this; recomputing from raw history per-event is the latency bottleneck |
| RAG explanation text | Keyed by hash of `(sorted fired_signals, severity, regulatory_control_ids)` | 24h | Identical alert patterns recur; skip a redundant LLM call and the latency/cost that comes with it |
| Dashboard KPI aggregates (alerts by severity last 24h, top-10 risk identities) | Cache-aside, write-through invalidation on new alert insert | 30s | Read-heavy, write-light; don't hit Postgres aggregate queries on every dashboard poll |
| Quantum scan summary (legacy vs PQC-ready session counts) | Cache-aside | 60s | Same shape as KPI cache, same reasoning |

**Frontend fetch pattern:** use React Query (`@tanstack/react-query`) with `staleTime` matched to the TTLs above per endpoint, `refetchOnWindowFocus: false` for dashboard views (avoid surprise reloads mid-demo), and a WebSocket (`/ws/alerts`) that invalidates the relevant React Query cache key on a new fused alert — so the UI updates in real time without polling, and polling still exists as a fallback if the socket drops.

---

## 6. FUSION CLASSIFIER SERVICE

**Contract, not implementation** — the model itself is trained separately (see the chat message after this document for the exact model list and training instructions). Build the service to this interface so training can be swapped in without touching the pipeline:

- Input: feature vector per `(identity_id, window)` — behavioural deltas from Section 5's baseline, plus the raw window's fired-signal list.
- Output: `{ "fusion_score": 0.0-1.0, "severity": "low|medium|high|critical", "contributing_signals": [...] }`
- Serve via a FastAPI endpoint (`POST /internal/fusion/score`) called by a downstream Kafka consumer of `fusion-alerts`, so the model can be retrained/reloaded without redeploying the streaming layer.
- Until the real model is trained, use a **documented, explicitly-labeled interim rule-based scorer** (weighted sum of fired signals) so the pipeline is testable end-to-end from day one — swap in the trained model behind the same contract once ready. Label this clearly in code comments and `LIMITATIONS.md` if it's still in place at submission time; don't let a placeholder scorer go unmentioned.

---

## 7. RAG EXPLANATION LAYER

- Corpus: short, **paraphrased summaries** (not verbatim reproductions) of relevant RBI Cyber Security Framework baseline controls (e.g., Control 8: User Access Control and Management — centralized authentication, least privilege, monitoring abnormal logon patterns) stored in ChromaDB with the control's official reference number attached as metadata. Keep the corpus small and precise — a dozen well-chosen control summaries beat a large noisy one.
- Prompt template for the explanation service: given `contributing_signals` + retrieved control summaries, generate a 2-3 sentence plain-language explanation of *what fired*, *why it's risky*, and *which control it relates to* — cite the control number, not the full circular text.
- Cache per Section 5. Stream via SSE to the alert detail view (reuse the existing Log Securely SSE pattern).

---

## 8. FRONTEND — DUAL-THEME DESIGN SYSTEM

**Architecture rule: one component tree, two token sets.** The layout, information hierarchy, and component structure are identical in both themes — only CSS custom properties and a small number of decorative elements change. Do not build two separate UIs; that doubles the work for a 5%-weighted criterion.

Implement as CSS custom properties on `[data-theme="brutalist"]` / `[data-theme="aero"]`, a `ThemeContext` in React, persisted to `localStorage`, toggle in the persistent header, 200ms crossfade on switch (no jarring reflow).

**Both themes share the same severity semantics** — critical/high/medium/low map to the same meaning in both skins even though exact shades differ, so switching theme never changes what an alert *means*.

### Theme: BRUTALIST

| Token | Value |
|---|---|
| Background | `#FFFFFF` |
| Border/text | `#0D0D0D`, 3px solid borders, 0-2px radius |
| Primary accent (chrome) | `#0033FF` |
| Secondary accent (badges) | `#FFE000` |
| Critical severity | `#FF2E2E` |
| Display font | Space Grotesk, 700 |
| Body/data font | IBM Plex Mono |
| Shadow | `6px 6px 0 #0D0D0D`, no blur; buttons "press" (shadow removed + translate on click) |

### Theme: AERO (Frutiger Aero)

| Token | Value |
|---|---|
| Background | gradient `#EAF6FB` → `#D3ECEF` |
| Glass panel | `rgba(255,255,255,0.35)`, `backdrop-filter: blur(20px)`, `1px solid rgba(255,255,255,0.6)` |
| Primary accent (chrome) | `#1FB6C9` |
| Secondary accent (positive states) | `#8BD450` |
| Critical severity | `#E8483A` |
| Display font | Baloo 2 or Quicksand, 600 |
| Body/data font | Nunito Sans |
| Shadow | `0 8px 24px rgba(31,182,201,0.25)`, blurred; radius 16-24px |
| Decoration | 1-2 soft blurred background orbs max, in empty space only — do not scatter these |

**Anti-patterns to avoid in both:** no accent line under titles, no decorative edge stripes on cards, no cream/beige "default" background outside the Aero theme's *intentional* soft palette, no low-contrast text, don't let either theme go half-styled — commit fully to both or the mismatch reads as unfinished.

---

## 9. PROGRESSIVE-DISCLOSURE DASHBOARD + SCENARIO RUNNER

**Level 1 (landing):** a small number of KPI cards only — active alerts by severity, top-5 identity risk scores, quantum exposure summary count. Nothing else. This is the whole point of "don't overload the user."

**Level 2 (drill-in):** click any KPI or alert row → Fusion Timeline view for that identity: security events and transaction events on one shared timeline, visually joined where they correlate.

**Level 3 (explain):** click an alert → explanation drawer with the RAG-generated text, cited control number, and a case-action bar (acknowledge / escalate / dismiss, logged to an audit trail).

**Separate views:** Quantum Risk panel (crypto inventory table + HNDL exposure map), Case Management (analyst queue), and:

**Scenario Runner (in-app test harness):** a Demo Mode panel, visibly gated behind a `DEMO_MODE=true` env flag (off by default — this is the security-dogfooding detail from rule 4), with four buttons — one per scenario in Section 3 — that inject the real event sequence through the actual Kafka→Flink→Fusion pipeline live, so a judge watching the demo sees data move through the real system, not a canned UI mock. This satisfies "test the entire flow inside the app" without needing external curl/Postman scripts during a live demo.

---

## 10. AUTOMATED TESTS + DELIVERABLES CHECKLIST

**Tests (required, not optional):**
- `pytest` suite: fusion feature computation, API contract tests for every endpoint in Section 9's API list, crypto-classification lookup table correctness.
- Frontend: Vitest/RTL for theme switching and progressive-disclosure state transitions.
- Playwright e2e: run all four Scenario Runner scenarios headlessly, assert the expected alert/severity appears within a reasonable window. This test suite doubles as your "Ease of Development & Maintenance" evidence.

**Map every deliverable to the submission deck's actual slides** (from the FinSpark template) so nothing is written twice or missed:

| Slide | Deliverable to produce |
|---|---|
| 3. Pre-Requisites | `README.md` — assumptions, access, datasets, tools, APIs, env vars needed |
| 4. Tools/Resources | `README.md` tech-stack section |
| 5. Supporting Functional Docs | `/docs/functional/` — user flow + logic flow diagrams |
| 6. Key Differentiators & Adoption Plan | `DIFFERENTIATORS.md` |
| 7. GitHub Repo + diagrams | Public repo link, clean commit history |
| 8. Business Potential | Written section — lead with the RBI parallel-reporting-track gap |
| 9. Uniqueness | Identity-linked joint-window fusion, not vendor PAM/UEBA comparison |
| 10. User Experience | Dual-theme + progressive disclosure, screenshots of both themes |
| 11. Scalability | Kafka/Flink horizontal scaling story, per-branch topic partitioning |
| 12. Ease of Deployment | Docker Compose, test suite, `.env.example` |
| 13. Security Considerations | Auth, secrets hygiene, `DEMO_MODE` gating, audit trail |
| 14. Architecture Diagram | Render Section 2's diagram properly (Mermaid/draw.io), don't submit ASCII |
| 15. Screenshots/Video/GitHub | Capture both themes, the Scenario Runner live, an explanation drawer |

---

## 11. BUILD PHASE ORDER (DO NOT REORDER)

1. Repo skeleton, Docker Compose, `.env.example`, CI-ready test scaffolding.
2. Kafka topics + synthetic generators (Section 3) — verify events flow and are inspectable.
3. Reuse existing 5 Flink jobs; add Identity Fusion Job + Crypto Inventory Job with the interim rule-based scorer (Section 6).
4. Redis feature store + all four caches (Section 5) wired in.
5. FastAPI gateway + all endpoints, Postgres persistence, WebSocket push.
6. RAG explanation service + ChromaDB corpus.
7. Frontend shell + theme engine (Section 8) + progressive-disclosure views (Section 9).
8. Scenario Runner wired to the real pipeline.
9. Test suites (Section 10).
10. Swap the trained fusion model in behind the Section 6 contract once ready (see chat message for training instructions — this happens in parallel with steps 5-9, not after).
11. Documentation pass mapped to Section 10's table.
12. Full QA pass: run every Scenario Runner scenario, check every dashboard state at every theme, check for any placeholder/TODO left in the codebase.

---

## 12. DEFINITION OF DONE

- [ ] Zero grep hits for `TODO`, `FIXME`, `lorem`, `placeholder` in the final repo.
- [ ] All four demo scenarios trigger real pipeline events and produce correctly-severity-scored fused alerts.
- [ ] Every alert has a non-empty, control-cited explanation.
- [ ] Quantum panel shows real classification of injected TLS sessions, including at least one HNDL-flagged session.
- [ ] Theme switch works with zero layout shift and identical severity meaning in both skins.
- [ ] `docker-compose up` brings up the full stack from a clean clone with no manual steps beyond `.env` population.
- [ ] `pytest` and Playwright suites pass.
- [ ] `LIMITATIONS.md` exists and is honest about anything short of Section 12's checklist above.