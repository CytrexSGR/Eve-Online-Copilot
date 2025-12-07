# War Room Integration Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Connect War Room combat data with Item Detail page through clickable items and a new Combat Stats panel.

**Architecture:** Add API endpoint for item combat stats, create reusable CollapsiblePanel component, restructure ItemDetail with four panels (Overview, Combat Stats, Production, Market), make all War Room items clickable links.

**Tech Stack:** FastAPI (Python), React + TypeScript, TanStack Query, Lucide Icons

---

## Task 1: Backend - Add Item Combat Stats Endpoint

**Files:**
- Modify: `/home/cytrex/eve_copilot/war_analyzer.py`
- Modify: `/home/cytrex/eve_copilot/routers/war.py`

**Step 1: Add method to war_analyzer.py**

Add this method to the `WarAnalyzer` class in `/home/cytrex/eve_copilot/war_analyzer.py` before the singleton line:

```python
    def get_item_combat_stats(self, type_id: int, days: int = 7) -> dict:
        """Get combat stats for a single item (ship or module)"""
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # Check ships first
                cur.execute('''
                    SELECT
                        csl.region_id,
                        srm.region_name,
                        SUM(csl.quantity) as destroyed
                    FROM combat_ship_losses csl
                    JOIN system_region_map srm ON csl.region_id = srm.region_id
                    WHERE csl.ship_type_id = %s
                    AND csl.date >= CURRENT_DATE - %s
                    GROUP BY csl.region_id, srm.region_name
                    ORDER BY destroyed DESC
                ''', (type_id, days))
                ship_results = cur.fetchall()

                # Check items/modules
                cur.execute('''
                    SELECT
                        cil.region_id,
                        srm.region_name,
                        SUM(cil.quantity_destroyed) as destroyed
                    FROM combat_item_losses cil
                    JOIN system_region_map srm ON cil.region_id = srm.region_id
                    WHERE cil.item_type_id = %s
                    AND cil.date >= CURRENT_DATE - %s
                    GROUP BY cil.region_id, srm.region_name
                    ORDER BY destroyed DESC
                ''', (type_id, days))
                item_results = cur.fetchall()

                # Combine results (prefer ship data if exists)
                results = ship_results if ship_results else item_results

                if not results:
                    return {
                        'type_id': type_id,
                        'days': days,
                        'total_destroyed': 0,
                        'by_region': [],
                        'market_comparison': [],
                        'has_data': False
                    }

                by_region = [
                    {'region_id': r[0], 'region_name': r[1], 'destroyed': r[2]}
                    for r in results
                ]
                total_destroyed = sum(r[2] for r in results)

                # Get market stock for comparison
                region_keys = {
                    10000002: 'the_forge',
                    10000043: 'domain',
                    10000030: 'heimatar',
                    10000032: 'sinq_laison',
                    10000042: 'metropolis'
                }

                cur.execute('''
                    SELECT region_id, sell_volume
                    FROM market_prices
                    WHERE type_id = %s
                ''', (type_id,))
                market_data = {r[0]: r[1] for r in cur.fetchall()}

                market_comparison = []
                for r in by_region:
                    region_id = r['region_id']
                    stock = market_data.get(region_id, 0)
                    market_comparison.append({
                        'region': region_keys.get(region_id, str(region_id)),
                        'region_name': r['region_name'],
                        'destroyed': r['destroyed'],
                        'stock': stock,
                        'gap': stock - r['destroyed']
                    })

                # Get type name
                cur.execute('SELECT "typeName" FROM "invTypes" WHERE "typeID" = %s', (type_id,))
                name_row = cur.fetchone()
                type_name = name_row[0] if name_row else f"Type {type_id}"

                return {
                    'type_id': type_id,
                    'type_name': type_name,
                    'days': days,
                    'total_destroyed': total_destroyed,
                    'by_region': by_region,
                    'market_comparison': market_comparison,
                    'has_data': True
                }
```

**Step 2: Add API endpoint to routers/war.py**

Add this endpoint at the end of `/home/cytrex/eve_copilot/routers/war.py`:

```python
@router.get("/item/{type_id}/stats")
async def get_item_combat_stats(
    type_id: int,
    days: int = Query(7, ge=1, le=30)
):
    """Get combat stats for a specific item"""
    try:
        return war_analyzer.get_item_combat_stats(type_id, days)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

**Step 3: Verify backend works**

Run:
```bash
curl -s http://localhost:8000/api/war/item/4310/stats | python3 -m json.tool
```

Expected: JSON with combat stats for Tornado (type_id 4310)

**Step 4: Commit**

```bash
git add war_analyzer.py routers/war.py
git commit -m "feat(api): add item combat stats endpoint"
```

---

## Task 2: Frontend - Add API Function

**Files:**
- Modify: `/home/cytrex/eve_copilot/frontend/src/api.ts`

**Step 1: Add getItemCombatStats function**

Add to the end of `/home/cytrex/eve_copilot/frontend/src/api.ts`:

```typescript
export async function getItemCombatStats(typeId: number, days = 7) {
  const response = await api.get(`/api/war/item/${typeId}/stats`, { params: { days } });
  return response.data;
}
```

**Step 2: Commit**

```bash
git add frontend/src/api.ts
git commit -m "feat(frontend): add getItemCombatStats API function"
```

---

## Task 3: Frontend - Create CollapsiblePanel Component

**Files:**
- Create: `/home/cytrex/eve_copilot/frontend/src/components/CollapsiblePanel.tsx`

**Step 1: Create the component**

Create `/home/cytrex/eve_copilot/frontend/src/components/CollapsiblePanel.tsx`:

```tsx
import { useState } from 'react';
import { ChevronDown, ChevronRight, LucideIcon } from 'lucide-react';

interface CollapsiblePanelProps {
  title: string;
  icon: LucideIcon;
  defaultOpen?: boolean;
  children: React.ReactNode;
  badge?: string | number;
  badgeColor?: 'green' | 'red' | 'yellow' | 'blue';
}

export default function CollapsiblePanel({
  title,
  icon: Icon,
  defaultOpen = true,
  children,
  badge,
  badgeColor = 'blue'
}: CollapsiblePanelProps) {
  const [isOpen, setIsOpen] = useState(defaultOpen);

  const badgeColors = {
    green: 'var(--color-success)',
    red: 'var(--color-error)',
    yellow: 'var(--color-warning)',
    blue: 'var(--accent-blue)'
  };

  return (
    <div className="collapsible-panel">
      <button
        className="panel-header"
        onClick={() => setIsOpen(!isOpen)}
      >
        <div className="panel-title">
          {isOpen ? <ChevronDown size={18} /> : <ChevronRight size={18} />}
          <Icon size={18} />
          <span>{title}</span>
        </div>
        {badge !== undefined && (
          <span
            className="panel-badge"
            style={{ backgroundColor: badgeColors[badgeColor] }}
          >
            {badge}
          </span>
        )}
      </button>
      {isOpen && (
        <div className="panel-content">
          {children}
        </div>
      )}

      <style>{`
        .collapsible-panel {
          background: var(--bg-card);
          border: 1px solid var(--border-color);
          border-radius: 8px;
          margin-bottom: 12px;
          overflow: hidden;
        }

        .panel-header {
          width: 100%;
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 12px 16px;
          background: var(--bg-secondary);
          border: none;
          cursor: pointer;
          color: var(--text-primary);
          font-size: 14px;
          font-weight: 600;
        }

        .panel-header:hover {
          background: var(--bg-tertiary);
        }

        .panel-title {
          display: flex;
          align-items: center;
          gap: 8px;
        }

        .panel-badge {
          padding: 2px 8px;
          border-radius: 12px;
          font-size: 12px;
          font-weight: 600;
          color: white;
        }

        .panel-content {
          padding: 16px;
          border-top: 1px solid var(--border-color);
        }
      `}</style>
    </div>
  );
}
```

**Step 2: Commit**

```bash
git add frontend/src/components/CollapsiblePanel.tsx
git commit -m "feat(frontend): add CollapsiblePanel component"
```

---

## Task 4: Frontend - Create CombatStatsPanel Component

**Files:**
- Create: `/home/cytrex/eve_copilot/frontend/src/components/CombatStatsPanel.tsx`

**Step 1: Create the component**

Create `/home/cytrex/eve_copilot/frontend/src/components/CombatStatsPanel.tsx`:

```tsx
import { useQuery } from '@tanstack/react-query';
import { Swords } from 'lucide-react';
import { getItemCombatStats } from '../api';
import CollapsiblePanel from './CollapsiblePanel';

interface CombatStatsPanelProps {
  typeId: number;
  days?: number;
}

interface CombatStats {
  type_id: number;
  type_name: string;
  days: number;
  total_destroyed: number;
  by_region: Array<{
    region_id: number;
    region_name: string;
    destroyed: number;
  }>;
  market_comparison: Array<{
    region: string;
    region_name: string;
    destroyed: number;
    stock: number;
    gap: number;
  }>;
  has_data: boolean;
}

export default function CombatStatsPanel({ typeId, days = 7 }: CombatStatsPanelProps) {
  const { data, isLoading } = useQuery<CombatStats>({
    queryKey: ['combatStats', typeId, days],
    queryFn: () => getItemCombatStats(typeId, days),
  });

  const badgeValue = data?.has_data ? data.total_destroyed : undefined;
  const badgeColor = data?.has_data && data.total_destroyed > 0 ? 'red' : 'blue';

  return (
    <CollapsiblePanel
      title="Combat Stats"
      icon={Swords}
      defaultOpen={true}
      badge={badgeValue}
      badgeColor={badgeColor as 'red' | 'blue'}
    >
      {isLoading ? (
        <div className="loading-small">Loading combat data...</div>
      ) : !data?.has_data ? (
        <div className="no-data">
          <Swords size={24} style={{ opacity: 0.3 }} />
          <p>No recent combat data</p>
          <span className="no-data-hint">This item hasn't been destroyed in combat in the last {days} days</span>
        </div>
      ) : (
        <div className="combat-stats-content">
          <div className="combat-summary">
            <div className="combat-stat-big">
              <span className="stat-number">{data.total_destroyed.toLocaleString()}</span>
              <span className="stat-label">destroyed ({days}d)</span>
            </div>
          </div>

          <h4>By Region</h4>
          <div className="region-breakdown">
            {data.market_comparison.map((r) => (
              <div key={r.region} className="region-row">
                <span className="region-name">{r.region_name}</span>
                <div className="region-stats">
                  <span className="destroyed">{r.destroyed} lost</span>
                  <span className="stock">{r.stock} stock</span>
                  <span className={`gap ${r.gap >= 0 ? 'positive' : 'negative'}`}>
                    {r.gap >= 0 ? '+' : ''}{r.gap}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      <style>{`
        .loading-small {
          padding: 20px;
          text-align: center;
          color: var(--text-secondary);
        }

        .no-data {
          display: flex;
          flex-direction: column;
          align-items: center;
          padding: 24px;
          color: var(--text-secondary);
          text-align: center;
        }

        .no-data p {
          margin: 8px 0 4px;
          font-weight: 500;
        }

        .no-data-hint {
          font-size: 12px;
          opacity: 0.7;
        }

        .combat-stats-content h4 {
          margin: 16px 0 8px;
          font-size: 12px;
          text-transform: uppercase;
          color: var(--text-secondary);
        }

        .combat-summary {
          display: flex;
          gap: 16px;
        }

        .combat-stat-big {
          display: flex;
          flex-direction: column;
        }

        .stat-number {
          font-size: 32px;
          font-weight: 700;
          color: var(--color-error);
        }

        .stat-label {
          font-size: 12px;
          color: var(--text-secondary);
        }

        .region-breakdown {
          display: flex;
          flex-direction: column;
          gap: 8px;
        }

        .region-row {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 8px 12px;
          background: var(--bg-secondary);
          border-radius: 6px;
        }

        .region-name {
          font-weight: 500;
        }

        .region-stats {
          display: flex;
          gap: 16px;
          font-size: 13px;
        }

        .destroyed {
          color: var(--color-error);
        }

        .stock {
          color: var(--text-secondary);
        }

        .gap {
          font-weight: 600;
          min-width: 50px;
          text-align: right;
        }

        .gap.positive {
          color: var(--color-success);
        }

        .gap.negative {
          color: var(--color-error);
        }
      `}</style>
    </CollapsiblePanel>
  );
}
```

**Step 2: Commit**

```bash
git add frontend/src/components/CombatStatsPanel.tsx
git commit -m "feat(frontend): add CombatStatsPanel component"
```

---

## Task 5: Frontend - Restructure ItemDetail Page

**Files:**
- Modify: `/home/cytrex/eve_copilot/frontend/src/pages/ItemDetail.tsx`

**Step 1: Replace entire ItemDetail.tsx**

Replace the entire content of `/home/cytrex/eve_copilot/frontend/src/pages/ItemDetail.tsx`:

```tsx
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
```

**Step 2: Commit**

```bash
git add frontend/src/pages/ItemDetail.tsx
git commit -m "feat(frontend): restructure ItemDetail with collapsible panels"
```

---

## Task 6: Frontend - Make War Room Items Clickable

**Files:**
- Modify: `/home/cytrex/eve_copilot/frontend/src/pages/WarRoom.tsx`

**Step 1: Add Link import**

At the top of `/home/cytrex/eve_copilot/frontend/src/pages/WarRoom.tsx`, add `Link` to the react-router-dom import:

```tsx
import { Link } from 'react-router-dom';
```

**Step 2: Update Ships Destroyed list**

Find this block (around line 221-226):
```tsx
{demand?.ships_lost?.slice(0, 15).map((ship) => (
  <div key={ship.type_id} className="list-item">
    <span className="item-name">{ship.name}</span>
    <span className="item-value">{ship.quantity.toLocaleString()}</span>
  </div>
))}
```

Replace with:
```tsx
{demand?.ships_lost?.slice(0, 15).map((ship) => (
  <Link key={ship.type_id} to={`/item/${ship.type_id}`} className="list-item clickable">
    <span className="item-name">{ship.name}</span>
    <span className="item-value">{ship.quantity.toLocaleString()}</span>
  </Link>
))}
```

**Step 3: Update Top Ships Galaxy-Wide list**

Find this block (around line 239-246):
```tsx
{topShips?.map((ship) => (
  <div key={ship.type_id} className="list-item">
    <div>
      <span className="item-name">{ship.name}</span>
      <span className="item-detail">{ship.group}</span>
    </div>
    <span className="item-value">{ship.quantity.toLocaleString()}</span>
  </div>
))}
```

Replace with:
```tsx
{topShips?.map((ship) => (
  <Link key={ship.type_id} to={`/item/${ship.type_id}`} className="list-item clickable">
    <div>
      <span className="item-name">{ship.name}</span>
      <span className="item-detail">{ship.group}</span>
    </div>
    <span className="item-value">{ship.quantity.toLocaleString()}</span>
  </Link>
))}
```

**Step 4: Update Market Gaps list**

Find this block (around line 260-270):
```tsx
{demand?.market_gaps?.length ? (
  demand.market_gaps.map((item) => (
    <div key={item.type_id} className="list-item">
      <div>
        <span className="item-name">{item.name}</span>
        <span className="item-detail">
          Lost: {item.quantity.toLocaleString()} | Stock: {item.market_stock.toLocaleString()}
        </span>
      </div>
      <span className="item-value negative">-{item.gap.toLocaleString()}</span>
    </div>
  ))
```

Replace with:
```tsx
{demand?.market_gaps?.length ? (
  demand.market_gaps.map((item) => (
    <Link key={item.type_id} to={`/item/${item.type_id}`} className="list-item clickable">
      <div>
        <span className="item-name">{item.name}</span>
        <span className="item-detail">
          Lost: {item.quantity.toLocaleString()} | Stock: {item.market_stock.toLocaleString()}
        </span>
      </div>
      <span className="item-value negative">-{item.gap.toLocaleString()}</span>
    </Link>
  ))
```

**Step 5: Add clickable styles**

Add to the `<style>` block at the end of the component:

```css
.list-item.clickable {
  text-decoration: none;
  color: inherit;
  transition: background 0.15s;
}

.list-item.clickable:hover {
  background: var(--bg-tertiary);
}
```

**Step 6: Commit**

```bash
git add frontend/src/pages/WarRoom.tsx
git commit -m "feat(frontend): make War Room items clickable"
```

---

## Task 7: Build and Test

**Step 1: Build frontend**

```bash
cd /home/cytrex/eve_copilot/frontend && npm run build
```

Expected: Build succeeds without errors

**Step 2: Test full flow**

1. Open http://192.168.178.108:3000/war-room
2. Click on any ship in "Ships Destroyed" list
3. Verify navigation to `/item/{type_id}`
4. Verify all four panels display (Overview, Combat Stats, Production, Market)
5. Click "Add to List" - verify modal opens

**Step 3: Final commit**

```bash
git add -A
git commit -m "feat: complete War Room integration with Item Detail"
```

---

## Summary

| Task | Description | Files |
|------|-------------|-------|
| 1 | Backend API endpoint | war_analyzer.py, routers/war.py |
| 2 | Frontend API function | api.ts |
| 3 | CollapsiblePanel component | components/CollapsiblePanel.tsx |
| 4 | CombatStatsPanel component | components/CombatStatsPanel.tsx |
| 5 | Restructure ItemDetail | pages/ItemDetail.tsx |
| 6 | Make War Room clickable | pages/WarRoom.tsx |
| 7 | Build and test | - |
