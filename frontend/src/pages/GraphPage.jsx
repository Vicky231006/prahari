import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';
import InvestigationGraph from '../components/InvestigationGraph';

export default function GraphPage() {
  const { identityId } = useParams();
  const navigate = useNavigate();

  const titleComponent = (
    <div className="flex items-center gap-12" style={{ borderRight: '1px solid var(--surface-border)', paddingRight: 16 }}>
      <button className="btn btn--ghost btn--small" onClick={() => navigate(-1)} title="Go back">
        <ArrowLeft size={16} /> Back
      </button>
      <h1 className="section-header m-0" style={{ fontSize: '1.1rem' }}>Investigation Graph</h1>
      <span className="font-mono text-xs text-muted" style={{ padding: '2px 6px', background: 'var(--surface-hover)', borderRadius: 4 }}>
        {identityId}
      </span>
    </div>
  );

  return (
    <div style={{ width: '100vw', height: '100vh', display: 'flex', flexDirection: 'column', overflow: 'hidden', background: 'var(--bg-color)' }}>
      <InvestigationGraph identityId={identityId} titleComponent={titleComponent} />
    </div>
  );
}
