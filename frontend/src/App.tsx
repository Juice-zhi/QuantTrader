import { BrowserRouter, HashRouter, Routes, Route, NavLink } from 'react-router-dom';
import { useEffect, useState } from 'react';
import { LayoutDashboard, BarChart3, FlaskConical, History, TrendingUp, Monitor, Globe } from 'lucide-react';
import Dashboard from './pages/Dashboard';
import Strategies from './pages/Strategies';
import Factors from './pages/Factors';
import Backtest from './pages/Backtest';
import Trading from './pages/Trading';
import './index.css';

const isElectron = !!(window as any).electronAPI;

const navItems = [
  { to: '/', icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/strategies', icon: FlaskConical, label: 'Strategies' },
  { to: '/factors', icon: BarChart3, label: 'Factors' },
  { to: '/backtest', icon: History, label: 'Backtest' },
  { to: '/trading', icon: TrendingUp, label: 'Trading' },
];

function AppContent() {
  const [backendOk, setBackendOk] = useState<boolean | null>(null);

  useEffect(() => {
    const check = async () => {
      try {
        const base = isElectron ? 'http://127.0.0.1:8000' : '';
        const r = await fetch(`${base}/health`);
        setBackendOk(r.ok);
      } catch { setBackendOk(false); }
    };
    check();
    const iv = setInterval(check, 10000);
    return () => clearInterval(iv);
  }, []);

  return (
    <div className="flex h-screen overflow-hidden">
      {/* Sidebar - macOS titlebar inset */}
      <nav className="w-56 shrink-0 flex flex-col border-r"
           style={{
             background: 'var(--bg-secondary)', borderColor: 'var(--border)',
             ...(isElectron && navigator.platform.includes('Mac') ? { paddingTop: '28px' } : {}),
           }}>
        <div className="p-5 border-b" style={{ borderColor: 'var(--border)' }}>
          <h1 className="text-lg font-bold" style={{ color: 'var(--accent)' }}>
            QuantTrader
          </h1>
          <p className="text-xs mt-0.5 flex items-center gap-1" style={{ color: 'var(--text-secondary)' }}>
            {isElectron ? <Monitor size={10} /> : <Globe size={10} />}
            {isElectron ? 'Desktop App' : 'Web App'}
          </p>
        </div>
        <div className="flex-1 py-3">
          {navItems.map(({ to, icon: Icon, label }) => (
            <NavLink
              key={to}
              to={to}
              end={to === '/'}
              className={({ isActive }) =>
                `flex items-center gap-3 px-5 py-2.5 text-sm transition-colors ${
                  isActive
                    ? 'border-r-2 font-medium'
                    : 'opacity-60 hover:opacity-100'
                }`
              }
              style={({ isActive }) => ({
                color: isActive ? 'var(--accent)' : 'var(--text-secondary)',
                borderColor: isActive ? 'var(--accent)' : 'transparent',
                background: isActive ? 'rgba(99,102,241,0.08)' : 'transparent',
              })}
            >
              <Icon size={18} />
              {label}
            </NavLink>
          ))}
        </div>
        <div className="p-4 text-xs space-y-1" style={{ color: 'var(--text-secondary)' }}>
          <div className="flex items-center gap-1.5">
            <span className={`w-1.5 h-1.5 rounded-full ${
              backendOk === true ? 'bg-green-500' : backendOk === false ? 'bg-red-500' : 'bg-yellow-500'
            }`} />
            Backend {backendOk === true ? 'Connected' : backendOk === false ? 'Offline' : 'Checking...'}
          </div>
          <div>v0.1.0</div>
        </div>
      </nav>

      {/* Main Content */}
      <main className="flex-1 overflow-y-auto p-6" style={{ background: 'var(--bg-primary)' }}>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/strategies" element={<Strategies />} />
          <Route path="/factors" element={<Factors />} />
          <Route path="/backtest" element={<Backtest />} />
          <Route path="/trading" element={<Trading />} />
        </Routes>
      </main>
    </div>
  );
}

// Electron 用 HashRouter (file:// 协议不支持 BrowserRouter)
// Web 用 BrowserRouter
export default function App() {
  const Router = isElectron ? HashRouter : BrowserRouter;
  return (
    <Router>
      <AppContent />
    </Router>
  );
}
