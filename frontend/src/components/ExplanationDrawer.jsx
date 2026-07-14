import { useState, useEffect, useCallback, useRef } from 'react';
import { createPortal } from 'react-dom';
import {
  X, CheckCircle, AlertTriangle, ShieldOff, Clock,
  ShieldX, CheckCheck, Loader2
} from 'lucide-react';
import { escalateAlert, dismissAlert } from '../api';
import SeverityBadge from './SeverityBadge';
import { useQueryClient } from '@tanstack/react-query';

// ── Lightweight toast system ────────────────────────────────────────────────
// No extra dependency. A single ToastContainer rendered into a portal at the
// document body so it stacks on top of everything (z-index 9999).

let _toastId = 0;
let _setToasts = null; // set by the first ToastContainer that mounts

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

  useEffect(() => {
    textareaRef.current?.focus();
  }, []);

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
          <button className="btn btn--ghost btn--small" onClick={onCancel}>
            Cancel
          </button>
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


// ── Main drawer component ────────────────────────────────────────────────────
export default function ExplanationDrawer({ alert, onClose, onActionComplete }) {
  const [explanationParts, setExplanationParts] = useState([]);
  const [controls, setControls] = useState([]);
  const [isStreaming, setIsStreaming] = useState(false);

  // Workflow state
  const [escalating, setEscalating] = useState(false);
  const [dismissing, setDismissing] = useState(false);
  const [showConfirmDismiss, setShowConfirmDismiss] = useState(false);

  // Local status mirrors the server truth; updated optimistically on success
  const [localStatus, setLocalStatus] = useState(null);

  const queryClient = useQueryClient();

  // Sync localStatus with the incoming alert prop whenever a different alert
  // is opened (or after the parent refreshes its data).
  useEffect(() => {
    if (alert) setLocalStatus(alert.status ?? 'open');
  }, [alert?.id]);

  // ── RAG explanation stream ──────────────────────────────────────────────
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
              } catch (_) { /* partial chunk – ignore */ }
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


  // ── Escalate handler ────────────────────────────────────────────────────
  const handleEscalate = async () => {
    if (!alert) return;
    setEscalating(true);
    try {
      await escalateAlert(alert.id, 'Tier 1 Analyst');
      setLocalStatus('escalated');
      toast('success', 'Escalated to Tier 2', `Alert for ${alert.identity_id} has been escalated. A case has been created.`);
      // Refresh alerts list, cases list, and audit trail in the background
      queryClient.invalidateQueries({ queryKey: ['alerts'] });
      queryClient.invalidateQueries({ queryKey: ['cases'] });
      queryClient.invalidateQueries({ queryKey: ['audit'] });
      if (onActionComplete) onActionComplete();
    } catch (err) {
      toast('error', 'Escalation failed', err.message);
    } finally {
      setEscalating(false);
    }
  };


  // ── Dismiss handlers ────────────────────────────────────────────────────
  const handleDismissClick = () => {
    if (!alert) return;
    setShowConfirmDismiss(true);
  };

  const handleDismissConfirm = async (reason) => {
    setShowConfirmDismiss(false);
    setDismissing(true);
    const prevStatus = localStatus;
    // Optimistic update so the UI feels instant
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
      // Rollback optimistic update on failure
      setLocalStatus(prevStatus);
      toast('error', 'Dismiss failed', err.message);
    } finally {
      setDismissing(false);
    }
  };

  const handleDismissCancel = () => setShowConfirmDismiss(false);


  if (!alert) return null;

  const isBusy = escalating || dismissing;
  const isTerminal = localStatus === 'escalated' || localStatus === 'dismissed';

  return (
    <>
      {/* Confirm modal rendered via portal — sits above the drawer overlay */}
      {showConfirmDismiss && (
        <ConfirmDismissModal
          identityId={alert.identity_id}
          onConfirm={handleDismissConfirm}
          onCancel={handleDismissCancel}
        />
      )}

      <div className="drawer-overlay" onClick={onClose} />
      <div className="drawer">
        {/* ── Header ── */}
        <div className="drawer__header">
          <div>
            <div className="flex items-center gap-12 mb-8">
              <h2 style={{ fontFamily: 'var(--font-display)', fontWeight: 'var(--font-weight-display)' }}>
                Identity Anomaly
              </h2>
              <SeverityBadge severity={alert.severity} />
              {/* Live status pill — updates immediately after action */}
              <span className={`status-pill status-pill--${localStatus ?? 'open'}`}>
                {localStatus ?? 'open'}
              </span>
            </div>
            <div className="text-xs font-mono text-muted">ID: {alert.identity_id}</div>
          </div>
          <button className="btn btn--ghost" onClick={onClose}><X size={20} /></button>
        </div>

        {/* ── Body ── */}
        <div className="drawer__body">
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
                  {controls.map(c => (
                    <span key={c} className="control-chip">{c}</span>
                  ))}
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
        </div>

        {/* ── Footer action buttons ── */}
        <div className="drawer__footer">
          {isTerminal ? (
            /* Alert already actioned — show a read-only status chip instead of buttons */
            <div
              className="flex items-center justify-center gap-8 text-sm text-muted"
              style={{ flex: 1, padding: '4px 0' }}
            >
              <CheckCheck size={15} />
              {localStatus === 'escalated'
                ? 'Escalated to Tier 2 — case created and audit logged.'
                : 'Dismissed as false positive — audit logged.'}
            </div>
          ) : (
            <>
              {/* Dismiss False Positive */}
              <button
                id="btn-dismiss-alert"
                className="btn btn--secondary"
                style={{ flex: 1 }}
                onClick={handleDismissClick}
                disabled={isBusy}
                title="Dismiss as False Positive (requires confirmation)"
              >
                {dismissing ? (
                  <Loader2 size={15} className="spin" />
                ) : (
                  <ShieldX size={15} />
                )}
                Dismiss False Positive
              </button>

              {/* Escalate to Tier 2 */}
              <button
                id="btn-escalate-alert"
                className="btn btn--primary"
                style={{ flex: 1 }}
                onClick={handleEscalate}
                disabled={isBusy}
                title="Escalate to Tier 2 — creates a case"
              >
                {escalating ? (
                  <Loader2 size={15} className="spin" />
                ) : (
                  <CheckCircle size={15} />
                )}
                Escalate to Tier 2
              </button>
            </>
          )}
        </div>
      </div>
    </>
  );
}
