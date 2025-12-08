import { useState, useMemo } from 'react';
import { BarChart3, ChevronDown, ChevronRight, MousePointer, Eye, RefreshCw, ArrowUpDown } from 'lucide-react';
import { formatISK, formatQuantity } from '../../../utils/format';
import type { RegionalComparison } from '../../../types/shopping';
import { REGION_NAMES, REGION_ORDER } from '../../../types/shopping';
import { ShoppingRouteDisplay } from './ShoppingRouteDisplay';

interface ComparisonViewProps {
  comparison: RegionalComparison | undefined;
  isLoading: boolean;
  onRefetch: () => void;
  onApplyOptimalRegions: () => void;
  onApplyRegionToAll: (region: string) => void;
  onSelectRegion: (itemId: number, region: string, price: number) => void;
  onViewOrders: (typeId: number, itemName: string, region: string) => void;
  isUpdating: boolean;
}

/**
 * Regional price comparison view with optimal route calculation
 */
export function ComparisonView({
  comparison,
  isLoading,
  onRefetch,
  onApplyOptimalRegions,
  onApplyRegionToAll,
  onSelectRegion,
  onViewOrders,
  isUpdating,
}: ComparisonViewProps) {
  const [showRegionTotals, setShowRegionTotals] = useState(true);
  const [interactionMode, setInteractionMode] = useState<'select' | 'orders'>('select');
  const [compareSort, setCompareSort] = useState<'name' | 'quantity'>('name');

  // Sort comparison items - stable sort prevents row jumping during selection
  const sortedComparisonItems = useMemo(() => {
    if (!comparison?.items) return [];
    return [...comparison.items].sort((a, b) => {
      if (compareSort === 'quantity') {
        return b.quantity - a.quantity; // Descending by quantity
      }
      return a.item_name.localeCompare(b.item_name); // Ascending by name
    });
  }, [comparison?.items, compareSort]);

  if (isLoading) {
    return (
      <div className="loading">
        <div className="spinner"></div>
        Loading regional prices...
      </div>
    );
  }

  if (!comparison?.items?.length) {
    return (
      <div className="card">
        <div className="empty-state">
          <p className="neutral">No items to compare.</p>
        </div>
      </div>
    );
  }

  return (
    <>
      {/* Region Totals Summary - Collapsible */}
      <div className="card" style={{ marginBottom: 16 }}>
        <div
          className="card-header"
          style={{ cursor: 'pointer', userSelect: 'none' }}
          onClick={() => setShowRegionTotals(!showRegionTotals)}
        >
          <span className="card-title">
            {showRegionTotals ? <ChevronDown size={18} /> : <ChevronRight size={18} />}
            <span style={{ marginLeft: 8 }}>Region Totals Summary</span>
          </span>
        </div>
        {showRegionTotals && (
          <div className="stats-grid" style={{ padding: 16 }}>
            {REGION_ORDER.map((region) => {
              const data = comparison.region_totals[region];
              const savings = comparison.optimal_route.savings_vs_single_region[region] || 0;
              const isOptimal = savings === 0 && data?.total === comparison.optimal_route.total_cost;
              return (
                <div
                  key={region}
                  className={`stat-card ${isOptimal ? 'best' : ''}`}
                  style={{
                    border: isOptimal ? '1px solid var(--accent-green)' : undefined,
                  }}
                >
                  <div className="stat-label">
                    {data?.display_name || region}
                    {data?.jumps !== undefined && (
                      <span className="neutral" style={{ fontWeight: 400, marginLeft: 4 }}>
                        ({data.jumps} jumps)
                      </span>
                    )}
                  </div>
                  <div className="stat-value isk">{formatISK(data?.total || 0)}</div>
                  {savings > 0 && (
                    <div className="negative" style={{ fontSize: 11 }}>
                      +{formatISK(savings)} vs optimal
                    </div>
                  )}
                  <button
                    className="btn btn-secondary"
                    style={{ marginTop: 8, padding: '4px 8px', fontSize: 11 }}
                    onClick={(e) => {
                      e.stopPropagation();
                      onApplyRegionToAll(region);
                    }}
                    disabled={isUpdating}
                  >
                    Apply All
                  </button>
                </div>
              );
            })}
            <div className="stat-card" style={{ border: '1px solid var(--accent-blue)' }}>
              <div className="stat-label">Optimal (Multi-Hub)</div>
              <div className="stat-value isk positive">{formatISK(comparison.optimal_route.total_cost)}</div>
              <button
                className="btn btn-primary"
                style={{ marginTop: 8, padding: '4px 8px', fontSize: 11 }}
                onClick={(e) => {
                  e.stopPropagation();
                  onApplyOptimalRegions();
                }}
                disabled={isUpdating}
              >
                Apply Optimal
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Comparison Table */}
      <div className="card">
        <div className="card-header">
          <span className="card-title">
            <BarChart3 size={18} style={{ marginRight: 8 }} />
            Regional Price Comparison
          </span>
          <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
            {/* Interaction Mode Toggle */}
            <div style={{ display: 'flex', background: 'var(--bg-dark)', borderRadius: 6, padding: 2 }}>
              <button
                className={`btn ${interactionMode === 'select' ? 'btn-primary' : 'btn-secondary'}`}
                style={{ padding: '4px 10px', borderRadius: 4, fontSize: 12, display: 'flex', alignItems: 'center', gap: 4 }}
                onClick={() => setInteractionMode('select')}
                title="Click cells to select region"
              >
                <MousePointer size={14} /> Select
              </button>
              <button
                className={`btn ${interactionMode === 'orders' ? 'btn-primary' : 'btn-secondary'}`}
                style={{ padding: '4px 10px', borderRadius: 4, fontSize: 12, display: 'flex', alignItems: 'center', gap: 4 }}
                onClick={() => setInteractionMode('orders')}
                title="Click cells to view orders"
              >
                <Eye size={14} /> Orders
              </button>
            </div>
            <button className="btn btn-secondary" style={{ padding: '4px 8px' }} onClick={onRefetch}>
              <RefreshCw size={14} />
            </button>
          </div>
        </div>
        <div className="table-container">
          <table>
            <thead>
              <tr>
                <th
                  style={{ cursor: 'pointer', userSelect: 'none' }}
                  onClick={() => setCompareSort('name')}
                  title="Sort by item name"
                >
                  Item {compareSort === 'name' && <ArrowUpDown size={12} style={{ marginLeft: 4, opacity: 0.7 }} />}
                </th>
                <th
                  style={{ cursor: 'pointer', userSelect: 'none' }}
                  onClick={() => setCompareSort('quantity')}
                  title="Sort by quantity (descending)"
                >
                  Qty {compareSort === 'quantity' && <ArrowUpDown size={12} style={{ marginLeft: 4, opacity: 0.7 }} />}
                </th>
                {REGION_ORDER.map((region) => (
                  <th key={region}>{REGION_NAMES[region]}</th>
                ))}
                <th>Selected</th>
              </tr>
            </thead>
            <tbody>
              {sortedComparisonItems.map((item) => (
                <tr key={item.id}>
                  <td>{item.item_name}</td>
                  <td>{formatQuantity(item.quantity)}</td>
                  {REGION_ORDER.map((region) => {
                    const data = item.regions[region];
                    const isCheapest = region === item.cheapest_region;
                    const isSelected = region === item.current_region;
                    return (
                      <td
                        key={region}
                        className={`isk ${isCheapest ? 'positive' : ''}`}
                        data-item-id={item.id}
                        data-type-id={item.type_id}
                        data-item-name={item.item_name}
                        data-region={region}
                        data-price={data?.unit_price || ''}
                        style={{
                          cursor: data?.unit_price ? 'pointer' : 'default',
                          background: isSelected ? 'var(--bg-hover)' : undefined,
                          borderLeft: isSelected ? '2px solid var(--accent-blue)' : undefined,
                        }}
                        onClick={(e) => {
                          e.stopPropagation();
                          e.preventDefault();
                          // Use data attributes to ensure correct item even during re-renders
                          const target = e.currentTarget;
                          const itemId = Number(target.dataset.itemId);
                          const typeId = Number(target.dataset.typeId);
                          const itemName = target.dataset.itemName || '';
                          const clickedRegion = target.dataset.region || '';
                          const price = target.dataset.price ? Number(target.dataset.price) : undefined;

                          if (!price) return;
                          if (isUpdating) return;

                          if (interactionMode === 'select') {
                            onSelectRegion(itemId, clickedRegion, price);
                          } else {
                            onViewOrders(typeId, itemName, clickedRegion);
                          }
                        }}
                        title={
                          interactionMode === 'select'
                            ? data?.has_stock
                              ? 'Click to select this region'
                              : 'Low stock - Click to select anyway'
                            : data?.has_stock
                            ? 'Click to view orders'
                            : 'Low stock - Click to view orders'
                        }
                      >
                        {data?.total ? (
                          <>
                            <div>{formatISK(data.total)}</div>
                            <div style={{ fontSize: 10, color: 'var(--text-secondary)' }}>
                              @{formatISK(data.unit_price || 0)}/u
                            </div>
                            <div className={`neutral ${!data.has_stock ? 'negative' : ''}`} style={{ fontSize: 10 }}>
                              {formatQuantity(data.volume)} avail
                            </div>
                          </>
                        ) : (
                          <span className="neutral">-</span>
                        )}
                      </td>
                    );
                  })}
                  <td>
                    {item.current_region ? (
                      <span className="badge badge-blue">
                        {REGION_NAMES[item.current_region] || item.current_region}
                      </span>
                    ) : (
                      <span className="neutral">-</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Current Shopping Route - based on selected regions */}
      <ShoppingRouteDisplay items={comparison.items} homeSystem={comparison.home_system} />
    </>
  );
}
