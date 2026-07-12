export default function SeverityBadge({ severity }) {
  const normSev = severity?.toLowerCase() || 'low';
  
  return (
    <div className={`severity-badge severity-badge--${normSev}`}>
      <span className={`severity-dot severity-dot--${normSev}`} />
      {normSev}
    </div>
  );
}
