import { useEffect, useState } from 'react';
import { tradingApi, strategiesApi, factorsApi } from '../services/api';
import {
  Wallet, Activity, Layers, BarChart3,
  ArrowUpRight, ArrowDownRight, Sparkles
} from 'lucide-react';

function MetricCard({ title, value, sub, icon: Icon, color, delay = 0 }: any) {
  return (
    <div className="qt-card qt-card-glow animate-in" style={{ animationDelay: `${delay}ms` }}>
      <div className="flex items-start justify-between mb-4">
        <span className="qt-label">{title}</span>
        <div
          style={{
            width: 32, height: 32, borderRadius: 'var(--radius-sm)',
            background: `${color}12`,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
          }}
        >
          <Icon size={16} style={{ color }} />
        </div>
      </div>
      <div style={{ fontFamily: 'var(--font-mono)', fontSize: 22, fontWeight: 600, color, letterSpacing: '-0.02em', lineHeight: 1 }}>
        {value}
      </div>
      {sub && (
        <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 8 }}>{sub}</div>
      )}
    </div>
  );
}

export default function Dashboard() {
  const [portfolio, setPortfolio] = useState<any>(null);
  const [strategies, setStrategies] = useState<any[]>([]);
  const [factorCount, setFactorCount] = useState(0);

  useEffect(() => {
    tradingApi.portfolio('paper').then(setPortfolio).catch(() => {});
    strategiesApi.list().then(d => setStrategies(d.strategies || [])).catch(() => {});
    factorsApi.list().then(d => setFactorCount(d.count || 0)).catch(() => {});
  }, []);

  const equity = portfolio?.total_equity ?? 100000;
  const pnl = portfolio?.realized_pnl ?? 0;
  const unrealized = portfolio?.unrealized_pnl ?? 0;
  const positions = portfolio?.positions?.length ?? 0;
  const activeStrats = strategies.filter(s => s.is_enabled).length;

  return (
    <div>
      {/* Header */}
      <div className="flex items-end justify-between mb-8 animate-in">
        <div>
          <div className="qt-label mb-2">Overview</div>
          <h1 style={{ fontFamily: 'var(--font-display)', fontSize: 28, fontWeight: 700, color: 'var(--text-bright)', letterSpacing: '-0.02em' }}>
            Dashboard
          </h1>
        </div>
        <div style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--text-muted)' }}>
          {new Date().toLocaleDateString('en-US', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })}
        </div>
      </div>

      {/* Metric Cards */}
      <div className="grid grid-cols-4 gap-4 mb-8">
        <MetricCard
          title="Total Equity"
          value={`$${equity.toLocaleString('en-US', { minimumFractionDigits: 2 })}`}
          icon={Wallet}
          color="var(--accent)"
          delay={50}
        />
        <MetricCard
          title="Realized PnL"
          value={`${pnl >= 0 ? '+' : ''}$${Math.abs(pnl).toFixed(2)}`}
          icon={pnl >= 0 ? ArrowUpRight : ArrowDownRight}
          color={pnl >= 0 ? 'var(--green)' : 'var(--red)'}
          delay={100}
        />
        <MetricCard
          title="Unrealized PnL"
          value={`$${unrealized.toFixed(2)}`}
          icon={Activity}
          color={unrealized >= 0 ? 'var(--green)' : 'var(--red)'}
          delay={150}
        />
        <MetricCard
          title="Positions"
          value={positions}
          sub={`${activeStrats} active / ${strategies.length} total strategies`}
          icon={Layers}
          color="var(--blue)"
          delay={200}
        />
      </div>

      {/* Bottom Sections */}
      <div className="grid grid-cols-5 gap-4">
        {/* Strategies Panel — wider */}
        <div className="col-span-3 qt-card animate-in" style={{ animationDelay: '250ms' }}>
          <div className="flex items-center justify-between mb-5">
            <div className="flex items-center gap-2.5">
              <Layers size={15} style={{ color: 'var(--accent)' }} />
              <span style={{ fontSize: 14, fontWeight: 600 }}>Strategies</span>
              <span className="qt-badge" style={{ background: 'var(--accent-glow)', color: 'var(--accent)' }}>
                {strategies.length}
              </span>
            </div>
          </div>

          {strategies.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '32px 0' }}>
              <Sparkles size={28} style={{ color: 'var(--text-muted)', margin: '0 auto 12px' }} />
              <p style={{ fontSize: 13, color: 'var(--text-muted)' }}>
                No strategies configured yet
              </p>
              <p style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 4 }}>
                Navigate to Strategies to create one
              </p>
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
              {strategies.slice(0, 6).map((s: any) => (
                <div
                  key={s.id}
                  className="flex items-center justify-between"
                  style={{
                    padding: '10px 14px',
                    borderRadius: 'var(--radius-sm)',
                    background: 'var(--bg-primary)',
                    border: '1px solid var(--border-subtle)',
                    transition: 'border-color 0.2s',
                  }}
                >
                  <div className="flex items-center gap-3">
                    <div
                      style={{
                        width: 7, height: 7, borderRadius: '50%',
                        background: s.is_enabled ? 'var(--green)' : 'var(--text-muted)',
                        ...(s.is_enabled ? { boxShadow: '0 0 6px var(--green)' } : {}),
                      }}
                    />
                    <span style={{ fontSize: 13, fontWeight: 500 }}>{s.name}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="qt-badge" style={{
                      background: s.is_enabled ? 'var(--green-dim)' : 'var(--bg-elevated)',
                      color: s.is_enabled ? 'var(--green)' : 'var(--text-muted)',
                    }}>
                      {s.status}
                    </span>
                    <span className="qt-badge" style={{ background: 'var(--blue-dim)', color: 'var(--blue)' }}>
                      {s.execution_mode}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Factor Library Panel */}
        <div className="col-span-2 qt-card animate-in" style={{ animationDelay: '300ms' }}>
          <div className="flex items-center gap-2.5 mb-5">
            <BarChart3 size={15} style={{ color: 'var(--accent)' }} />
            <span style={{ fontSize: 14, fontWeight: 600 }}>Factor Library</span>
          </div>

          <div style={{
            fontFamily: 'var(--font-display)',
            fontSize: 48, fontWeight: 700,
            lineHeight: 1,
            marginBottom: 8,
          }}>
            <span className="text-gradient">{factorCount}</span>
          </div>
          <p style={{ fontSize: 12, color: 'var(--text-secondary)', marginBottom: 20, lineHeight: 1.5 }}>
            factors available across 5 analytical categories
          </p>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            {[
              { name: 'Technical', count: 9, color: 'var(--accent)' },
              { name: 'Momentum', count: 5, color: 'var(--green)' },
              { name: 'Volatility', count: 5, color: 'var(--red)' },
              { name: 'Volume', count: 6, color: 'var(--yellow)' },
              { name: 'Composite', count: 1, color: 'var(--purple)' },
            ].map(cat => (
              <div key={cat.name} className="flex items-center gap-3" style={{ padding: '6px 0' }}>
                <div style={{ width: 3, height: 16, borderRadius: 2, background: cat.color }} />
                <span style={{ fontSize: 12, color: 'var(--text-secondary)', flex: 1 }}>{cat.name}</span>
                <span style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: cat.color }}>{cat.count}</span>
                <div style={{
                  flex: 2, height: 3, borderRadius: 2, background: 'var(--bg-primary)',
                  overflow: 'hidden',
                }}>
                  <div style={{
                    width: `${(cat.count / 26) * 100}%`, height: '100%',
                    borderRadius: 2, background: cat.color, opacity: 0.6,
                  }} />
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
