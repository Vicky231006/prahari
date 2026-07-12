import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { fetchAlerts } from '../api';
import { ShieldAlert, Filter, Search } from 'lucide-react';
import SeverityBadge from '../components/SeverityBadge';
import ExplanationDrawer from '../components/ExplanationDrawer';
import { useSearchParams } from 'react-router-dom';

export default function Alerts() {
  const [searchParams, setSearchParams] = useSearchParams();
  const identityIdFilter = searchParams.get('identity_id') || '';
  const severityFilter = searchParams.get('severity') || '';
  
  const [selectedAlert, setSelectedAlert] = useState(null);

  const { data: alerts, isLoading, refetch } = useQuery({
    queryKey: ['alerts', { severity: severityFilter, identity_id: identityIdFilter }],
    queryFn: () => fetchAlerts({ severity: severityFilter, identity_id: identityIdFilter }),
    staleTime: 5000,
  });

  const handleFilterChange = (key, value) => {
    if (value) searchParams.set(key, value);
    else searchParams.delete(key);
    setSearchParams(searchParams);
  };

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
        </div>
      </div>

      <div className="card" style={{ padding: 0 }}>
        {isLoading ? (
          <div className="loading-center"><div className="spinner" /> Loading alerts...</div>
        ) : alerts?.length === 0 ? (
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
              {alerts?.map(alert => (
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
                      {alert.case?.status || 'open'}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      <ExplanationDrawer 
        alert={selectedAlert} 
        onClose={() => setSelectedAlert(null)}
        onActionComplete={refetch}
      />
    </div>
  );
}
