import { ShoppingCart, Check, Trash2, Copy } from 'lucide-react';
import { formatISK, formatQuantity } from '../../../utils/format';
import type { ShoppingListItem } from '../../../types/shopping';

interface ShoppingListTableProps {
  items: (ShoppingListItem & { aggregatedQuantity?: number })[];
  totalCost: number;
  onMarkPurchased: (itemId: number) => void;
  onUnmarkPurchased: (itemId: number) => void;
  onRemoveItem: (itemId: number) => void;
  onExport: () => void;
}

export function ShoppingListTable({
  items,
  totalCost,
  onMarkPurchased,
  onUnmarkPurchased,
  onRemoveItem,
  onExport
}: ShoppingListTableProps) {
  return (
    <div className="card">
      <div className="card-header">
        <span className="card-title">
          <ShoppingCart size={18} style={{ marginRight: 8 }} />
          Shopping List
          <span className="neutral" style={{ fontWeight: 400, marginLeft: 8 }}>
            ({items.length} items • {formatISK(totalCost)})
          </span>
        </span>
        {items.length > 0 && (
          <button
            className="btn btn-secondary"
            style={{ padding: '6px 12px' }}
            onClick={onExport}
          >
            <Copy size={14} style={{ marginRight: 6 }} /> Copy
          </button>
        )}
      </div>

      {items.length === 0 ? (
        <div className="empty-state" style={{ padding: 40 }}>
          <ShoppingCart size={48} style={{ opacity: 0.3, marginBottom: 12 }} />
          <p className="neutral">No items in this list yet.</p>
          <p className="neutral" style={{ fontSize: 12 }}>
            Add a product above and calculate materials.
          </p>
        </div>
      ) : (
        <div className="table-container">
          <table>
            <thead>
              <tr>
                <th style={{ width: 40 }}></th>
                <th>Item</th>
                <th style={{ textAlign: 'right' }}>Quantity</th>
                <th style={{ textAlign: 'right' }}>Unit Price</th>
                <th style={{ textAlign: 'right' }}>Total</th>
                <th style={{ width: 40 }}></th>
              </tr>
            </thead>
            <tbody>
              {items.map((item) => (
                <tr
                  key={item.type_id}
                  style={{ opacity: item.is_purchased ? 0.5 : 1 }}
                >
                  <td>
                    <button
                      className="btn-icon"
                      onClick={() =>
                        item.is_purchased
                          ? onUnmarkPurchased(item.id)
                          : onMarkPurchased(item.id)
                      }
                      style={{
                        color: item.is_purchased
                          ? 'var(--accent-green)'
                          : 'var(--text-secondary)',
                      }}
                    >
                      <Check size={16} />
                    </button>
                  </td>
                  <td style={{ textDecoration: item.is_purchased ? 'line-through' : 'none' }}>
                    {item.item_name}
                  </td>
                  <td style={{ textAlign: 'right' }}>{formatQuantity(item.quantity)}</td>
                  <td style={{ textAlign: 'right' }} className="isk">
                    {formatISK(item.target_price, false)}
                  </td>
                  <td style={{ textAlign: 'right' }} className="isk">
                    {formatISK((item.target_price || 0) * item.quantity)}
                  </td>
                  <td>
                    <button
                      className="btn-icon"
                      onClick={() => onRemoveItem(item.id)}
                    >
                      <Trash2 size={14} />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
            <tfoot>
              <tr style={{ background: 'var(--bg-dark)', fontWeight: 600 }}>
                <td colSpan={4} style={{ textAlign: 'right', padding: '12px 16px' }}>
                  Total
                </td>
                <td style={{ textAlign: 'right', padding: '12px 16px' }} className="isk">
                  {formatISK(totalCost)}
                </td>
                <td></td>
              </tr>
            </tfoot>
          </table>
        </div>
      )}
    </div>
  );
}
