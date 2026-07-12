import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { fetchCases, fetchAuditTrail } from '../api';
import { Briefcase, Activity } from 'lucide-react';
import SeverityBadge from '../components/SeverityBadge';

export default function Cases() {
  const [statusFilter, setStatusFilter] = useState('');
  
  const { data: cases, isLoading: casesLoading } = useQuery({
    queryKey: ['cases', statusFilter],
    queryFn: () => fetchCases(statusFilter),
    staleTime: 5000,
  });

  const { data: audit, isLoading: auditLoading } = useQuery({
    queryKey: ['audit'],
    queryFn: fetchAuditTrail,
    staleTime: 10000,
  });

  return (
    <div className="fade-in">
      <div className="flex items-center justify-between mb-24">
        <div>
          <h1 className="section-header mb-8">Case Management & Audit</h1>
          <p className="section-sub mb-0">Immutable tracking of analyst actions and alert lifecycle.</p>
        </div>
        <select 
          value={statusFilter} 
          onChange={(e) => setStatusFilter(e.target.value)}
          style={{ background: 'var(--input-bg)', border: 'var(--surface-border)', borderRadius: 'var(--radius-sm)', padding: '8px 12px', color: 'var(--text-primary)', fontSize: '0.82rem', outline: 'none' }}
        >
          <option value="">All Statuses</option>
          <option value="open">Open</option>
          <option value="escalated">Escalated</option>
          <option value="dismissed">Dismissed</option>
        </select>
      </div>

      <div className="app-layout" style={{ display: 'grid', gridTemplateColumns: '1fr 350px', gap: '24px', gridTemplateAreas: 'none', height: 'auto', overflow: 'visible' }}>
        
        <div className="card p-0" style={{ alignSelf: 'start' }}>
          {casesLoading ? (
             <div className="loading-center"><div className="spinner" /> Loading cases...</div>
          ) : cases?.length === 0 ? (
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
                {cases?.map(c => (
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

        <div className="card" style={{ padding: '24px 20px', alignSelf: 'start' }}>
          <div className="flex items-center gap-8 mb-16 pb-16 border-bottom">
            <Activity size={16} className="text-muted" />
            <h3 style={{ fontSize: '0.9rem' }}>Recent Audit Trail</h3>
          </div>
          
          <div className="flex-col">
            {auditLoading ? (
              <div className="text-sm text-muted text-center py-24">Loading audit log...</div>
            ) : audit?.length === 0 ? (
              <div className="text-sm text-muted text-center py-24">No actions logged yet.</div>
            ) : (
              audit?.map(a => (
                <div key={a.id} className="audit-entry">
                  <div className="audit-entry__icon">
                    {a.actor.charAt(0).toUpperCase()}
                  </div>
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
        </div>
      </div>
    </div>
  );
}
