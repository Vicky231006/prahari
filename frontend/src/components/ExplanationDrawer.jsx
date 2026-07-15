import { useState, useEffect, useCallback, useRef } from 'react';
import { createPortal } from 'react-dom';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import {
  X, CheckCircle, AlertTriangle, ShieldOff, Clock,
  ShieldX, CheckCheck, Loader2, User, Activity, FileText,
  Shield, CreditCard, Monitor, Users, ArrowRightLeft,
  Zap, FolderOpen, ClipboardCheck, ShieldAlert, Info,
  Smartphone, Globe, Building2, ChevronRight
} from 'lucide-react';
import { escalateAlert, dismissAlert, fetchIdentityProfile, fetchAlertTimeline } from '../api';
import SeverityBadge from './SeverityBadge';
import { useNavigate } from 'react-router-dom';

// ── Lightweight toast system ────────────────────────────────────────────────────
let _toastId = 0;
let _setToasts = null;

export function ToastContainer() {
  const [toasts, setToasts] = useState([]);
  _setToasts = setToasts;

  const remove = useCallback((id) => {
    setToasts(prev => prev.filter(t => t.id !== id));
  }, []);

  return createPortal(
    <div className="toast-container">
      {toasts.map(t => (
        <div key={t.id} className={`toast toast--${t.type}`} onClick={() => remove(t.id)}>
          <span className="toast__icon">
            {t.type === 'success' ? <CheckCheck size={16} /> : <ShieldX size={16} />}
          </span>
          <div className="toast__body">
            <div className="toast__title">{t.title}</div>
            {t.msg && <div className="toast__msg">{t.msg}</div>}
          </div>
          <div className="toast__progress" />
        </div>
      ))}
    </div>,
    document.body
  );
}

function toast(type, title, msg = '') {
  if (!_setToasts) return;
  const id = ++_toastId;
  _setToasts(prev => [...prev, { id, type, title, msg }]);
  setTimeout(() => {
    _setToasts(prev => prev.filter(t => t.id !== id));
  }, 4200);
}

// ── Confirm dismiss modal ────────────────────────────────────────────────────
function ConfirmDismissModal({ identityId, onConfirm, onCancel }) {
  const [reason, setReason] = useState('');
  const textareaRef = useRef(null);

  useEffect(() => { textareaRef.current?.focus(); }, []);

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) onConfirm(reason);
    if (e.key === 'Escape') onCancel();
  };

  return createPortal(
    <div className="confirm-overlay" onKeyDown={handleKeyDown}>
      <div className="confirm-modal" onClick={e => e.stopPropagation()}>
        <div className="flex items-center gap-8 mb-8">
          <ShieldX size={18} style={{ color: 'var(--severity-critical)' }} />
          <div className="confirm-modal__title">Dismiss as False Positive?</div>
        </div>
        <div className="confirm-modal__body">
          Alert for identity <strong className="font-mono">{identityId}</strong> will be marked
          as a false positive. A case will be created and the audit trail will be updated.
          This action cannot be undone.
        </div>
        <textarea
          ref={textareaRef}
          rows={3}
          placeholder="Reason / analyst notes (optional)…"
          value={reason}
          onChange={e => setReason(e.target.value)}
        />
        <div className="confirm-modal__actions">
          <button className="btn btn--ghost btn--small" onClick={onCancel}>Cancel</button>
          <button
            className="btn btn--primary btn--small"
            style={{ background: 'var(--severity-critical)' }}
            onClick={() => onConfirm(reason)}
          >
            Confirm Dismiss
          </button>
        </div>
      </div>
    </div>,
    document.body
  );
}

// ── Icon map for timeline event types ───────────────────────────────────────
const TIMELINE_ICONS = {
  user: <User size={8} />,
  'shield-alert': <ShieldAlert size={8} />,
  'shield-x': <ShieldX size={8} />,
  'arrow-right-left': <ArrowRightLeft size={8} />,
  zap: <Zap size={8} />,
  'folder-open': <FolderOpen size={8} />,
  'clipboard-check': <ClipboardCheck size={8} />,
};

const TYPE_LABELS = {
  ACCOUNT_HISTORY: 'History',
  FRAUD_HISTORY: 'Fraud Record',
  SECURITY_EVENT: 'Security',
  TRANSACTION_EVENT: 'Transaction',
  ALERT_GENERATED: 'Alert',
  CASE_CREATED: 'Case',
  AUDIT_ESCALATE: 'Escalated',
  AUDIT_DISMISS: 'Dismissed',
  AUDIT_ACKNOWLEDGE: 'Acknowledged',
};

function fmt(ts) {
  if (!ts) return '—';
  try { return new Date(ts).toLocaleString('en-IN', { dateStyle: 'short', timeStyle: 'medium' }); }
  catch { return ts; }
}

function fmtCurrency(n) {
  if (n == null) return '—';
  return `₹${Number(n).toLocaleString('en-IN')}`;
}

// ── Customer Risk Profile Panel ──────────────────────────────────────────────
function CustomerRiskProfile({ identityId }) {
  const { data: profile, isLoading, error } = useQuery({
    queryKey: ['identity', identityId],
    queryFn: () => fetchIdentityProfile(identityId),
    staleTime: 60000,
    retry: 1,
  });

  if (isLoading) return <div className="loading-center"><div className="spinner" /> Loading profile...</div>;
  if (error || !profile) return (
    <div className="empty-state" style={{ padding: '40px 20px' }}>
      <Info className="empty-state__icon" />
      <div className="empty-state__text">Identity profile not found for {identityId}</div>
    </div>
  );

  const kycColor = profile.kyc_status === 'verified'
    ? 'var(--secondary)' : profile.kyc_status === 'pending'
    ? 'var(--severity-high)' : 'var(--severity-critical)';

  const riskColor = profile.risk_tier === 'LOW'
    ? 'var(--secondary)' : profile.risk_tier === 'MEDIUM'
    ? 'var(--severity-high)' : 'var(--severity-critical)';

  const devices = Array.isArray(profile.known_devices) ? profile.known_devices : [];
  const beneficiaries = Array.isArray(profile.known_beneficiaries) ? profile.known_beneficiaries : [];

  return (
    <div>
      {/* Core identity fields */}
      <div className="risk-section-title"><User size={14} /> Identity Overview</div>
      <div className="risk-profile-grid">
        <div className="risk-profile-field">
          <span className="risk-profile-field__label">Customer Name</span>
          <span className="risk-profile-field__value">{profile.customer_name || '—'}</span>
        </div>
        <div className="risk-profile-field">
          <span className="risk-profile-field__label">Customer Type</span>
          <span className="risk-profile-field__value">{profile.customer_type || '—'}</span>
        </div>
        <div className="risk-profile-field">
          <span className="risk-profile-field__label">Segment</span>
          <span className="risk-profile-field__value">{profile.customer_segment || '—'}</span>
        </div>
        <div className="risk-profile-field">
          <span className="risk-profile-field__label">KYC Status</span>
          <span className="risk-profile-field__value" style={{ color: kycColor }}>
            {(profile.kyc_status || '—').toUpperCase()}
          </span>
        </div>
        <div className="risk-profile-field">
          <span className="risk-profile-field__label">Account Age</span>
          <span className="risk-profile-field__value">
            {profile.account_age_days ? `${Math.floor(profile.account_age_days / 365)} yrs` : '—'}
          </span>
        </div>
        <div className="risk-profile-field">
          <span className="risk-profile-field__label">Customer Since</span>
          <span className="risk-profile-field__value risk-profile-field__value--mono">
            {profile.customer_since || '—'}
          </span>
        </div>
        <div className="risk-profile-field">
          <span className="risk-profile-field__label">Branch</span>
          <span className="risk-profile-field__value">{profile.primary_branch || '—'}</span>
        </div>
        <div className="risk-profile-field">
          <span className="risk-profile-field__label">Region</span>
          <span className="risk-profile-field__value">{profile.region || '—'}</span>
        </div>
        <div className="risk-profile-field">
          <span className="risk-profile-field__label">Risk Tier</span>
          <span className="risk-profile-field__value" style={{ color: riskColor }}>
            {profile.risk_tier || '—'}
          </span>
        </div>
      </div>

      {/* Financial data */}
      <div className="risk-section-title"><CreditCard size={14} /> Financial Profile</div>
      <div className="risk-profile-grid">
        <div className="risk-profile-field">
          <span className="risk-profile-field__label">Current Balance</span>
          <span className="risk-profile-field__value">{fmtCurrency(profile.current_balance)}</span>
        </div>
        <div className="risk-profile-field">
          <span className="risk-profile-field__label">Avg Daily Volume</span>
          <span className="risk-profile-field__value">{fmtCurrency(profile.average_daily_volume)}</span>
        </div>
        <div className="risk-profile-field">
          <span className="risk-profile-field__label">Monthly Transactions</span>
          <span className="risk-profile-field__value">{profile.monthly_txn_count ?? '—'}</span>
        </div>
        <div className="risk-profile-field">
          <span className="risk-profile-field__label">Avg Txn Amount</span>
          <span className="risk-profile-field__value">{fmtCurrency(profile.avg_txn_amount)}</span>
        </div>
        <div className="risk-profile-field">
          <span className="risk-profile-field__label">Preferred Channel</span>
          <span className="risk-profile-field__value">{profile.preferred_payment_method || '—'}</span>
        </div>
        <div className="risk-profile-field">
          <span className="risk-profile-field__label">Dormant Account</span>
          <span className="risk-profile-field__value" style={{ color: profile.dormant_account_flag ? 'var(--severity-high)' : 'inherit' }}>
            {profile.dormant_account_flag ? 'YES' : 'No'}
          </span>
        </div>
      </div>

      {/* Risk & History */}
      <div className="risk-section-title"><ShieldAlert size={14} /> Risk & History</div>
      <div className="risk-profile-grid">
        <div className="risk-profile-field">
          <span className="risk-profile-field__label">Previous Alerts</span>
          <span className="risk-profile-field__value" style={{ color: (profile.previous_alerts_count || 0) > 0 ? 'var(--severity-high)' : 'inherit' }}>
            {profile.previous_alerts_count ?? 0}
          </span>
        </div>
        <div className="risk-profile-field">
          <span className="risk-profile-field__label">Previous Cases</span>
          <span className="risk-profile-field__value" style={{ color: (profile.previous_cases_count || 0) > 0 ? 'var(--severity-high)' : 'inherit' }}>
            {profile.previous_cases_count ?? 0}
          </span>
        </div>
        <div className="risk-profile-field">
          <span className="risk-profile-field__label">Fraud History</span>
          <span className="risk-profile-field__value" style={{ color: (profile.fraud_history_count || 0) > 0 ? 'var(--severity-critical)' : 'inherit' }}>
            {profile.fraud_history_count ?? 0} incident(s)
          </span>
        </div>
        <div className="risk-profile-field">
          <span className="risk-profile-field__label">Device Trust Score</span>
          <span className="risk-profile-field__value" style={{ color: (profile.device_trust_score || 0) < 0.5 ? 'var(--severity-critical)' : 'inherit' }}>
            {profile.device_trust_score != null ? `${(profile.device_trust_score * 100).toFixed(0)}%` : '—'}
          </span>
        </div>
        <div className="risk-profile-field">
          <span className="risk-profile-field__label">VIP Customer</span>
          <span className="risk-profile-field__value">{profile.vip_flag ? 'Yes' : 'No'}</span>
        </div>
        <div className="risk-profile-field">
          <span className="risk-profile-field__label">Risk Score</span>
          <span className="risk-profile-field__value risk-profile-field__value--mono">
            {profile.risk_score != null ? (profile.risk_score * 100).toFixed(1) + '%' : '—'}
          </span>
        </div>
      </div>

      {/* Known Devices */}
      <div className="risk-section-title"><Monitor size={14} /> Known Devices ({devices.length})</div>
      <div className="chip-list">
        {devices.length === 0 && <span className="text-xs text-muted">No devices on record</span>}
        {devices.map((d, i) => {
          const trusted = d?.trusted_flag !== false;
          const label = typeof d === 'string' ? d : `${d?.os || 'Device'} · ${(d?.device_id || '').slice(0, 10)}`;
          return (
            <span key={i} className={`chip ${!trusted ? 'chip--danger' : ''}`}>
              <Smartphone size={10} />
              {label}
              {!trusted && ' ⚠'}
            </span>
          );
        })}
      </div>

      {/* Known Beneficiaries */}
      <div className="risk-section-title"><Users size={14} /> Known Beneficiaries ({beneficiaries.length})</div>
      <div className="chip-list">
        {beneficiaries.length === 0 && <span className="text-xs text-muted">No beneficiaries on record</span>}
        {beneficiaries.slice(0, 12).map((b, i) => {
          const label = typeof b === 'string' ? b
            : `${b?.beneficiary_name || 'Unknown'} · ${b?.bank || ''} ${b?.ifsc || ''}`.trim();
          return (
            <span key={i} className="chip">
              <Globe size={10} />
              {label.slice(0, 32)}
            </span>
          );
        })}
        {beneficiaries.length > 12 && (
          <span className="chip" style={{ opacity: 0.6 }}>+{beneficiaries.length - 12} more</span>
        )}
      </div>
    </div>
  );
}

// ── Investigation Timeline Panel ─────────────────────────────────────────────
function InvestigationTimeline({ alertId }) {
  const { data, isLoading, error } = useQuery({
    queryKey: ['timeline', alertId],
    queryFn: () => fetchAlertTimeline(alertId),
    staleTime: 30000,
    retry: 1,
  });

  if (isLoading) return <div className="loading-center"><div className="spinner" /> Building timeline...</div>;
  if (error) return (
    <div className="empty-state" style={{ padding: '40px 20px' }}>
      <Activity className="empty-state__icon" />
      <div className="empty-state__text">Could not load investigation timeline.</div>
    </div>
  );

  const events = data?.events ?? [];

  if (events.length === 0) return (
    <div className="empty-state" style={{ padding: '40px 20px' }}>
      <Activity className="empty-state__icon" />
      <div className="empty-state__text">No timeline events found for this alert.</div>
    </div>
  );

  return (
    <div className="timeline">
      {events.map((ev, i) => (
        <div key={i} className="timeline-event">
          <div className={`timeline-dot timeline-dot--${ev.severity}`} />
          <div className={`timeline-card timeline-card--${ev.severity}`}>
            <div className="timeline-card__header">
              <span className="timeline-card__type">
                {TYPE_LABELS[ev.type] || ev.type}
              </span>
              <span className="timeline-card__title">{ev.title}</span>
              <span className="timeline-card__time">{fmt(ev.timestamp)}</span>
            </div>
            <div className="timeline-card__desc">{ev.description}</div>
          </div>
        </div>
      ))}
    </div>
  );
}

// ── RAG Explanation Panel (extracted from original drawer) ───────────────────
function ExplanationPanel({ alert }) {
  const [explanationParts, setExplanationParts] = useState([]);
  const [controls, setControls] = useState([]);
  const [isStreaming, setIsStreaming] = useState(false);

  useEffect(() => {
    if (!alert) return;
    setExplanationParts([]);
    setControls([]);
    setIsStreaming(true);
    let isCancelled = false;

    const streamExplanation = async () => {
      try {
        const res = await fetch('/api/explain/stream', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            signals: alert.contributing_signals,
            severity: alert.severity,
          }),
        });
        if (!res.ok) throw new Error('Stream failed');

        const reader = res.body.getReader();
        const decoder = new TextDecoder();

        while (!isCancelled) {
          const { value, done } = await reader.read();
          if (done) break;
          const chunk = decoder.decode(value, { stream: true });
          for (const line of chunk.split('\n')) {
            if (line.startsWith('data: ')) {
              const data = line.substring(6).trim();
              if (data === '[DONE]') { setIsStreaming(false); break; }
              try {
                const parsed = JSON.parse(data);
                if (parsed.type === 'text') setExplanationParts(prev => [...prev, parsed.content]);
                else if (parsed.type === 'controls') setControls(parsed.controls);
              } catch (_) { /* partial chunk */ }
            }
          }
        }
      } catch {
        if (!isCancelled) {
          setExplanationParts(['Failed to generate explanation. Falling back to offline rule cache.']);
          setIsStreaming(false);
        }
      }
    };

    streamExplanation();
    return () => { isCancelled = true; };
  }, [alert?.id]);

  return (
    <>
      <div className="section-header">Regulatory Context &amp; Explanation</div>
      <div className="card mb-24">
        <div className="explanation-text">
          {explanationParts.join('')}
          {isStreaming && <span className="cursor-blink" />}
        </div>
        {controls.length > 0 && (
          <div className="mt-16 pt-16" style={{ borderTop: 'var(--surface-border)' }}>
            <div className="text-xs text-muted mb-8 text-uppercase">Cited RBI Controls</div>
            <div className="flex" style={{ flexWrap: 'wrap' }}>
              {controls.map(c => <span key={c} className="control-chip">{c}</span>)}
            </div>
          </div>
        )}
      </div>

      <div className="section-header">Contributing Signals</div>
      <div className="card">
        <ul style={{ listStyle: 'none' }}>
          {alert.contributing_signals.map(sig => (
            <li key={sig} className="flex items-center gap-8 py-8 border-bottom">
              <AlertTriangle size={14} className="text-muted" />
              <span className="font-mono text-sm">{sig}</span>
            </li>
          ))}
        </ul>
      </div>

      <div className="mt-24 text-xs text-muted">
        <div className="flex items-center gap-8 mb-8">
          <Clock size={14} /> Fused at {new Date(alert.created_at).toLocaleString()}
        </div>
        <div className="flex items-center gap-8">
          <ShieldOff size={14} /> Confidence Score: {(alert.fusion_score * 100).toFixed(1)}%
        </div>
      </div>
    </>
  );
}

export default function ExplanationDrawer({ alert, onClose, onActionComplete }) {
  const [activeTab, setActiveTab] = useState('explanation');
  const navigate = useNavigate();

  // Workflow state
  const [escalating, setEscalating] = useState(false);
  const [dismissing, setDismissing] = useState(false);
  const [showConfirmDismiss, setShowConfirmDismiss] = useState(false);
  const [localStatus, setLocalStatus] = useState(null);

  const queryClient = useQueryClient();

  useEffect(() => {
    if (alert) {
      setLocalStatus(alert.status ?? 'open');
      setActiveTab('explanation'); // reset to first tab on new alert
    }
  }, [alert?.id]);

  const handleEscalate = async () => {
    if (!alert) return;
    setEscalating(true);
    try {
      await escalateAlert(alert.id, 'Tier 1 Analyst');
      setLocalStatus('escalated');
      toast('success', 'Escalated to Tier 2', `Alert for ${alert.identity_id} has been escalated.`);
      queryClient.invalidateQueries({ queryKey: ['alerts'] });
      queryClient.invalidateQueries({ queryKey: ['cases'] });
      queryClient.invalidateQueries({ queryKey: ['audit'] });
      queryClient.invalidateQueries({ queryKey: ['timeline', alert.id] });
      if (onActionComplete) onActionComplete();
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
      await dismissAlert(alert.id, 'Tier 1 Analyst', reason || 'Dismissed as False Positive');
      toast('success', 'Alert Dismissed', `${alert.identity_id} marked as false positive.`);
      queryClient.invalidateQueries({ queryKey: ['alerts'] });
      queryClient.invalidateQueries({ queryKey: ['cases'] });
      queryClient.invalidateQueries({ queryKey: ['audit'] });
      if (onActionComplete) onActionComplete();
      onClose();
    } catch (err) {
      setLocalStatus(prevStatus);
      toast('error', 'Dismiss failed', err.message);
    } finally {
      setDismissing(false);
    }
  };

  if (!alert) return null;

  const isBusy = escalating || dismissing;
  const isTerminal = localStatus === 'escalated' || localStatus === 'dismissed';

  const tabs = [
    { id: 'explanation', label: 'Explanation', icon: <FileText size={13} /> },
    { id: 'profile', label: 'Risk Profile', icon: <User size={13} /> },
    { id: 'timeline', label: 'Timeline', icon: <Activity size={13} /> },
    { id: 'graph', label: 'Graph', icon: <Globe size={13} /> },
  ];

  return (
    <>
      {showConfirmDismiss && (
        <ConfirmDismissModal
          identityId={alert.identity_id}
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
                Investigation Workspace
              </h2>
              <SeverityBadge severity={alert.severity} />
              <span className={`status-pill status-pill--${localStatus ?? 'open'}`}>
                {localStatus ?? 'open'}
              </span>
            </div>
            <div className="flex items-center gap-12 text-xs text-muted">
              <span className="font-mono">{alert.identity_id}</span>
              <span>·</span>
              <span>Score: {(alert.fusion_score * 100).toFixed(1)}%</span>
              <span>·</span>
              <span>{new Date(alert.created_at).toLocaleString('en-IN', { dateStyle: 'short', timeStyle: 'short' })}</span>
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
        <div
          className="drawer__body"
          style={activeTab === 'graph'
            ? { padding: 0, overflow: 'hidden', flex: 1, display: 'flex', flexDirection: 'column' }
            : {}
          }
        >
          {activeTab === 'explanation' && <ExplanationPanel alert={alert} />}
          {activeTab === 'profile' && <CustomerRiskProfile identityId={alert.identity_id} />}
          {activeTab === 'timeline' && <InvestigationTimeline alertId={alert.id} />}
          {activeTab === 'graph' && (
            <div className="empty-state" style={{ height: '100%', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center' }}>
              <Globe className="empty-state__icon" size={32} />
              <div className="empty-state__text mb-16">The Investigation Graph has moved to a dedicated page for better performance and scalability.</div>
              <button className="btn btn--primary" onClick={() => navigate(`/graph/${alert.identity_id}`)}>
                Open Investigation Graph
              </button>
            </div>
          )}
        </div>

        {/* ── Footer action buttons (preserved from original drawer) ── */}
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
                id="btn-dismiss-alert"
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
                id="btn-escalate-alert"
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
