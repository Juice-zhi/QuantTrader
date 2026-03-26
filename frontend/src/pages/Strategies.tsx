import { useEffect, useState } from 'react';
import { strategiesApi } from '../services/api';
import { Play, Square, Plus, Trash2 } from 'lucide-react';

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
    await strategiesApi.create({
      ...form,
      params: JSON.parse(form.params || '{}'),
    });
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
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-xl font-bold">Strategy Control Center</h2>
        <button onClick={() => setShowCreate(!showCreate)}
          className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium text-white"
          style={{ background: 'var(--accent)' }}>
          <Plus size={16} /> New Strategy
        </button>
      </div>

      {/* Create Form */}
      {showCreate && (
        <div className="rounded-xl p-5 border mb-6" style={{ background: 'var(--bg-card)', borderColor: 'var(--border)' }}>
          <h3 className="text-sm font-semibold mb-4">Create Strategy</h3>
          <div className="grid grid-cols-2 gap-4">
            <input placeholder="Strategy Name" value={form.name}
              onChange={e => setForm({ ...form, name: e.target.value })}
              className="px-3 py-2 rounded-lg text-sm border bg-transparent"
              style={{ borderColor: 'var(--border)', color: 'var(--text-primary)' }} />
            <select value={form.strategy_type}
              onChange={e => {
                const t = types.find(t => t.name === e.target.value);
                setForm({ ...form, strategy_type: e.target.value, params: JSON.stringify(t?.params || {}, null, 2) });
              }}
              className="px-3 py-2 rounded-lg text-sm border"
              style={{ borderColor: 'var(--border)', background: 'var(--bg-secondary)', color: 'var(--text-primary)' }}>
              <option value="">Select Strategy Type...</option>
              {types.map(t => <option key={t.name} value={t.name}>{t.name}</option>)}
            </select>
            <select value={form.exchange} onChange={e => setForm({ ...form, exchange: e.target.value })}
              className="px-3 py-2 rounded-lg text-sm border"
              style={{ borderColor: 'var(--border)', background: 'var(--bg-secondary)', color: 'var(--text-primary)' }}>
              <option value="paper">Paper Trading</option>
              <option value="binance">Binance</option>
              <option value="okx">OKX</option>
              <option value="bybit">Bybit</option>
              <option value="ibkr">IBKR (US Stocks)</option>
            </select>
            <textarea placeholder='{"key": "value"}' value={form.params}
              onChange={e => setForm({ ...form, params: e.target.value })}
              rows={3}
              className="px-3 py-2 rounded-lg text-sm border font-mono bg-transparent"
              style={{ borderColor: 'var(--border)', color: 'var(--text-primary)' }} />
          </div>
          <button onClick={create} className="mt-4 px-4 py-2 rounded-lg text-sm font-medium text-white"
            style={{ background: 'var(--accent)' }}>Create</button>
        </div>
      )}

      {/* Strategy Types */}
      <h3 className="text-sm font-semibold mb-3" style={{ color: 'var(--text-secondary)' }}>
        Available Strategy Types ({types.length})
      </h3>
      <div className="grid grid-cols-3 gap-3 mb-8">
        {types.map((t: any, i: number) => (
          <div key={i} className="rounded-lg p-4 border" style={{ background: 'var(--bg-card)', borderColor: 'var(--border)' }}>
            <div className="text-sm font-semibold mb-1">{t.name}</div>
            <p className="text-xs leading-relaxed" style={{ color: 'var(--text-secondary)' }}>{t.description}</p>
          </div>
        ))}
      </div>

      {/* Configured Strategies */}
      <h3 className="text-sm font-semibold mb-3" style={{ color: 'var(--text-secondary)' }}>
        Configured Strategies ({strategies.length})
      </h3>
      <div className="space-y-3">
        {strategies.map((s: any) => (
          <div key={s.id} className="rounded-xl p-5 border flex items-center justify-between"
               style={{ background: 'var(--bg-card)', borderColor: 'var(--border)' }}>
            <div className="flex-1">
              <div className="flex items-center gap-3">
                <span className="text-sm font-semibold">{s.name}</span>
                <span className={`text-xs px-2 py-0.5 rounded-full ${
                  s.is_enabled ? 'bg-green-500/20 text-green-400' : 'bg-gray-500/20 text-gray-400'
                }`}>{s.status}</span>
                <span className="text-xs px-2 py-0.5 rounded-full bg-blue-500/20 text-blue-400">
                  {s.execution_mode}
                </span>
              </div>
              <div className="text-xs mt-1" style={{ color: 'var(--text-secondary)' }}>
                Type: {s.strategy_type} | Exchange: {s.exchange || 'N/A'} | Params: {JSON.stringify(s.params)}
              </div>
            </div>
            <div className="flex items-center gap-2">
              <button onClick={() => toggle(s)}
                className={`p-2 rounded-lg text-sm ${s.is_enabled ? 'bg-red-500/20 text-red-400' : 'bg-green-500/20 text-green-400'}`}>
                {s.is_enabled ? <Square size={16} /> : <Play size={16} />}
              </button>
              <button onClick={() => remove(s.id)} className="p-2 rounded-lg bg-gray-500/20 text-gray-400">
                <Trash2 size={16} />
              </button>
            </div>
          </div>
        ))}
        {strategies.length === 0 && (
          <p className="text-sm text-center py-8" style={{ color: 'var(--text-secondary)' }}>
            No strategies configured yet. Click "New Strategy" to create one.
          </p>
        )}
      </div>
    </div>
  );
}
