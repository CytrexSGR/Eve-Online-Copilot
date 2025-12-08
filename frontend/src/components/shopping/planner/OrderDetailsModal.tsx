import { useQuery } from '@tanstack/react-query';
import { X } from 'lucide-react';
import { api } from '../../../api';
import { formatISK, formatQuantity } from '../../../utils/format';
import type { OrderSnapshotResponse } from '../../../types/shopping';
import { REGION_NAMES } from '../../../types/shopping';

interface OrderDetailsModalProps {
  typeId: number;
  itemName: string;
  region: string;
  onClose: () => void;
}

/**
 * Modal displaying detailed order book data for an item in a specific region
 */
export function OrderDetailsModal({
  typeId,
  itemName,
  region,
  onClose,
}: OrderDetailsModalProps) {
  const { data, isLoading } = useQuery<OrderSnapshotResponse>({
    queryKey: ['order-snapshots', typeId, region],
    queryFn: async () => {
      const response = await api.get(`/api/shopping/orders/${typeId}`, {
        params: { region },
      });
      return response.data;
    },
  });

  const regionData = data?.regions?.[region];

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
        zIndex: 1000,
      }}
      onClick={onClose}
    >
      <div
        className="card"
        style={{
          maxWidth: 600,
          maxHeight: '80vh',
          overflow: 'auto',
          padding: 20,
        }}
        onClick={(e) => e.stopPropagation()}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
          <h3 style={{ margin: 0 }}>
            {itemName} - {REGION_NAMES[region] || region}
          </h3>
          <button className="btn btn-secondary" onClick={onClose} style={{ padding: '4px 8px' }}>
            <X size={16} />
          </button>
        </div>

        {isLoading ? (
          <div className="neutral">Loading orders...</div>
        ) : !regionData || regionData.sells.length === 0 ? (
          <div className="neutral">No order data available</div>
        ) : (
          <>
            <h4 style={{ marginBottom: 8 }}>Sell Orders (Top 10)</h4>
            <table className="data-table" style={{ width: '100%', marginBottom: 16 }}>
              <thead>
                <tr>
                  <th>#</th>
                  <th style={{ textAlign: 'right' }}>Price</th>
                  <th style={{ textAlign: 'right' }}>Volume</th>
                  <th style={{ textAlign: 'right' }}>Issued</th>
                </tr>
              </thead>
              <tbody>
                {regionData.sells.map((order) => (
                  <tr key={order.rank}>
                    <td>{order.rank}</td>
                    <td style={{ textAlign: 'right' }}>{formatISK(order.price)}</td>
                    <td style={{ textAlign: 'right' }}>{formatQuantity(order.volume)}</td>
                    <td style={{ textAlign: 'right', fontSize: 11 }} className="neutral">
                      {order.issued ? new Date(order.issued).toLocaleDateString() : '-'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>

            {regionData.buys.length > 0 && (
              <>
                <h4 style={{ marginBottom: 8 }}>Buy Orders (Top 10)</h4>
                <table className="data-table" style={{ width: '100%' }}>
                  <thead>
                    <tr>
                      <th>#</th>
                      <th style={{ textAlign: 'right' }}>Price</th>
                      <th style={{ textAlign: 'right' }}>Volume</th>
                      <th style={{ textAlign: 'right' }}>Issued</th>
                    </tr>
                  </thead>
                  <tbody>
                    {regionData.buys.map((order) => (
                      <tr key={order.rank}>
                        <td>{order.rank}</td>
                        <td style={{ textAlign: 'right' }}>{formatISK(order.price)}</td>
                        <td style={{ textAlign: 'right' }}>{formatQuantity(order.volume)}</td>
                        <td style={{ textAlign: 'right', fontSize: 11 }} className="neutral">
                          {order.issued ? new Date(order.issued).toLocaleDateString() : '-'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </>
            )}

            {regionData.updated_at && (
              <div className="neutral" style={{ marginTop: 12, fontSize: 11 }}>
                Updated: {new Date(regionData.updated_at).toLocaleString()}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
