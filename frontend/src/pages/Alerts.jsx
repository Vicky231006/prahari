import { useState, useCallback } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { fetchAlerts } from '../api';
import { ShieldAlert, Filter, Search, ChevronDown, RefreshCw } from 'lucide-react';
import SeverityBadge from '../components/SeverityBadge';
import ExplanationDrawer from '../components/ExplanationDrawer';
import { useSearchParams } from 'react-router-dom';

export default function Alerts() {
  const [searchParams, setSearchParams] = useSearchParams();
  const identityIdFilter = searchParams.get('identity_id') || '';
  const severityFilter = searchParams.get('severity') || '';

  const [selectedAlert, setSelectedAlert] = useState(null);

  // Cursor stack: array of next_cursor values for visited pages.
  // cursor = null means first page; cursor = string means a subsequent page.
  const [cursor, setCursor] = useState(null);
  const [cursorHistory, setCursorHistory] = useState([]); // for back navigation

  // Reset pagination when filters change
  const handleFilterChange = useCallback((key, value) => {
    setCursor(null);
    setCursorHistory([]);
    if (value) searchParams.set(key, value);
    else searchParams.delete(key);
    setSearchParams(searchParams);
  }, [searchParams, setSearchParams]);

  const queryClient = useQueryClient();

  const { data, isLoading, isFetching, refetch } = useQuery({
    queryKey: ['alerts', { severity: severityFilter, identity_id: identityIdFilter, cursor }],
    queryFn: () => fetchAlerts(
      { severity: severityFilter, identity_id: identityIdFilter },
      { limit: 50, beforeId: cursor }
    ),
    staleTime: 5000,
    keepPreviousData: true, // prevents flash to empty state during page transitions
  });

  const alerts = data?.items ?? [];
  const nextCursor = data?.next_cursor ?? null;
  const hasMore = Boolean(nextCursor);

  const loadNextPage = () => {
    if (!nextCursor) return;
    setCursorHistory(prev => [...prev, cursor]); // save current cursor to go back
    setCursor(nextCursor);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const loadPrevPage = () => {
    const history = [...cursorHistory];
    const prev = history.pop();
    setCursorHistory(history);
    setCursor(prev ?? null);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const isFirstPage = cursorHistory.length === 0;

  return (
    <div className="fade-in">
      <div className="flex items-center justify-between mb-24">
        <div>
          <h1 className="section-header mb-8">Fusion Alerts</h1>
          <p className="section-sub mb-0">Joint correlation across transactional and security domains.</p>
        </div>

        <div className="flex gap-12">
          <div className="flex items-center gap-8 px-12" style={{ background: 'var(--input-bg)', borderRadius: 'var(--radius-sm)', border: 'var(--surface-border)' }}>
            <Search size={14} className="text-muted" />
            <input
              type="text"
              placeholder="Filter by Identity ID..."
              value={identityIdFilter}
              onChange={(e) => handleFilterChange('identity_id', e.target.value)}
              style={{ background: 'transparent', border: 'none', outline: 'none', padding: '8px 4px', color: 'var(--text-primary)', fontSize: '0.82rem' }}
            />
          </div>
          <select
            value={severityFilter}
            onChange={(e) => handleFilterChange('severity', e.target.value)}
            style={{ background: 'var(--input-bg)', border: 'var(--surface-border)', borderRadius: 'var(--radius-sm)', padding: '8px 12px', color: 'var(--text-primary)', fontSize: '0.82rem', outline: 'none' }}
          >
            <option value="">All Severities</option>
            <option value="critical">Critical</option>
            <option value="high">High</option>
            <option value="medium">Medium</option>
            <option value="low">Low</option>
          </select>

          <button
            onClick={refetch}
            className="btn btn--secondary btn--small flex items-center gap-6"
            title="Refresh"
            disabled={isFetching}
          >
            <RefreshCw size={13} className={isFetching ? 'spin' : ''} />
          </button>
        </div>
      </div>

      <div className="card" style={{ padding: 0 }}>
        {isLoading ? (
          <div className="loading-center"><div className="spinner" /> Loading alerts...</div>
        ) : alerts.length === 0 ? (
          <div className="empty-state">
            <ShieldAlert className="empty-state__icon" />
            <div className="empty-state__text">No alerts found matching criteria.</div>
          </div>
        ) : (
          <table className="data-table">
            <thead>
              <tr>
                <th>Severity</th>
                <th>Identity ID</th>
                <th>Fusion Score</th>
                <th>Signals Correlated</th>
                <th>Time (IST)</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {alerts.map(alert => (
                <tr key={alert.id} onClick={() => setSelectedAlert(alert)}>
                  <td><SeverityBadge severity={alert.severity} /></td>
                  <td className="font-mono font-600 text-sm">{alert.identity_id}</td>
                  <td>{(alert.fusion_score * 100).toFixed(1)}%</td>
                  <td>
                    <span className="text-xs text-muted truncate" style={{ maxWidth: '200px', display: 'inline-block' }}>
                      {alert.contributing_signals.join(', ')}
                    </span>
                  </td>
                  <td className="text-xs text-muted">{new Date(alert.created_at).toLocaleTimeString()}</td>
                  <td>
                    <span className="severity-badge" style={{ background: 'var(--surface-hover)' }}>
                      {alert.status || 'open'}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Pagination controls */}
      {(hasMore || !isFirstPage) && (
        <div className="flex items-center justify-between mt-16" style={{ opacity: isFetching ? 0.5 : 1 }}>
          <button
            className="btn btn--secondary btn--small"
            onClick={loadPrevPage}
            disabled={isFirstPage || isFetching}
          >
            ← Previous
          </button>

          <span className="text-xs text-muted">
            Showing {alerts.length} alerts &nbsp;·&nbsp; Page {cursorHistory.length + 1}
          </span>

          <button
            className="btn btn--secondary btn--small flex items-center gap-6"
            onClick={loadNextPage}
            disabled={!hasMore || isFetching}
          >
            Load more <ChevronDown size={13} />
          </button>
        </div>
      )}

      <ExplanationDrawer
        alert={selectedAlert}
        onClose={() => setSelectedAlert(null)}
        onActionComplete={refetch}
      />
    </div>
  );
}
