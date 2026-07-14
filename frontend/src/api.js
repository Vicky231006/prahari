const API_BASE = '/api';

/**
 * Fetch a page of fused alerts.
 *
 * The backend now returns { items, next_cursor } instead of a plain array.
 * Pass `beforeId` (the value of `next_cursor` from the previous response) to
 * fetch the next page.  When next_cursor is null there are no more pages.
 */
export async function fetchAlerts(filters = {}, { limit = 50, beforeId = null } = {}) {
  const params = new URLSearchParams();
  if (filters.severity) params.set('severity', filters.severity);
  if (filters.identity_id) params.set('identity_id', filters.identity_id);
  params.set('limit', String(limit));
  if (beforeId) params.set('before_id', beforeId);

  const res = await fetch(`${API_BASE}/alerts?${params}`);
  if (!res.ok) throw new Error('Failed to fetch alerts');
  return res.json(); // { items: AlertResponse[], next_cursor: string | null }
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

/**
 * Fetch a page of cases.
 * Returns { items: CaseResponse[], next_cursor: string | null }
 */
export async function fetchCases(status, { limit = 50, beforeId = null } = {}) {
  const params = new URLSearchParams();
  if (status) params.set('status', status);
  params.set('limit', String(limit));
  if (beforeId) params.set('before_id', beforeId);

  const res = await fetch(`${API_BASE}/cases?${params}`);
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

/**
 * Fetch a page of audit trail entries.
 * Returns { items: AuditTrailResponse[], next_cursor: string | null }
 */
export async function fetchAuditTrail({ limit = 50, beforeId = null } = {}) {
  const params = new URLSearchParams();
  params.set('limit', String(limit));
  if (beforeId) params.set('before_id', beforeId);

  const res = await fetch(`${API_BASE}/audit?${params}`);
  if (!res.ok) throw new Error('Failed to fetch audit trail');
  return res.json();
}

/**
 * Fetch a page of quantum/TLS sessions.
 * Returns { items: QuantumAlertResponse[], next_cursor: string | null }
 */
export async function fetchQuantumSessions({ limit = 100, beforeId = null } = {}) {
  const params = new URLSearchParams();
  params.set('limit', String(limit));
  if (beforeId) params.set('before_id', beforeId);

  const res = await fetch(`${API_BASE}/quantum/sessions?${params}`);
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
