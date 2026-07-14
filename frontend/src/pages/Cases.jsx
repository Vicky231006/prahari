import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { fetchCases, fetchAuditTrail } from '../api';
import { Briefcase, Activity, ChevronDown } from 'lucide-react';
import SeverityBadge from '../components/SeverityBadge';

export default function Cases() {
  const [statusFilter, setStatusFilter] = useState('');

  // Separate cursor state for the cases table and the audit trail sidebar
  const [casesCursor, setCasesCursor] = useState(null);
  const [casesCursorHistory, setCasesCursorHistory] = useState([]);
  const [auditCursor, setAuditCursor] = useState(null);

  const handleStatusChange = (value) => {
    // Reset cases pagination when filter changes
    setCasesCursor(null);
    setCasesCursorHistory([]);
    setStatusFilter(value);
  };

  // ── Cases query ──────────────────────────────────────────────────────────
  const { data: casesData, isLoading: casesLoading, isFetching: casesFetching } = useQuery({
    queryKey: ['cases', statusFilter, casesCursor],
    queryFn: () => fetchCases(statusFilter, { limit: 50, beforeId: casesCursor }),
    staleTime: 5000,
    keepPreviousData: true,
  });

  const cases = casesData?.items ?? [];
  const casesNextCursor = casesData?.next_cursor ?? null;
  const casesHasMore = Boolean(casesNextCursor);
  const casesIsFirstPage = casesCursorHistory.length === 0;

  const loadCasesNext = () => {
    if (!casesNextCursor) return;
    setCasesCursorHistory(prev => [...prev, casesCursor]);
    setCasesCursor(casesNextCursor);
  };
  const loadCasesPrev = () => {
    const history = [...casesCursorHistory];
    const prev = history.pop();
    setCasesCursorHistory(history);
    setCasesCursor(prev ?? null);
  };

  // ── Audit trail query ────────────────────────────────────────────────────
  const { data: auditData, isLoading: auditLoading } = useQuery({
    queryKey: ['audit', auditCursor],
    queryFn: () => fetchAuditTrail({ limit: 50, beforeId: auditCursor }),
    staleTime: 10000,
    keepPreviousData: true,
  });

  const audit = auditData?.items ?? [];
  const auditNextCursor = auditData?.next_cursor ?? null;

  return (
    <div className="fade-in">
      <div className="flex items-center justify-between mb-24">
        <div>
          <h1 className="section-header mb-8">Case Management &amp; Audit</h1>
          <p className="section-sub mb-0">Immutable tracking of analyst actions and alert lifecycle.</p>
        </div>
        <select
          value={statusFilter}
          onChange={(e) => handleStatusChange(e.target.value)}
          style={{ background: 'var(--input-bg)', border: 'var(--surface-border)', borderRadius: 'var(--radius-sm)', padding: '8px 12px', color: 'var(--text-primary)', fontSize: '0.82rem', outline: 'none' }}
        >
          <option value="">All Statuses</option>
          <option value="open">Open</option>
          <option value="escalated">Escalated</option>
          <option value="dismissed">Dismissed</option>
        </select>
      </div>

      <div className="app-layout" style={{ display: 'grid', gridTemplateColumns: '1fr 350px', gap: '24px', gridTemplateAreas: 'none', height: 'auto', overflow: 'visible' }}>

        {/* ── Cases table ───────────────────────────────────────────────── */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
          <div className="card p-0" style={{ alignSelf: 'start' }}>
            {casesLoading ? (
              <div className="loading-center"><div className="spinner" /> Loading cases...</div>
            ) : cases.length === 0 ? (
              <div className="empty-state">
                <Briefcase className="empty-state__icon" />
                <div className="empty-state__text">No cases found in this queue.</div>
              </div>
            ) : (
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Status</th>
                    <th>Alert Severity</th>
                    <th>Identity ID</th>
                    <th>Last Updated</th>
                  </tr>
                </thead>
                <tbody>
                  {cases.map(c => (
                    <tr key={c.id}>
                      <td>
                        <span className="severity-badge" style={{ background: 'var(--surface-hover)' }}>{c.status}</span>
                      </td>
                      <td><SeverityBadge severity={c.alert?.severity} /></td>
                      <td className="font-mono text-sm">{c.alert?.identity_id}</td>
                      <td className="text-xs text-muted">{new Date(c.updated_at).toLocaleString()}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>

          {/* Cases pagination */}
          {(casesHasMore || !casesIsFirstPage) && (
            <div className="flex items-center justify-between" style={{ opacity: casesFetching ? 0.5 : 1 }}>
              <button className="btn btn--secondary btn--small" onClick={loadCasesPrev} disabled={casesIsFirstPage || casesFetching}>
                ← Previous
              </button>
              <span className="text-xs text-muted">Page {casesCursorHistory.length + 1}</span>
              <button
                className="btn btn--secondary btn--small flex items-center gap-6"
                onClick={loadCasesNext}
                disabled={!casesHasMore || casesFetching}
              >
                Load more <ChevronDown size={13} />
              </button>
            </div>
          )}
        </div>

        {/* ── Audit trail sidebar ───────────────────────────────────────── */}
        <div className="card" style={{ padding: '24px 20px', alignSelf: 'start' }}>
          <div className="flex items-center gap-8 mb-16 pb-16 border-bottom">
            <Activity size={16} className="text-muted" />
            <h3 style={{ fontSize: '0.9rem' }}>Recent Audit Trail</h3>
          </div>

          <div className="flex-col">
            {auditLoading ? (
              <div className="text-sm text-muted text-center py-24">Loading audit log...</div>
            ) : audit.length === 0 ? (
              <div className="text-sm text-muted text-center py-24">No actions logged yet.</div>
            ) : (
              audit.map(a => (
                <div key={a.id} className="audit-entry">
                  <div className="audit-entry__icon">{a.actor.charAt(0).toUpperCase()}</div>
                  <div className="audit-entry__content">
                    <div className="text-sm">
                      <span className="audit-entry__action">{a.actor}</span> performed <strong>{a.action}</strong>
                    </div>
                    {a.details.notes && (
                      <div className="text-xs text-muted mt-8 font-mono" style={{ padding: '6px 10px', background: 'var(--surface-hover)', borderRadius: '4px' }}>
                        "{a.details.notes}"
                      </div>
                    )}
                    <div className="audit-entry__time">{new Date(a.created_at).toLocaleString()}</div>
                  </div>
                </div>
              ))
            )}
          </div>

          {/* Audit trail load-more (sidebar — no back nav needed) */}
          {auditNextCursor && (
            <button
              className="btn btn--secondary btn--small flex items-center gap-6 mt-16"
              style={{ width: '100%', justifyContent: 'center' }}
              onClick={() => setAuditCursor(auditNextCursor)}
            >
              Load more entries <ChevronDown size={13} />
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
