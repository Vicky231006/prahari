import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { fetchCases, fetchAuditTrail } from '../api';
import { Briefcase } from 'lucide-react';
import SeverityBadge from '../components/SeverityBadge';
import SharedCasesLayout from '../components/shared/SharedCasesLayout';

export default function Cases() {
  const [statusFilter, setStatusFilter] = useState('');

  // Separate cursor state for the cases table and the audit trail sidebar
  const [casesCursor, setCasesCursor] = useState(null);
  const [casesCursorHistory, setCasesCursorHistory] = useState([]);
  const [auditCursor, setAuditCursor] = useState(null);

  const handleStatusChange = (value) => {
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

  // ── Components to pass to layout ──
  const tableEmptyState = (
    <div className="empty-state">
      <Briefcase className="empty-state__icon" />
      <div className="empty-state__text">No cases found in this queue.</div>
    </div>
  );

  const tableComponent = (
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
  );

  return (
    <SharedCasesLayout
      title="Alert Cases & Audit"
      subtitle="Immutable tracking of analyst actions and traditional alert lifecycle."
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
  );
}
