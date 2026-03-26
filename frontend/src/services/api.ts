// Electron 桌面应用模式下直接连后端; Web模式下通过 Vite proxy
const isElectron = typeof window !== 'undefined' && !!(window as any).electronAPI;
const BASE = isElectron ? 'http://127.0.0.1:8000' : '';

async function request<T>(url: string, options?: RequestInit): Promise<T> {
  const resp = await fetch(`${BASE}${url}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });
  return resp.json();
}

// ── Data API ──
export const dataApi = {
  getOhlcv: (symbol: string, timeframe = '1d', exchange = 'binance') =>
    request<any>(`/api/data/ohlcv?symbol=${encodeURIComponent(symbol)}&timeframe=${timeframe}&exchange=${exchange}`),
  getSymbols: (marketType?: string) =>
    request<any>(`/api/data/symbols${marketType ? `?market_type=${marketType}` : ''}`),
};

// ── Factors API ──
export const factorsApi = {
  list: (category?: string) =>
    request<any>(`/api/factors/list${category ? `?category=${category}` : ''}`),
  categories: () => request<any>('/api/factors/categories'),
  compute: (body: any) =>
    request<any>('/api/factors/compute', { method: 'POST', body: JSON.stringify(body) }),
  ic: (body: any) =>
    request<any>('/api/factors/ic', { method: 'POST', body: JSON.stringify(body) }),
};

// ── Strategies API ──
export const strategiesApi = {
  types: () => request<any>('/api/strategies/types'),
  list: () => request<any>('/api/strategies/'),
  create: (body: any) =>
    request<any>('/api/strategies/', { method: 'POST', body: JSON.stringify(body) }),
  update: (id: number, body: any) =>
    request<any>(`/api/strategies/${id}`, { method: 'PUT', body: JSON.stringify(body) }),
  delete: (id: number) =>
    request<any>(`/api/strategies/${id}`, { method: 'DELETE' }),
};

// ── Backtest API ──
export const backtestApi = {
  run: (body: any) =>
    request<any>('/api/backtest/run', { method: 'POST', body: JSON.stringify(body) }),
  results: () => request<any>('/api/backtest/results'),
  detail: (id: number) => request<any>(`/api/backtest/results/${id}`),
};

// ── Trading API ──
export const tradingApi = {
  exchanges: () => request<any>('/api/trading/exchanges'),
  setPrice: (symbol: string, price: number, exchange = 'paper') =>
    request<any>('/api/trading/set-price', {
      method: 'POST', body: JSON.stringify({ symbol, price, exchange }),
    }),
  execute: (body: any) =>
    request<any>('/api/trading/execute', { method: 'POST', body: JSON.stringify(body) }),
  portfolio: (exchange = 'paper') =>
    request<any>(`/api/trading/portfolio?exchange=${exchange}`),
  activeStrategies: () => request<any>('/api/trading/active-strategies'),
};
