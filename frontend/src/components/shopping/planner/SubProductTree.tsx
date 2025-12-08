import { formatQuantity } from '../../../utils/format';
import type { ShoppingListItem } from '../../../types/shopping';

interface SubProductTreeProps {
  subProduct: ShoppingListItem;
  depth: number;
  updateBuildDecision: {
    mutate: (params: { itemId: number; decision: 'buy' | 'build' }) => void;
    isPending: boolean;
  };
  onBulkUpdate: (itemIds: number[], decision: 'buy' | 'build') => void;
}

/**
 * Recursive component to display sub-product tree with BUY/BUILD toggles
 */
export function SubProductTree({ subProduct, depth, updateBuildDecision, onBulkUpdate }: SubProductTreeProps) {
  // Collect all descendant IDs for bulk operations
  const collectDescendantIds = (item: ShoppingListItem): number[] => {
    const ids = [item.id];
    if (item.sub_products) {
      item.sub_products.forEach((sp) => {
        ids.push(...collectDescendantIds(sp));
      });
    }
    return ids;
  };

  const descendantIds = collectDescendantIds(subProduct);

  return (
    <div style={{ marginLeft: depth * 16, marginBottom: 8 }}>
      <div
        style={{
          padding: '8px 12px',
          background: 'var(--bg-dark)',
          borderRadius: 6,
          borderLeft: `3px solid ${
            subProduct.build_decision === 'build' ? 'var(--accent-green)' : 'var(--accent-blue)'
          }`,
        }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            {/* BUY/BUILD Toggle */}
            <div
              style={{
                display: 'flex',
                background: 'var(--bg-darker)',
                borderRadius: 4,
                padding: 1,
                border: '1px solid var(--border)',
              }}
            >
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  updateBuildDecision.mutate({ itemId: subProduct.id, decision: 'buy' });
                }}
                disabled={updateBuildDecision.isPending}
                style={{
                  padding: '2px 8px',
                  borderRadius: 3,
                  border: 'none',
                  fontSize: 10,
                  fontWeight: 600,
                  cursor: 'pointer',
                  background: subProduct.build_decision !== 'build' ? 'var(--accent-blue)' : 'transparent',
                  color: subProduct.build_decision !== 'build' ? 'white' : 'var(--text-secondary)',
                  transition: 'all 0.15s',
                }}
                title="Buy from market"
              >
                BUY
              </button>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  updateBuildDecision.mutate({ itemId: subProduct.id, decision: 'build' });
                }}
                disabled={updateBuildDecision.isPending}
                style={{
                  padding: '2px 8px',
                  borderRadius: 3,
                  border: 'none',
                  fontSize: 10,
                  fontWeight: 600,
                  cursor: 'pointer',
                  background: subProduct.build_decision === 'build' ? 'var(--accent-green)' : 'transparent',
                  color: subProduct.build_decision === 'build' ? 'white' : 'var(--text-secondary)',
                  transition: 'all 0.15s',
                }}
                title="Build from materials"
              >
                BUILD
              </button>
            </div>
            <div>
              <span style={{ fontWeight: 500, fontSize: 13 }}>{subProduct.item_name}</span>
              <span className="neutral" style={{ marginLeft: 8, fontWeight: 400, fontSize: 12 }}>
                x{formatQuantity(subProduct.quantity)}
              </span>
            </div>
          </div>

          {/* Bulk Actions - only show if has sub-products */}
          {subProduct.sub_products && subProduct.sub_products.length > 0 && (
            <div style={{ display: 'flex', gap: 4 }}>
              <button
                className="btn-icon"
                onClick={() => onBulkUpdate(descendantIds, 'buy')}
                style={{ fontSize: 9, padding: '2px 6px' }}
                title="Set all to BUY"
              >
                All BUY
              </button>
              <button
                className="btn-icon"
                onClick={() => onBulkUpdate(descendantIds, 'build')}
                style={{ fontSize: 9, padding: '2px 6px' }}
                title="Set all to BUILD"
              >
                All BUILD
              </button>
            </div>
          )}
        </div>

        {/* Show materials if BUILD decision */}
        {subProduct.build_decision === 'build' && subProduct.materials && subProduct.materials.length > 0 && (
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4, marginTop: 8 }}>
            {subProduct.materials.map((mat) => (
              <span
                key={mat.id}
                style={{
                  padding: '2px 6px',
                  background: 'var(--bg-darker)',
                  borderRadius: 4,
                  fontSize: 11,
                }}
              >
                {mat.item_name}: {formatQuantity(mat.quantity)}
              </span>
            ))}
          </div>
        )}

        {/* Recursively render sub-products if BUILD decision */}
        {subProduct.build_decision === 'build' && subProduct.sub_products && subProduct.sub_products.length > 0 && (
          <div style={{ marginTop: 8 }}>
            {subProduct.sub_products.map((sp) => (
              <SubProductTree
                key={sp.id}
                subProduct={sp}
                depth={depth + 1}
                updateBuildDecision={updateBuildDecision}
                onBulkUpdate={onBulkUpdate}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
