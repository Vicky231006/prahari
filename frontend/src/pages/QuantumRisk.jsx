import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { fetchQuantumSessions, fetchDashboardKPIs } from '../api';
import { Binary, ShieldAlert, Key, ChevronDown } from 'lucide-react';
import SeverityBadge from '../components/SeverityBadge';

export default function QuantumRisk() {
  const { data: kpis } = useQuery({
    queryKey: ['dashboard_kpis'],
    queryFn: fetchDashboardKPIs,
    staleTime: 30000,
  });

  // Cursor pagination state for the sessions table
  const [cursor, setCursor] = useState(null);
  const [cursorHistory, setCursorHistory] = useState([]);

  const { data, isLoading, isFetching } = useQuery({
    queryKey: ['quantum_sessions', cursor],
    queryFn: () => fetchQuantumSessions({ limit: 100, beforeId: cursor }),
    staleTime: 5000,
    keepPreviousData: true,
  });

  const sessions = data?.items ?? [];
  const nextCursor = data?.next_cursor ?? null;
  const hasMore = Boolean(nextCursor);
  const isFirstPage = cursorHistory.length === 0;

  const loadNext = () => {
    if (!nextCursor) return;
    setCursorHistory(prev => [...prev, cursor]);
    setCursor(nextCursor);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };
  const loadPrev = () => {
    const history = [...cursorHistory];
    const prev = history.pop();
    setCursorHistory(history);
    setCursor(prev ?? null);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const stats = kpis?.quantum_stats || { legacy_count: 0, hybrid_count: 0, pqc_ready_count: 0 };
  const total = (stats.legacy_count || 0) + (stats.hybrid_count || 0) + (stats.pqc_ready_count || 0) || 1;
  const pctLegacy = (((stats.legacy_count || 0) / total) * 100).toFixed(1);
  const pctHybrid = (((stats.hybrid_count || 0) / total) * 100).toFixed(1);
  const pctPQC = (((stats.pqc_ready_count || 0) / total) * 100).toFixed(1);

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
            <span><strong>PQC-Ready</strong> (ML-KEM, ML-DSA) — {stats.pqc_ready_count || 0} sessions</span>
          </div>
          <div className="quantum-legend__item">
            <div className="quantum-legend__dot quantum-bar__segment--hybrid" />
            <span><strong>Hybrid</strong> (X25519-MLKEM) — {stats.hybrid_count || 0} sessions</span>
          </div>
          <div className="quantum-legend__item">
            <div className="quantum-legend__dot quantum-bar__segment--legacy" />
            <span><strong>Legacy Risk</strong> (RSA, ECDHE) — {stats.legacy_count || 0} sessions</span>
          </div>
        </div>
      </div>

      <h2 className="section-header" style={{ fontSize: '1.2rem', display: 'flex', alignItems: 'center', gap: '8px' }}>
        <ShieldAlert size={18} className="text-severity-critical" /> HNDL Exposure &amp; Harvesting Anomalies
      </h2>
      <p className="section-sub">Sessions carrying long-shelf-life sensitive data over legacy cryptography.</p>

      <div className="card p-0">
        {isLoading ? (
          <div className="loading-center"><div className="spinner" /> Loading inventory...</div>
        ) : sessions.length === 0 ? (
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
              {sessions.map(s => (
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

      {/* Pagination controls */}
      {(hasMore || !isFirstPage) && (
        <div className="flex items-center justify-between mt-16" style={{ opacity: isFetching ? 0.5 : 1 }}>
          <button className="btn btn--secondary btn--small" onClick={loadPrev} disabled={isFirstPage || isFetching}>
            ← Previous
          </button>
          <span className="text-xs text-muted">
            Showing {sessions.length} sessions &nbsp;·&nbsp; Page {cursorHistory.length + 1}
          </span>
          <button
            className="btn btn--secondary btn--small flex items-center gap-6"
            onClick={loadNext}
            disabled={!hasMore || isFetching}
          >
            Load more <ChevronDown size={13} />
          </button>
        </div>
      )}
    </div>
  );
}
