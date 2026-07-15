import { useState } from 'react';
import {
  X, FileText, Activity, Server,
  Shield, Info, PieChart, Search, AlertTriangle,
  Briefcase, UserPlus, FileOutput, DownloadCloud, CheckCircle,
  ShieldX, CheckCheck, Loader2
} from 'lucide-react';
import SeverityBadge from './SeverityBadge';
import { useQueryClient } from '@tanstack/react-query';
import { ConfirmDismissModal, toast } from './ExplanationDrawer';
import { escalateQuantumSession, dismissQuantumSession } from '../api';

// Helper component for "Data not adequate"
function DataNotAdequate() {
  return (
    <span className="text-muted" style={{ display: 'inline-flex', alignItems: 'center', gap: '4px', fontStyle: 'italic', fontSize: '0.8rem' }}>
      <Info size={12} /> Data not adequate
    </span>
  );
}

// ── Tabs ──

function ExplanationTab({ session }) {
  const isLegacy = session.classification === 'legacy';
  const isHNDL = session.is_hndl_exposed;
  
  const rulesBasedSummary = `This TLS session was classified as ${session.classification?.toUpperCase()} due to the use of ${session.key_exchange} for key exchange and ${session.signature_algo} for signatures. ` + 
    (isLegacy ? "These classical cryptographic algorithms are vulnerable to Shor's algorithm running on a cryptographically relevant quantum computer (CRQC)." : "This session utilizes quantum-resistant algorithms.") + 
    (isHNDL ? ` Because the data sensitivity is marked as ${session.data_sensitivity}, this session is highly susceptible to Harvest Now, Decrypt Later (HNDL) attacks.` : "");

  return (
    <div className="fade-in" style={{ padding: '24px', overflowY: 'auto' }}>
      <div className="section-header" style={{ fontSize: '1.2rem', marginBottom: '16px' }}>Anomaly Explanation</div>
      
      <div className="card mb-24" style={{ padding: '24px' }}>
        <h4 className="mb-8" style={{ fontWeight: 600, fontSize: '0.95rem', color: 'var(--text-primary)' }}>Why this asset was flagged</h4>
        <ul style={{ paddingLeft: '20px', marginBottom: '20px', color: 'var(--text-secondary)', fontSize: '0.85rem', lineHeight: '1.5' }}>
          {session.risk_factors?.length > 0 ? (
            session.risk_factors.map(rf => <li key={rf} style={{ marginBottom: '4px' }}>{rf.replace(/_/g, ' ')}</li>)
          ) : (
            <li>No specific risk factors flagged.</li>
          )}
        </ul>

        <h4 className="mb-8" style={{ fontWeight: 600, fontSize: '0.95rem', color: 'var(--text-primary)' }}>Current Algorithms</h4>
        <div className="flex gap-12 mb-20">
          <div style={{ background: 'var(--surface-hover)', border: '1px solid var(--surface-border)', borderRadius: '6px', padding: '6px 12px', fontSize: '0.8rem', fontFamily: 'monospace', color: 'var(--text-secondary)' }}>
            Key Exchange: <strong style={{ color: 'var(--text-primary)' }}>{session.key_exchange}</strong>
          </div>
          <div style={{ background: 'var(--surface-hover)', border: '1px solid var(--surface-border)', borderRadius: '6px', padding: '6px 12px', fontSize: '0.8rem', fontFamily: 'monospace', color: 'var(--text-secondary)' }}>
            Signature: <strong style={{ color: 'var(--text-primary)' }}>{session.signature_algo}</strong>
          </div>
        </div>

        {isLegacy && (
          <div style={{ borderTop: '1px solid var(--surface-border)', paddingTop: '16px', marginBottom: '16px' }}>
            <h4 className="mb-8" style={{ fontWeight: 600, fontSize: '0.95rem', color: 'var(--text-primary)' }}>Why they are vulnerable</h4>
            <p className="text-secondary" style={{ fontSize: '0.85rem', lineHeight: '1.5', margin: 0 }}>
              Algorithms like {session.key_exchange} and {session.signature_algo} rely on the difficulty of integer factorization or the discrete logarithm problem. A CRQC running Shor's algorithm can solve these problems in polynomial time, completely breaking the encryption.
            </p>
          </div>
        )}

        {isHNDL && (
          <div style={{ borderTop: '1px solid var(--surface-border)', paddingTop: '16px' }}>
            <h4 className="mb-8 flex items-center gap-6 text-severity-critical" style={{ fontWeight: 600, fontSize: '0.95rem' }}>
              <AlertTriangle size={15} /> Harvest Now, Decrypt Later (HNDL)
            </h4>
            <p className="text-secondary" style={{ fontSize: '0.85rem', lineHeight: '1.5', margin: 0 }}>
              Adversaries are currently intercepting and storing this encrypted traffic. Because the data has a long shelf-life (Data Sensitivity: <strong>{session.data_sensitivity}</strong>), it will still be valuable when quantum computers become capable of decrypting it retrospectively.
            </p>
          </div>
        )}
      </div>

      <div className="section-header" style={{ fontSize: '1.1rem', marginBottom: '12px' }}>AI Summary (Rule-Based Fallback)</div>
      <div className="explanation-text" style={{ padding: '16px', background: 'var(--surface-hover)', borderRadius: '8px', fontSize: '0.85rem', lineHeight: '1.5', color: 'var(--text-secondary)', border: '1px solid var(--surface-border)' }}>
        {rulesBasedSummary}
      </div>
    </div>
  );
}

function RiskProfileTab({ session }) {
  return (
    <div className="fade-in" style={{ padding: '24px', overflowY: 'auto' }}>
      <div className="risk-section-title"><Server size={14} /> Risk Profile Parameters</div>
      <div className="risk-profile-grid">
        <div className="risk-profile-field">
          <span className="risk-profile-field__label">Risk Score</span>
          <span className="risk-profile-field__value"><DataNotAdequate /></span>
        </div>
        <div className="risk-profile-field">
          <span className="risk-profile-field__label">Exposure Score</span>
          <span className="risk-profile-field__value"><DataNotAdequate /></span>
        </div>
        <div className="risk-profile-field">
          <span className="risk-profile-field__label">Business Criticality</span>
          <span className="risk-profile-field__value"><DataNotAdequate /></span>
        </div>
        <div className="risk-profile-field">
          <span className="risk-profile-field__label">Internet Exposure</span>
          <span className="risk-profile-field__value">
            {session.destination === 'external' ? 'Yes (External)' : 'No (Internal)'}
          </span>
        </div>
        <div className="risk-profile-field">
          <span className="risk-profile-field__label">Sensitive Data</span>
          <span className="risk-profile-field__value" style={{ textTransform: 'capitalize' }}>
            {session.data_sensitivity || 'routine'}
          </span>
        </div>
        <div className="risk-profile-field">
          <span className="risk-profile-field__label">Risk Drivers</span>
          <span className="risk-profile-field__value">
            {session.risk_factors?.length > 0 ? session.risk_factors.join(', ') : 'None'}
          </span>
        </div>
      </div>
    </div>
  );
}

function RecommendationsTab({ session }) {
  const isLegacy = session.classification === 'legacy';
  const priority = session.data_sensitivity !== 'routine' ? 'Critical' : 'High';
  
  let recommendedMigration = "N/A (Already PQC)";
  if (isLegacy) {
    recommendedMigration = "";
    if (session.key_exchange?.includes("RSA") || session.key_exchange?.includes("ECDHE")) {
      recommendedMigration += "Migrate to ML-KEM-768";
    }
    if (session.signature_algo?.includes("RSA") || session.signature_algo?.includes("ECDSA")) {
      if (recommendedMigration) recommendedMigration += " & ";
      recommendedMigration += "ML-DSA-65";
    }
    if (!recommendedMigration) recommendedMigration = "Upgrade to PQC Algorithms";
  }

  return (
    <div className="fade-in" style={{ padding: '24px', overflowY: 'auto' }}>
      <div className="section-header" style={{ fontSize: '1.2rem', marginBottom: '16px' }}>Remediation Recommendations</div>
      
      {isLegacy ? (
        <div className="card p-0">
          <table className="data-table">
            <thead>
              <tr>
                <th>Priority</th>
                <th>Recommended PQC Migration</th>
                <th>Estimated Effort</th>
                <th>Expected Risk Reduction</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td><SeverityBadge severity={priority === 'Critical' ? 'critical' : 'high'} /></td>
                <td className="font-600">{recommendedMigration}</td>
                <td><DataNotAdequate /></td>
                <td><DataNotAdequate /></td>
                <td><DataNotAdequate /></td>
              </tr>
            </tbody>
          </table>
        </div>
      ) : (
        <div className="empty-state">
          <Shield className="empty-state__icon" style={{ color: 'var(--secondary)' }} />
          <div className="empty-state__text">This session is already utilizing quantum-resistant cryptography. No migrations recommended.</div>
        </div>
      )}
    </div>
  );
}

function ImpactAnalysisTab() {
  return (
    <div className="fade-in" style={{ padding: '24px', overflowY: 'auto' }}>
      <div className="section-header" style={{ fontSize: '1.2rem', marginBottom: '16px' }}>Impact Analysis</div>
      <div className="card">
        <div className="risk-profile-grid" style={{ gridTemplateColumns: '1fr' }}>
          <div className="risk-profile-field">
            <span className="risk-profile-field__label">Connected Systems</span>
            <span className="risk-profile-field__value"><DataNotAdequate /></span>
          </div>
          <div className="risk-profile-field">
            <span className="risk-profile-field__label">Dependent Applications</span>
            <span className="risk-profile-field__value"><DataNotAdequate /></span>
          </div>
          <div className="risk-profile-field">
            <span className="risk-profile-field__label">Estimated Blast Radius</span>
            <span className="risk-profile-field__value"><DataNotAdequate /></span>
          </div>
          <div className="risk-profile-field">
            <span className="risk-profile-field__label">Business Impact</span>
            <span className="risk-profile-field__value"><DataNotAdequate /></span>
          </div>
        </div>
      </div>
    </div>
  );
}

function ComplianceTab({ session }) {
  const kx = session.key_exchange || '';
  const sig = session.signature_algo || '';

  const isFips203Pass = kx.includes("ML-KEM");
  const isFips203Partial = kx.includes("hybrid") || kx.includes("X25519-MLKEM");
  const fips203Status = isFips203Pass ? "Pass" : (isFips203Partial ? "Partial (Hybrid)" : "Fail");

  const isFips204Pass = sig.includes("ML-DSA");
  const fips204Status = isFips204Pass ? "Pass" : "Fail";

  const isFips205Pass = sig.includes("SLH-DSA");
  const fips205Status = isFips205Pass ? "Pass" : "Fail";

  // CNSA 2.0 requires ML-KEM and ML-DSA
  const isCnsaPass = (isFips203Pass || isFips203Partial) && isFips204Pass;
  const cnsaStatus = isCnsaPass ? "Pass" : "Fail";

  const renderBadge = (status) => {
    if (status === "Pass") return <SeverityBadge severity="low" />; // green
    if (status === "Fail") return <SeverityBadge severity="critical" />; // red
    return <SeverityBadge severity="high" />; // yellow for partial
  };

  return (
    <div className="fade-in" style={{ padding: '24px', overflowY: 'auto' }}>
      <div className="section-header" style={{ fontSize: '1.2rem', marginBottom: '16px' }}>Compliance Posture</div>
      <div className="card p-0">
        <table className="data-table">
          <thead>
            <tr>
              <th>Framework / Standard</th>
              <th>Status</th>
              <th>Explanation</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td className="font-600">NIST FIPS 203 (ML-KEM)</td>
              <td>{renderBadge(fips203Status)}</td>
              <td className="text-sm text-secondary">
                {isFips203Pass ? `Compliant key exchange detected (${kx}).` : (isFips203Partial ? `Hybrid key exchange detected (${kx}). Permitted during transition.` : `Legacy key exchange (${kx}) is not compliant with PQC standards.`)}
              </td>
            </tr>
            <tr>
              <td className="font-600">NIST FIPS 204 (ML-DSA)</td>
              <td>{renderBadge(fips204Status)}</td>
              <td className="text-sm text-secondary">
                {isFips204Pass ? `Compliant signature detected (${sig}).` : `Legacy signature (${sig}) is not compliant with PQC standards.`}
              </td>
            </tr>
            <tr>
              <td className="font-600">NIST FIPS 205 (SLH-DSA)</td>
              <td>{renderBadge(fips205Status)}</td>
              <td className="text-sm text-secondary">
                {isFips205Pass ? `Compliant stateless hash-based signature detected (${sig}).` : `Stateless hash-based signature not detected.`}
              </td>
            </tr>
            <tr>
              <td className="font-600">CNSA 2.0</td>
              <td>{renderBadge(cnsaStatus)}</td>
              <td className="text-sm text-secondary">
                {isCnsaPass ? "Meets CNSA 2.0 requirements for PQC." : "Fails CNSA 2.0 requirements. Both ML-KEM and ML-DSA/LMS are required."}
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  );
}

export default function QuantumWorkspaceDrawer({ session, onClose }) {
  const [activeTab, setActiveTab] = useState('explanation');
  const [isCaseCreated, setIsCaseCreated] = useState(false);
  const [showToast, setShowToast] = useState(false);
  
  // Investigation actions state
  const [escalating, setEscalating] = useState(false);
  const [dismissing, setDismissing] = useState(false);
  const [showConfirmDismiss, setShowConfirmDismiss] = useState(false);
  const [localStatus, setLocalStatus] = useState(session?.status || 'open');

  const queryClient = useQueryClient();

  if (!session) return null;

  const handleCreateCase = () => {
    setIsCaseCreated(true);
    setShowToast(true);
    setTimeout(() => setShowToast(false), 3000);
  };

  const handleEscalate = async () => {
    setEscalating(true);
    try {
      await escalateQuantumSession(session.session_id, 'Tier 1 Analyst');
      setLocalStatus('escalated');
      toast('success', 'Escalated to Tier 2', `Quantum session ${session.session_id.substring(0,8)} has been escalated.`);
      queryClient.invalidateQueries({ queryKey: ['quantum_sessions'] });
      queryClient.invalidateQueries({ queryKey: ['cases'] });
      queryClient.invalidateQueries({ queryKey: ['audit_quantum'] });
    } catch (err) {
      toast('error', 'Escalation failed', err.message);
    } finally {
      setEscalating(false);
    }
  };

  const handleDismissConfirm = async (reason) => {
    setShowConfirmDismiss(false);
    setDismissing(true);
    const prevStatus = localStatus;
    setLocalStatus('dismissed');
    try {
      await dismissQuantumSession(session.session_id, 'Tier 1 Analyst', reason || 'Dismissed as False Positive');
      toast('success', 'Session Dismissed', `Session marked as false positive.`);
      queryClient.invalidateQueries({ queryKey: ['quantum_sessions'] });
      queryClient.invalidateQueries({ queryKey: ['cases'] });
      queryClient.invalidateQueries({ queryKey: ['audit_quantum'] });
      onClose();
    } catch (err) {
      setLocalStatus(prevStatus);
      toast('error', 'Dismiss failed', err.message);
    } finally {
      setDismissing(false);
    }
  };

  const tabs = [
    { id: 'explanation', label: 'Explanation', icon: <FileText size={13} /> },
    { id: 'profile', label: 'Risk Profile', icon: <Server size={13} /> },
    { id: 'recommendations', label: 'Recommendations', icon: <Shield size={13} /> },
    { id: 'impact', label: 'Impact Analysis', icon: <Activity size={13} /> },
    { id: 'compliance', label: 'Compliance', icon: <PieChart size={13} /> },
  ];

  const riskLevel = session.classification === 'legacy' ? 'high' : 'low';
  const readinessScore = session.readiness_score != null ? `${session.readiness_score}%` : 'Data not adequate';
  const assetName = session.asset_name || `Session ${session.session_id?.substring(0, 8) || 'Unknown'}`;
  const environment = session.environment || <DataNotAdequate />;
  const lastObserved = session.created_at
    ? new Date(session.created_at).toLocaleString('en-IN', { dateStyle: 'short', timeStyle: 'short' })
    : <DataNotAdequate />;
  const status = localStatus;
  const isTerminal = status === 'escalated' || status === 'dismissed';
  const isBusy = escalating || dismissing;

  return (
    <>
      {showConfirmDismiss && (
        <ConfirmDismissModal
          identityId={session.session_id}
          onConfirm={handleDismissConfirm}
          onCancel={() => setShowConfirmDismiss(false)}
        />
      )}
      <div className="drawer-overlay" onClick={onClose} />
      <div className="drawer drawer--workspace">
        
        {/* ── Header ── */}
        <div className="drawer__header">
          <div>
            <div className="flex items-center gap-12 mb-8">
              <h2 style={{ fontFamily: 'var(--font-display)', fontWeight: 'var(--font-weight-display)' }}>
                Quantum Investigation Workspace
              </h2>
              <SeverityBadge severity={riskLevel} />
              <span className={`status-pill status-pill--${status}`}>
                {status.toUpperCase()}
              </span>
            </div>
            
            <div className="flex items-center gap-12 text-xs text-muted">
              <span className="font-mono">ID: {session.session_id}</span>
              <span>·</span>
              <span className="font-mono">Readiness: {readinessScore}</span>
              <span>·</span>
              <span>Env: {environment}</span>
              <span>·</span>
              <span>Last Observed: {lastObserved}</span>
            </div>
          </div>
          <button className="btn btn--ghost" onClick={onClose}><X size={20} /></button>
        </div>

        {/* ── Tab Navigation ── */}
        <div className="workspace-tabs">
          {tabs.map(tab => (
            <button
              key={tab.id}
              className={`workspace-tab ${activeTab === tab.id ? 'workspace-tab--active' : ''}`}
              onClick={() => setActiveTab(tab.id)}
            >
              {tab.icon}
              {tab.label}
            </button>
          ))}
        </div>

        {/* ── Tab Body ── */}
        <div className="drawer__body" style={{ display: 'flex', flexDirection: 'column', flex: 1, padding: 0 }}>
          {activeTab === 'explanation' && <ExplanationTab session={session} />}
          {activeTab === 'profile' && <RiskProfileTab session={session} />}
          {activeTab === 'recommendations' && <RecommendationsTab session={session} />}
          {activeTab === 'impact' && <ImpactAnalysisTab session={session} />}
          {activeTab === 'compliance' && <ComplianceTab session={session} />}
        </div>
        
        {/* ── Footer action buttons ── */}
        <div className="drawer__footer">
          {isTerminal ? (
            <div className="flex items-center justify-center gap-8 text-sm text-muted" style={{ flex: 1, padding: '4px 0' }}>
              <CheckCheck size={15} />
              {localStatus === 'escalated'
                ? 'Escalated to Tier 2 — case created and audit logged.'
                : 'Dismissed as false positive — audit logged.'}
            </div>
          ) : (
            <>
              <button
                className="btn btn--secondary"
                style={{ flex: 1 }}
                onClick={() => setShowConfirmDismiss(true)}
                disabled={isBusy}
                title="Dismiss as False Positive (requires confirmation)"
              >
                {dismissing ? <Loader2 size={15} className="spin" /> : <ShieldX size={15} />}
                Dismiss False Positive
              </button>
              <button
                className="btn btn--primary"
                style={{ flex: 1 }}
                onClick={handleEscalate}
                disabled={isBusy}
                title="Escalate to Tier 2 — creates a case"
              >
                {escalating ? <Loader2 size={15} className="spin" /> : <CheckCircle size={15} />}
                Escalate to Tier 2
              </button>
            </>
          )}
        </div>
      </div>
    </>
  );
}
