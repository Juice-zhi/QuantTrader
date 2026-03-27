import { BrowserRouter, HashRouter, Routes, Route, NavLink, useLocation } from 'react-router-dom';
import { useEffect, useState } from 'react';
import {
  LayoutDashboard, BarChart3, FlaskConical, History, TrendingUp,
  Monitor, Globe, Zap
} from 'lucide-react';
import Dashboard from './pages/Dashboard';
import Strategies from './pages/Strategies';
import Factors from './pages/Factors';
import Backtest from './pages/Backtest';
import Trading from './pages/Trading';
import './index.css';

const isElectron = !!(window as any).electronAPI;

const navItems = [
  { to: '/', icon: LayoutDashboard, label: 'Dashboard', shortcut: '1' },
  { to: '/strategies', icon: FlaskConical, label: 'Strategies', shortcut: '2' },
  { to: '/factors', icon: BarChart3, label: 'Factors', shortcut: '3' },
  { to: '/backtest', icon: History, label: 'Backtest', shortcut: '4' },
  { to: '/trading', icon: TrendingUp, label: 'Trading', shortcut: '5' },
];

function AppContent() {
  const [backendOk, setBackendOk] = useState<boolean | null>(null);
  const [now, setNow] = useState(new Date());
  const location = useLocation();

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

  useEffect(() => {
    const iv = setInterval(() => setNow(new Date()), 1000);
    return () => clearInterval(iv);
  }, []);

  return (
    <div className="noise-overlay flex h-screen overflow-hidden" style={{ background: 'var(--bg-void)' }}>
      {/* ── Sidebar ── */}
      <nav
        className="shrink-0 flex flex-col"
        style={{
          width: 220,
          background: 'var(--bg-primary)',
          borderRight: '1px solid var(--border)',
          ...(isElectron && navigator.platform.includes('Mac') ? { paddingTop: 28 } : {}),
        }}
      >
        {/* Brand */}
        <div style={{ padding: '24px 20px 20px' }}>
          <div className="flex items-center gap-2.5">
            <div
              className="flex items-center justify-center"
              style={{
                width: 30, height: 30, borderRadius: 7,
                background: 'linear-gradient(135deg, var(--accent), #d4ae52)',
              }}
            >
              <Zap size={15} color="#0c0d12" strokeWidth={2.5} />
            </div>
            <div>
              <div
                style={{
                  fontFamily: 'var(--font-display)',
                  fontSize: 17, fontWeight: 700,
                  color: 'var(--text-bright)',
                  lineHeight: 1.1,
                  letterSpacing: '-0.02em',
                }}
              >
                Quant<span className="text-gradient">Trader</span>
              </div>
            </div>
          </div>
          <div
            className="flex items-center gap-1.5 mt-3"
            style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: 'var(--text-muted)', letterSpacing: '0.06em' }}
          >
            {isElectron ? <Monitor size={10} /> : <Globe size={10} />}
            {isElectron ? 'DESKTOP' : 'WEB'} &middot; v0.1.0
          </div>
        </div>

        <div className="glow-line mx-4" />

        {/* Navigation */}
        <div className="flex-1 py-4 px-3">
          {navItems.map(({ to, icon: Icon, label, shortcut }, idx) => (
            <NavLink
              key={to}
              to={to}
              end={to === '/'}
              className="animate-in"
              style={{
                animationDelay: `${idx * 50}ms`,
                display: 'flex', alignItems: 'center', gap: 10,
                padding: '10px 12px', marginBottom: 2,
                borderRadius: 'var(--radius-sm)',
                fontSize: 13, fontWeight: 500,
                textDecoration: 'none',
                transition: 'all 0.2s',
                ...(location.pathname === to || (to === '/' && location.pathname === '/')
                  ? (to === location.pathname || (to === '/' && location.pathname === '/'))
                    ? {
                        background: 'var(--accent-glow)',
                        color: 'var(--accent)',
                        boxShadow: 'inset 2px 0 0 var(--accent)',
                      }
                    : {}
                  : {}
                ),
                color: (location.pathname === to) ? 'var(--accent)' :
                       (to === '/' && location.pathname === '/') ? 'var(--accent)' :
                       'var(--text-secondary)',
                background: (location.pathname === to || (to === '/' && location.pathname === '/'))
                  ? 'var(--accent-glow)' : 'transparent',
                boxShadow: (location.pathname === to || (to === '/' && location.pathname === '/'))
                  ? 'inset 2px 0 0 var(--accent)' : 'none',
              }}
              onMouseEnter={e => {
                if (location.pathname !== to && !(to === '/' && location.pathname === '/')) {
                  (e.currentTarget as HTMLElement).style.background = 'var(--bg-hover)';
                  (e.currentTarget as HTMLElement).style.color = 'var(--text-primary)';
                }
              }}
              onMouseLeave={e => {
                if (location.pathname !== to && !(to === '/' && location.pathname === '/')) {
                  (e.currentTarget as HTMLElement).style.background = 'transparent';
                  (e.currentTarget as HTMLElement).style.color = 'var(--text-secondary)';
                }
              }}
            >
              <Icon size={16} />
              <span className="flex-1">{label}</span>
              <span style={{
                fontFamily: 'var(--font-mono)', fontSize: 9, color: 'var(--text-muted)',
                opacity: 0.5, letterSpacing: '0.05em',
              }}>
                {shortcut}
              </span>
            </NavLink>
          ))}
        </div>

        {/* Status footer */}
        <div style={{ padding: '16px 16px 20px', borderTop: '1px solid var(--border-subtle)' }}>
          <div className="flex items-center gap-2 mb-2">
            <div
              style={{
                width: 6, height: 6, borderRadius: '50%',
                background: backendOk === true ? 'var(--green)' : backendOk === false ? 'var(--red)' : 'var(--yellow)',
                ...(backendOk === true ? { boxShadow: '0 0 6px var(--green)' } : {}),
              }}
            />
            <span style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: 'var(--text-muted)', letterSpacing: '0.06em' }}>
              {backendOk === true ? 'API CONNECTED' : backendOk === false ? 'API OFFLINE' : 'CONNECTING...'}
            </span>
          </div>
          <div style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: 'var(--text-muted)', letterSpacing: '0.08em' }}>
            {now.toLocaleTimeString('en-US', { hour12: false })}
          </div>
        </div>
      </nav>

      {/* ── Main Content ── */}
      <main
        className="flex-1 overflow-y-auto"
        style={{ background: 'var(--bg-secondary)', padding: '28px 32px' }}
      >
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

export default function App() {
  const Router = isElectron ? HashRouter : BrowserRouter;
  return (
    <Router>
      <AppContent />
    </Router>
  );
}
