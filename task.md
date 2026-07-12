# PRAHARI — Remaining Tasks

> Last updated: 2026-07-12 21:58 IST
> Reference: `PROMPT.md` Sections 8, 9, 10, 11, 12

---

## Phase 8 — Frontend Shell + Dual-Theme Engine (Section 8)

### 8.1 — Scaffold React + Vite project
- [ ] `npx create-vite frontend --template react`
- [ ] Install deps: `@tanstack/react-query`, React Router
- [ ] Configure Vite proxy to gateway `http://localhost:8080`

### 8.2 — Dual-Theme CSS Token System (Section 8)
- [ ] Define CSS custom properties on `[data-theme="brutalist"]` and `[data-theme="aero"]`
- [ ] **Brutalist tokens**: `#FFFFFF` bg, `#0D0D0D` borders (3px solid, 0–2px radius), `#0033FF` primary, `#FFE000` secondary, `#FF2E2E` critical, Space Grotesk 700 display, IBM Plex Mono body, `6px 6px 0 #0D0D0D` shadow, press-effect buttons
- [ ] **Aero tokens**: `#EAF6FB → #D3ECEF` gradient bg, glass panels (`rgba(255,255,255,0.35)`, `backdrop-filter: blur(20px)`), `#1FB6C9` primary, `#8BD450` secondary, `#E8483A` critical, Baloo 2/Quicksand 600 display, Nunito Sans body, `0 8px 24px rgba(31,182,201,0.25)` shadow, 16–24px radius, 1–2 soft blurred background orbs
- [ ] `ThemeContext` in React, persisted to `localStorage`
- [ ] Theme toggle in persistent header
- [ ] 200ms crossfade transition on theme switch (no layout reflow)
- [ ] Both themes share identical severity semantics (critical/high/medium/low)

### 8.3 — Shared Layout Shell
- [ ] Persistent header with: app name, theme toggle, connection status indicator
- [ ] Sidebar navigation: Dashboard, Alerts, Quantum Risk, Cases, Scenario Runner (if DEMO_MODE)
- [ ] Main content area with responsive layout
- [ ] All severity colors consistent across both themes

---

## Phase 9 — Progressive-Disclosure Dashboard + Scenario Runner (Section 9)

### 9.1 — Level 1: KPI Landing Page
- [ ] KPI cards: active alerts by severity, top-5 identity risk scores, quantum exposure summary
- [ ] Data fetched via React Query (`GET /api/dashboard/kpis`) with `staleTime: 30000`
- [ ] WebSocket connection (`/ws/alerts`) that invalidates React Query cache on `NEW_ALERT` / `NEW_QUANTUM_ALERT`
- [ ] Polling fallback if WebSocket drops

### 9.2 — Level 2: Alert List / Fusion Timeline
- [ ] Click KPI card → navigate to filtered alert list
- [ ] Alert list view with severity badges, fusion scores, identity IDs, timestamps
- [ ] Fusion Timeline view for a single identity: security events + transaction events on one shared timeline, visually joined where they correlate

### 9.3 — Level 3: Alert Explanation Drawer
- [ ] Click alert row → slide-out drawer with:
  - RAG-generated explanation text (streamed via SSE from `/api/explain/stream`)
  - Cited RBI control numbers
  - Case action bar: Acknowledge / Escalate / Dismiss (`POST /api/cases/{id}/action`)
  - Audit trail log for this case

### 9.4 — Quantum Risk Panel
- [ ] Crypto inventory table showing all TLS sessions with classification badges
- [ ] PQC readiness ratio (pie/donut chart or progress bar)
- [ ] HNDL exposure list highlighting flagged sessions
- [ ] Data from `GET /api/quantum/sessions` + Redis-cached stats

### 9.5 — Case Management View
- [ ] Analyst queue: list of cases with status filters (open/acknowledged/escalated/dismissed)
- [ ] Click case → linked alert detail
- [ ] Data from `GET /api/cases`

### 9.6 — Scenario Runner (Demo Mode Panel)
- [ ] Visibly gated behind `DEMO_MODE=true` (env flag checked via API or config endpoint)
- [ ] 4 scenario buttons: ATO, Insider Collusion, Credential Stuffing→ATO, HNDL Exposure
- [ ] Each button calls `POST /api/demo/inject` with the scenario type
- [ ] Shows injection status, event count, and live alert appearance in the dashboard
- [ ] Not visible in the sidebar/UI at all when DEMO_MODE is false

---

## Phase 10 — Automated Tests (Section 10)

### 10.1 — Backend tests (DONE ✅)
- [x] `pytest` suite: fusion feature computation, API contract tests, crypto classification

### 10.2 — Frontend tests
- [ ] Vitest + React Testing Library: theme switching toggle test
- [ ] Vitest + RTL: progressive-disclosure state transitions (KPI → alert list → drawer)

### 10.3 — E2E tests
- [ ] Playwright: run all 4 Scenario Runner scenarios headlessly
- [ ] Assert expected alert/severity appears within a reasonable timeout window
- [ ] This test suite doubles as "Ease of Development & Maintenance" evidence

---

## Phase 11 — Documentation Pass (Section 10 table)

| Deliverable | Status | Maps to Slide |
|-------------|--------|---------------|
| `README.md` — assumptions, datasets, tools, env vars, setup instructions | ❌ TODO | Slides 3 & 4 |
| `/docs/functional/` — user flow + logic flow diagrams | ❌ TODO (directory exists, needs real content) | Slide 5 |
| `DIFFERENTIATORS.md` — key differentiators & adoption plan | ❌ TODO | Slide 6 |
| Architecture diagram (Mermaid/draw.io, not ASCII) | ❌ TODO | Slide 14 |
| `LIMITATIONS.md` — honest limitations | ❌ TODO | Section 12 requirement |
| Screenshots of both themes + Scenario Runner + explanation drawer | ❌ TODO | Slide 15 |

---

## Phase 12 — Final QA Pass (Section 12 Definition of Done)

- [ ] Zero grep hits for `TODO`, `FIXME`, `lorem`, `placeholder` in the final repo
- [ ] All 4 demo scenarios trigger real pipeline events and produce correctly-severity-scored fused alerts
- [ ] Every alert has a non-empty, control-cited explanation
- [ ] Quantum panel shows real classification including at least one HNDL-flagged session
- [ ] Theme switch works with zero layout shift and identical severity meaning in both skins
- [ ] `docker-compose up` brings up the full stack from a clean clone with no manual steps beyond `.env` population
- [ ] `pytest` and Playwright suites pass

---

## Blockers / Dependencies

| Item | Status | Notes |
|------|--------|-------|
| Gemini API Key | ⏳ Pending | `.env` has placeholder. RAG service falls back to deterministic generator. User will provide when available. |
| Docker stack verification | ⏳ Not yet tested | `docker compose --profile full up` not run yet. Pending frontend completion. |
| `fusion_model.joblib` version skew | ⚠️ Warning | Model was pickled with scikit-learn 1.6.1, current env has 1.9.0. Works but shows `InconsistentVersionWarning`. Not a blocker. |
