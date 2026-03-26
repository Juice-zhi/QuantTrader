import { useEffect, useState } from 'react';
import { tradingApi, strategiesApi, factorsApi } from '../services/api';
import { TrendingUp, TrendingDown, DollarSign, Activity, Layers, BarChart3 } from 'lucide-react';

function Card({ title, value, sub, icon: Icon, color }: any) {
  return (
    <div className="rounded-xl p-5 border" style={{ background: 'var(--bg-card)', borderColor: 'var(--border)' }}>
      <div className="flex items-center justify-between mb-3">
        <span className="text-xs font-medium uppercase tracking-wider" style={{ color: 'var(--text-secondary)' }}>{title}</span>
        <Icon size={18} style={{ color }} />
      </div>
      <div className="text-2xl font-bold" style={{ color }}>{value}</div>
      {sub && <div className="text-xs mt-1" style={{ color: 'var(--text-secondary)' }}>{sub}</div>}
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
      <h2 className="text-xl font-bold mb-6">Dashboard</h2>

      <div className="grid grid-cols-4 gap-4 mb-8">
        <Card title="Total Equity" value={`$${equity.toLocaleString()}`} icon={DollarSign} color="var(--accent)" />
        <Card
          title="Realized PnL"
          value={`${pnl >= 0 ? '+' : ''}$${pnl.toFixed(2)}`}
          icon={pnl >= 0 ? TrendingUp : TrendingDown}
          color={pnl >= 0 ? 'var(--green)' : 'var(--red)'}
        />
        <Card title="Unrealized PnL" value={`$${unrealized.toFixed(2)}`}
          icon={Activity} color={unrealized >= 0 ? 'var(--green)' : 'var(--red)'} />
        <Card title="Open Positions" value={positions} sub={`${activeStrats} active strategies`}
          icon={Layers} color="var(--yellow)" />
      </div>

      {/* Quick Stats */}
      <div className="grid grid-cols-2 gap-4">
        <div className="rounded-xl p-5 border" style={{ background: 'var(--bg-card)', borderColor: 'var(--border)' }}>
          <h3 className="text-sm font-semibold mb-4 flex items-center gap-2">
            <Layers size={16} style={{ color: 'var(--accent)' }} /> Strategies ({strategies.length})
          </h3>
          {strategies.length === 0 ? (
            <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>
              No strategies configured. Go to Strategies page to create one.
            </p>
          ) : (
            <div className="space-y-2">
              {strategies.slice(0, 5).map((s: any) => (
                <div key={s.id} className="flex items-center justify-between py-2 px-3 rounded-lg"
                     style={{ background: 'var(--bg-secondary)' }}>
                  <span className="text-sm">{s.name}</span>
                  <span className={`text-xs px-2 py-0.5 rounded-full ${
                    s.is_enabled ? 'bg-green-500/20 text-green-400' : 'bg-gray-500/20 text-gray-400'
                  }`}>
                    {s.status}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="rounded-xl p-5 border" style={{ background: 'var(--bg-card)', borderColor: 'var(--border)' }}>
          <h3 className="text-sm font-semibold mb-4 flex items-center gap-2">
            <BarChart3 size={16} style={{ color: 'var(--accent)' }} /> Factor Library
          </h3>
          <div className="text-4xl font-bold mb-2" style={{ color: 'var(--accent)' }}>{factorCount}</div>
          <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>factors available across 5 categories</p>
          <div className="flex gap-2 mt-3 flex-wrap">
            {['technical', 'momentum', 'volatility', 'volume', 'composite'].map(c => (
              <span key={c} className="text-xs px-2 py-1 rounded-md" style={{ background: 'var(--bg-secondary)', color: 'var(--text-secondary)' }}>
                {c}
              </span>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
