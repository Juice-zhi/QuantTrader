import { useState, useEffect } from 'react';
import { backtestApi, strategiesApi } from '../services/api';
import { XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Area, AreaChart } from 'recharts';
import { Play, Loader2, Clock, Target, AlertTriangle, Calendar } from 'lucide-react';

const MARKET_LABELS: Record<string, string> = {
  crypto: '🪙 Crypto',
  us_stock: '🇺🇸 US Stocks',
  hk_stock: '🇭🇰 HK Stocks',
  cn_stock: '🇨🇳 A-Shares',
};

// 快捷时间范围
const DATE_PRESETS = [
  { label: '近6月', months: 6 },
  { label: '近1年', months: 12 },
  { label: '近2年', months: 24 },
  { label: '近3年', months: 36 },
  { label: '近5年', months: 60 },
  { label: '全部', months: 0 },
];

function getDateBefore(months: number): string {
  const d = new Date();
  d.setMonth(d.getMonth() - months);
  return d.toISOString().slice(0, 10);
}

function todayStr(): string {
  return new Date().toISOString().slice(0, 10);
}

export default function Backtest() {
  const [types, setTypes] = useState<any[]>([]);
  const [results, setResults] = useState<any[]>([]);
  const [symbols, setSymbols] = useState<Record<string, any[]>>({});
  const [activeResult, setActiveResult] = useState<any>(null);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activePreset, setActivePreset] = useState('全部');
  const [form, setForm] = useState({
    strategy_type: '', symbol: 'BTC/USDT', timeframe: '1d',
    exchange: 'binance', initial_capital: 100000, params: '{}',
    start_date: '', end_date: '',
  });

  useEffect(() => {
    strategiesApi.types().then(d => setTypes(d.strategies || []));
    backtestApi.results().then(d => setResults(d.results || [])).catch(() => {});
    backtestApi.symbols().then(setSymbols).catch(() => {});
  }, []);

  const handleSymbolSelect = (sym: any) => {
    setForm(f => ({ ...f, symbol: sym.symbol, exchange: sym.exchange }));
  };

  const runBacktest = async () => {
    setRunning(true);
    setError(null);
    setActiveResult(null);
    try {
      const body: any = {
        ...form,
        initial_capital: Number(form.initial_capital),
        params: JSON.parse(form.params || '{}'),
      };
      // 只在有值时发送日期
      if (form.start_date) body.start_date = form.start_date;
      else delete body.start_date;
      if (form.end_date) body.end_date = form.end_date;
      else delete body.end_date;

      const result = await backtestApi.run(body);
      if (result.error) {
        setError(result.error);
      } else {
        setActiveResult(result);
        backtestApi.results().then(d => setResults(d.results || [])).catch(() => {});
      }
    } catch (e: any) {
      setError(e.message || 'Unknown error');
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

      {/* Symbol Picker */}
      <div className="qt-card animate-in mb-4" style={{ animationDelay: '30ms', padding: '16px 20px' }}>
        <div className="qt-label mb-3">Select Symbol</div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          {Object.entries(symbols).map(([market, syms]) => (
            <div key={market}>
              <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 6 }}>
                {MARKET_LABELS[market] || market}
              </div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 5 }}>
                {(syms as any[]).map((s: any) => {
                  const isSelected = form.symbol === s.symbol && form.exchange === s.exchange;
                  return (
                    <button
                      key={s.symbol}
                      onClick={() => handleSymbolSelect(s)}
                      className="qt-btn"
                      style={{
                        padding: '5px 10px', fontSize: 11,
                        fontFamily: 'var(--font-mono)',
                        background: isSelected ? 'var(--accent)' : 'var(--bg-primary)',
                        color: isSelected ? '#0c0d12' : 'var(--text-secondary)',
                        border: `1px solid ${isSelected ? 'var(--accent)' : 'var(--border)'}`,
                        fontWeight: isSelected ? 600 : 400,
                      }}
                    >
                      {s.symbol}
                      <span style={{ opacity: 0.6, marginLeft: 4, fontSize: 9 }}>{s.name}</span>
                    </button>
                  );
                })}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Config Form */}
      <div className="qt-card animate-in mb-6" style={{ animationDelay: '50ms' }}>
        <div className="grid grid-cols-3 gap-4 mb-4">
          <div>
            <label className="qt-label" style={{ display: 'block', marginBottom: 6 }}>Strategy</label>
            <select value={form.strategy_type} onChange={e => {
              const t = types.find(t => (t.class_name || t.name) === e.target.value);
              setForm({ ...form, strategy_type: e.target.value, params: JSON.stringify(t?.params || {}, null, 2) });
            }} className="qt-select w-full">
              <option value="">Select strategy...</option>
              {types.map(t => <option key={t.class_name || t.name} value={t.class_name || t.name}>{t.name}</option>)}
            </select>
          </div>
          <div>
            <label className="qt-label" style={{ display: 'block', marginBottom: 6 }}>Symbol</label>
            <div className="qt-input" style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '7px 14px' }}>
              <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 600, color: 'var(--accent)' }}>{form.symbol}</span>
              <span style={{ fontSize: 10, color: 'var(--text-muted)' }}>@ {form.exchange}</span>
            </div>
          </div>
          <div>
            <label className="qt-label" style={{ display: 'block', marginBottom: 6 }}>Timeframe</label>
            <select value={form.timeframe} onChange={e => setForm({ ...form, timeframe: e.target.value })} className="qt-select w-full">
              {['1m','5m','15m','1h','4h','1d'].map(tf => <option key={tf} value={tf}>{tf}</option>)}
            </select>
          </div>
        </div>

        {/* Date Range */}
        <div className="mb-4">
          <div className="flex items-center gap-2 mb-2">
            <Calendar size={12} style={{ color: 'var(--accent)' }} />
            <label className="qt-label">Date Range</label>
          </div>
          <div className="flex items-center gap-3">
            {/* Preset buttons */}
            <div className="flex gap-1.5">
              {DATE_PRESETS.map(p => (
                <button
                  key={p.label}
                  onClick={() => {
                    setActivePreset(p.label);
                    if (p.months === 0) {
                      setForm(f => ({ ...f, start_date: '', end_date: '' }));
                    } else {
                      setForm(f => ({ ...f, start_date: getDateBefore(p.months), end_date: todayStr() }));
                    }
                  }}
                  className="qt-btn"
                  style={{
                    padding: '4px 10px', fontSize: 11,
                    background: activePreset === p.label ? 'var(--accent)' : 'var(--bg-primary)',
                    color: activePreset === p.label ? '#0c0d12' : 'var(--text-secondary)',
                    border: `1px solid ${activePreset === p.label ? 'var(--accent)' : 'var(--border)'}`,
                    fontWeight: activePreset === p.label ? 600 : 400,
                  }}
                >
                  {p.label}
                </button>
              ))}
            </div>
            <div style={{ width: 1, height: 20, background: 'var(--border)' }} />
            {/* Custom date inputs */}
            <div className="flex items-center gap-2">
              <input
                type="date"
                value={form.start_date}
                onChange={e => { setForm(f => ({ ...f, start_date: e.target.value })); setActivePreset(''); }}
                className="qt-input"
                style={{ width: 150, padding: '4px 8px', fontSize: 12, fontFamily: 'var(--font-mono)' }}
                placeholder="Start"
              />
              <span style={{ color: 'var(--text-muted)', fontSize: 11 }}>→</span>
              <input
                type="date"
                value={form.end_date}
                onChange={e => { setForm(f => ({ ...f, end_date: e.target.value })); setActivePreset(''); }}
                className="qt-input"
                style={{ width: 150, padding: '4px 8px', fontSize: 12, fontFamily: 'var(--font-mono)' }}
                placeholder="End"
              />
            </div>
            {form.start_date && (
              <span style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: 'var(--text-muted)' }}>
                {form.start_date} ~ {form.end_date || 'now'}
              </span>
            )}
            {!form.start_date && (
              <span style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: 'var(--text-muted)' }}>
                All available data
              </span>
            )}
          </div>
        </div>

        <div className="grid grid-cols-3 gap-4 mb-4">
          <div>
            <label className="qt-label" style={{ display: 'block', marginBottom: 6 }}>Exchange</label>
            <select value={form.exchange} onChange={e => setForm({ ...form, exchange: e.target.value })} className="qt-select w-full">
              <option value="binance">Binance</option>
              <option value="okx">OKX</option>
              <option value="nasdaq">NASDAQ</option>
              <option value="nyse">NYSE</option>
              <option value="hkex">HKEX</option>
              <option value="sse">SSE (上交所)</option>
              <option value="szse">SZSE (深交所)</option>
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

      {/* Error display */}
      {error && (
        <div className="qt-card animate-in mb-6" style={{
          borderColor: 'var(--red)', borderLeft: '3px solid var(--red)',
          padding: '14px 18px', display: 'flex', alignItems: 'flex-start', gap: 10,
        }}>
          <AlertTriangle size={16} style={{ color: 'var(--red)', marginTop: 2, flexShrink: 0 }} />
          <div>
            <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--red)', marginBottom: 4 }}>Backtest Error</div>
            <div style={{ fontSize: 12, color: 'var(--text-secondary)', fontFamily: 'var(--font-mono)', lineHeight: 1.5, wordBreak: 'break-all' }}>
              {error}
            </div>
          </div>
        </div>
      )}

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
                  {equityData.length} points | {form.symbol}
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
