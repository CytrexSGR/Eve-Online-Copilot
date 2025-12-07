import { useState, useEffect, useCallback } from 'react';
import { ArrowLeft, Check, Loader2, Copy, Map, TrendingDown } from 'lucide-react';
import { api } from '../../api';
import { formatISK, formatQuantity } from '../../utils/format';
import type {
  ProductInfo,
  ShoppingItem,
  CompareRegionsResponse,
  REGION_NAMES as RegionNamesType,
  REGION_ORDER as RegionOrderType,
} from './types';

const REGION_NAMES: typeof RegionNamesType = {
  the_forge: 'Jita',
  domain: 'Amarr',
  heimatar: 'Rens',
  sinq_laison: 'Dodixie',
  metropolis: 'Hek',
};

const REGION_ORDER: typeof RegionOrderType = ['the_forge', 'domain', 'heimatar', 'sinq_laison', 'metropolis'];

interface RegionalComparisonStepProps {
  product: ProductInfo;
  shoppingList: ShoppingItem[];
  comparison: CompareRegionsResponse | null;
  onComparisonLoaded: (comparison: CompareRegionsResponse) => void;
  onBack: () => void;
  onDone: () => void;
}

export function RegionalComparisonStep({
  product,
  shoppingList,
  comparison,
  onComparisonLoaded,
  onBack,
  onDone,
}: RegionalComparisonStepProps) {
  const [isLoading, setIsLoading] = useState(!comparison);
  const [error, setError] = useState<string | null>(null);
  const [copiedRegion, setCopiedRegion] = useState<string | null>(null);

  // Fetch regional comparison
  useEffect(() => {
    if (comparison) return;

    const fetchComparison = async () => {
      setIsLoading(true);
      setError(null);

      try {
        const items = shoppingList.map(item => ({
          type_id: item.type_id,
          quantity: item.quantity,
        }));

        const response = await api.post<CompareRegionsResponse>('/api/shopping/wizard/compare-regions', {
          items,
        });

        onComparisonLoaded(response.data);
      } catch (err) {
        console.error('Failed to fetch regional comparison:', err);
        setError('Failed to load regional price comparison');
      }

      setIsLoading(false);
    };

    fetchComparison();
  }, [shoppingList, comparison, onComparisonLoaded]);

  // Export to clipboard in EVE Multibuy format
  const handleExport = useCallback((region?: string) => {
    if (!comparison) return;

    let itemsToExport: Array<{ item_name: string; quantity: number }> = [];

    if (region) {
      // Export items from specific region stop
      const stop = comparison.optimal_route.stops.find(s => s.region === region);
      if (stop) {
        itemsToExport = stop.items.map(item => ({
          item_name: item.item_name,
          quantity: item.quantity,
        }));
      }
    } else {
      // Export all items
      itemsToExport = shoppingList.map(item => ({
        item_name: item.item_name,
        quantity: item.quantity,
      }));
    }

    // Format for EVE Multibuy
    const content = itemsToExport
      .map(item => `${item.item_name} ${item.quantity}`)
      .join('\n');

    navigator.clipboard.writeText(content);
    setCopiedRegion(region || 'all');
    setTimeout(() => setCopiedRegion(null), 2000);
  }, [comparison, shoppingList]);

  if (isLoading) {
    return (
      <div style={{ padding: 24, textAlign: 'center' }}>
        <Loader2 size={32} className="spin" style={{ marginBottom: 16 }} />
        <h3>Loading Regional Prices...</h3>
        <p className="neutral">Fetching prices from all trade hubs</p>
      </div>
    );
  }

  if (error) {
    return (
      <div style={{ padding: 24 }}>
        <div style={{
          padding: 20,
          background: 'rgba(255, 100, 100, 0.1)',
          border: '1px solid var(--accent-red)',
          borderRadius: 8,
          color: 'var(--accent-red)',
          marginBottom: 24,
        }}>
          {error}
        </div>
        <button onClick={onBack} className="btn btn-secondary">
          <ArrowLeft size={18} /> Back
        </button>
      </div>
    );
  }

  if (!comparison) return null;

  const { optimal_route } = comparison;

  return (
    <div style={{ padding: 24 }}>
      <h2 style={{ marginBottom: 8 }}>Step 4: Regional Comparison</h2>
      <p className="neutral" style={{ marginBottom: 8 }}>
        Building: <strong>{product.runs}x {product.name}</strong>
      </p>
      <p className="neutral" style={{ marginBottom: 24 }}>
        Compare prices across trade hubs and plan your shopping route.
      </p>

      {/* Price Comparison Table */}
      <div style={{ marginBottom: 24, overflow: 'auto' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr style={{ background: 'var(--bg-dark)' }}>
              <th style={{ padding: '10px 16px', textAlign: 'left' }}>Item</th>
              <th style={{ padding: '10px 16px', textAlign: 'right' }}>Qty</th>
              {REGION_ORDER.map(region => (
                <th key={region} style={{ padding: '10px 16px', textAlign: 'right' }}>
                  {REGION_NAMES[region]}
                </th>
              ))}
              <th style={{ padding: '10px 16px', textAlign: 'center' }}>Best</th>
            </tr>
          </thead>
          <tbody>
            {comparison.comparison.map((item) => (
              <tr key={item.type_id} style={{ borderBottom: '1px solid var(--border)' }}>
                <td style={{ padding: '10px 16px' }}>{item.item_name}</td>
                <td style={{ padding: '10px 16px', textAlign: 'right' }}>
                  {formatQuantity(item.quantity)}
                </td>
                {REGION_ORDER.map(region => {
                  const regionData = item.prices[region];
                  const isBest = region === item.best_region;
                  return (
                    <td
                      key={region}
                      style={{
                        padding: '10px 16px',
                        textAlign: 'right',
                        background: isBest ? 'rgba(100, 200, 100, 0.1)' : undefined,
                      }}
                      className={isBest ? 'positive' : 'isk'}
                    >
                      {regionData?.total ? (
                        <>
                          <div>{formatISK(regionData.total)}</div>
                          <div style={{ fontSize: 10, opacity: 0.7 }}>
                            @{formatISK(regionData.price || 0)}/u
                          </div>
                        </>
                      ) : (
                        <span className="neutral">-</span>
                      )}
                    </td>
                  );
                })}
                <td style={{ padding: '10px 16px', textAlign: 'center' }}>
                  {item.best_region && (
                    <span className="badge badge-green" style={{ fontSize: 11 }}>
                      {REGION_NAMES[item.best_region]}
                    </span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Optimal Route Section */}
      <div style={{
        background: 'var(--bg-dark)',
        borderRadius: 8,
        padding: 20,
        marginBottom: 24,
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 16 }}>
          <Map size={20} style={{ color: 'var(--accent-blue)' }} />
          <h3 style={{ margin: 0 }}>Optimal Shopping Route</h3>
        </div>

        {/* Route Stops */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16, marginBottom: 20 }}>
          {optimal_route.stops.map((stop, idx) => (
            <div
              key={stop.region}
              style={{
                padding: 16,
                background: 'var(--bg-card)',
                borderRadius: 8,
                border: '1px solid var(--border)',
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                  <span style={{
                    width: 28,
                    height: 28,
                    borderRadius: '50%',
                    background: 'var(--accent-blue)',
                    color: 'white',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    fontWeight: 600,
                  }}>
                    {idx + 1}
                  </span>
                  <div>
                    <div style={{ fontWeight: 600, fontSize: 16 }}>{stop.region_name}</div>
                    <div className="neutral" style={{ fontSize: 12 }}>
                      {stop.items.length} items
                      {stop.jumps_from_previous && idx > 0 && (
                        <span> • {stop.jumps_from_previous} jumps from previous</span>
                      )}
                    </div>
                  </div>
                </div>
                <div style={{ textAlign: 'right' }}>
                  <div className="isk" style={{ fontWeight: 600, fontSize: 16 }}>
                    {formatISK(stop.subtotal)}
                  </div>
                  <button
                    onClick={() => handleExport(stop.region)}
                    className="btn btn-secondary"
                    style={{ padding: '4px 8px', fontSize: 11, marginTop: 4 }}
                  >
                    {copiedRegion === stop.region ? (
                      <><Check size={12} /> Copied</>
                    ) : (
                      <><Copy size={12} /> Copy</>
                    )}
                  </button>
                </div>
              </div>

              {/* Items in this stop */}
              <div style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))',
                gap: 8,
              }}>
                {stop.items.map((item) => (
                  <div
                    key={item.type_id}
                    style={{
                      padding: '6px 10px',
                      background: 'var(--bg-dark)',
                      borderRadius: 4,
                      fontSize: 12,
                      display: 'flex',
                      justifyContent: 'space-between',
                    }}
                  >
                    <span>{item.item_name}</span>
                    <span className="neutral">x{formatQuantity(item.quantity)}</span>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>

        {/* Savings Summary */}
        <div style={{
          padding: 16,
          background: 'rgba(100, 200, 100, 0.1)',
          borderRadius: 8,
          border: '1px solid var(--accent-green)',
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div>
              <div style={{ fontSize: 14, marginBottom: 4 }}>
                <strong>Total Cost (Multi-Hub):</strong>{' '}
                <span className="isk" style={{ fontSize: 18 }}>{formatISK(optimal_route.total)}</span>
              </div>
              <div className="neutral" style={{ fontSize: 12 }}>
                vs Jita-only: {formatISK(optimal_route.jita_only_total)}
              </div>
            </div>
            {optimal_route.savings > 0 && (
              <div style={{ textAlign: 'right' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 4, color: 'var(--accent-green)' }}>
                  <TrendingDown size={18} />
                  <span style={{ fontSize: 16, fontWeight: 600 }}>
                    Save {formatISK(optimal_route.savings)}
                  </span>
                </div>
                <div className="positive" style={{ fontSize: 12 }}>
                  ({optimal_route.savings_percent.toFixed(1)}% less)
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Action Buttons */}
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        paddingTop: 16,
        borderTop: '1px solid var(--border)',
      }}>
        <button
          onClick={onBack}
          className="btn btn-secondary"
          style={{ padding: '12px 24px', display: 'flex', alignItems: 'center', gap: 8 }}
        >
          <ArrowLeft size={18} />
          Back
        </button>

        <div style={{ display: 'flex', gap: 12 }}>
          <button
            onClick={() => handleExport()}
            className="btn btn-secondary"
            style={{ padding: '12px 24px', display: 'flex', alignItems: 'center', gap: 8 }}
          >
            {copiedRegion === 'all' ? (
              <><Check size={18} /> Copied!</>
            ) : (
              <><Copy size={18} /> Export All</>
            )}
          </button>

          <button
            onClick={onDone}
            className="btn btn-primary"
            style={{ padding: '12px 24px', display: 'flex', alignItems: 'center', gap: 8 }}
          >
            <Check size={18} />
            Done
          </button>
        </div>
      </div>
    </div>
  );
}

export default RegionalComparisonStep;
