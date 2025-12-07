import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Search, Factory, Package, TrendingUp } from 'lucide-react';
import { api, searchItems } from '../api';

interface Material {
  type_id: number;
  name: string;
  base_quantity: number;
  adjusted_quantity: number;
  prices_by_region: Record<string, number>;
}

interface ProductionData {
  type_id: number;
  item_name: string;
  me_level: number;
  materials: Material[];
  production_cost_by_region: Record<string, number>;
  cheapest_production_region: string;
  cheapest_production_cost: number;
  product_prices: Record<string, { lowest_sell: number; highest_buy: number }>;
  best_sell_region: string;
  best_sell_price: number;
}

interface SearchResult {
  typeID: number;
  typeName: string;
}

const REGION_NAMES: Record<string, string> = {
  the_forge: 'Jita',
  domain: 'Amarr',
  heimatar: 'Rens',
  sinq_laison: 'Dodixie',
  metropolis: 'Hek',
};

function formatISK(value: number | null): string {
  if (value === null || value === undefined) return '-';
  if (value >= 1_000_000_000) return `${(value / 1_000_000_000).toFixed(2)}B`;
  if (value >= 1_000_000) return `${(value / 1_000_000).toFixed(2)}M`;
  if (value >= 1_000) return `${(value / 1_000).toFixed(1)}K`;
  return value.toFixed(2);
}

export default function ProductionPlanner() {
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedItem, setSelectedItem] = useState<SearchResult | null>(null);
  const [meLevel, setMeLevel] = useState(10);
  const [runs, setRuns] = useState(1);
  const [showResults, setShowResults] = useState(false);

  // Search items
  const { data: searchResults } = useQuery<SearchResult[]>({
    queryKey: ['itemSearch', searchQuery],
    queryFn: () => searchItems(searchQuery),
    enabled: searchQuery.length >= 2,
  });

  // Get production optimization data
  const { data: productionData, isLoading, error } = useQuery<ProductionData>({
    queryKey: ['production', selectedItem?.typeID, meLevel],
    queryFn: async () => {
      const response = await api.get(`/api/production/optimize/${selectedItem!.typeID}`, {
        params: { me: meLevel },
      });
      return response.data;
    },
    enabled: !!selectedItem,
  });

  const handleSelectItem = (item: SearchResult) => {
    setSelectedItem(item);
    setSearchQuery(item.typeName);
    setShowResults(false);
  };

  // Calculate profit for best route
  const bestProfit = productionData
    ? productionData.best_sell_price - productionData.cheapest_production_cost
    : 0;
  const bestRoi = productionData && productionData.cheapest_production_cost > 0
    ? (bestProfit / productionData.cheapest_production_cost) * 100
    : 0;

  return (
    <div>
      <div className="page-header">
        <h1>Production Planner</h1>
        <p>Optimize material costs and find the best production & sales regions</p>
      </div>

      <div className="card">
        <div className="filters">
          <div className="filter-group" style={{ flex: 1 }}>
            <label>Search Item</label>
            <div className="search-box">
              <Search size={18} />
              <input
                type="text"
                placeholder="Search for an item to produce..."
                value={searchQuery}
                onChange={(e) => {
                  setSearchQuery(e.target.value);
                  setShowResults(true);
                }}
                onFocus={() => setShowResults(true)}
              />
              {showResults && searchResults && searchResults.length > 0 && (
                <div className="search-results">
                  {searchResults.slice(0, 10).map((item) => (
                    <div
                      key={item.typeID}
                      className="search-result-item"
                      onClick={() => handleSelectItem(item)}
                    >
                      {item.typeName}
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          <div className="filter-group">
            <label>ME Level</label>
            <select
              value={meLevel}
              onChange={(e) => setMeLevel(Number(e.target.value))}
            >
              {[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10].map((level) => (
                <option key={level} value={level}>ME {level}</option>
              ))}
            </select>
          </div>

          <div className="filter-group">
            <label>Runs</label>
            <input
              type="number"
              value={runs}
              onChange={(e) => setRuns(Math.max(1, Number(e.target.value)))}
              min={1}
              style={{ width: 80 }}
            />
          </div>
        </div>
      </div>

      {isLoading && (
        <div className="card">
          <div className="loading">
            <div className="spinner"></div>
            Calculating optimal production...
          </div>
        </div>
      )}

      {error && (
        <div className="card">
          <div className="empty-state">
            <p>No blueprint found for this item.</p>
            <p className="neutral">Try searching for a manufacturable item.</p>
          </div>
        </div>
      )}

      {productionData && (
        <>
          {/* Summary Stats */}
          <div className="stats-grid">
            <div className="stat-card">
              <div className="stat-label">Best Production Cost</div>
              <div className="stat-value isk">
                {formatISK(productionData.cheapest_production_cost * runs)}
              </div>
              <div className="neutral" style={{ fontSize: 12, marginTop: 4 }}>
                in {REGION_NAMES[productionData.cheapest_production_region]}
              </div>
            </div>
            <div className="stat-card">
              <div className="stat-label">Best Sell Price</div>
              <div className="stat-value isk positive">
                {formatISK(productionData.best_sell_price * runs)}
              </div>
              <div className="neutral" style={{ fontSize: 12, marginTop: 4 }}>
                in {REGION_NAMES[productionData.best_sell_region]}
              </div>
            </div>
            <div className="stat-card">
              <div className="stat-label">Profit</div>
              <div className={`stat-value ${bestProfit > 0 ? 'positive' : 'negative'}`}>
                {bestProfit > 0 ? '+' : ''}{formatISK(bestProfit * runs)}
              </div>
            </div>
            <div className="stat-card">
              <div className="stat-label">ROI</div>
              <div className={`stat-value ${bestRoi > 0 ? 'positive' : 'negative'}`}>
                {bestRoi.toFixed(1)}%
              </div>
            </div>
          </div>

          {/* Production Cost by Region */}
          <div className="card">
            <h3 style={{ marginBottom: 16 }}>
              <Factory size={18} style={{ marginRight: 8 }} />
              Production Cost by Region
            </h3>
            <div className="region-grid">
              {Object.entries(productionData.production_cost_by_region)
                .sort((a, b) => (a[1] || Infinity) - (b[1] || Infinity))
                .map(([region, cost]) => (
                  <div
                    key={region}
                    className={`region-card ${region === productionData.cheapest_production_region ? 'best' : ''}`}
                  >
                    <div className="region-name">
                      {REGION_NAMES[region] || region}
                      {region === productionData.cheapest_production_region && (
                        <span className="badge badge-green" style={{ marginLeft: 8 }}>Cheapest</span>
                      )}
                    </div>
                    <div className="region-price">
                      {formatISK(cost ? cost * runs : null)}
                    </div>
                  </div>
                ))}
            </div>
          </div>

          {/* Sell Prices by Region */}
          <div className="card">
            <h3 style={{ marginBottom: 16 }}>
              <TrendingUp size={18} style={{ marginRight: 8 }} />
              Sell Prices by Region
            </h3>
            <div className="region-grid">
              {Object.entries(productionData.product_prices)
                .sort((a, b) => (b[1]?.highest_buy || 0) - (a[1]?.highest_buy || 0))
                .map(([region, prices]) => (
                  <div
                    key={region}
                    className={`region-card ${region === productionData.best_sell_region ? 'best' : ''}`}
                  >
                    <div className="region-name">
                      {REGION_NAMES[region] || region}
                      {region === productionData.best_sell_region && (
                        <span className="badge badge-green" style={{ marginLeft: 8 }}>Best</span>
                      )}
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', gap: 16 }}>
                      <div>
                        <div className="neutral" style={{ fontSize: 12 }}>Sell Order</div>
                        <div className="region-price">
                          {formatISK(prices?.lowest_sell ? prices.lowest_sell * runs : null)}
                        </div>
                      </div>
                      <div>
                        <div className="neutral" style={{ fontSize: 12 }}>Buy Order</div>
                        <div className="region-price positive">
                          {formatISK(prices?.highest_buy ? prices.highest_buy * runs : null)}
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
            </div>
          </div>

          {/* Materials Table */}
          <div className="card">
            <h3 style={{ marginBottom: 16 }}>
              <Package size={18} style={{ marginRight: 8 }} />
              Required Materials (x{runs})
            </h3>
            <div className="table-container">
              <table>
                <thead>
                  <tr>
                    <th>Material</th>
                    <th>Base Qty</th>
                    <th>With ME{meLevel}</th>
                    <th>Total Needed</th>
                    {Object.keys(REGION_NAMES).map((region) => (
                      <th key={region}>{REGION_NAMES[region]}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {productionData.materials.map((mat) => {
                    const cheapestRegion = Object.entries(mat.prices_by_region)
                      .filter(([_, price]) => price !== null)
                      .sort((a, b) => a[1] - b[1])[0]?.[0];

                    return (
                      <tr key={mat.type_id}>
                        <td><strong>{mat.name}</strong></td>
                        <td className="neutral">{mat.base_quantity}</td>
                        <td>{mat.adjusted_quantity}</td>
                        <td className="positive">{mat.adjusted_quantity * runs}</td>
                        {Object.keys(REGION_NAMES).map((region) => {
                          const price = mat.prices_by_region[region];
                          const isCheapest = region === cheapestRegion;
                          return (
                            <td
                              key={region}
                              className={`isk ${isCheapest ? 'positive' : ''}`}
                            >
                              {formatISK(price ? price * mat.adjusted_quantity * runs : null)}
                            </td>
                          );
                        })}
                      </tr>
                    );
                  })}
                  <tr style={{ fontWeight: 'bold', background: 'var(--bg-dark)' }}>
                    <td colSpan={4}>Total</td>
                    {Object.keys(REGION_NAMES).map((region) => {
                      const cost = productionData.production_cost_by_region[region];
                      const isCheapest = region === productionData.cheapest_production_region;
                      return (
                        <td key={region} className={`isk ${isCheapest ? 'positive' : ''}`}>
                          {formatISK(cost ? cost * runs : null)}
                        </td>
                      );
                    })}
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}

      {!selectedItem && !isLoading && (
        <div className="card">
          <div className="empty-state">
            <Factory size={48} />
            <p>Search for an item to plan production</p>
          </div>
        </div>
      )}
    </div>
  );
}
