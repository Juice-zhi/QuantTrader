import { useState, useEffect } from 'react';
import { backtestApi, strategiesApi } from '../services/api';
import { XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Area, AreaChart } from 'recharts';
import { Play, Loader2, Clock, Target } from 'lucide-react';

export default function Backtest() {
  const [types, setTypes] = useState<any[]>([]);
  const [results, setResults] = useState<any[]>([]);
  const [activeResult, setActiveResult] = useState<any>(null);
  const [running, setRunning] = useState(false);
  const [form, setForm] = useState({
    strategy_type: '', symbol: 'BTC/USDT', timeframe: '1d',
    exchange: 'binance', initial_capital: 100000, params: '{}',
  });

  useEffect(() => {
    strategiesApi.types().then(d => setTypes(d.strategies || []));
    backtestApi.results().then(d => setResults(d.results || []));
  }, []);

  const runBacktest = async () => {
    setRunning(true);
    try {
      const result = await backtestApi.run({
        ...form,
        initial_capital: Number(form.initial_capital),
        params: JSON.parse(form.params || '{}'),
      });
      setActiveResult(result);
      backtestApi.results().then(d => setResults(d.results || []));
    } catch (e: any) {
      alert('Backtest failed: ' + e.message);
    }
    setRunning(false);
  };

  const equityData = activeResult?.equity_curve?.map((e: any, i: number) => ({
    idx: i,
    equity: Number(e.equity?.toFixed(2)),
  })) || [];

  const CustomTooltip = ({ active, payload }: any) => {
    if (!active || !payload?.length) return null;
    return (
      <div style={{
        background: 'var(--bg-elevated)', border: '1px solid var(--border-active)',
        borderRadius: 'var(--radius-sm)', padding: '8px 12px',
        fontFamily: 'var(--font-mono)', fontSize: 11,
      }}>
        <span style={{ color: 'var(--accent)' }}>${payload[0].value?.toLocaleString()}</span>
      </div>
    );
  };

  return (
    <div>
      {/* Header */}
      <div className="flex items-end justify-between mb-8 animate-in">
        <div>
          <div className="qt-label mb-2">Simulation</div>
          <h1 style={{ fontFamily: 'var(--font-display)', fontSize: 28, fontWeight: 700, color: 'var(--text-bright)', letterSpacing: '-0.02em' }}>
            Backtest Engine
          </h1>
        </div>
      </div>

      {/* Config Form */}
      <div className="qt-card animate-in mb-6" style={{ animationDelay: '50ms' }}>
        <div className="grid grid-cols-3 gap-4 mb-4">
          <div>
            <label className="qt-label" style={{ display: 'block', marginBottom: 6 }}>Strategy</label>
            <select value={form.strategy_type} onChange={e => {
              const t = types.find(t => t.name === e.target.value);
              setForm({ ...form, strategy_type: e.target.value, params: JSON.stringify(t?.params || {}, null, 2) });
            }} className="qt-select w-full">
              <option value="">Select strategy...</option>
              {types.map(t => <option key={t.name} value={t.name}>{t.name}</option>)}
            </select>
          </div>
          <div>
            <label className="qt-label" style={{ display: 'block', marginBottom: 6 }}>Symbol</label>
            <input value={form.symbol} onChange={e => setForm({ ...form, symbol: e.target.value })} className="qt-input" />
          </div>
          <div>
            <label className="qt-label" style={{ display: 'block', marginBottom: 6 }}>Timeframe</label>
            <select value={form.timeframe} onChange={e => setForm({ ...form, timeframe: e.target.value })} className="qt-select w-full">
              {['1m','5m','15m','1h','4h','1d'].map(tf => <option key={tf} value={tf}>{tf}</option>)}
            </select>
          </div>
        </div>
        <div className="grid grid-cols-3 gap-4 mb-4">
          <div>
            <label className="qt-label" style={{ display: 'block', marginBottom: 6 }}>Exchange</label>
            <select value={form.exchange} onChange={e => setForm({ ...form, exchange: e.target.value })} className="qt-select w-full">
              <option value="binance">Binance</option>
              <option value="okx">OKX</option>
              <option value="nasdaq">NASDAQ</option>
            </select>
          </div>
          <div>
            <label className="qt-label" style={{ display: 'block', marginBottom: 6 }}>Capital</label>
            <input type="number" value={form.initial_capital}
              onChange={e => setForm({ ...form, initial_capital: +e.target.value })} className="qt-input" />
          </div>
          <div style={{ display: 'flex', alignItems: 'flex-end' }}>
            <button onClick={runBacktest} disabled={running || !form.strategy_type}
              className="qt-btn qt-btn-accent w-full" style={{ height: 40 }}>
              {running ? <Loader2 size={15} className="animate-spin" /> : <Play size={15} />}
              {running ? 'Running...' : 'Run Backtest'}
            </button>
          </div>
        </div>
        <div>
          <label className="qt-label" style={{ display: 'block', marginBottom: 6 }}>Parameters (JSON)</label>
          <textarea value={form.params} onChange={e => setForm({ ...form, params: e.target.value })}
            rows={3} className="qt-input" style={{ fontFamily: 'var(--font-mono)', fontSize: 12, resize: 'vertical' }} />
        </div>
      </div>

      {/* Results */}
      {activeResult && (
        <div className="animate-in" style={{ animationDelay: '100ms' }}>
          {/* Metrics Grid */}
          <div className="grid grid-cols-4 gap-3 mb-4">
            {[
              { label: 'Total Return', value: `${(activeResult.metrics.total_return * 100).toFixed(2)}%`, color: activeResult.metrics.total_return >= 0 ? 'var(--green)' : 'var(--red)' },
              { label: 'Sharpe Ratio', value: activeResult.metrics.sharpe_ratio.toFixed(2), color: 'var(--accent)' },
              { label: 'Max Drawdown', value: `${(activeResult.metrics.max_drawdown * 100).toFixed(2)}%`, color: 'var(--red)' },
              { label: 'Win Rate', value: `${(activeResult.metrics.win_rate * 100).toFixed(1)}%`, color: 'var(--yellow)' },
              { label: 'Profit Factor', value: activeResult.metrics.profit_factor.toFixed(2), color: 'var(--green)' },
              { label: 'Total Trades', value: activeResult.metrics.total_trades, color: 'var(--text-primary)' },
              { label: 'Annual Return', value: `${(activeResult.metrics.annual_return * 100).toFixed(2)}%`, color: activeResult.metrics.annual_return >= 0 ? 'var(--green)' : 'var(--red)' },
              { label: 'Volatility', value: `${((activeResult.metrics.volatility || 0) * 100).toFixed(2)}%`, color: 'var(--yellow)' },
            ].map((m, i) => (
              <div key={i} className="qt-card" style={{ padding: '14px 16px' }}>
                <div className="qt-label" style={{ marginBottom: 6 }}>{m.label}</div>
                <div style={{ fontFamily: 'var(--font-mono)', fontSize: 18, fontWeight: 600, color: m.color, letterSpacing: '-0.02em' }}>
                  {m.value}
                </div>
              </div>
            ))}
          </div>

          {/* Equity Curve */}
          {equityData.length > 0 && (
            <div className="qt-card mb-4" style={{ padding: '20px 20px 12px' }}>
              <div className="flex items-center gap-2 mb-4">
                <Target size={14} style={{ color: 'var(--accent)' }} />
                <span style={{ fontSize: 13, fontWeight: 600 }}>Equity Curve</span>
                <span style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: 'var(--text-muted)' }}>
                  {equityData.length} data points
                </span>
              </div>
              <ResponsiveContainer width="100%" height={260}>
                <AreaChart data={equityData}>
                  <defs>
                    <linearGradient id="eqGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="var(--accent)" stopOpacity={0.2} />
                      <stop offset="100%" stopColor="var(--accent)" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--border-subtle)" />
                  <XAxis dataKey="idx" stroke="var(--text-muted)" fontSize={9} tickLine={false} axisLine={false} />
                  <YAxis stroke="var(--text-muted)" fontSize={9} tickLine={false} axisLine={false}
                    tickFormatter={v => `$${(v/1000).toFixed(0)}k`} />
                  <Tooltip content={<CustomTooltip />} />
                  <Area type="monotone" dataKey="equity" stroke="var(--accent)" strokeWidth={1.5} fill="url(#eqGrad)" />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          )}

          {/* Trade Log */}
          {activeResult.trades?.length > 0 && (
            <div className="qt-card" style={{ padding: '20px' }}>
              <div className="flex items-center gap-2 mb-4">
                <Clock size={14} style={{ color: 'var(--accent)' }} />
                <span style={{ fontSize: 13, fontWeight: 600 }}>Trade Log</span>
                <span className="qt-badge" style={{ background: 'var(--accent-glow)', color: 'var(--accent)' }}>
                  {activeResult.trades.length}
                </span>
              </div>
              <div style={{ overflowX: 'auto' }}>
                <table className="qt-table">
                  <thead>
                    <tr>
                      <th>Entry</th><th>Exit</th>
                      <th style={{ textAlign: 'right' }}>Entry Price</th>
                      <th style={{ textAlign: 'right' }}>Exit Price</th>
                      <th style={{ textAlign: 'right' }}>PnL</th>
                      <th style={{ textAlign: 'right' }}>Return</th>
                      <th>Reason</th>
                    </tr>
                  </thead>
                  <tbody>
                    {activeResult.trades.map((t: any, i: number) => (
                      <tr key={i}>
                        <td style={{ fontFamily: 'var(--font-mono)' }}>{String(t.entry_date).slice(0, 10)}</td>
                        <td style={{ fontFamily: 'var(--font-mono)' }}>{String(t.exit_date).slice(0, 10)}</td>
                        <td style={{ textAlign: 'right', fontFamily: 'var(--font-mono)' }}>{t.entry_price}</td>
                        <td style={{ textAlign: 'right', fontFamily: 'var(--font-mono)' }}>{t.exit_price}</td>
                        <td style={{ textAlign: 'right', fontFamily: 'var(--font-mono)', fontWeight: 600, color: t.pnl >= 0 ? 'var(--green)' : 'var(--red)' }}>
                          {t.pnl >= 0 ? '+' : ''}{t.pnl}
                        </td>
                        <td style={{ textAlign: 'right', fontFamily: 'var(--font-mono)', color: t.return_pct >= 0 ? 'var(--green)' : 'var(--red)' }}>
                          {(t.return_pct * 100).toFixed(2)}%
                        </td>
                        <td>
                          <span className="qt-badge" style={{
                            background: t.exit_reason === 'stop_loss' ? 'var(--red-dim)' : 'var(--bg-elevated)',
                            color: t.exit_reason === 'stop_loss' ? 'var(--red)' : 'var(--text-secondary)',
                          }}>{t.exit_reason}</span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      )}

      {/* History */}
      {results.length > 0 && !activeResult && (
        <div className="qt-card animate-in" style={{ animationDelay: '100ms' }}>
          <div className="flex items-center gap-2 mb-4">
            <Clock size={14} style={{ color: 'var(--accent)' }} />
            <span style={{ fontSize: 13, fontWeight: 600 }}>History</span>
          </div>
          <table className="qt-table">
            <thead>
              <tr>
                <th>Symbol</th><th>TF</th>
                <th style={{ textAlign: 'right' }}>Return</th>
                <th style={{ textAlign: 'right' }}>Sharpe</th>
                <th style={{ textAlign: 'right' }}>Drawdown</th>
                <th style={{ textAlign: 'right' }}>Win Rate</th>
                <th style={{ textAlign: 'right' }}>Trades</th>
                <th>Date</th>
              </tr>
            </thead>
            <tbody>
              {results.map((r: any) => (
                <tr key={r.id}>
                  <td style={{ fontWeight: 600 }}>{r.symbol}</td>
                  <td><span className="qt-badge" style={{ background: 'var(--bg-elevated)', color: 'var(--text-secondary)' }}>{r.timeframe}</span></td>
                  <td style={{ textAlign: 'right', fontFamily: 'var(--font-mono)', fontWeight: 600, color: r.total_return >= 0 ? 'var(--green)' : 'var(--red)' }}>
                    {(r.total_return * 100).toFixed(2)}%
                  </td>
                  <td style={{ textAlign: 'right', fontFamily: 'var(--font-mono)' }}>{r.sharpe_ratio.toFixed(2)}</td>
                  <td style={{ textAlign: 'right', fontFamily: 'var(--font-mono)', color: 'var(--red)' }}>{(r.max_drawdown * 100).toFixed(2)}%</td>
                  <td style={{ textAlign: 'right', fontFamily: 'var(--font-mono)' }}>{(r.win_rate * 100).toFixed(1)}%</td>
                  <td style={{ textAlign: 'right', fontFamily: 'var(--font-mono)' }}>{r.total_trades}</td>
                  <td style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--text-muted)' }}>{r.created_at?.slice(0, 10)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
