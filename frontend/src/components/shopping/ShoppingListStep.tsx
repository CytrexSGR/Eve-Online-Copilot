import { ArrowLeft, ArrowRight, Package, Boxes, ShoppingCart } from 'lucide-react';
import { formatISK, formatQuantity } from '../../utils/format';
import type { ProductInfo, ShoppingItem, ShoppingTotals } from './types';

interface ShoppingListStepProps {
  product: ProductInfo;
  shoppingList: ShoppingItem[];
  totals: ShoppingTotals | null;
  onProceed: () => void;
  onBack: () => void;
}

export function ShoppingListStep({
  product,
  shoppingList,
  totals,
  onProceed,
  onBack,
}: ShoppingListStepProps) {
  // Separate items by category
  const subComponents = shoppingList.filter(item => item.category === 'sub_component');
  const materials = shoppingList.filter(item => item.category === 'material');

  return (
    <div style={{ padding: 24 }}>
      <h2 style={{ marginBottom: 8 }}>Step 3: Shopping List</h2>
      <p className="neutral" style={{ marginBottom: 8 }}>
        Building: <strong>{product.runs}x {product.name}</strong>
      </p>
      <p className="neutral" style={{ marginBottom: 24 }}>
        Review your complete shopping list with estimated costs from Jita.
      </p>

      {/* Sub-Components Section */}
      {subComponents.length > 0 && (
        <div style={{ marginBottom: 24 }}>
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: 8,
            padding: '12px 16px',
            background: 'var(--accent-blue)',
            borderRadius: '8px 8px 0 0',
            color: 'white',
          }}>
            <ShoppingCart size={18} />
            <span style={{ fontWeight: 600 }}>SUB-COMPONENTS TO BUY</span>
            <span style={{ opacity: 0.8 }}>({subComponents.length} items)</span>
          </div>

          <div style={{
            border: '1px solid var(--border)',
            borderTop: 'none',
            borderRadius: '0 0 8px 8px',
          }}>
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead>
                <tr style={{ background: 'var(--bg-dark)' }}>
                  <th style={{ padding: '10px 16px', textAlign: 'left' }}>Item</th>
                  <th style={{ padding: '10px 16px', textAlign: 'right' }}>Quantity</th>
                  <th style={{ padding: '10px 16px', textAlign: 'right' }}>Unit Price</th>
                  <th style={{ padding: '10px 16px', textAlign: 'right' }}>Total</th>
                </tr>
              </thead>
              <tbody>
                {subComponents.map((item) => (
                  <tr
                    key={item.type_id}
                    style={{ borderBottom: '1px solid var(--border)' }}
                  >
                    <td style={{ padding: '10px 16px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                        <Package size={16} style={{ color: 'var(--accent-blue)' }} />
                        {item.item_name}
                      </div>
                    </td>
                    <td style={{ padding: '10px 16px', textAlign: 'right' }}>
                      {formatQuantity(item.quantity)}
                    </td>
                    <td style={{ padding: '10px 16px', textAlign: 'right' }} className="isk">
                      {item.jita_sell ? formatISK(item.jita_sell) : '-'}
                    </td>
                    <td style={{ padding: '10px 16px', textAlign: 'right', fontWeight: 500 }} className="isk">
                      {item.total_cost ? formatISK(item.total_cost) : '-'}
                    </td>
                  </tr>
                ))}
              </tbody>
              <tfoot>
                <tr style={{ background: 'var(--bg-dark)' }}>
                  <td colSpan={3} style={{ padding: '10px 16px', fontWeight: 600 }}>
                    Subtotal
                  </td>
                  <td style={{ padding: '10px 16px', textAlign: 'right', fontWeight: 600 }} className="isk">
                    {totals ? formatISK(totals.sub_components) : '-'}
                  </td>
                </tr>
              </tfoot>
            </table>
          </div>
        </div>
      )}

      {/* Raw Materials Section */}
      {materials.length > 0 && (
        <div style={{ marginBottom: 24 }}>
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: 8,
            padding: '12px 16px',
            background: 'var(--accent-green)',
            borderRadius: '8px 8px 0 0',
            color: 'white',
          }}>
            <Boxes size={18} />
            <span style={{ fontWeight: 600 }}>RAW MATERIALS</span>
            <span style={{ opacity: 0.8 }}>({materials.length} items)</span>
          </div>

          <div style={{
            border: '1px solid var(--border)',
            borderTop: 'none',
            borderRadius: '0 0 8px 8px',
            maxHeight: 400,
            overflow: 'auto',
          }}>
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead style={{ position: 'sticky', top: 0 }}>
                <tr style={{ background: 'var(--bg-dark)' }}>
                  <th style={{ padding: '10px 16px', textAlign: 'left' }}>Item</th>
                  <th style={{ padding: '10px 16px', textAlign: 'right' }}>Quantity</th>
                  <th style={{ padding: '10px 16px', textAlign: 'right' }}>Unit Price</th>
                  <th style={{ padding: '10px 16px', textAlign: 'right' }}>Total</th>
                </tr>
              </thead>
              <tbody>
                {materials.map((item) => (
                  <tr
                    key={item.type_id}
                    style={{ borderBottom: '1px solid var(--border)' }}
                  >
                    <td style={{ padding: '10px 16px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                        <Boxes size={16} style={{ color: 'var(--accent-green)' }} />
                        {item.item_name}
                      </div>
                    </td>
                    <td style={{ padding: '10px 16px', textAlign: 'right' }}>
                      {formatQuantity(item.quantity)}
                    </td>
                    <td style={{ padding: '10px 16px', textAlign: 'right' }} className="isk">
                      {item.jita_sell ? formatISK(item.jita_sell) : '-'}
                    </td>
                    <td style={{ padding: '10px 16px', textAlign: 'right', fontWeight: 500 }} className="isk">
                      {item.total_cost ? formatISK(item.total_cost) : '-'}
                    </td>
                  </tr>
                ))}
              </tbody>
              <tfoot>
                <tr style={{ background: 'var(--bg-dark)' }}>
                  <td colSpan={3} style={{ padding: '10px 16px', fontWeight: 600 }}>
                    Subtotal
                  </td>
                  <td style={{ padding: '10px 16px', textAlign: 'right', fontWeight: 600 }} className="isk">
                    {totals ? formatISK(totals.raw_materials) : '-'}
                  </td>
                </tr>
              </tfoot>
            </table>
          </div>
        </div>
      )}

      {/* Grand Total */}
      <div style={{
        padding: 20,
        background: 'var(--bg-dark)',
        borderRadius: 8,
        marginBottom: 24,
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
      }}>
        <span style={{ fontSize: 18, fontWeight: 600 }}>TOTAL ESTIMATED COST</span>
        <span style={{ fontSize: 24, fontWeight: 700 }} className="isk">
          {totals ? formatISK(totals.grand_total) : '-'}
        </span>
      </div>

      {/* Navigation Buttons */}
      <div style={{ display: 'flex', justifyContent: 'space-between' }}>
        <button
          onClick={onBack}
          className="btn btn-secondary"
          style={{ padding: '12px 24px', display: 'flex', alignItems: 'center', gap: 8 }}
        >
          <ArrowLeft size={18} />
          Back
        </button>

        <button
          onClick={onProceed}
          className="btn btn-primary"
          style={{ padding: '12px 24px', display: 'flex', alignItems: 'center', gap: 8 }}
        >
          Compare Regions
          <ArrowRight size={18} />
        </button>
      </div>
    </div>
  );
}

export default ShoppingListStep;
