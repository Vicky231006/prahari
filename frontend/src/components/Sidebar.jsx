import { NavLink } from 'react-router-dom';
import { LayoutDashboard, ShieldAlert, Binary, Briefcase, PlaySquare } from 'lucide-react';

export default function Sidebar({ demoMode = false }) {
  return (
    <nav className="app-sidebar">
      <div className="nav-section-label">Main</div>
      
      <NavLink to="/" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
        <LayoutDashboard /> Dashboard
      </NavLink>
      
      <NavLink to="/alerts" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
        <ShieldAlert /> Alerts
      </NavLink>
      
      <NavLink to="/quantum" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
        <Binary /> Quantum Risk
      </NavLink>
      
      <div className="nav-section-label">Investigation</div>
      
      <NavLink to="/cases" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
        <Briefcase /> Alert Cases & Audit
      </NavLink>

      {demoMode && (
        <>
          <div className="nav-section-label">Simulation</div>
          <NavLink to="/scenario-runner" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
            <PlaySquare /> Scenario Runner
          </NavLink>
        </>
      )}
    </nav>
  );
}
