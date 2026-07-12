import { useQuery } from '@tanstack/react-query';
import { fetchQuantumSessions, fetchDashboardKPIs } from '../api';
import { Binary, ShieldAlert, Key } from 'lucide-react';
import SeverityBadge from '../components/SeverityBadge';

export default function QuantumRisk() {
  const { data: kpis } = useQuery({ queryKey: ['dashboard_kpis'], queryFn: fetchDashboardKPIs, staleTime: 30000 });
  const { data: sessions, isLoading } = useQuery({ queryKey: ['quantum_sessions'], queryFn: fetchQuantumSessions, staleTime: 5000 });

  const stats = kpis?.quantum_stats || { total_scanned: 0, legacy: 0, hybrid: 0, pqc_ready: 0 };
  const total = stats.total_scanned || 1;
  const pctLegacy = ((stats.legacy / total) * 100).toFixed(1);
  const pctHybrid = ((stats.hybrid / total) * 100).toFixed(1);
  const pctPQC = ((stats.pqc_ready / total) * 100).toFixed(1);

  return (
    <div className="fade-in">
      <h1 className="section-header mb-8">Quantum Cryptanalysis Inventory</h1>
      <p className="section-sub">Real-time classification of TLS handshakes against NIST FIPS 203/204/205 PQC standards.</p>

      <div className="card mb-24">
        <div className="flex items-center gap-12 mb-16">
          <Binary size={18} className="text-muted" />
          <h3 style={{ fontSize: '0.9rem' }}>PQC Readiness Exposure</h3>
        </div>
        
        <div className="quantum-bar">
          <div className="quantum-bar__segment quantum-bar__segment--pqc" style={{ width: `${pctPQC}%` }} title="PQC Ready">{pctPQC}%</div>
          <div className="quantum-bar__segment quantum-bar__segment--hybrid" style={{ width: `${pctHybrid}%` }} title="Hybrid">{pctHybrid}%</div>
          <div className="quantum-bar__segment quantum-bar__segment--legacy" style={{ width: `${pctLegacy}%` }} title="Legacy">{pctLegacy}%</div>
        </div>
        
        <div className="quantum-legend">
          <div className="quantum-legend__item">
            <div className="quantum-legend__dot quantum-bar__segment--pqc" />
            <span><strong>PQC-Ready</strong> (ML-KEM, ML-DSA) — {stats.pqc_ready} sessions</span>
          </div>
          <div className="quantum-legend__item">
            <div className="quantum-legend__dot quantum-bar__segment--hybrid" />
            <span><strong>Hybrid</strong> (X25519-MLKEM) — {stats.hybrid} sessions</span>
          </div>
          <div className="quantum-legend__item">
            <div className="quantum-legend__dot quantum-bar__segment--legacy" />
            <span><strong>Legacy Risk</strong> (RSA, ECDHE) — {stats.legacy} sessions</span>
          </div>
        </div>
      </div>

      <h2 className="section-header" style={{ fontSize: '1.2rem', display: 'flex', alignItems: 'center', gap: '8px' }}>
        <ShieldAlert size={18} className="text-severity-critical" /> HNDL Exposure & Harvesting Anomalies
      </h2>
      <p className="section-sub">Sessions carrying long-shelf-life sensitive data over legacy cryptography.</p>

      <div className="card p-0">
        {isLoading ? (
          <div className="loading-center"><div className="spinner" /> Loading inventory...</div>
        ) : sessions?.length === 0 ? (
          <div className="empty-state">
            <Key className="empty-state__icon" />
            <div className="empty-state__text">No HNDL-exposed sessions detected.</div>
          </div>
        ) : (
          <table className="data-table">
            <thead>
              <tr>
                <th>Classification</th>
                <th>Session ID</th>
                <th>Key Exchange</th>
                <th>Data Sensitivity</th>
                <th>Egress Volume</th>
                <th>Time (IST)</th>
              </tr>
            </thead>
            <tbody>
              {sessions?.map(s => (
                <tr key={s.id}>
                  <td>
                    {s.classification === 'legacy' ? <SeverityBadge severity="high" /> : <SeverityBadge severity="low" />}
                  </td>
                  <td className="font-mono text-sm">{s.session_id.substring(0, 16)}...</td>
                  <td className="font-mono text-xs">{s.key_exchange}</td>
                  <td>
                    <span className="severity-badge" style={{ background: 'var(--surface-hover)', color: s.data_sensitivity === 'routine' ? 'var(--text-muted)' : 'var(--severity-critical)' }}>
                      {s.data_sensitivity}
                    </span>
                  </td>
                  <td className="text-xs font-mono">{s.bytes_transferred.toLocaleString()} bytes</td>
                  <td className="text-xs text-muted">{new Date(s.created_at).toLocaleTimeString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
