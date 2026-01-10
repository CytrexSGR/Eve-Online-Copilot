import { ShoppingCart, Copy, Trash2, Truck, Package, BarChart3 } from 'lucide-react';
import { formatISK } from '../../../utils/format';
import type { ShoppingListDetail, CargoSummaryResponse } from '../../../types/shopping';

interface ListHeaderProps {
  list: ShoppingListDetail;
  cargoSummary: CargoSummaryResponse | undefined;
  viewMode: 'list' | 'compare' | 'transport';
  setViewMode: (mode: 'list' | 'compare' | 'transport') => void;
  globalRuns: number;
  setGlobalRuns: (runs: number) => void;
  onExport: () => void;
  onDelete: () => void;
}

export function ListHeader({
  list,
  cargoSummary,
  viewMode,
  setViewMode,
  globalRuns,
  setGlobalRuns,
  onExport,
  onDelete
}: ListHeaderProps) {
  return (
    <div className="card" style={{ marginBottom: 16 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
          <div>
            <h2 style={{ margin: 0 }}>{list.name}</h2>
            <div className="neutral" style={{ marginTop: 4 }}>
              {list.items?.length || 0} items
              {list.total_cost && ` • ${formatISK(list.total_cost)} total`}
            </div>
          </div>
          {cargoSummary && cargoSummary.materials.total_volume_m3 > 0 && (
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: 8,
              padding: '8px 12px',
              background: 'var(--bg-dark)',
              borderRadius: 6,
              fontSize: 13
            }}>
              <Package size={16} />
              <span>Cargo: <strong>{cargoSummary.materials.volume_formatted}</strong></span>
              <span className="neutral">({cargoSummary.materials.total_items} items)</span>
            </div>
          )}
        </div>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          {/* Global Runs Multiplier */}
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: 6,
            padding: '6px 12px',
            background: 'var(--bg-dark)',
            borderRadius: 6
          }}>
            <span style={{ fontSize: 12 }}>×</span>
            <input
              type="number"
              min="1"
              max="1000"
              value={globalRuns}
              onChange={(e) => setGlobalRuns(Math.max(1, parseInt(e.target.value) || 1))}
              style={{
                width: 50,
                padding: '4px 8px',
                borderRadius: 4,
                border: '1px solid var(--border)',
                background: 'var(--bg-darker)',
                color: 'var(--text-primary)',
                fontSize: 14,
                fontWeight: 600,
                textAlign: 'center'
              }}
              title="Global runs multiplier"
            />
          </div>

          {/* View Mode Tabs */}
          <button
            className={`btn ${viewMode === 'list' ? 'btn-primary' : 'btn-secondary'}`}
            style={{ padding: '6px 12px', borderRadius: 4 }}
            onClick={() => setViewMode('list')}
          >
            <ShoppingCart size={16} />
          </button>
          <button
            className={`btn ${viewMode === 'compare' ? 'btn-primary' : 'btn-secondary'}`}
            style={{ padding: '6px 12px', borderRadius: 4 }}
            onClick={() => setViewMode('compare')}
            title="Compare Regions"
          >
            <BarChart3 size={16} />
          </button>
          <button
            className={`btn ${viewMode === 'transport' ? 'btn-primary' : 'btn-secondary'}`}
            onClick={() => setViewMode('transport')}
            disabled={!cargoSummary || cargoSummary.materials.total_volume_m3 === 0}
            title={!cargoSummary || cargoSummary.materials.total_volume_m3 === 0
              ? 'Add items to see transport options'
              : 'Plan transport'}
          >
            <Truck size={16} style={{ marginRight: 6 }} />
            Transport
          </button>
          <button className="btn btn-secondary" onClick={onExport}>
            <Copy size={16} /> Export All
          </button>
          <button
            className="btn btn-secondary"
            style={{ color: 'var(--accent-red)' }}
            onClick={onDelete}
          >
            <Trash2 size={16} />
          </button>
        </div>
      </div>
    </div>
  );
}
