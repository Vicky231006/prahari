# 🎨 Dhaal (ढाल): Frontend Web Application
> **React + Vite Dashboard for Cyber-Fraud Fusion Analytics & Incident Response**

This is the user interface of Dhaal (ढाल), designed for SOC Tier-2 analysts to monitor, investigate, and remediate fused security-transaction anomalies. It is built as a highly responsive React Single Page Application (SPA).

---

## ⚡ Technical Stack
- **Framework**: React 18 + Vite
- **State & Data Fetching**: `@tanstack/react-query` (React Query)
- **Routing**: `react-router-dom`
- **Icons**: `lucide-react`
- **Real-Time Feed**: Native WebSockets for instant alert broadcasting
- **Styling**: Pure CSS + CSS variables (no TailwindCSS or CSS frameworks)
- **Testing**:
  - Unit & Component: `Vitest` + `@testing-library/react`
  - E2E Integration: `@playwright/test`

---

## 🖼️ Key UI Components & Views

### 1. Progressive-Disclosure Dashboard
- **Level 1 (KPI Landing Page)**: High-level dashboard showing "Total Active Anomalies", "High Risk Identities", and "HNDL Session Exposure" counters. Contains live WebSocket status connection indicator.
- **Level 2 (Anomalies Queue)**: Interactive tables for Fusion Alerts and Quantum Alerts. Features live filtering, status badge sorting, and clear severity indicators.
- **Level 3 (Investigation Workspace)**: A slide-out drawer (960px width) allowing granular inspection:
  - **Explanation Tab**: SSE-streamed RAG explanations detailing violated RBI framework controls.
  - **Risk Profile Tab**: Fetches the 18+ profile fields of the identity to check KYC status, average transaction values, beneficiary pool, and trusted device lists.
  - **Timeline Tab**: Displays a chronological vertical timeline combining registration, security events, transactions, alert emission, and previous analyst audits.

### 2. Scenario Runner
- Allows developers/judges to inject synthetic multi-channel cyber-fraud scenarios into the pipeline ( ATO, Insider Collusion, Credential Stuffing, and HNDL Exposure). 
- Requires `DEMO_MODE=true` environment variable enabled in the backend gateway.

### 3. Dual-Theme Engine
Built with Vanilla CSS custom properties to demonstrate flexibility:
- **Aero Theme**: Glassmorphism aesthetic, dark gradients, glowing state indicators, and subtle translucent backdrops.
- **Brutalist Theme**: High-contrast, thick black borders, flat primary colored blocks, and heavy monospace styling.

---

## 📂 Directory Layout

```text
frontend/
├── e2e/                     # Playwright End-to-End browser scenarios
├── src/
│   ├── assets/              # Static media assets & images
│   ├── components/          # Reusable UI components
│   │   ├── ExplanationDrawer.jsx   # Tabbed Investigation Workspace Drawer
│   │   ├── Header.jsx              # Global header with WebSocket connection state
│   │   ├── InvestigationGraph.jsx  # Graph visualization of correlated networks
│   │   ├── SeverityBadge.jsx       # Standardised severity chips
│   │   └── Sidebar.jsx             # Main navigation sidebar
│   ├── context/             # Global contexts (Theme Context)
│   ├── pages/               # Top-level page views
│   │   ├── Alerts.jsx              # Fusion anomalies list
│   │   ├── Cases.jsx               # Cases list & audit log
│   │   ├── Dashboard.jsx           # Main KPI dashboard landing
│   │   ├── GraphPage.jsx           # Visual network relations
│   │   ├── QuantumRisk.jsx         # Post-Quantum inventory & HNDL sessions
│   │   └── ScenarioRunner.jsx      # Kafka scenario injection trigger panel
│   ├── api.js               # Centralised API fetch & SSE client setup
│   ├── App.css              # Baseline CSS overrides
│   ├── App.jsx              # Routing & Context mapping
│   ├── index.css            # Custom utility styling and theme custom properties
│   └── main.jsx             # Application entrypoint
├── vite.config.js           # Vite development server and proxy configs
└── package.json             # Package scripts & dependencies
```

---

## 🚀 Running the Frontend

### Prerequisites
- Node.js 20+

### Installation & Run
1.  Navigate to the directory:
    ```bash
    cd frontend
    ```
2.  Install dependencies:
    ```bash
    npm install
    ```
3.  Run the development server:
    ```bash
    npm run dev
    ```
    The application will launch on `http://localhost:5173`.

---

## 🧪 Testing

### Running Unit & Component Tests
Tests are written with Vitest to ensure layout components render correctly and state flows:
```bash
npm run test
```

### Running End-to-End Tests
Playwright tests simulate actual user journeys through the application:
```bash
# Verify UI and Scenario triggers
npx playwright test
```
