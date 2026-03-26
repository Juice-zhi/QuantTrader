import { useState, useEffect } from 'react';
import { backtestApi, strategiesApi } from '../services/api';
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts';
import { Play } from 'lucide-react';

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

  return (
    <div>
      <h2 className="text-xl font-bold mb-6">Backtest Engine</h2>

      {/* Config Form */}
      <div className="rounded-xl p-5 border mb-6" style={{ background: 'var(--bg-card)', borderColor: 'var(--border)' }}>
        <div className="grid grid-cols-3 gap-4 mb-4">
          <select value={form.strategy_type} onChange={e => {
            const t = types.find(t => t.name === e.target.value);
            setForm({ ...form, strategy_type: e.target.value, params: JSON.stringify(t?.params || {}, null, 2) });
          }}
            className="px-3 py-2 rounded-lg text-sm border"
            style={{ borderColor: 'var(--border)', background: 'var(--bg-secondary)', color: 'var(--text-primary)' }}>
            <option value="">Select Strategy...</option>
            {types.map(t => <option key={t.name} value={t.name}>{t.name}</option>)}
          </select>
          <input value={form.symbol} onChange={e => setForm({ ...form, symbol: e.target.value })}
            placeholder="Symbol (e.g. BTC/USDT)"
            className="px-3 py-2 rounded-lg text-sm border bg-transparent"
            style={{ borderColor: 'var(--border)', color: 'var(--text-primary)' }} />
          <select value={form.timeframe} onChange={e => setForm({ ...form, timeframe: e.target.value })}
            className="px-3 py-2 rounded-lg text-sm border"
            style={{ borderColor: 'var(--border)', background: 'var(--bg-secondary)', color: 'var(--text-primary)' }}>
            {['1m','5m','15m','1h','4h','1d'].map(tf => <option key={tf} value={tf}>{tf}</option>)}
          </select>
        </div>
        <div className="grid grid-cols-3 gap-4 mb-4">
          <select value={form.exchange} onChange={e => setForm({ ...form, exchange: e.target.value })}
            className="px-3 py-2 rounded-lg text-sm border"
            style={{ borderColor: 'var(--border)', background: 'var(--bg-secondary)', color: 'var(--text-primary)' }}>
            <option value="binance">Binance</option>
            <option value="okx">OKX</option>
            <option value="nasdaq">NASDAQ</option>
          </select>
          <input type="number" value={form.initial_capital}
            onChange={e => setForm({ ...form, initial_capital: +e.target.value })}
            placeholder="Initial Capital"
            className="px-3 py-2 rounded-lg text-sm border bg-transparent"
            style={{ borderColor: 'var(--border)', color: 'var(--text-primary)' }} />
          <button onClick={runBacktest} disabled={running || !form.strategy_type}
            className="flex items-center justify-center gap-2 px-4 py-2 rounded-lg text-sm font-medium text-white disabled:opacity-50"
            style={{ background: 'var(--accent)' }}>
            <Play size={16} /> {running ? 'Running...' : 'Run Backtest'}
          </button>
        </div>
        <textarea value={form.params} onChange={e => setForm({ ...form, params: e.target.value })}
          rows={3} className="w-full px-3 py-2 rounded-lg text-sm border font-mono bg-transparent"
          style={{ borderColor: 'var(--border)', color: 'var(--text-primary)' }}
          placeholder="Strategy parameters (JSON)" />
      </div>

      {/* Results */}
      {activeResult && (
        <div className="space-y-4 mb-8">
          {/* Metrics */}
          <div className="grid grid-cols-4 gap-3">
            {[
              { label: 'Total Return', value: `${(activeResult.metrics.total_return * 100).toFixed(2)}%`, color: activeResult.metrics.total_return >= 0 ? 'var(--green)' : 'var(--red)' },
              { label: 'Sharpe Ratio', value: activeResult.metrics.sharpe_ratio.toFixed(2), color: 'var(--accent)' },
              { label: 'Max Drawdown', value: `${(activeResult.metrics.max_drawdown * 100).toFixed(2)}%`, color: 'var(--red)' },
              { label: 'Win Rate', value: `${(activeResult.metrics.win_rate * 100).toFixed(1)}%`, color: 'var(--yellow)' },
              { label: 'Profit Factor', value: activeResult.metrics.profit_factor.toFixed(2), color: 'var(--green)' },
              { label: 'Total Trades', value: activeResult.metrics.total_trades, color: 'var(--accent)' },
              { label: 'Annual Return', value: `${(activeResult.metrics.annual_return * 100).toFixed(2)}%`, color: 'var(--green)' },
              { label: 'Volatility', value: `${((activeResult.metrics.volatility || 0) * 100).toFixed(2)}%`, color: 'var(--yellow)' },
            ].map((m, i) => (
              <div key={i} className="rounded-lg p-3 border" style={{ background: 'var(--bg-card)', borderColor: 'var(--border)' }}>
                <div className="text-xs" style={{ color: 'var(--text-secondary)' }}>{m.label}</div>
                <div className="text-lg font-bold" style={{ color: m.color }}>{m.value}</div>
              </div>
            ))}
          </div>

          {/* Equity Curve */}
          {equityData.length > 0 && (
            <div className="rounded-xl p-5 border" style={{ background: 'var(--bg-card)', borderColor: 'var(--border)' }}>
              <h3 className="text-sm font-semibold mb-4">Equity Curve</h3>
              <ResponsiveContainer width="100%" height={300}>
                <LineChart data={equityData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                  <XAxis dataKey="idx" stroke="var(--text-secondary)" fontSize={10} />
                  <YAxis stroke="var(--text-secondary)" fontSize={10} />
                  <Tooltip contentStyle={{ background: 'var(--bg-card)', border: '1px solid var(--border)', borderRadius: 8, color: 'var(--text-primary)' }} />
                  <Line type="monotone" dataKey="equity" stroke="var(--accent)" strokeWidth={2} dot={false} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          )}

          {/* Trade Log */}
          {activeResult.trades?.length > 0 && (
            <div className="rounded-xl p-5 border" style={{ background: 'var(--bg-card)', borderColor: 'var(--border)' }}>
              <h3 className="text-sm font-semibold mb-4">Trade Log ({activeResult.trades.length} trades)</h3>
              <div className="overflow-x-auto">
                <table className="w-full text-xs">
                  <thead>
                    <tr style={{ color: 'var(--text-secondary)' }}>
                      <th className="text-left p-2">Entry</th>
                      <th className="text-left p-2">Exit</th>
                      <th className="text-right p-2">Entry Price</th>
                      <th className="text-right p-2">Exit Price</th>
                      <th className="text-right p-2">PnL</th>
                      <th className="text-right p-2">Return</th>
                      <th className="text-left p-2">Reason</th>
                    </tr>
                  </thead>
                  <tbody>
                    {activeResult.trades.map((t: any, i: number) => (
                      <tr key={i} className="border-t" style={{ borderColor: 'var(--border)' }}>
                        <td className="p-2">{String(t.entry_date).slice(0, 10)}</td>
                        <td className="p-2">{String(t.exit_date).slice(0, 10)}</td>
                        <td className="p-2 text-right">{t.entry_price}</td>
                        <td className="p-2 text-right">{t.exit_price}</td>
                        <td className="p-2 text-right font-medium" style={{ color: t.pnl >= 0 ? 'var(--green)' : 'var(--red)' }}>
                          {t.pnl >= 0 ? '+' : ''}{t.pnl}
                        </td>
                        <td className="p-2 text-right" style={{ color: t.return_pct >= 0 ? 'var(--green)' : 'var(--red)' }}>
                          {(t.return_pct * 100).toFixed(2)}%
                        </td>
                        <td className="p-2">{t.exit_reason}</td>
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
      {results.length > 0 && (
        <div className="rounded-xl p-5 border" style={{ background: 'var(--bg-card)', borderColor: 'var(--border)' }}>
          <h3 className="text-sm font-semibold mb-4">Backtest History</h3>
          <table className="w-full text-xs">
            <thead>
              <tr style={{ color: 'var(--text-secondary)' }}>
                <th className="text-left p-2">Symbol</th>
                <th className="text-left p-2">TF</th>
                <th className="text-right p-2">Return</th>
                <th className="text-right p-2">Sharpe</th>
                <th className="text-right p-2">Drawdown</th>
                <th className="text-right p-2">Win Rate</th>
                <th className="text-right p-2">Trades</th>
                <th className="text-left p-2">Date</th>
              </tr>
            </thead>
            <tbody>
              {results.map((r: any) => (
                <tr key={r.id} className="border-t" style={{ borderColor: 'var(--border)' }}>
                  <td className="p-2">{r.symbol}</td>
                  <td className="p-2">{r.timeframe}</td>
                  <td className="p-2 text-right" style={{ color: r.total_return >= 0 ? 'var(--green)' : 'var(--red)' }}>
                    {(r.total_return * 100).toFixed(2)}%
                  </td>
                  <td className="p-2 text-right">{r.sharpe_ratio.toFixed(2)}</td>
                  <td className="p-2 text-right" style={{ color: 'var(--red)' }}>{(r.max_drawdown * 100).toFixed(2)}%</td>
                  <td className="p-2 text-right">{(r.win_rate * 100).toFixed(1)}%</td>
                  <td className="p-2 text-right">{r.total_trades}</td>
                  <td className="p-2">{r.created_at?.slice(0, 10)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
