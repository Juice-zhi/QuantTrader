import { useEffect, useState } from 'react';
import { factorsApi } from '../services/api';

const CATEGORY_COLORS: Record<string, string> = {
  technical: '#6366f1',
  momentum: '#22c55e',
  volatility: '#ef4444',
  volume: '#eab308',
  composite: '#8b5cf6',
};

export default function Factors() {
  const [factors, setFactors] = useState<any[]>([]);
  const [categories, setCategories] = useState<string[]>([]);
  const [selectedCat, setSelectedCat] = useState<string>('');

  useEffect(() => {
    factorsApi.list(selectedCat || undefined).then(d => {
      setFactors(d.factors || []);
      if (!selectedCat) setCategories(d.categories || []);
    });
  }, [selectedCat]);

  const grouped = factors.reduce((acc: Record<string, any[]>, f) => {
    const cat = f.category || 'unknown';
    if (!acc[cat]) acc[cat] = [];
    acc[cat].push(f);
    return acc;
  }, {});

  return (
    <div>
      <h2 className="text-xl font-bold mb-6">Factor Library</h2>

      {/* Category Tabs */}
      <div className="flex gap-2 mb-6">
        <button onClick={() => setSelectedCat('')}
          className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
            !selectedCat ? 'text-white' : ''
          }`}
          style={{
            background: !selectedCat ? 'var(--accent)' : 'var(--bg-card)',
            color: !selectedCat ? '#fff' : 'var(--text-secondary)',
          }}>
          All ({factors.length})
        </button>
        {categories.map(cat => (
          <button key={cat} onClick={() => setSelectedCat(cat)}
            className="px-3 py-1.5 rounded-lg text-xs font-medium transition-colors"
            style={{
              background: selectedCat === cat ? CATEGORY_COLORS[cat] : 'var(--bg-card)',
              color: selectedCat === cat ? '#fff' : 'var(--text-secondary)',
            }}>
            {cat}
          </button>
        ))}
      </div>

      {/* Factor Grid */}
      {Object.entries(grouped).map(([cat, facs]) => (
        <div key={cat} className="mb-8">
          <div className="flex items-center gap-2 mb-3">
            <span className="w-2 h-2 rounded-full" style={{ background: CATEGORY_COLORS[cat] || '#888' }} />
            <h3 className="text-sm font-semibold uppercase tracking-wider" style={{ color: 'var(--text-secondary)' }}>
              {cat} ({facs.length})
            </h3>
          </div>
          <div className="grid grid-cols-3 gap-3">
            {facs.map((f: any, i: number) => (
              <div key={i} className="rounded-lg p-4 border hover:border-opacity-50 transition-colors cursor-pointer"
                   style={{ background: 'var(--bg-card)', borderColor: 'var(--border)' }}>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-mono font-semibold">{f.class_name}</span>
                  <span className="text-xs px-1.5 py-0.5 rounded" style={{
                    background: `${CATEGORY_COLORS[cat]}20`,
                    color: CATEGORY_COLORS[cat],
                  }}>
                    {cat}
                  </span>
                </div>
                <p className="text-xs leading-relaxed" style={{ color: 'var(--text-secondary)' }}>
                  {f.description || 'No description'}
                </p>
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}
