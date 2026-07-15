import { useState, useEffect } from 'react';
import { Routes, Route } from 'react-router-dom';
import { useQueryClient } from '@tanstack/react-query';
import Header from './components/Header';
import Sidebar from './components/Sidebar';
import Dashboard from './pages/Dashboard';
import Alerts from './pages/Alerts';
import QuantumRisk from './pages/QuantumRisk';
import Cases from './pages/Cases';
import ScenarioRunner from './pages/ScenarioRunner';
import GraphPage from './pages/GraphPage';
import { createAlertsWebSocket } from './api';
import { ToastContainer } from './components/ExplanationDrawer';

// Check if demo mode is active by fetching the config endpoint. 
// For this 4-day build, we can just fetch it once on mount or assume true if env says so.
// Let's create a simple state for it.
const isDemoMode = true; // In a real app, fetch this from /api/config or similar

export default function App() {
  const [wsConnected, setWsConnected] = useState(false);
  const queryClient = useQueryClient();

  useEffect(() => {
    const ws = createAlertsWebSocket((msg) => {
      if (msg.type === 'WS_CONNECTED') setWsConnected(true);
      else if (msg.type === 'WS_DISCONNECTED') setWsConnected(false);
      else if (msg.type === 'NEW_ALERT' || msg.type === 'NEW_QUANTUM_ALERT') {
        // Invalidate queries so they refetch immediately on new data
        queryClient.invalidateQueries({ queryKey: ['alerts'] });
        queryClient.invalidateQueries({ queryKey: ['dashboard_kpis'] });
        queryClient.invalidateQueries({ queryKey: ['quantum_sessions'] });
        queryClient.invalidateQueries({ queryKey: ['cases'] });
      }
    });

    return () => ws.close();
  }, [queryClient]);

  return (
    <>
      <ToastContainer />
      <Routes>
        <Route path="/graph/:identityId" element={<GraphPage />} />
        <Route path="*" element={
          <div className="app-layout">
            <Header wsConnected={wsConnected} />
            <Sidebar demoMode={isDemoMode} />
            <main className="app-main" id="app-main">
              <Routes>
                <Route path="/" element={<Dashboard />} />
                <Route path="/alerts" element={<Alerts />} />
                <Route path="/quantum" element={<QuantumRisk />} />
                <Route path="/cases" element={<Cases />} />
                {isDemoMode && <Route path="/scenario-runner" element={<ScenarioRunner />} />}
              </Routes>
            </main>
          </div>
        } />
      </Routes>
    </>
  );
}
