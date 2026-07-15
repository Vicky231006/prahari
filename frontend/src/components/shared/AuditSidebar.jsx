import { Activity, ChevronDown, Briefcase } from 'lucide-react';

export default function AuditSidebar({ audit, loading, nextCursor, onNextPage, title = "Recent Audit Trail", emptyText = "No actions logged yet." }) {
  return (
    <div className="card" style={{ padding: '24px 20px', alignSelf: 'start', position: 'sticky', top: '24px', maxHeight: 'calc(100vh - 120px)', display: 'flex', flexDirection: 'column' }}>
      <div className="flex items-center gap-8 mb-16 pb-16 border-bottom" style={{ flexShrink: 0 }}>
        <Activity size={16} className="text-muted" />
        <h3 style={{ fontSize: '0.9rem' }}>{title}</h3>
      </div>

      <div className="flex-col" style={{ flex: 1, overflowY: 'auto', paddingRight: '10px' }}>
        {loading ? (
          <div className="text-sm text-muted text-center py-24">Loading audit log...</div>
        ) : audit.length === 0 ? (
          <div className="text-sm text-muted text-center py-24">{emptyText}</div>
        ) : (
          audit.map(a => (
            <div key={a.id} className="audit-entry">
              <div className="audit-entry__icon">{a.actor ? a.actor.charAt(0).toUpperCase() : <Briefcase size={14} />}</div>
              <div className="audit-entry__content">
                <div className="text-sm">
                  <span className="audit-entry__action">{a.actor || 'System'}</span> performed <strong>{a.action}</strong>
                </div>
                {(a.details?.notes || a.notes) && (
                  <div className="text-xs text-muted mt-8 font-mono" style={{ padding: '6px 10px', background: 'var(--surface-hover)', borderRadius: '4px' }}>
                    "{a.details?.notes || a.notes}"
                  </div>
                )}
                <div className="audit-entry__time">{new Date(a.created_at).toLocaleString()}</div>
              </div>
            </div>
          ))
        )}
      </div>

      {nextCursor && onNextPage && (
        <button
          className="btn btn--secondary btn--small flex items-center gap-6 mt-16"
          style={{ width: '100%', justifyContent: 'center', flexShrink: 0 }}
          onClick={() => onNextPage(nextCursor)}
        >
          Load more entries <ChevronDown size={13} />
        </button>
      )}
    </div>
  );
}
