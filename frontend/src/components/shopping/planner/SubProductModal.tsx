import { X } from 'lucide-react';
import { formatQuantity } from '../../../utils/format';
import type { CalculateMaterialsResponse } from '../../../types/shopping';

interface SubProductModalProps {
  pendingMaterials: CalculateMaterialsResponse;
  subProductDecisions: Record<number, 'buy' | 'build'>;
  setSubProductDecisions: (decisions: Record<number, 'buy' | 'build'>) => void;
  onClose: () => void;
  onApply: () => void;
  isApplying?: boolean;
}

export function SubProductModal({
  pendingMaterials,
  subProductDecisions,
  setSubProductDecisions,
  onClose,
  onApply,
  isApplying
}: SubProductModalProps) {
  const setAllDecisions = (decision: 'buy' | 'build') => {
    const allDecisions: Record<number, 'buy' | 'build'> = {};
    pendingMaterials.sub_products.forEach(sp => {
      allDecisions[sp.type_id] = decision;
    });
    setSubProductDecisions(allDecisions);
  };

  return (
    <div
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        backgroundColor: 'rgba(0,0,0,0.7)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 1000
      }}
      onClick={onClose}
    >
      <div
        className="card"
        style={{
          maxWidth: 500,
          maxHeight: '80vh',
          overflow: 'auto',
          padding: 20
        }}
        onClick={e => e.stopPropagation()}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
          <h3 style={{ margin: 0 }}>Sub-Components Found</h3>
          <button
            className="btn btn-secondary"
            onClick={onClose}
            style={{ padding: '4px 8px' }}
          >
            <X size={16} />
          </button>
        </div>

        <p className="neutral" style={{ marginBottom: 12 }}>
          These materials can be built from blueprints. Choose for each whether to buy or build:
        </p>

        {/* Select All buttons */}
        <div style={{ display: 'flex', gap: 8, marginBottom: 12 }}>
          <button
            className="btn btn-secondary"
            style={{ flex: 1, padding: '6px 12px', fontSize: 12 }}
            onClick={() => setAllDecisions('buy')}
          >
            Select All: Buy
          </button>
          <button
            className="btn btn-secondary"
            style={{ flex: 1, padding: '6px 12px', fontSize: 12 }}
            onClick={() => setAllDecisions('build')}
          >
            Select All: Build
          </button>
        </div>

        <div style={{
          display: 'flex',
          flexDirection: 'column',
          gap: 12,
          marginBottom: 20,
          maxHeight: 400,
          overflowY: 'auto'
        }}>
          {pendingMaterials.sub_products.map(sp => (
            <div
              key={sp.type_id}
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                padding: '10px 12px',
                background: 'var(--bg-dark)',
                borderRadius: 6
              }}
            >
              <div>
                <div style={{ fontWeight: 500 }}>{sp.item_name}</div>
                <div className="neutral" style={{ fontSize: 12 }}>x{formatQuantity(sp.quantity)}</div>
              </div>
              <select
                value={subProductDecisions[sp.type_id] || 'buy'}
                onChange={e => setSubProductDecisions({
                  ...subProductDecisions,
                  [sp.type_id]: e.target.value as 'buy' | 'build'
                })}
                style={{
                  padding: '6px 10px',
                  background: 'var(--bg-darker)',
                  border: '1px solid var(--border-color)',
                  borderRadius: 4,
                  color: 'inherit'
                }}
              >
                <option value="buy">Buy</option>
                <option value="build">Build</option>
              </select>
            </div>
          ))}
        </div>

        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8 }}>
          <button
            className="btn btn-secondary"
            onClick={onClose}
          >
            Cancel
          </button>
          <button
            className="btn btn-primary"
            onClick={onApply}
            disabled={isApplying}
          >
            {isApplying ? 'Applying...' : 'Apply Materials'}
          </button>
        </div>
      </div>
    </div>
  );
}
