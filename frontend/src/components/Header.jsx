import { useTheme } from '../context/ThemeContext';
import { Sun, Moon, Wifi, WifiOff } from 'lucide-react';

export default function Header({ wsConnected }) {
  const { theme, toggleTheme } = useTheme();

  return (
    <header className="app-header" id="app-header">
      <div className="app-header__left">
        <span className="app-header__logo">◆ PRAHARI</span>
        <span className="text-xs text-muted" style={{ marginTop: 2 }}>Security Sentinel</span>
      </div>
      <div className="app-header__right">
        <div className="conn-status" id="ws-status">
          <span className={`conn-dot ${wsConnected ? 'conn-dot--connected' : 'conn-dot--disconnected'}`} />
          {wsConnected ? 'Live' : 'Offline'}
        </div>
        <button className="theme-toggle" onClick={toggleTheme} id="theme-toggle-btn">
          {theme === 'aero' ? <Moon size={14} /> : <Sun size={14} />}
          {theme === 'aero' ? 'Brutalist' : 'Aero'}
        </button>
      </div>
    </header>
  );
}
