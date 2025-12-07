import { useState } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { ArrowLeft, Package, TrendingUp, ChevronRight, ShoppingCart, Info } from 'lucide-react';
import { api } from '../api';
import { formatISK, formatQuantity } from '../utils/format';
import AddToListModal from '../components/AddToListModal';
import CollapsiblePanel from '../components/CollapsiblePanel';
import CombatStatsPanel from '../components/CombatStatsPanel';

interface ProductionData {
  type_id: number;
  item_name: string;
  me_level: number;
  materials: {
    type_id: number;
    name: string;
    base_quantity: number;
    adjusted_quantity: number;
    prices_by_region: Record<string, number>;
    volumes_by_region: Record<string, number>;
  }[];
  production_cost_by_region: Record<string, number>;
  cheapest_production_region: string;
  cheapest_production_cost: number;
  product_prices: Record<string, { lowest_sell: number; highest_buy: number }>;
  best_sell_region: string;
  best_sell_price: number;
}

interface ItemInfo {
  type_id: number;
  type_name: string;
  group_name: string;
  category_name: string;
}

const REGION_NAMES: Record<string, string> = {
  the_forge: 'Jita',
  domain: 'Amarr',
  heimatar: 'Rens',
  sinq_laison: 'Dodixie',
  metropolis: 'Hek',
};

export default function ItemDetail() {
  const { typeId } = useParams<{ typeId: string }>();
  const navigate = useNavigate();
  const [showAddToList, setShowAddToList] = useState(false);
  const numericTypeId = parseInt(typeId || '0', 10);

  // Fetch item basic info
  const { data: itemInfo } = useQuery<ItemInfo>({
    queryKey: ['itemInfo', typeId],
    queryFn: async () => {
      const response = await api.get(`/api/items/${typeId}`);
      return response.data;
    },
    enabled: !!typeId,
  });

  // Fetch production data
  const { data: prodData, isLoading: prodLoading } = useQuery<ProductionData>({
    queryKey: ['production', typeId],
    queryFn: async () => {
      const response = await api.get(`/api/production/optimize/${typeId}`, {
        params: { me: 10 }
      });
      return response.data;
    },
    enabled: !!typeId,
  });

  const bestProfit = prodData
    ? prodData.best_sell_price - prodData.cheapest_production_cost
    : 0;

  const itemName = prodData?.item_name || itemInfo?.type_name || `Item ${typeId}`;

  return (
    <div>
      {/* Breadcrumb */}
      <div className="breadcrumb">
        <Link to="/">Market Scanner</Link>
        <ChevronRight size={14} />
        <span>{itemName}</span>
      </div>

      {/* Overview Panel */}
      <CollapsiblePanel title="Overview" icon={Info} defaultOpen={true}>
        <div className="overview-content">
          <img
            src={`https://images.evetech.net/types/${typeId}/icon?size=64`}
            alt={itemName}
            className="item-icon"
            onError={(e) => { e.currentTarget.style.display = 'none'; }}
          />
          <div className="overview-info">
            <h1 className="item-name">{itemName}</h1>
            {itemInfo && (
              <p className="item-meta">
                {itemInfo.group_name} • {itemInfo.category_name}
              </p>
            )}
            {prodData && (
              <p className="item-meta">ME Level: {prodData.me_level}</p>
            )}
          </div>
          <button className="btn btn-primary add-to-list-btn" onClick={() => setShowAddToList(true)}>
            <ShoppingCart size={16} /> Add to List
          </button>
        </div>

        <style>{`
          .overview-content {
            display: flex;
            align-items: center;
            gap: 16px;
          }

          .item-icon {
            width: 64px;
            height: 64px;
            border-radius: 8px;
            background: var(--bg-secondary);
          }

          .overview-info {
            flex: 1;
          }

          .item-name {
            font-size: 24px;
            font-weight: 700;
            margin: 0;
          }

          .item-meta {
            margin: 4px 0 0;
            color: var(--text-secondary);
            font-size: 13px;
          }

          .add-to-list-btn {
            white-space: nowrap;
          }
        `}</style>
      </CollapsiblePanel>

      {/* Combat Stats Panel */}
      <CombatStatsPanel typeId={numericTypeId} days={7} />

      {/* Production Panel */}
      <CollapsiblePanel
        title="Production"
        icon={Package}
        defaultOpen={true}
        badge={prodData ? formatISK(prodData.cheapest_production_cost) : undefined}
      >
        {prodLoading ? (
          <div className="loading-small">Loading production data...</div>
        ) : !prodData ? (
          <div className="no-data">
            <Package size={24} style={{ opacity: 0.3 }} />
            <p>No blueprint data available</p>
          </div>
        ) : (
          <>
            {/* Summary Stats */}
            <div className="stats-row">
              <div className="stat-item">
                <span className="stat-label">Best Production Cost</span>
                <span className="stat-value">{formatISK(prodData.cheapest_production_cost)}</span>
                <span className="stat-hint">in {REGION_NAMES[prodData.cheapest_production_region]}</span>
              </div>
              <div className="stat-item">
                <span className="stat-label">Best Sell Price</span>
                <span className="stat-value positive">{formatISK(prodData.best_sell_price)}</span>
                <span className="stat-hint">in {REGION_NAMES[prodData.best_sell_region]}</span>
              </div>
              <div className="stat-item">
                <span className="stat-label">Max Profit</span>
                <span className={`stat-value ${bestProfit > 0 ? 'positive' : 'negative'}`}>
                  {bestProfit > 0 ? '+' : ''}{formatISK(bestProfit)}
                </span>
                <span className="stat-hint">
                  ROI: {prodData.cheapest_production_cost > 0
                    ? ((bestProfit / prodData.cheapest_production_cost) * 100).toFixed(1)
                    : 0}%
                </span>
              </div>
            </div>

            {/* Materials Table */}
            <h4>Required Materials</h4>
            <div className="table-container">
              <table>
                <thead>
                  <tr>
                    <th>Material</th>
                    <th>Qty</th>
                    {Object.keys(REGION_NAMES).map((region) => (
                      <th key={region}>{REGION_NAMES[region]}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {prodData.materials.map((mat) => {
                    const prices = Object.entries(mat.prices_by_region).filter(([_, p]) => p);
                    const cheapestRegion = prices.length > 0
                      ? prices.sort((a, b) => a[1] - b[1])[0][0]
                      : null;

                    return (
                      <tr key={mat.type_id}>
                        <td>
                          <Link to={`/item/${mat.type_id}`} className="material-link">
                            {mat.name}
                          </Link>
                        </td>
                        <td>{formatQuantity(mat.adjusted_quantity)}</td>
                        {Object.keys(REGION_NAMES).map((region) => {
                          const price = mat.prices_by_region[region];
                          const total = price ? price * mat.adjusted_quantity : null;
                          const isCheapest = region === cheapestRegion;

                          return (
                            <td key={region} className={`isk ${isCheapest ? 'positive' : ''}`}>
                              {formatISK(total)}
                            </td>
                          );
                        })}
                      </tr>
                    );
                  })}
                  <tr className="total-row">
                    <td colSpan={2}><strong>Total Cost</strong></td>
                    {Object.keys(REGION_NAMES).map((region) => {
                      const cost = prodData.production_cost_by_region[region];
                      const isCheapest = region === prodData.cheapest_production_region;
                      return (
                        <td key={region} className={`isk ${isCheapest ? 'positive' : ''}`}>
                          <strong>{formatISK(cost)}</strong>
                        </td>
                      );
                    })}
                  </tr>
                </tbody>
              </table>
            </div>
          </>
        )}

        <style>{`
          .loading-small, .no-data {
            padding: 24px;
            text-align: center;
            color: var(--text-secondary);
          }

          .no-data {
            display: flex;
            flex-direction: column;
            align-items: center;
          }

          .no-data p {
            margin: 8px 0 0;
          }

          .stats-row {
            display: flex;
            gap: 24px;
            margin-bottom: 20px;
          }

          .stat-item {
            display: flex;
            flex-direction: column;
          }

          .stat-label {
            font-size: 12px;
            color: var(--text-secondary);
          }

          .stat-value {
            font-size: 20px;
            font-weight: 700;
          }

          .stat-value.positive {
            color: var(--color-success);
          }

          .stat-value.negative {
            color: var(--color-error);
          }

          .stat-hint {
            font-size: 11px;
            color: var(--text-tertiary);
          }

          h4 {
            margin: 16px 0 8px;
            font-size: 12px;
            text-transform: uppercase;
            color: var(--text-secondary);
          }

          .total-row {
            background: var(--bg-secondary);
          }
        `}</style>
      </CollapsiblePanel>

      {/* Market Prices Panel */}
      <CollapsiblePanel
        title="Market Prices"
        icon={TrendingUp}
        defaultOpen={true}
        badge={prodData?.best_sell_region ? REGION_NAMES[prodData.best_sell_region] : undefined}
        badgeColor="green"
      >
        {!prodData ? (
          <div className="no-data">
            <TrendingUp size={24} style={{ opacity: 0.3 }} />
            <p>No market data available</p>
          </div>
        ) : (
          <div className="region-grid">
            {Object.entries(prodData.product_prices)
              .sort((a, b) => (b[1]?.highest_buy || 0) - (a[1]?.highest_buy || 0))
              .map(([region, prices]) => {
                const isBest = region === prodData.best_sell_region;
                const productionCost = prodData.production_cost_by_region[region] || prodData.cheapest_production_cost;
                const profitBuyOrder = (prices?.highest_buy || 0) - productionCost;

                return (
                  <div key={region} className={`region-card ${isBest ? 'best' : ''}`}>
                    <div className="region-name">
                      {REGION_NAMES[region] || region}
                      {isBest && <span className="badge badge-green">Best</span>}
                    </div>
                    <div className="price-row">
                      <div>
                        <div className="price-label">Sell Order</div>
                        <div className="price-value">{formatISK(prices?.lowest_sell)}</div>
                      </div>
                      <div>
                        <div className="price-label">Buy Order</div>
                        <div className="price-value positive">{formatISK(prices?.highest_buy)}</div>
                      </div>
                    </div>
                    <div className="profit-row">
                      <span className="price-label">Profit (Instant)</span>
                      <span className={profitBuyOrder > 0 ? 'positive' : 'negative'}>
                        {formatISK(profitBuyOrder)}
                      </span>
                    </div>
                  </div>
                );
              })}
          </div>
        )}

        <style>{`
          .region-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
            gap: 12px;
          }

          .region-card {
            padding: 12px;
            background: var(--bg-secondary);
            border-radius: 8px;
            border: 1px solid var(--border-color);
          }

          .region-card.best {
            border-color: var(--color-success);
          }

          .region-name {
            font-weight: 600;
            margin-bottom: 8px;
            display: flex;
            align-items: center;
            gap: 8px;
          }

          .badge-green {
            background: var(--color-success);
            color: white;
            padding: 2px 6px;
            border-radius: 4px;
            font-size: 10px;
          }

          .price-row {
            display: flex;
            justify-content: space-between;
            margin-bottom: 8px;
          }

          .price-label {
            font-size: 10px;
            color: var(--text-secondary);
          }

          .price-value {
            font-weight: 600;
          }

          .price-value.positive {
            color: var(--color-success);
          }

          .profit-row {
            padding-top: 8px;
            border-top: 1px solid var(--border-color);
            display: flex;
            justify-content: space-between;
            align-items: center;
          }

          .positive {
            color: var(--color-success);
          }

          .negative {
            color: var(--color-error);
          }
        `}</style>
      </CollapsiblePanel>

      {/* Back Button */}
      <button className="btn" onClick={() => navigate(-1)} style={{ marginTop: 16 }}>
        <ArrowLeft size={16} /> Back
      </button>

      {/* Add to Shopping List Modal */}
      {prodData && (
        <AddToListModal
          isOpen={showAddToList}
          onClose={() => setShowAddToList(false)}
          productionTypeId={prodData.type_id}
          me={prodData.me_level}
        />
      )}
    </div>
  );
}
