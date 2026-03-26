import { useEffect, useState } from 'react';
import { tradingApi } from '../services/api';
import { ArrowUpCircle, ArrowDownCircle, RefreshCw } from 'lucide-react';

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
    setLog(l => [`Set ${orderForm.symbol} = $${orderForm.price}`, ...l].slice(0, 20));
    refresh();
  };

  const execute = async (signal: number) => {
    const resp = await tradingApi.execute({
      exchange: selectedExchange, symbol: orderForm.symbol,
      signal, quantity: Number(orderForm.quantity),
    });
    setLog(l => [
      `${signal > 0 ? 'BUY' : 'SELL'} ${orderForm.quantity} ${orderForm.symbol} -> ${resp.status} @ $${resp.filled_price || 'N/A'}`,
      ...l
    ].slice(0, 20));
    refresh();
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-xl font-bold">Trading Terminal</h2>
        <div className="flex items-center gap-3">
          <select value={selectedExchange} onChange={e => setSelectedExchange(e.target.value)}
            className="px-3 py-2 rounded-lg text-sm border"
            style={{ borderColor: 'var(--border)', background: 'var(--bg-secondary)', color: 'var(--text-primary)' }}>
            {exchanges.map(e => (
              <option key={e.name} value={e.name}>
                {e.name} {e.is_paper ? '(Paper)' : '(Live)'}
              </option>
            ))}
          </select>
          <button onClick={refresh} className="p-2 rounded-lg" style={{ background: 'var(--bg-card)' }}>
            <RefreshCw size={16} />
          </button>
        </div>
      </div>

      <div className="grid grid-cols-3 gap-4 mb-6">
        {/* Account */}
        <div className="rounded-xl p-5 border" style={{ background: 'var(--bg-card)', borderColor: 'var(--border)' }}>
          <h3 className="text-xs font-semibold mb-4 uppercase" style={{ color: 'var(--text-secondary)' }}>Account</h3>
          {portfolio && (
            <div className="space-y-3">
              <div>
                <div className="text-xs" style={{ color: 'var(--text-secondary)' }}>Total Equity</div>
                <div className="text-xl font-bold">${portfolio.total_equity?.toFixed(2)}</div>
              </div>
              <div className="flex justify-between">
                <div>
                  <div className="text-xs" style={{ color: 'var(--text-secondary)' }}>Cash</div>
                  <div className="text-sm font-medium">${portfolio.available_cash?.toFixed(2)}</div>
                </div>
                <div>
                  <div className="text-xs" style={{ color: 'var(--text-secondary)' }}>Positions</div>
                  <div className="text-sm font-medium">${portfolio.positions_value?.toFixed(2)}</div>
                </div>
              </div>
              <div className="flex justify-between">
                <div>
                  <div className="text-xs" style={{ color: 'var(--text-secondary)' }}>Realized PnL</div>
                  <div className="text-sm font-medium" style={{ color: portfolio.realized_pnl >= 0 ? 'var(--green)' : 'var(--red)' }}>
                    ${portfolio.realized_pnl?.toFixed(2)}
                  </div>
                </div>
                <div>
                  <div className="text-xs" style={{ color: 'var(--text-secondary)' }}>Unrealized PnL</div>
                  <div className="text-sm font-medium" style={{ color: portfolio.unrealized_pnl >= 0 ? 'var(--green)' : 'var(--red)' }}>
                    ${portfolio.unrealized_pnl?.toFixed(2)}
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Order Panel */}
        <div className="rounded-xl p-5 border" style={{ background: 'var(--bg-card)', borderColor: 'var(--border)' }}>
          <h3 className="text-xs font-semibold mb-4 uppercase" style={{ color: 'var(--text-secondary)' }}>Order</h3>
          <div className="space-y-3">
            <input value={orderForm.symbol} onChange={e => setOrderForm({ ...orderForm, symbol: e.target.value })}
              placeholder="Symbol" className="w-full px-3 py-2 rounded-lg text-sm border bg-transparent"
              style={{ borderColor: 'var(--border)', color: 'var(--text-primary)' }} />
            <input value={orderForm.quantity} onChange={e => setOrderForm({ ...orderForm, quantity: e.target.value })}
              placeholder="Quantity" type="number" className="w-full px-3 py-2 rounded-lg text-sm border bg-transparent"
              style={{ borderColor: 'var(--border)', color: 'var(--text-primary)' }} />
            <div className="flex gap-2">
              <input value={orderForm.price} onChange={e => setOrderForm({ ...orderForm, price: e.target.value })}
                placeholder="Price (Paper)" type="number" className="flex-1 px-3 py-2 rounded-lg text-sm border bg-transparent"
                style={{ borderColor: 'var(--border)', color: 'var(--text-primary)' }} />
              <button onClick={setPrice} className="px-3 py-2 rounded-lg text-xs" style={{ background: 'var(--bg-secondary)' }}>
                Set
              </button>
            </div>
            <div className="flex gap-2">
              <button onClick={() => execute(1)}
                className="flex-1 flex items-center justify-center gap-1 py-2.5 rounded-lg text-sm font-medium text-white bg-green-600 hover:bg-green-700">
                <ArrowUpCircle size={16} /> BUY
              </button>
              <button onClick={() => execute(-1)}
                className="flex-1 flex items-center justify-center gap-1 py-2.5 rounded-lg text-sm font-medium text-white bg-red-600 hover:bg-red-700">
                <ArrowDownCircle size={16} /> SELL
              </button>
            </div>
          </div>
        </div>

        {/* Activity Log */}
        <div className="rounded-xl p-5 border" style={{ background: 'var(--bg-card)', borderColor: 'var(--border)' }}>
          <h3 className="text-xs font-semibold mb-4 uppercase" style={{ color: 'var(--text-secondary)' }}>Activity Log</h3>
          <div className="space-y-1.5 max-h-64 overflow-y-auto">
            {log.length === 0 && (
              <p className="text-xs" style={{ color: 'var(--text-secondary)' }}>No activity yet</p>
            )}
            {log.map((l, i) => (
              <div key={i} className="text-xs font-mono py-1 px-2 rounded" style={{ background: 'var(--bg-secondary)' }}>
                {l}
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Positions */}
      <div className="rounded-xl p-5 border" style={{ background: 'var(--bg-card)', borderColor: 'var(--border)' }}>
        <h3 className="text-sm font-semibold mb-4">Open Positions</h3>
        {(!portfolio?.positions || portfolio.positions.length === 0) ? (
          <p className="text-sm text-center py-6" style={{ color: 'var(--text-secondary)' }}>No open positions</p>
        ) : (
          <table className="w-full text-xs">
            <thead>
              <tr style={{ color: 'var(--text-secondary)' }}>
                <th className="text-left p-2">Symbol</th>
                <th className="text-left p-2">Side</th>
                <th className="text-right p-2">Quantity</th>
                <th className="text-right p-2">Entry Price</th>
                <th className="text-right p-2">Current Price</th>
                <th className="text-right p-2">Unrealized PnL</th>
              </tr>
            </thead>
            <tbody>
              {portfolio.positions.map((p: any, i: number) => (
                <tr key={i} className="border-t" style={{ borderColor: 'var(--border)' }}>
                  <td className="p-2 font-medium">{p.symbol}</td>
                  <td className="p-2"><span className={p.side === 'long' ? 'text-green-400' : 'text-red-400'}>{p.side}</span></td>
                  <td className="p-2 text-right">{p.quantity}</td>
                  <td className="p-2 text-right">${p.entry_price.toFixed(2)}</td>
                  <td className="p-2 text-right">${p.current_price.toFixed(2)}</td>
                  <td className="p-2 text-right font-medium" style={{ color: p.unrealized_pnl >= 0 ? 'var(--green)' : 'var(--red)' }}>
                    ${p.unrealized_pnl.toFixed(2)}
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
