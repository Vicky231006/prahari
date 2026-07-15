import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { fetchQuantumSessions, fetchAuditTrail } from '../api';
import { Key } from 'lucide-react';
import SeverityBadge from '../components/SeverityBadge';
import SharedCasesLayout from '../components/shared/SharedCasesLayout';
import QuantumWorkspaceDrawer from '../components/QuantumWorkspaceDrawer';

export default function QuantumCases() {
  const [statusFilter, setStatusFilter] = useState('');

  // ── Pagination and selection state ──
  const [casesCursor, setCasesCursor] = useState(null);
  const [casesCursorHistory, setCasesCursorHistory] = useState([]);
  const [auditCursor, setAuditCursor] = useState(null);
  const [selectedSession, setSelectedSession] = useState(null);

  const handleStatusChange = (value) => {
    setCasesCursor(null);
    setCasesCursorHistory([]);
    setStatusFilter(value);
  };

  // ── Quantum Sessions Query ───────────────────────────────────────────────
  // We use fetchQuantumSessions here as requested to display Quantum Investigation sessions
  const { data: casesData, isLoading: casesLoading, isFetching: casesFetching } = useQuery({
    queryKey: ['quantum_sessions', statusFilter, casesCursor],
    queryFn: () => fetchQuantumSessions({ limit: 50, beforeId: casesCursor }),
    staleTime: 5000,
    keepPreviousData: true,
  });

  const allCases = casesData?.items ?? [];
  // Client-side status filtering to mirror Cases.jsx exactly
  const cases = allCases.filter(c => {
    const currentStatus = c.status || 'open';
    if (!statusFilter) return true;
    return currentStatus === statusFilter;
  });

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
    queryKey: ['audit_quantum', auditCursor],
    queryFn: () => fetchAuditTrail({ limit: 50, beforeId: auditCursor, isQuantum: true }),
    staleTime: 10000,
    keepPreviousData: true,
  });

  // Filter audit records to only show quantum-specific ones in a real app.
  // For demo purposes, we will display the fetched audit trail.
  const audit = auditData?.items ?? [];
  const auditNextCursor = auditData?.next_cursor ?? null;

  // ── Components to pass to layout ──
  const tableEmptyState = (
    <div className="empty-state">
      <Key className="empty-state__icon" />
      <div className="empty-state__text">No quantum cases found in this queue.</div>
    </div>
  );

  const tableComponent = (
    <table className="data-table">
      <thead>
        <tr>
          <th>Status</th>
          <th>Quantum Severity</th>
          <th>Session ID</th>
          <th>Environment</th>
          <th>Readiness</th>
          <th>Last Updated</th>
        </tr>
      </thead>
      <tbody>
        {cases.map(c => {
          const riskLevel = c.classification === 'legacy' ? 'high' : 'low';
          return (
            <tr key={c.id} onClick={() => setSelectedSession(c)} style={{ cursor: 'pointer' }}>
              <td>
                <span className="severity-badge" style={{ background: 'var(--surface-hover)' }}>
                  {c.status || 'open'}
                </span>
              </td>
              <td><SeverityBadge severity={riskLevel} /></td>
              <td className="font-mono text-sm">{c.session_id?.substring(0, 16)}...</td>
              <td className="text-sm">{c.environment || 'Cloud'}</td>
              <td className="font-mono text-sm">{c.readiness_score != null ? `${c.readiness_score}%` : 'N/A'}</td>
              <td className="text-xs text-muted">{new Date(c.created_at).toLocaleString()}</td>
            </tr>
          );
        })}
      </tbody>
    </table>
  );

  return (
    <>
      {selectedSession && (
        <QuantumWorkspaceDrawer 
          session={selectedSession} 
          onClose={() => setSelectedSession(null)} 
        />
      )}
      <SharedCasesLayout
        title="Quantum Cases & Audit"
        subtitle="Immutable tracking of analyst actions and quantum risk investigations."
        statusFilter={statusFilter}
        onStatusChange={handleStatusChange}
        
        tableComponent={tableComponent}
        tableLoading={casesLoading}
        tableEmptyState={tableEmptyState}
        tableIsEmpty={cases.length === 0}
        
        hasMore={casesHasMore}
        isFirstPage={casesIsFirstPage}
        isFetching={casesFetching}
        currentPage={casesCursorHistory.length + 1}
        onLoadNext={loadCasesNext}
        onLoadPrev={loadCasesPrev}
        
        audit={audit}
        auditLoading={auditLoading}
        auditNextCursor={auditNextCursor}
        onAuditNextPage={setAuditCursor}
        auditTitle="Recent Audit Trail"
        auditEmptyText="No actions logged yet."
      />
    </>
  );
}
