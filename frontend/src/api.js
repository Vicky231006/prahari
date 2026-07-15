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
 * Escalate an alert to Tier 2.
 * Creates a linked Case if one does not already exist.
 * Writes an ESCALATE audit entry.
 * Returns the updated AlertResponse { ...alert, status: 'escalated' }.
 */
export async function escalateAlert(alertId, actor = 'Tier 1 Analyst', notes = '') {
  const res = await fetch(`${API_BASE}/alerts/${alertId}/escalate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ actor, notes }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Unknown error' }));
    throw new Error(err.detail || 'Escalation failed');
  }
  return res.json();
}

/**
 * Dismiss an alert as a False Positive.
 * Creates a linked Case if one does not already exist.
 * Writes a DISMISS audit entry including the analyst reason.
 * Returns the updated AlertResponse { ...alert, status: 'dismissed' }.
 */
export async function dismissAlert(alertId, actor = 'Tier 1 Analyst', notes = '') {
  const res = await fetch(`${API_BASE}/alerts/${alertId}/dismiss`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ actor, notes }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Unknown error' }));
    throw new Error(err.detail || 'Dismiss failed');
  }
  return res.json();
}

/**
 * Fetch a page of audit trail entries.
 * Returns { items: AuditTrailResponse[], next_cursor: string | null }
 */
export async function fetchAuditTrail({ limit = 50, beforeId = null, isQuantum = false } = {}) {
  if (isQuantum) {
    const qAudits = JSON.parse(localStorage.getItem('quantum_audits') || '[]');
    return { items: qAudits, next_cursor: null };
  }

  const params = new URLSearchParams();
  params.set('limit', String(limit));
  if (beforeId) params.set('before_id', beforeId);

  const res = await fetch(`${API_BASE}/audit?${params}`);
  if (!res.ok) throw new Error('Failed to fetch audit trail');
  return res.json();
}

/**
 * MOCK: Escalate Quantum Session
 * Simulates backend integration for quantum case management
 */
export async function escalateQuantumSession(sessionId, actor = 'Tier 1 Analyst', notes = '') {
  localStorage.setItem(`quantum_status_${sessionId}`, 'escalated');
  const qAudits = JSON.parse(localStorage.getItem('quantum_audits') || '[]');
  qAudits.unshift({
    id: 'qaudit-' + Math.random().toString(36).substr(2, 9),
    actor,
    action: 'ESCALATE',
    notes,
    created_at: new Date().toISOString()
  });
  localStorage.setItem('quantum_audits', JSON.stringify(qAudits));
  return new Promise((resolve) => setTimeout(() => resolve({ status: 'escalated' }), 600));
}

/**
 * MOCK: Dismiss Quantum Session
 * Simulates backend integration for quantum case management
 */
export async function dismissQuantumSession(sessionId, actor = 'Tier 1 Analyst', notes = '') {
  localStorage.setItem(`quantum_status_${sessionId}`, 'dismissed');
  const qAudits = JSON.parse(localStorage.getItem('quantum_audits') || '[]');
  qAudits.unshift({
    id: 'qaudit-' + Math.random().toString(36).substr(2, 9),
    actor,
    action: 'DISMISS',
    notes,
    created_at: new Date().toISOString()
  });
  localStorage.setItem('quantum_audits', JSON.stringify(qAudits));
  return new Promise((resolve) => setTimeout(() => resolve({ status: 'dismissed' }), 600));
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
  const data = await res.json();
  if (data && data.items) {
    data.items = data.items.map(item => ({
      ...item,
      status: localStorage.getItem(`quantum_status_${item.session_id}`) || 'open'
    }));
  }
  return data;
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

/**
 * Fetch the rich identity profile for a given identity ID.
 * Returns IdentityProfileResponse from /api/identities/{identity_id}.
 */
export async function fetchIdentityProfile(identityId) {
  const res = await fetch(`${API_BASE}/identities/${encodeURIComponent(identityId)}`);
  if (!res.ok) throw new Error('Identity profile not found');
  return res.json();
}

/**
 * Fetch the investigation timeline for a specific alert.
 * Returns AlertTimelineResponse from /api/alerts/{id}/timeline.
 */
export async function fetchAlertTimeline(alertId) {
  const res = await fetch(`${API_BASE}/alerts/${alertId}/timeline`);
  if (!res.ok) throw new Error('Failed to fetch alert timeline');
  return res.json();
}

/**
 * Fetch the investigation graph for a specific identity.
 * Returns GraphResponse from /api/graph/{identity_id}.
 */
export async function fetchInvestigationGraph(identityId) {
  const res = await fetch(`${API_BASE}/graph/${encodeURIComponent(identityId)}`);
  if (!res.ok) throw new Error('Failed to fetch investigation graph');
  return res.json();
}
