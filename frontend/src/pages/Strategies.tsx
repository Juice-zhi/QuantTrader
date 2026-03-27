import { useEffect, useState } from 'react';
import { strategiesApi } from '../services/api';
import { Play, Square, Plus, Trash2, X, Cpu } from 'lucide-react';

export default function Strategies() {
  const [types, setTypes] = useState<any[]>([]);
  const [strategies, setStrategies] = useState<any[]>([]);
  const [showCreate, setShowCreate] = useState(false);
  const [form, setForm] = useState({ name: '', strategy_type: '', exchange: 'paper', params: '{}' });

  const load = () => {
    strategiesApi.types().then(d => setTypes(d.strategies || []));
    strategiesApi.list().then(d => setStrategies(d.strategies || []));
  };
  useEffect(load, []);

  const create = async () => {
    await strategiesApi.create({ ...form, params: JSON.parse(form.params || '{}') });
    setShowCreate(false);
    setForm({ name: '', strategy_type: '', exchange: 'paper', params: '{}' });
    load();
  };

  const toggle = async (s: any) => {
    await strategiesApi.update(s.id, { is_enabled: !s.is_enabled });
    load();
  };

  const remove = async (id: number) => {
    await strategiesApi.delete(id);
    load();
  };

  return (
    <div>
      {/* Header */}
      <div className="flex items-end justify-between mb-8 animate-in">
        <div>
          <div className="qt-label mb-2">Control Center</div>
          <h1 style={{ fontFamily: 'var(--font-display)', fontSize: 28, fontWeight: 700, color: 'var(--text-bright)', letterSpacing: '-0.02em' }}>
            Strategies
          </h1>
        </div>
        <button onClick={() => setShowCreate(!showCreate)} className="qt-btn qt-btn-accent">
          {showCreate ? <X size={15} /> : <Plus size={15} />}
          {showCreate ? 'Cancel' : 'New Strategy'}
        </button>
      </div>

      {/* Create Form */}
      {showCreate && (
        <div className="qt-card animate-in mb-6" style={{ border: '1px solid var(--accent-dim)' }}>
          <div className="flex items-center gap-2 mb-5">
            <Plus size={14} style={{ color: 'var(--accent)' }} />
            <span style={{ fontSize: 14, fontWeight: 600 }}>New Strategy</span>
          </div>
          <div className="grid grid-cols-2 gap-4 mb-4">
            <div>
              <label className="qt-label" style={{ display: 'block', marginBottom: 6 }}>Name</label>
              <input placeholder="My Alpha Strategy" value={form.name}
                onChange={e => setForm({ ...form, name: e.target.value })}
                className="qt-input" />
            </div>
            <div>
              <label className="qt-label" style={{ display: 'block', marginBottom: 6 }}>Type</label>
              <select value={form.strategy_type}
                onChange={e => {
                  const t = types.find(t => t.name === e.target.value);
                  setForm({ ...form, strategy_type: e.target.value, params: JSON.stringify(t?.params || {}, null, 2) });
                }}
                className="qt-select w-full">
                <option value="">Select strategy type...</option>
                {types.map(t => <option key={t.name} value={t.name}>{t.name}</option>)}
              </select>
            </div>
            <div>
              <label className="qt-label" style={{ display: 'block', marginBottom: 6 }}>Exchange</label>
              <select value={form.exchange} onChange={e => setForm({ ...form, exchange: e.target.value })}
                className="qt-select w-full">
                <option value="paper">Paper Trading</option>
                <option value="binance">Binance</option>
                <option value="okx">OKX</option>
                <option value="bybit">Bybit</option>
                <option value="ibkr">IBKR (US Stocks)</option>
              </select>
            </div>
            <div>
              <label className="qt-label" style={{ display: 'block', marginBottom: 6 }}>Parameters</label>
              <textarea placeholder='{"key": "value"}' value={form.params}
                onChange={e => setForm({ ...form, params: e.target.value })}
                rows={3}
                className="qt-input"
                style={{ fontFamily: 'var(--font-mono)', fontSize: 12, resize: 'vertical' }} />
            </div>
          </div>
          <button onClick={create} className="qt-btn qt-btn-accent">
            <Plus size={14} /> Create Strategy
          </button>
        </div>
      )}

      {/* Available Strategy Types */}
      <div className="mb-8 animate-in" style={{ animationDelay: '50ms' }}>
        <div className="qt-label mb-4">Available Types</div>
        <div className="grid grid-cols-3 gap-3">
          {types.map((t: any, i: number) => (
            <div key={i} className="qt-card qt-card-glow" style={{ padding: 16 }}>
              <div className="flex items-center gap-2 mb-2">
                <Cpu size={13} style={{ color: 'var(--accent)' }} />
                <span style={{ fontSize: 13, fontWeight: 600 }}>{t.name}</span>
              </div>
              <p style={{ fontSize: 11, color: 'var(--text-secondary)', lineHeight: 1.6 }}>
                {t.description}
              </p>
            </div>
          ))}
        </div>
      </div>

      {/* Configured Strategies */}
      <div className="animate-in" style={{ animationDelay: '100ms' }}>
        <div className="qt-label mb-4">Active Configurations ({strategies.length})</div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {strategies.map((s: any) => (
            <div key={s.id} className="qt-card" style={{
              padding: '16px 20px',
              display: 'flex', alignItems: 'center', justifyContent: 'space-between',
              borderLeft: s.is_enabled ? '2px solid var(--green)' : '2px solid var(--border)',
            }}>
              <div style={{ flex: 1 }}>
                <div className="flex items-center gap-3 mb-1">
                  <span style={{ fontSize: 14, fontWeight: 600 }}>{s.name}</span>
                  <span className="qt-badge" style={{
                    background: s.is_enabled ? 'var(--green-dim)' : 'var(--bg-elevated)',
                    color: s.is_enabled ? 'var(--green)' : 'var(--text-muted)',
                  }}>{s.status}</span>
                  <span className="qt-badge" style={{ background: 'var(--blue-dim)', color: 'var(--blue)' }}>
                    {s.execution_mode}
                  </span>
                  {s.exchange && (
                    <span className="qt-badge" style={{ background: 'var(--purple-dim)', color: 'var(--purple)' }}>
                      {s.exchange}
                    </span>
                  )}
                </div>
                <div style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--text-muted)' }}>
                  {s.strategy_type} &middot; {JSON.stringify(s.params)}
                </div>
              </div>
              <div className="flex items-center gap-2">
                <button onClick={() => toggle(s)} className="qt-btn qt-btn-ghost" style={{ padding: '7px 12px' }}>
                  {s.is_enabled ? <Square size={14} style={{ color: 'var(--red)' }} /> : <Play size={14} style={{ color: 'var(--green)' }} />}
                  <span style={{ fontSize: 12 }}>{s.is_enabled ? 'Stop' : 'Start'}</span>
                </button>
                <button onClick={() => remove(s.id)} className="qt-btn qt-btn-ghost" style={{ padding: '7px 10px' }}>
                  <Trash2 size={14} style={{ color: 'var(--red)' }} />
                </button>
              </div>
            </div>
          ))}
          {strategies.length === 0 && (
            <div className="qt-card" style={{ textAlign: 'center', padding: '40px 0', borderStyle: 'dashed' }}>
              <p style={{ fontSize: 13, color: 'var(--text-muted)' }}>
                No strategies configured. Click <strong style={{ color: 'var(--accent)' }}>New Strategy</strong> to begin.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
