import { useState, useEffect } from 'react';
import { X, CheckCircle, AlertTriangle, ShieldOff, Clock } from 'lucide-react';
import { performCaseAction } from '../api';
import SeverityBadge from './SeverityBadge';

export default function ExplanationDrawer({ alert, onClose, onActionComplete }) {
  const [explanationParts, setExplanationParts] = useState([]);
  const [controls, setControls] = useState([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [isTakingAction, setIsTakingAction] = useState(false);

  useEffect(() => {
    if (!alert) return;
    
    // Clear previous
    setExplanationParts([]);
    setControls([]);
    setIsStreaming(true);

    const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    // Actually, RAG uses SSE (Server-Sent Events) from /api/explain/stream via POST. 
    // We can fetch it with the native Fetch API.
    
    let isCancelled = false;

    const streamExplanation = async () => {
      try {
        const res = await fetch('/api/explain/stream', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            signals: alert.contributing_signals,
            severity: alert.severity
          })
        });

        if (!res.ok) throw new Error('Stream failed');

        const reader = res.body.getReader();
        const decoder = new TextDecoder();

        while (!isCancelled) {
          const { value, done } = await reader.read();
          if (done) break;

          const chunk = decoder.decode(value, { stream: true });
          const lines = chunk.split('\n');

          for (const line of lines) {
            if (line.startsWith('event: ')) {
              const eventType = line.substring(7).trim();
              // next line should be data:
              continue;
            }
            if (line.startsWith('data: ')) {
              const data = line.substring(6).trim();
              if (data === '[DONE]') {
                setIsStreaming(false);
                break;
              }
              
              try {
                const parsed = JSON.parse(data);
                if (parsed.type === 'text') {
                  setExplanationParts(prev => [...prev, parsed.content]);
                } else if (parsed.type === 'controls') {
                  setControls(parsed.controls);
                }
              } catch (e) { /* ignore parse error on partial chunks */ }
            }
          }
        }
      } catch (err) {
        if (!isCancelled) {
          setExplanationParts(['Failed to generate explanation. Falling back to offline rule cache.']);
          setIsStreaming(false);
        }
      }
    };

    streamExplanation();

    return () => { isCancelled = true; };
  }, [alert]);

  const handleAction = async (action) => {
    if (!alert?.case?.id) return;
    setIsTakingAction(true);
    try {
      await performCaseAction(alert.case.id, action, 'analyst', `Manually marked as ${action}`);
      if (onActionComplete) onActionComplete();
    } catch (err) {
      console.error(err);
      alert('Failed to perform action');
    } finally {
      setIsTakingAction(false);
      onClose();
    }
  };

  if (!alert) return null;

  return (
    <>
      <div className="drawer-overlay" onClick={onClose} />
      <div className="drawer">
        <div className="drawer__header">
          <div>
            <div className="flex items-center gap-12 mb-8">
              <h2 style={{ fontFamily: 'var(--font-display)', fontWeight: 'var(--font-weight-display)' }}>
                Identity Anomaly
              </h2>
              <SeverityBadge severity={alert.severity} />
            </div>
            <div className="text-xs font-mono text-muted">ID: {alert.identity_id}</div>
          </div>
          <button className="btn btn--ghost" onClick={onClose}><X size={20} /></button>
        </div>

        <div className="drawer__body">
          <div className="section-header">Regulatory Context & Explanation</div>
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

        <div className="drawer__footer">
          <button 
            className="btn btn--secondary" 
            style={{ flex: 1 }} 
            onClick={() => handleAction('dismiss')}
            disabled={isTakingAction}
          >
            Dismiss False Positive
          </button>
          <button 
            className="btn btn--primary" 
            style={{ flex: 1 }}
            onClick={() => handleAction('escalate')}
            disabled={isTakingAction}
          >
            <CheckCircle size={16} /> Escalate to Tier 2
          </button>
        </div>
      </div>
    </>
  );
}
