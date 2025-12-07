import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Search, TrendingUp, ArrowRight, MapPin } from 'lucide-react';
import { api, searchItems } from '../api';

interface ArbitrageOpportunity {
  type_id: number;
  buy_region: string;
  buy_region_id: number;
  buy_price: number;
  sell_region: string;
  sell_region_id: number;
  sell_price: number;
  profit_per_unit: number;
  profit_percent: number;
  buy_volume_available: number;
  sell_volume_demand: number;
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

function formatISK(value: number): string {
  if (value >= 1_000_000_000) return `${(value / 1_000_000_000).toFixed(2)}B`;
  if (value >= 1_000_000) return `${(value / 1_000_000).toFixed(2)}M`;
  if (value >= 1_000) return `${(value / 1_000).toFixed(1)}K`;
  return value.toFixed(2);
}

export default function ArbitrageFinder() {
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedItem, setSelectedItem] = useState<SearchResult | null>(null);
  const [minProfit, setMinProfit] = useState(5);
  const [showResults, setShowResults] = useState(false);

  // Search items
  const { data: searchResults } = useQuery<SearchResult[]>({
    queryKey: ['itemSearch', searchQuery],
    queryFn: () => searchItems(searchQuery),
    enabled: searchQuery.length >= 2,
  });

  // Get arbitrage opportunities
  const { data: arbitrageData, isLoading, error } = useQuery<{
    opportunities: ArbitrageOpportunity[];
    item_name: string;
  }>({
    queryKey: ['arbitrage', selectedItem?.typeID, minProfit],
    queryFn: async () => {
      const response = await api.get(`/api/market/arbitrage/${selectedItem!.typeID}`, {
        params: { min_profit: minProfit },
      });
      return response.data;
    },
    enabled: !!selectedItem,
  });

  // Get price comparison for selected item
  const { data: priceData } = useQuery({
    queryKey: ['priceCompare', selectedItem?.typeID],
    queryFn: async () => {
      const response = await api.get(`/api/market/compare/${selectedItem!.typeID}`);
      return response.data;
    },
    enabled: !!selectedItem,
  });

  const handleSelectItem = (item: SearchResult) => {
    setSelectedItem(item);
    setSearchQuery(item.typeName);
    setShowResults(false);
  };

  return (
    <div>
      <div className="page-header">
        <h1>Arbitrage Finder</h1>
        <p>Find profitable trade routes between trade hubs</p>
      </div>

      <div className="card">
        <div className="filters">
          <div className="filter-group" style={{ flex: 1 }}>
            <label>Search Item</label>
            <div className="search-box">
              <Search size={18} />
              <input
                type="text"
                placeholder="Search for an item..."
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
            <label>Min Profit %</label>
            <input
              type="number"
              value={minProfit}
              onChange={(e) => setMinProfit(Number(e.target.value))}
              style={{ width: 100 }}
            />
          </div>
        </div>
      </div>

      {selectedItem && priceData && (
        <div className="card">
          <h3 style={{ marginBottom: 16 }}>
            <MapPin size={18} style={{ marginRight: 8 }} />
            Prices Across Regions: {priceData.item_name}
          </h3>
          <div className="region-grid">
            {Object.entries(priceData.prices_by_region).map(([region, data]: [string, any]) => (
              <div
                key={region}
                className={`region-card ${region === priceData.best_buy_region ? 'best' : ''}`}
              >
                <div className="region-name">
                  {REGION_NAMES[region] || region}
                  {region === priceData.best_buy_region && (
                    <span className="badge badge-green" style={{ marginLeft: 8 }}>Best Buy</span>
                  )}
                  {region === priceData.best_sell_region && (
                    <span className="badge badge-yellow" style={{ marginLeft: 8 }}>Best Sell</span>
                  )}
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', gap: 16 }}>
                  <div>
                    <div className="neutral" style={{ fontSize: 12 }}>Sell</div>
                    <div className="region-price">
                      {data.lowest_sell ? formatISK(data.lowest_sell) : '-'}
                    </div>
                  </div>
                  <div>
                    <div className="neutral" style={{ fontSize: 12 }}>Buy</div>
                    <div className="region-price positive">
                      {data.highest_buy ? formatISK(data.highest_buy) : '-'}
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {selectedItem && (
        <div className="card">
          <h3 style={{ marginBottom: 16 }}>
            <TrendingUp size={18} style={{ marginRight: 8 }} />
            Arbitrage Opportunities
          </h3>

          {isLoading ? (
            <div className="loading">
              <div className="spinner"></div>
              Analyzing trade routes...
            </div>
          ) : error ? (
            <div className="empty-state">
              <p>Error loading data. Please try again.</p>
            </div>
          ) : !arbitrageData?.opportunities?.length ? (
            <div className="empty-state">
              <p>No arbitrage opportunities found with {minProfit}% minimum profit.</p>
              <p className="neutral">Try lowering the minimum profit threshold.</p>
            </div>
          ) : (
            <div className="table-container">
              <table>
                <thead>
                  <tr>
                    <th>Buy From</th>
                    <th></th>
                    <th>Sell To</th>
                    <th>Buy Price</th>
                    <th>Sell Price</th>
                    <th>Profit/Unit</th>
                    <th>ROI</th>
                    <th>Volume</th>
                  </tr>
                </thead>
                <tbody>
                  {arbitrageData.opportunities.map((opp, idx) => (
                    <tr key={idx}>
                      <td>
                        <span className="badge badge-blue">
                          {REGION_NAMES[opp.buy_region] || opp.buy_region}
                        </span>
                      </td>
                      <td>
                        <ArrowRight size={16} className="neutral" />
                      </td>
                      <td>
                        <span className="badge badge-green">
                          {REGION_NAMES[opp.sell_region] || opp.sell_region}
                        </span>
                      </td>
                      <td className="isk">{formatISK(opp.buy_price)}</td>
                      <td className="isk">{formatISK(opp.sell_price)}</td>
                      <td className="isk positive">+{formatISK(opp.profit_per_unit)}</td>
                      <td>
                        <span className={`badge ${opp.profit_percent >= 50 ? 'badge-green' : 'badge-yellow'}`}>
                          {opp.profit_percent.toFixed(1)}%
                        </span>
                      </td>
                      <td className="neutral">
                        {Math.min(opp.buy_volume_available, opp.sell_volume_demand).toLocaleString()}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {!selectedItem && (
        <div className="card">
          <div className="empty-state">
            <Search size={48} />
            <p>Search for an item to find arbitrage opportunities</p>
          </div>
        </div>
      )}
    </div>
  );
}
