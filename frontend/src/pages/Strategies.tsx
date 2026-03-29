import { useEffect, useState, useCallback } from 'react';
import { strategiesApi } from '../services/api';
import { Play, Square, Plus, Trash2, X, Cpu, Sliders, RotateCcw, Save, ChevronDown, ChevronRight } from 'lucide-react';

/* ─── Param Editor Component ─── */

interface ParamField {
  key: string;
  label: string;
  type: string;
  default: number;
  current: number;
  min?: number;
  max?: number;
  step?: number;
}

function ParamEditor({
  strategy,
  onSave,
  onReset,
  onClose,
}: {
  strategy: any;
  onSave: (id: number, params: Record<string, number>) => void;
  onReset: (id: number) => void;
  onClose: () => void;
}) {
  const schema: ParamField[] = strategy.param_schema || [];
  const [localParams, setLocalParams] = useState<Record<string, number>>(() => {
    const p: Record<string, number> = {};
    schema.forEach(f => { p[f.key] = f.current ?? f.default; });
    return p;
  });
  const [dirty, setDirty] = useState<Set<string>>(new Set());

  const updateParam = (key: string, val: number) => {
    setLocalParams(prev => ({ ...prev, [key]: val }));
    setDirty(prev => {
      const next = new Set(prev);
      const field = schema.find(f => f.key === key);
      if (field && val !== field.current) next.add(key);
      else next.delete(key);
      return next;
    });
  };

  const handleSave = () => {
    // Only send changed params
    const changed: Record<string, number> = {};
    dirty.forEach(key => { changed[key] = localParams[key]; });
    if (Object.keys(changed).length > 0) {
      onSave(strategy.id, changed);
      setDirty(new Set());
    }
  };

  const handleReset = () => {
    onReset(strategy.id);
    // Reset local state to defaults
    const p: Record<string, number> = {};
    schema.forEach(f => { p[f.key] = f.default; });
    setLocalParams(p);
    setDirty(new Set());
  };

  if (schema.length === 0) {
    return (
      <div style={{ padding: '16px 0', textAlign: 'center' }}>
        <p style={{ fontSize: 12, color: 'var(--text-muted)' }}>No configurable parameters</p>
      </div>
    );
  }

  return (
    <div style={{ paddingTop: 12 }}>
      <div className="glow-line mb-4" />

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
        {schema.map(field => {
          const val = localParams[field.key] ?? field.current;
          const isChanged = dirty.has(field.key);
          const hasRange = field.min !== undefined && field.max !== undefined;
          const pct = hasRange ? ((val - field.min!) / (field.max! - field.min!)) * 100 : 0;

          return (
            <div
              key={field.key}
              style={{
                padding: '12px 14px',
                borderRadius: 'var(--radius-sm)',
                background: isChanged ? 'var(--accent-glow)' : 'var(--bg-primary)',
                border: `1px solid ${isChanged ? 'var(--accent-dim)' : 'var(--border-subtle)'}`,
                transition: 'all 0.2s',
              }}
            >
              {/* Label row */}
              <div className="flex items-center justify-between mb-2">
                <span style={{
                  fontFamily: 'var(--font-mono)', fontSize: 10, fontWeight: 500,
                  letterSpacing: '0.05em', color: 'var(--text-secondary)',
                  textTransform: 'uppercase',
                }}>
                  {field.key}
                </span>
                {isChanged && (
                  <span style={{
                    fontSize: 9, fontFamily: 'var(--font-mono)',
                    color: 'var(--accent)', letterSpacing: '0.06em',
                  }}>MODIFIED</span>
                )}
              </div>

              {/* Description */}
              <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 8, lineHeight: 1.4 }}>
                {field.label}
              </div>

              {/* Value display */}
              <div className="flex items-center gap-3 mb-2">
                <input
                  type="number"
                  value={val}
                  step={field.step || 0.01}
                  min={field.min}
                  max={field.max}
                  onChange={e => updateParam(field.key, parseFloat(e.target.value) || 0)}
                  style={{
                    width: 90, padding: '4px 8px',
                    fontFamily: 'var(--font-mono)', fontSize: 14, fontWeight: 600,
                    color: isChanged ? 'var(--accent)' : 'var(--text-bright)',
                    background: 'var(--bg-secondary)',
                    border: '1px solid var(--border)',
                    borderRadius: 4, textAlign: 'right',
                    outline: 'none',
                  }}
                />
                {field.default !== undefined && (
                  <span style={{ fontSize: 10, color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                    default: {field.default}
                  </span>
                )}
              </div>

              {/* Slider */}
              {hasRange && (
                <div>
                  <input
                    type="range"
                    min={field.min}
                    max={field.max}
                    step={field.step || 0.01}
                    value={val}
                    onChange={e => updateParam(field.key, parseFloat(e.target.value))}
                    style={{
                      width: '100%', height: 4, appearance: 'none',
                      background: `linear-gradient(to right, var(--accent) ${pct}%, var(--border) ${pct}%)`,
                      borderRadius: 2, outline: 'none', cursor: 'pointer',
                      accentColor: 'var(--accent)',
                    }}
                  />
                  <div className="flex justify-between" style={{
                    fontFamily: 'var(--font-mono)', fontSize: 9, color: 'var(--text-muted)', marginTop: 2,
                  }}>
                    <span>{field.min}</span>
                    <span>{field.max}</span>
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Action buttons */}
      <div className="flex items-center justify-between mt-4">
        <button onClick={handleReset} className="qt-btn qt-btn-ghost" style={{ fontSize: 12, padding: '6px 14px' }}>
          <RotateCcw size={13} /> Reset to Defaults
        </button>
        <div className="flex items-center gap-2">
          <button onClick={onClose} className="qt-btn qt-btn-ghost" style={{ fontSize: 12, padding: '6px 14px' }}>
            Cancel
          </button>
          <button
            onClick={handleSave}
            disabled={dirty.size === 0}
            className="qt-btn qt-btn-accent"
            style={{ fontSize: 12, padding: '6px 14px', opacity: dirty.size === 0 ? 0.4 : 1 }}
          >
            <Save size={13} /> Apply {dirty.size > 0 ? `(${dirty.size})` : ''}
          </button>
        </div>
      </div>
    </div>
  );
}


/* ─── Main Strategies Page ─── */

export default function Strategies() {
  const [types, setTypes] = useState<any[]>([]);
  const [strategies, setStrategies] = useState<any[]>([]);
  const [showCreate, setShowCreate] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [form, setForm] = useState({ name: '', strategy_type: '', exchange: 'paper', params: '{}' });
  const [saveStatus, setSaveStatus] = useState<string | null>(null);

  const load = useCallback(() => {
    strategiesApi.types().then(d => setTypes(d.strategies || []));
    strategiesApi.list().then(d => setStrategies(d.strategies || []));
  }, []);
  useEffect(load, [load]);

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
    if (editingId === id) setEditingId(null);
    load();
  };

  const saveParams = async (id: number, params: Record<string, number>) => {
    await strategiesApi.update(id, { params });
    setSaveStatus(`Saved ${Object.keys(params).length} parameter(s)`);
    setTimeout(() => setSaveStatus(null), 2000);
    load();
  };

  const resetParams = async (id: number) => {
    await strategiesApi.resetParams(id);
    setSaveStatus('Parameters reset to defaults');
    setTimeout(() => setSaveStatus(null), 2000);
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
        <div className="flex items-center gap-3">
          {saveStatus && (
            <span className="animate-in" style={{
              fontFamily: 'var(--font-mono)', fontSize: 11,
              color: 'var(--green)', letterSpacing: '0.04em',
            }}>
              ✓ {saveStatus}
            </span>
          )}
          <button onClick={() => setShowCreate(!showCreate)} className="qt-btn qt-btn-accent">
            {showCreate ? <X size={15} /> : <Plus size={15} />}
            {showCreate ? 'Cancel' : 'New Strategy'}
          </button>
        </div>
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
                  const t = types.find(t => (t.class_name || t.name) === e.target.value);
                  setForm({ ...form, strategy_type: e.target.value, params: JSON.stringify(t?.params || {}, null, 2) });
                }}
                className="qt-select w-full">
                <option value="">Select strategy type...</option>
                {types.map(t => <option key={t.class_name || t.name} value={t.class_name || t.name}>{t.name}</option>)}
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
              {t.param_schema && t.param_schema.length > 0 && (
                <div style={{ marginTop: 8, display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                  {t.param_schema.map((p: any) => (
                    <span key={p.key} className="qt-badge" style={{
                      background: 'var(--bg-primary)', color: 'var(--text-muted)',
                      border: '1px solid var(--border-subtle)',
                    }}>
                      {p.key}
                    </span>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Configured Strategies with Editor */}
      <div className="animate-in" style={{ animationDelay: '100ms' }}>
        <div className="qt-label mb-4">Active Configurations ({strategies.length})</div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {strategies.map((s: any) => {
            const isEditing = editingId === s.id;
            return (
              <div key={s.id} className="qt-card" style={{
                padding: '16px 20px',
                borderLeft: s.is_enabled ? '2px solid var(--green)' : '2px solid var(--border)',
              }}>
                {/* Strategy header row */}
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
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
                      {s.strategy_type} · {Object.keys(s.params || {}).length} params
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => setEditingId(isEditing ? null : s.id)}
                      className="qt-btn qt-btn-ghost"
                      style={{
                        padding: '7px 12px',
                        ...(isEditing ? { background: 'var(--accent-glow)', borderColor: 'var(--accent-dim)' } : {}),
                      }}
                    >
                      <Sliders size={14} style={{ color: isEditing ? 'var(--accent)' : 'var(--text-secondary)' }} />
                      <span style={{ fontSize: 12, color: isEditing ? 'var(--accent)' : undefined }}>
                        {isEditing ? 'Close' : 'Tune'}
                      </span>
                      {isEditing ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
                    </button>
                    <button onClick={() => toggle(s)} className="qt-btn qt-btn-ghost" style={{ padding: '7px 12px' }}>
                      {s.is_enabled ? <Square size={14} style={{ color: 'var(--red)' }} /> : <Play size={14} style={{ color: 'var(--green)' }} />}
                      <span style={{ fontSize: 12 }}>{s.is_enabled ? 'Stop' : 'Start'}</span>
                    </button>
                    <button onClick={() => remove(s.id)} className="qt-btn qt-btn-ghost" style={{ padding: '7px 10px' }}>
                      <Trash2 size={14} style={{ color: 'var(--red)' }} />
                    </button>
                  </div>
                </div>

                {/* Inline Param Editor */}
                {isEditing && (
                  <ParamEditor
                    strategy={s}
                    onSave={saveParams}
                    onReset={resetParams}
                    onClose={() => setEditingId(null)}
                  />
                )}
              </div>
            );
          })}
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
