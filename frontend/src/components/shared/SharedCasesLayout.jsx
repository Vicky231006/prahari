import { ChevronDown } from 'lucide-react';
import AuditSidebar from './AuditSidebar';

export default function SharedCasesLayout({
  title,
  subtitle,
  statusFilter,
  onStatusChange,
  
  // Table Props
  tableComponent,
  tableLoading,
  tableEmptyState,
  tableIsEmpty,
  
  // Pagination Props
  hasMore,
  isFirstPage,
  isFetching,
  currentPage,
  onLoadNext,
  onLoadPrev,
  
  // Audit Props
  audit,
  auditLoading,
  auditNextCursor,
  onAuditNextPage,
  auditTitle,
  auditEmptyText
}) {
  return (
    <div className="fade-in">
      <div className="flex items-center justify-between mb-24">
        <div>
          <h1 className="section-header mb-8">{title}</h1>
          <p className="section-sub mb-0">{subtitle}</p>
        </div>
        <select
          value={statusFilter}
          onChange={(e) => onStatusChange(e.target.value)}
          style={{ background: 'var(--input-bg)', border: 'var(--surface-border)', borderRadius: 'var(--radius-sm)', padding: '8px 12px', color: 'var(--text-primary)', fontSize: '0.82rem', outline: 'none' }}
        >
          <option value="">All Statuses</option>
          <option value="open">Open</option>
          <option value="escalated">Escalated</option>
          <option value="dismissed">Dismissed</option>
          <option value="mitigated">Mitigated</option>
        </select>
      </div>

      <div className="app-layout" style={{ display: 'grid', gridTemplateColumns: '1fr 350px', gap: '24px', gridTemplateAreas: 'none', height: 'auto', overflow: 'visible' }}>
        
        {/* ── Main Table Area ── */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
          <div className="card p-0" style={{ alignSelf: 'start' }}>
            {tableLoading ? (
              <div className="loading-center"><div className="spinner" /> Loading cases...</div>
            ) : tableIsEmpty ? (
              tableEmptyState
            ) : (
              tableComponent
            )}
          </div>

          {/* Cases pagination */}
          {(hasMore || !isFirstPage) && (
            <div className="flex items-center justify-between" style={{ opacity: isFetching ? 0.5 : 1 }}>
              <button className="btn btn--secondary btn--small" onClick={onLoadPrev} disabled={isFirstPage || isFetching}>
                ← Previous
              </button>
              <span className="text-xs text-muted">Page {currentPage}</span>
              <button
                className="btn btn--secondary btn--small flex items-center gap-6"
                onClick={onLoadNext}
                disabled={!hasMore || isFetching}
              >
                Load more <ChevronDown size={13} />
              </button>
            </div>
          )}
        </div>

        {/* ── Audit Trail Sidebar ── */}
        <AuditSidebar 
          audit={audit}
          loading={auditLoading}
          nextCursor={auditNextCursor}
          onNextPage={onAuditNextPage}
          title={auditTitle}
          emptyText={auditEmptyText}
        />
      </div>
    </div>
  );
}
