import { useState } from 'react';
import { injectScenario } from '../api';
import { PlaySquare, AlertCircle, CheckCircle } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

const SCENARIOS = [
  {
    id: 'ato',
    title: 'Account Takeover (ATO)',
    desc: 'Injects a login from a new device with impossible travel, followed immediately by a high-value transfer to a new beneficiary.'
  },
  {
    id: 'insider_collusion',
    title: 'Insider Collusion',
    desc: 'Injects an unusual data access by a privileged account, correlated with a transaction from a linked identity to a shared beneficiary.'
  },
  {
    id: 'credential_stuffing_ato',
    title: 'Credential Stuffing → ATO',
    desc: 'Injects a burst of failed logins across identities from few IPs, followed by one success and an immediate transaction.'
  },
  {
    id: 'hndl_exposure',
    title: 'HNDL Exposure',
    desc: 'Injects a TLS session carrying KYC or credit history sensitivity data negotiated over a legacy (RSA/ECDHE) key exchange.'
  }
];

export default function ScenarioRunner() {
  const [running, setRunning] = useState(null);
  const [results, setResults] = useState({});
  const navigate = useNavigate();

  const handleRun = async (scenarioId) => {
    setRunning(scenarioId);
    try {
      const res = await injectScenario(scenarioId);
      setResults(prev => ({ ...prev, [scenarioId]: { success: true, message: res.message || 'Injected successfully' } }));
    } catch (err) {
      setResults(prev => ({ ...prev, [scenarioId]: { success: false, message: err.message } }));
    } finally {
      setRunning(null);
    }
  };

  return (
    <div className="fade-in">
      <div className="flex items-center justify-between mb-24">
        <div>
          <h1 className="section-header mb-8 flex items-center gap-12">
            <PlaySquare className="text-accent" /> Scenario Runner
          </h1>
          <p className="section-sub mb-0">Inject synthetic attack sequences through the live Kafka → Flink → Pipeline flow.</p>
        </div>
        <div className="severity-badge" style={{ background: 'var(--severity-critical-bg)', color: 'var(--severity-critical)', border: '1px solid var(--severity-critical)' }}>
          DEMO MODE ACTIVE
        </div>
      </div>

      <div className="scenario-grid">
        {SCENARIOS.map(sc => (
          <div key={sc.id} className="card scenario-card">
            <div className="scenario-card__title">{sc.title}</div>
            <div className="scenario-card__desc">{sc.desc}</div>
            
            <div className="mt-auto pt-16 flex items-center justify-between">
              <button 
                className="btn btn--primary" 
                onClick={() => handleRun(sc.id)}
                disabled={running !== null}
              >
                {running === sc.id ? <><div className="spinner" style={{ width: 14, height: 14, borderWidth: 2 }} /> Injecting...</> : 'Inject Scenario'}
              </button>
              
              {results[sc.id]?.success && (
                <button className="btn btn--ghost text-xs" onClick={() => navigate(sc.id === 'hndl_exposure' ? '/quantum' : '/alerts')}>
                  View Results →
                </button>
              )}
            </div>

            {results[sc.id] && (
              <div className={`scenario-card__result ${results[sc.id].success ? 'scenario-card__result--success' : 'scenario-card__result--error'} mt-8 flex items-center gap-8`}>
                {results[sc.id].success ? <CheckCircle size={14} /> : <AlertCircle size={14} />}
                {results[sc.id].message}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
