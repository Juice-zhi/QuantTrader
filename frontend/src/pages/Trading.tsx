import { useEffect, useState } from 'react';
import { tradingApi } from '../services/api';
import { ArrowUpCircle, ArrowDownCircle, RefreshCw, Terminal, Wallet, Crosshair, Layers } from 'lucide-react';

export default function Trading() {
  const [portfolio, setPortfolio] = useState<any>(null);
  const [exchanges, setExchanges] = useState<any[]>([]);
  const [selectedExchange, setSelectedExchange] = useState('paper');
  const [orderForm, setOrderForm] = useState({ symbol: 'BTC/USDT', quantity: '0.1', price: '50000' });
  const [log, setLog] = useState<string[]>([]);

  const refresh = () => {
    tradingApi.portfolio(selectedExchange).then(setPortfolio).catch(() => {});
    tradingApi.exchanges().then(d => setExchanges(d.exchanges || [])).catch(() => {});
  };
  useEffect(refresh, [selectedExchange]);

  const setPrice = async () => {
    await tradingApi.setPrice(orderForm.symbol, Number(orderForm.price), selectedExchange);
    setLog(l => [`[PRICE] ${orderForm.symbol} = $${orderForm.price}`, ...l].slice(0, 30));
    refresh();
  };

  const execute = async (signal: number) => {
    const resp = await tradingApi.execute({
      exchange: selectedExchange, symbol: orderForm.symbol,
      signal, quantity: Number(orderForm.quantity),
    });
    const ts = new Date().toLocaleTimeString('en-US', { hour12: false });
    setLog(l => [
      `[${ts}] ${signal > 0 ? 'BUY' : 'SELL'} ${orderForm.quantity} ${orderForm.symbol} => ${resp.status} @ $${resp.filled_price?.toFixed(2) || 'N/A'}`,
      ...l
    ].slice(0, 30));
    refresh();
  };

  return (
    <div>
      {/* Header */}
      <div className="flex items-end justify-between mb-8 animate-in">
        <div>
          <div className="qt-label mb-2">Execution</div>
          <h1 style={{ fontFamily: 'var(--font-display)', fontSize: 28, fontWeight: 700, color: 'var(--text-bright)', letterSpacing: '-0.02em' }}>
            Trading Terminal
          </h1>
        </div>
        <div className="flex items-center gap-3">
          <select value={selectedExchange} onChange={e => setSelectedExchange(e.target.value)} className="qt-select">
            {exchanges.map(e => (
              <option key={e.name} value={e.name}>
                {e.name} {e.is_paper ? '(Paper)' : '(Live)'}
              </option>
            ))}
          </select>
          <button onClick={refresh} className="qt-btn qt-btn-ghost" style={{ padding: '9px 10px' }}>
            <RefreshCw size={14} />
          </button>
        </div>
      </div>

      <div className="grid grid-cols-3 gap-4 mb-6">
        {/* Account */}
        <div className="qt-card animate-in" style={{ animationDelay: '50ms' }}>
          <div className="flex items-center gap-2 mb-5">
            <Wallet size={14} style={{ color: 'var(--accent)' }} />
            <span className="qt-label">Account</span>
          </div>
          {portfolio && (
            <div>
              <div style={{ marginBottom: 16 }}>
                <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 4 }}>Total Equity</div>
                <div style={{ fontFamily: 'var(--font-mono)', fontSize: 24, fontWeight: 700, color: 'var(--text-bright)', letterSpacing: '-0.03em' }}>
                  ${portfolio.total_equity?.toLocaleString('en-US', { minimumFractionDigits: 2 })}
                </div>
              </div>
              <div className="glow-line mb-4" />
              <div className="grid grid-cols-2 gap-4">
                {[
                  { label: 'Cash', value: `$${portfolio.available_cash?.toFixed(2)}`, color: 'var(--text-primary)' },
                  { label: 'Positions', value: `$${portfolio.positions_value?.toFixed(2)}`, color: 'var(--text-primary)' },
                  { label: 'Realized PnL', value: `$${portfolio.realized_pnl?.toFixed(2)}`, color: portfolio.realized_pnl >= 0 ? 'var(--green)' : 'var(--red)' },
                  { label: 'Unrealized PnL', value: `$${portfolio.unrealized_pnl?.toFixed(2)}`, color: portfolio.unrealized_pnl >= 0 ? 'var(--green)' : 'var(--red)' },
                ].map((item, i) => (
                  <div key={i}>
                    <div style={{ fontSize: 10, color: 'var(--text-muted)', marginBottom: 3, fontFamily: 'var(--font-mono)', letterSpacing: '0.08em', textTransform: 'uppercase' }}>{item.label}</div>
                    <div style={{ fontFamily: 'var(--font-mono)', fontSize: 13, fontWeight: 500, color: item.color }}>{item.value}</div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Order Panel */}
        <div className="qt-card animate-in" style={{ animationDelay: '100ms' }}>
          <div className="flex items-center gap-2 mb-5">
            <Crosshair size={14} style={{ color: 'var(--accent)' }} />
            <span className="qt-label">Order</span>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div>
              <label className="qt-label" style={{ display: 'block', marginBottom: 4 }}>Symbol</label>
              <input value={orderForm.symbol} onChange={e => setOrderForm({ ...orderForm, symbol: e.target.value })}
                className="qt-input" />
            </div>
            <div>
              <label className="qt-label" style={{ display: 'block', marginBottom: 4 }}>Quantity</label>
              <input value={orderForm.quantity} onChange={e => setOrderForm({ ...orderForm, quantity: e.target.value })}
                type="number" className="qt-input" />
            </div>
            <div>
              <label className="qt-label" style={{ display: 'block', marginBottom: 4 }}>Price (Paper)</label>
              <div className="flex gap-2">
                <input value={orderForm.price} onChange={e => setOrderForm({ ...orderForm, price: e.target.value })}
                  type="number" className="qt-input" style={{ flex: 1 }} />
                <button onClick={setPrice} className="qt-btn qt-btn-ghost" style={{ whiteSpace: 'nowrap' }}>Set</button>
              </div>
            </div>
            <div className="flex gap-2" style={{ marginTop: 4 }}>
              <button onClick={() => execute(1)}
                className="qt-btn flex-1"
                style={{ background: 'var(--green)', color: '#0c0d12', fontWeight: 600, padding: '10px 0' }}>
                <ArrowUpCircle size={15} /> BUY
              </button>
              <button onClick={() => execute(-1)}
                className="qt-btn flex-1"
                style={{ background: 'var(--red)', color: '#fff', fontWeight: 600, padding: '10px 0' }}>
                <ArrowDownCircle size={15} /> SELL
              </button>
            </div>
          </div>
        </div>

        {/* Activity Log */}
        <div className="qt-card animate-in" style={{ animationDelay: '150ms' }}>
          <div className="flex items-center gap-2 mb-5">
            <Terminal size={14} style={{ color: 'var(--accent)' }} />
            <span className="qt-label">Activity Log</span>
          </div>
          <div style={{
            maxHeight: 280, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 3,
          }}>
            {log.length === 0 && (
              <div style={{ textAlign: 'center', padding: '24px 0' }}>
                <Terminal size={20} style={{ color: 'var(--text-muted)', margin: '0 auto 8px' }} />
                <p style={{ fontSize: 11, color: 'var(--text-muted)' }}>Awaiting orders...</p>
              </div>
            )}
            {log.map((l, i) => (
              <div key={i} style={{
                fontFamily: 'var(--font-mono)', fontSize: 11, lineHeight: 1.6,
                padding: '5px 10px', borderRadius: 'var(--radius-sm)',
                background: 'var(--bg-primary)',
                color: l.includes('BUY') ? 'var(--green)' : l.includes('SELL') ? 'var(--red)' : 'var(--text-secondary)',
                borderLeft: `2px solid ${l.includes('BUY') ? 'var(--green)' : l.includes('SELL') ? 'var(--red)' : 'var(--border)'}`,
              }}>
                {l}
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Positions */}
      <div className="qt-card animate-in" style={{ animationDelay: '200ms' }}>
        <div className="flex items-center gap-2 mb-4">
          <Layers size={14} style={{ color: 'var(--accent)' }} />
          <span style={{ fontSize: 13, fontWeight: 600 }}>Open Positions</span>
        </div>
        {(!portfolio?.positions || portfolio.positions.length === 0) ? (
          <div style={{ textAlign: 'center', padding: '32px 0' }}>
            <p style={{ fontSize: 12, color: 'var(--text-muted)' }}>No open positions</p>
          </div>
        ) : (
          <table className="qt-table">
            <thead>
              <tr>
                <th>Symbol</th><th>Side</th>
                <th style={{ textAlign: 'right' }}>Quantity</th>
                <th style={{ textAlign: 'right' }}>Entry Price</th>
                <th style={{ textAlign: 'right' }}>Current Price</th>
                <th style={{ textAlign: 'right' }}>Unrealized PnL</th>
              </tr>
            </thead>
            <tbody>
              {portfolio.positions.map((p: any, i: number) => (
                <tr key={i}>
                  <td style={{ fontWeight: 600 }}>{p.symbol}</td>
                  <td>
                    <span className="qt-badge" style={{
                      background: p.side === 'long' ? 'var(--green-dim)' : 'var(--red-dim)',
                      color: p.side === 'long' ? 'var(--green)' : 'var(--red)',
                    }}>{p.side.toUpperCase()}</span>
                  </td>
                  <td style={{ textAlign: 'right', fontFamily: 'var(--font-mono)' }}>{p.quantity}</td>
                  <td style={{ textAlign: 'right', fontFamily: 'var(--font-mono)' }}>${p.entry_price.toFixed(2)}</td>
                  <td style={{ textAlign: 'right', fontFamily: 'var(--font-mono)' }}>${p.current_price.toFixed(2)}</td>
                  <td style={{ textAlign: 'right', fontFamily: 'var(--font-mono)', fontWeight: 600, color: p.unrealized_pnl >= 0 ? 'var(--green)' : 'var(--red)' }}>
                    {p.unrealized_pnl >= 0 ? '+' : ''}${p.unrealized_pnl.toFixed(2)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
