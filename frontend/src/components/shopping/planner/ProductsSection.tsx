import { useState } from 'react';
import { Package, Plus, Calculator, RefreshCw, ChevronUp, ChevronDown, Trash2 } from 'lucide-react';
import { formatQuantity } from '../../../utils/format';
import { SubProductTree } from './SubProductTree';
import type { ShoppingListDetail, ShoppingProduct } from '../../../types/shopping';
import type { UseMutationResult } from '@tanstack/react-query';

interface ProductsSectionProps {
  list: ShoppingListDetail;
  expandedProducts: Set<number>;
  toggleProductExpanded: (id: number) => void;
  onAddProduct: () => void;
  onCalculateMaterials: (productId: number) => void;
  onCalculateAllMaterials: () => void;
  onRecalculateAll: () => void;
  onUpdateRuns: (productId: number, runs: number, meLevel: number) => void;
  onRemoveProduct: (productId: number) => void;
  updateBuildDecision: UseMutationResult<void, unknown, { itemId: number; decision: 'buy' | 'build' }, unknown>;
  onBulkBuildDecision: (itemIds: number[], decision: 'buy' | 'build') => Promise<void>;
  isCalculating?: boolean;
}

export function ProductsSection({
  list,
  expandedProducts,
  toggleProductExpanded,
  onAddProduct,
  onCalculateMaterials,
  onCalculateAllMaterials,
  onRecalculateAll,
  onUpdateRuns,
  onRemoveProduct,
  updateBuildDecision,
  onBulkBuildDecision,
  isCalculating
}: ProductsSectionProps) {
  return (
    <div className="card" style={{ marginBottom: 16 }}>
      <div className="card-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <span className="card-title">
          <Package size={18} style={{ marginRight: 8 }} />
          Products ({list.products?.length || 0})
        </span>
        <button
          className="btn btn-primary"
          style={{ padding: '6px 12px', fontSize: 12 }}
          onClick={onAddProduct}
        >
          <Plus size={14} style={{ marginRight: 4 }} />
          Add Product
        </button>
      </div>
      <div style={{ padding: 16 }}>
        {(!list.products || list.products.length === 0) ? (
          <div style={{ textAlign: 'center', padding: '24px 0', color: 'var(--text-secondary)' }}>
            <Package size={32} style={{ opacity: 0.5, marginBottom: 8 }} />
            <div>No products yet</div>
            <div style={{ fontSize: 12, marginTop: 4 }}>
              Click "Add Product" to add a ship, module or other buildable item
            </div>
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            {/* Calculate/Recalculate buttons */}
            <div style={{ display: 'flex', gap: 8, marginBottom: 8 }}>
              {list.products.some(p => !p.materials_calculated) && (
                <button
                  className="btn btn-primary"
                  onClick={onCalculateAllMaterials}
                  disabled={isCalculating}
                >
                  <Calculator size={16} style={{ marginRight: 8 }} />
                  Calculate Materials
                </button>
              )}
              {list.products.some(p => p.materials_calculated) && (
                <button
                  className="btn"
                  style={{ background: 'var(--bg-darker)', border: '1px solid var(--border-color)' }}
                  onClick={onRecalculateAll}
                  disabled={isCalculating}
                >
                  <RefreshCw size={16} style={{ marginRight: 8 }} />
                  Recalculate All
                </button>
              )}
            </div>

            {list.products.map((product) => (
              <ProductRow
                key={product.id}
                product={product}
                isExpanded={expandedProducts.has(product.id)}
                onToggleExpand={() => toggleProductExpanded(product.id)}
                onCalculate={() => onCalculateMaterials(product.id)}
                onUpdateRuns={(runs, meLevel) => onUpdateRuns(product.id, runs, meLevel)}
                onRemove={() => onRemoveProduct(product.id)}
                updateBuildDecision={updateBuildDecision}
                onBulkBuildDecision={onBulkBuildDecision}
                isCalculating={isCalculating}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

interface ProductRowProps {
  product: ShoppingProduct;
  isExpanded: boolean;
  onToggleExpand: () => void;
  onCalculate: () => void;
  onUpdateRuns: (runs: number, meLevel: number) => void;
  onRemove: () => void;
  updateBuildDecision: UseMutationResult<void, unknown, { itemId: number; decision: 'buy' | 'build' }, unknown>;
  onBulkBuildDecision: (itemIds: number[], decision: 'buy' | 'build') => Promise<void>;
  isCalculating?: boolean;
}

function ProductRow({
  product,
  isExpanded,
  onToggleExpand,
  onCalculate,
  onUpdateRuns,
  onRemove,
  updateBuildDecision,
  onBulkBuildDecision,
  isCalculating
}: ProductRowProps) {
  return (
    <div style={{ borderRadius: 8, overflow: 'hidden' }}>
      {/* Product Row Header */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '10px 16px',
          background: 'var(--bg-dark)',
          borderRadius: product.materials_calculated ? '8px 8px 0 0' : 8,
          borderLeft: '3px solid var(--accent-green)'
        }}
      >
        {/* Left: Expand + Name + Info */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, flex: 1 }}>
          {product.materials_calculated && (
            <button
              onClick={onToggleExpand}
              style={{
                background: 'none',
                border: 'none',
                color: 'var(--text-secondary)',
                cursor: 'pointer',
                padding: 4
              }}
            >
              {isExpanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
            </button>
          )}
          <div style={{ minWidth: 200 }}>
            <div style={{ fontWeight: 600, fontSize: 14 }}>{product.item_name}</div>
            <div className="neutral" style={{ fontSize: 11 }}>
              {product.runs || 1} runs × {product.output_per_run || 1} = {(product.runs || 1) * (product.output_per_run || 1)} units
            </div>
          </div>
        </div>

        {/* Middle: Controls */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
          {/* Runs */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
            <label style={{ fontSize: 11, color: 'var(--text-secondary)' }}>Runs:</label>
            <input
              type="number"
              min="1"
              max="1000"
              defaultValue={product.runs || 1}
              style={{
                width: 50,
                padding: '4px 6px',
                borderRadius: 4,
                border: '1px solid var(--border)',
                background: 'var(--bg-darker)',
                color: 'inherit',
                fontSize: 12
              }}
              onBlur={(e) => {
                const newRuns = parseInt(e.target.value) || 1;
                if (newRuns !== product.runs) {
                  onUpdateRuns(newRuns, product.me_level || 10);
                }
              }}
              onKeyDown={(e) => {
                if (e.key === 'Enter') {
                  (e.target as HTMLInputElement).blur();
                }
              }}
            />
          </div>

          {/* ME */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
            <label style={{ fontSize: 11, color: 'var(--text-secondary)' }}>ME:</label>
            <input
              type="number"
              min="0"
              max="10"
              defaultValue={product.me_level || 10}
              style={{
                width: 40,
                padding: '4px 6px',
                borderRadius: 4,
                border: '1px solid var(--border)',
                background: 'var(--bg-darker)',
                color: 'inherit',
                fontSize: 12
              }}
              onBlur={(e) => {
                const newME = parseInt(e.target.value) || 10;
                if (newME !== product.me_level) {
                  onUpdateRuns(product.runs || 1, newME);
                }
              }}
              onKeyDown={(e) => {
                if (e.key === 'Enter') {
                  (e.target as HTMLInputElement).blur();
                }
              }}
            />
          </div>

          {/* Status Badge */}
          {product.materials_calculated ? (
            <span className="badge badge-green" style={{ fontSize: 10 }}>Materials calculated</span>
          ) : (
            <span className="badge" style={{ fontSize: 10, background: 'var(--bg-darker)' }}>Not calculated</span>
          )}

          {/* Calculate Button */}
          <button
            className="btn btn-primary"
            style={{ padding: '5px 10px', fontSize: 11 }}
            onClick={onCalculate}
            disabled={isCalculating}
          >
            <Calculator size={12} style={{ marginRight: 4 }} />
            {product.materials_calculated ? 'Recalculate' : 'Calculate'}
          </button>

          {/* Delete */}
          <button
            className="btn-icon"
            style={{ color: 'var(--accent-red)' }}
            onClick={() => {
              if (confirm(`Remove ${product.item_name} and its materials?`)) {
                onRemove();
              }
            }}
            title="Remove product"
          >
            <Trash2 size={14} />
          </button>
        </div>
      </div>

      {/* Materials List (expandable) */}
      {product.materials_calculated && isExpanded && (
        <div style={{
          background: 'var(--bg-darker)',
          padding: '12px 16px',
          borderRadius: '0 0 8px 8px',
          borderTop: '1px solid var(--border-color)'
        }}>
          {product.materials && product.materials.length > 0 && (
            <div style={{ marginBottom: 12 }}>
              <div style={{ fontSize: 12, fontWeight: 500, marginBottom: 8, color: 'var(--text-secondary)' }}>
                Materials ({product.materials.length})
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 8 }}>
                {product.materials.map((mat) => (
                  <div
                    key={mat.id}
                    style={{
                      display: 'flex',
                      justifyContent: 'space-between',
                      padding: '6px 10px',
                      background: 'var(--bg-dark)',
                      borderRadius: 4,
                      fontSize: 12
                    }}
                  >
                    <span>{mat.item_name}</span>
                    <span className="isk">{formatQuantity(mat.quantity)}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {product.sub_products && product.sub_products.length > 0 && (
            <div>
              <div style={{ fontSize: 12, fontWeight: 500, marginBottom: 8, color: 'var(--text-secondary)' }}>
                Sub-Components ({product.sub_products.length})
              </div>
              {product.sub_products.map((subProduct) => (
                <SubProductTree
                  key={subProduct.id}
                  subProduct={subProduct}
                  depth={0}
                  updateBuildDecision={updateBuildDecision}
                  onBulkUpdate={onBulkBuildDecision}
                />
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
