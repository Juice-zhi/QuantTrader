import { useEffect, useState } from 'react';
import { factorsApi } from '../services/api';
import { Search } from 'lucide-react';

const CATEGORY_META: Record<string, { color: string; icon: string }> = {
  technical: { color: 'var(--accent)', icon: 'TEC' },
  momentum: { color: 'var(--green)', icon: 'MOM' },
  volatility: { color: 'var(--red)', icon: 'VOL' },
  volume: { color: 'var(--yellow)', icon: 'VLM' },
  composite: { color: 'var(--purple)', icon: 'CMP' },
};

export default function Factors() {
  const [factors, setFactors] = useState<any[]>([]);
  const [categories, setCategories] = useState<string[]>([]);
  const [selectedCat, setSelectedCat] = useState<string>('');
  const [search, setSearch] = useState('');

  useEffect(() => {
    factorsApi.list(selectedCat || undefined).then(d => {
      setFactors(d.factors || []);
      if (!selectedCat) setCategories(d.categories || []);
    });
  }, [selectedCat]);

  const filtered = search
    ? factors.filter(f => f.class_name?.toLowerCase().includes(search.toLowerCase()) || f.description?.toLowerCase().includes(search.toLowerCase()))
    : factors;

  const grouped = filtered.reduce((acc: Record<string, any[]>, f) => {
    const cat = f.category || 'unknown';
    if (!acc[cat]) acc[cat] = [];
    acc[cat].push(f);
    return acc;
  }, {});

  return (
    <div>
      {/* Header */}
      <div className="flex items-end justify-between mb-8 animate-in">
        <div>
          <div className="qt-label mb-2">Analytics</div>
          <h1 style={{ fontFamily: 'var(--font-display)', fontSize: 28, fontWeight: 700, color: 'var(--text-bright)', letterSpacing: '-0.02em' }}>
            Factor Library
          </h1>
        </div>
        <div className="flex items-center gap-3">
          <div style={{ position: 'relative' }}>
            <Search size={14} style={{ position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
            <input
              value={search} onChange={e => setSearch(e.target.value)}
              placeholder="Search factors..."
              className="qt-input"
              style={{ paddingLeft: 34, width: 220 }}
            />
          </div>
        </div>
      </div>

      {/* Category Tabs */}
      <div className="flex gap-2 mb-8 animate-in" style={{ animationDelay: '50ms' }}>
        <button onClick={() => setSelectedCat('')}
          className="qt-btn"
          style={{
            padding: '7px 14px', fontSize: 12,
            background: !selectedCat ? 'var(--accent)' : 'var(--bg-card)',
            color: !selectedCat ? '#0c0d12' : 'var(--text-secondary)',
            border: !selectedCat ? 'none' : '1px solid var(--border)',
            fontWeight: !selectedCat ? 600 : 400,
          }}>
          All ({factors.length})
        </button>
        {categories.map(cat => {
          const meta = CATEGORY_META[cat] || { color: '#888', icon: '?' };
          return (
            <button key={cat} onClick={() => setSelectedCat(cat)}
              className="qt-btn"
              style={{
                padding: '7px 14px', fontSize: 12,
                background: selectedCat === cat ? meta.color : 'var(--bg-card)',
                color: selectedCat === cat ? '#0c0d12' : 'var(--text-secondary)',
                border: selectedCat === cat ? 'none' : '1px solid var(--border)',
                fontWeight: selectedCat === cat ? 600 : 400,
              }}>
              {cat.charAt(0).toUpperCase() + cat.slice(1)}
            </button>
          );
        })}
      </div>

      {/* Factor Grid */}
      {Object.entries(grouped).map(([cat, facs], catIdx) => {
        const meta = CATEGORY_META[cat] || { color: '#888', icon: '?' };
        return (
          <div key={cat} className="mb-8 animate-in" style={{ animationDelay: `${100 + catIdx * 60}ms` }}>
            <div className="flex items-center gap-3 mb-4">
              <div style={{
                width: 3, height: 18, borderRadius: 2, background: meta.color,
              }} />
              <span className="qt-label" style={{ color: meta.color, fontSize: 11 }}>
                {cat.toUpperCase()}
              </span>
              <span style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: 'var(--text-muted)' }}>
                {facs.length} factors
              </span>
              <div className="glow-line flex-1" style={{ background: `linear-gradient(90deg, ${meta.color}33, transparent)` }} />
            </div>
            <div className="grid grid-cols-3 gap-3">
              {facs.map((f: any, i: number) => (
                <div key={i} className="qt-card qt-card-glow group" style={{ padding: 16, cursor: 'default' }}>
                  <div className="flex items-center justify-between mb-3">
                    <span style={{
                      fontFamily: 'var(--font-mono)', fontSize: 13, fontWeight: 600, color: 'var(--text-bright)',
                    }}>
                      {f.class_name}
                    </span>
                    <span className="qt-badge" style={{
                      background: `${meta.color}15`,
                      color: meta.color,
                      border: `1px solid ${meta.color}25`,
                    }}>
                      {meta.icon}
                    </span>
                  </div>
                  <p style={{ fontSize: 11.5, color: 'var(--text-secondary)', lineHeight: 1.6 }}>
                    {f.description || 'No description available'}
                  </p>
                </div>
              ))}
            </div>
          </div>
        );
      })}
    </div>
  );
}
