import { useQuery } from '@tanstack/react-query';
import { fetchDashboardKPIs } from '../api';
import { AlertCircle, ShieldAlert, Activity, UserX, Binary } from 'lucide-react';
import SeverityBadge from '../components/SeverityBadge';
import { useNavigate } from 'react-router-dom';

export default function Dashboard() {
  const navigate = useNavigate();
  const { data: kpis, isLoading, error } = useQuery({
    queryKey: ['dashboard_kpis'],
    queryFn: fetchDashboardKPIs,
    staleTime: 30000,
  });

  if (isLoading) return <div className="loading-center"><div className="spinner" /> Loading Core Metrics...</div>;
  if (error) return <div className="empty-state"><AlertCircle className="empty-state__icon" /> <div className="empty-state__text">Failed to load KPIs</div></div>;

  const alerts = kpis?.alerts_by_severity || {};
  const totalAlerts = Object.values(alerts).reduce((a, b) => a + b, 0);

  return (
    <div className="fade-in">
      <h1 className="section-header">Real-Time Core Metrics</h1>
      <p className="section-sub">Aggregated sliding-window anomalies across transaction and security streams.</p>

      <div className="kpi-grid">
        <div className="card card--clickable" onClick={() => navigate('/alerts')}>
          <div className="flex items-center gap-8 mb-8">
            <ShieldAlert size={18} className="text-muted" />
            <div className="kpi-card__label">Total Active Anomalies</div>
          </div>
          <div className="kpi-card__value">{totalAlerts}</div>
          <div className="kpi-card__sub text-muted flex gap-12 mt-12">
             <SeverityBadge severity="critical" /> {alerts.critical || 0}
             <SeverityBadge severity="high" /> {alerts.high || 0}
          </div>
        </div>

        <div className="card card--clickable" onClick={() => navigate('/quantum')}>
          <div className="flex items-center gap-8 mb-8">
            <Binary size={18} className="text-muted" />
            <div className="kpi-card__label">Quantum Risk Exposure</div>
          </div>
          <div className="kpi-card__value">{kpis?.quantum_stats?.hndl_exposed_count || 0}</div>
          <div className="kpi-card__sub text-muted mt-12">
            HNDL Flagged Sessions in last 24h
          </div>
        </div>
      </div>

      <h2 className="section-header mt-24">High-Risk Identities</h2>
      <div className="card p-0">
        <table className="data-table">
          <thead>
            <tr>
              <th>Identity ID</th>
              <th>Risk Score</th>
              <th>Recent Anomalies</th>
              <th>Action</th>
            </tr>
          </thead>
          <tbody>
            {kpis?.top_risk_identities?.length === 0 ? (
              <tr><td colSpan="4" className="text-center py-24 text-muted">No high-risk identities currently detected.</td></tr>
            ) : (
              kpis?.top_risk_identities?.map((id) => (
                <tr key={id.identity_id} onClick={() => navigate(`/alerts?identity_id=${id.identity_id}`)}>
                  <td className="font-mono text-sm font-600">{id.identity_id}</td>
                  <td>
                    <span style={{ color: id.risk_score > 80 ? 'var(--severity-critical)' : 'var(--severity-high)', fontWeight: 600 }}>
                      {id.risk_score.toFixed(1)}
                    </span>
                  </td>
                  <td>{id.alert_count} recent anomalies</td>
                  <td>
                    <button className="btn btn--secondary btn--small">View Timeline</button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
