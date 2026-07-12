const API_BASE = '/api';

export async function fetchAlerts(filters = {}) {
  const params = new URLSearchParams();
  if (filters.severity) params.set('severity', filters.severity);
  if (filters.identity_id) params.set('identity_id', filters.identity_id);
  const res = await fetch(`${API_BASE}/alerts?${params}`);
  if (!res.ok) throw new Error('Failed to fetch alerts');
  return res.json();
}

export async function fetchAlertDetail(alertId) {
  const res = await fetch(`${API_BASE}/alerts/${alertId}`);
  if (!res.ok) throw new Error('Failed to fetch alert detail');
  return res.json();
}

export async function fetchDashboardKPIs() {
  const res = await fetch(`${API_BASE}/dashboard/kpis`);
  if (!res.ok) throw new Error('Failed to fetch KPIs');
  return res.json();
}

export async function fetchCases(status) {
  const params = status ? `?status=${status}` : '';
  const res = await fetch(`${API_BASE}/cases${params}`);
  if (!res.ok) throw new Error('Failed to fetch cases');
  return res.json();
}

export async function performCaseAction(caseId, action, actor = 'analyst', notes = '') {
  const res = await fetch(`${API_BASE}/cases/${caseId}/action`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ action, actor, notes }),
  });
  if (!res.ok) throw new Error('Failed to perform case action');
  return res.json();
}

export async function fetchAuditTrail() {
  const res = await fetch(`${API_BASE}/audit`);
  if (!res.ok) throw new Error('Failed to fetch audit trail');
  return res.json();
}

export async function fetchQuantumSessions() {
  const res = await fetch(`${API_BASE}/quantum/sessions`);
  if (!res.ok) throw new Error('Failed to fetch quantum sessions');
  return res.json();
}

export async function injectScenario(scenarioType) {
  const res = await fetch(`${API_BASE}/demo/inject`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ scenario_type: scenarioType }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Unknown error' }));
    throw new Error(err.detail || 'Scenario injection failed');
  }
  return res.json();
}

export function createAlertsWebSocket(onMessage) {
  const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const wsUrl = `${proto}//${window.location.host}/ws/alerts`;
  const ws = new WebSocket(wsUrl);

  ws.onopen = () => { onMessage({ type: 'WS_CONNECTED' }); };
  ws.onclose = () => { onMessage({ type: 'WS_DISCONNECTED' }); };
  ws.onerror = () => { onMessage({ type: 'WS_DISCONNECTED' }); };
  ws.onmessage = (evt) => {
    try {
      const data = JSON.parse(evt.data);
      onMessage(data);
    } catch (e) { /* ignore malformed messages */ }
  };

  return ws;
}
