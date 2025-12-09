import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Search, TrendingUp, ArrowRight, Ship, Package, Clock, Shield, AlertTriangle } from 'lucide-react';
import { getEnhancedArbitrage, searchItems, type EnhancedArbitrageResponse } from '../api';

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
  'The Forge': 'Jita',
  'Domain': 'Amarr',
  'Heimatar': 'Rens',
  'Sinq Laison': 'Dodixie',
  'Metropolis': 'Hek',
};

const SHIP_TYPES = [
  { value: 'industrial', label: 'Industrial (5,000 m³)', capacity: 5000 },
  { value: 'blockade_runner', label: 'Blockade Runner (10,000 m³)', capacity: 10000 },
  { value: 'deep_space_transport', label: 'Deep Space Transport (60,000 m³)', capacity: 60000 },
  { value: 'freighter', label: 'Freighter (1,000,000 m³)', capacity: 1000000 },
];

function formatISK(value: number): string {
  if (value >= 1_000_000_000) return `${(value / 1_000_000_000).toFixed(2)}B`;
  if (value >= 1_000_000) return `${(value / 1_000_000).toFixed(2)}M`;
  if (value >= 1_000) return `${(value / 1_000).toFixed(1)}K`;
  return value.toFixed(2);
}

function formatVolume(volume: number): string {
  if (volume >= 1_000_000) return `${(volume / 1_000_000).toFixed(2)}M m³`;
  if (volume >= 1_000) return `${(volume / 1_000).toFixed(1)}K m³`;
  return `${volume.toFixed(0)} m³`;
}

function getSafetyIcon(safety: string) {
  switch (safety) {
    case 'safe':
      return <Shield size={16} className="positive" />;
    case 'caution':
      return <AlertTriangle size={16} className="warning" />;
    case 'dangerous':
      return <AlertTriangle size={16} className="negative" />;
    default:
      return <Shield size={16} className="neutral" />;
  }
}

function getSafetyBadge(safety: string) {
  switch (safety) {
    case 'safe':
      return <span className="badge badge-green">HighSec</span>;
    case 'caution':
      return <span className="badge badge-yellow">LowSec</span>;
    case 'dangerous':
      return <span className="badge badge-red">NullSec</span>;
    default:
      return <span className="badge badge-blue">Unknown</span>;
  }
}

export default function ArbitrageFinder() {
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedItem, setSelectedItem] = useState<SearchResult | null>(null);
  const [minProfit, setMinProfit] = useState(5);
  const [shipType, setShipType] = useState('industrial');
  const [showResults, setShowResults] = useState(false);

  // Search items
  const { data: searchResults } = useQuery<SearchResult[]>({
    queryKey: ['itemSearch', searchQuery],
    queryFn: () => searchItems(searchQuery),
    enabled: searchQuery.length >= 2,
  });

  // Get enhanced arbitrage opportunities
  const { data: arbitrageData, isLoading, error } = useQuery<EnhancedArbitrageResponse>({
    queryKey: ['enhancedArbitrage', selectedItem?.typeID, minProfit, shipType],
    queryFn: () => getEnhancedArbitrage(selectedItem!.typeID, minProfit, shipType),
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
        <p>Find profitable trade routes between trade hubs with route planning and cargo optimization</p>
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
            <label>Ship Type</label>
            <select
              value={shipType}
              onChange={(e) => setShipType(e.target.value)}
              style={{ minWidth: 220 }}
            >
              {SHIP_TYPES.map((ship) => (
                <option key={ship.value} value={ship.value}>
                  {ship.label}
                </option>
              ))}
            </select>
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

        {selectedItem && arbitrageData && (
          <div style={{ marginTop: 16, padding: '12px 16px', background: 'var(--bg-secondary)', borderRadius: 8 }}>
            <div style={{ display: 'flex', gap: 24, fontSize: 14 }}>
              <div>
                <span className="neutral">Item: </span>
                <strong>{arbitrageData.item_name}</strong>
              </div>
              {arbitrageData.item_volume && (
                <div>
                  <Package size={14} style={{ marginRight: 4, verticalAlign: 'middle' }} />
                  <span className="neutral">Volume: </span>
                  <strong>{formatVolume(arbitrageData.item_volume)}</strong>
                </div>
              )}
              <div>
                <Ship size={14} style={{ marginRight: 4, verticalAlign: 'middle' }} />
                <span className="neutral">Cargo: </span>
                <strong>{formatVolume(arbitrageData.ship_capacity)}</strong>
              </div>
              <div>
                <span className="neutral">Opportunities: </span>
                <strong className="positive">{arbitrageData.opportunity_count}</strong>
              </div>
            </div>
          </div>
        )}
      </div>

      {selectedItem && (
        <div className="card">
          <h3 style={{ marginBottom: 16 }}>
            <TrendingUp size={18} style={{ marginRight: 8 }} />
            Enhanced Arbitrage Opportunities
          </h3>

          {isLoading ? (
            <div className="loading">
              <div className="spinner"></div>
              Calculating routes, cargo, and profitability...
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
                    <th>Route</th>
                    <th>Safety</th>
                    <th>Jumps</th>
                    <th>Time</th>
                    <th>Units/Trip</th>
                    <th>Profit/Trip</th>
                    <th>Net Profit</th>
                    <th>ISK/m³</th>
                    <th>Profit/Hour</th>
                    <th>ROI</th>
                  </tr>
                </thead>
                <tbody>
                  {arbitrageData.opportunities.map((opp, idx) => (
                    <tr key={idx}>
                      <td>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                          <span className="badge badge-blue">
                            {REGION_NAMES[opp.buy_region] || opp.buy_region}
                          </span>
                          <ArrowRight size={14} className="neutral" />
                          <span className="badge badge-green">
                            {REGION_NAMES[opp.sell_region] || opp.sell_region}
                          </span>
                        </div>
                      </td>
                      <td>
                        {opp.route ? (
                          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                            {getSafetyIcon(opp.route.safety)}
                            {getSafetyBadge(opp.route.safety)}
                          </div>
                        ) : (
                          <span className="neutral">-</span>
                        )}
                      </td>
                      <td className="neutral">
                        {opp.route ? `${opp.route.jumps} jumps` : '-'}
                      </td>
                      <td className="neutral">
                        {opp.route ? (
                          <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                            <Clock size={14} />
                            {opp.route.time_minutes}m
                          </div>
                        ) : (
                          '-'
                        )}
                      </td>
                      <td className="neutral">
                        {opp.cargo ? opp.cargo.units_per_trip.toLocaleString() : '-'}
                      </td>
                      <td className="isk positive">
                        {opp.cargo ? `+${formatISK(opp.cargo.gross_profit_per_trip)}` : '-'}
                      </td>
                      <td className="isk positive">
                        <strong>
                          {opp.profitability
                            ? `+${formatISK(opp.profitability.net_profit)}`
                            : '-'}
                        </strong>
                      </td>
                      <td className="isk">
                        {opp.cargo ? formatISK(opp.cargo.isk_per_m3) : '-'}
                      </td>
                      <td className="isk positive">
                        {opp.profitability?.profit_per_hour ? (
                          <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                            <Clock size={14} />
                            {formatISK(opp.profitability.profit_per_hour)}/h
                          </div>
                        ) : (
                          '-'
                        )}
                      </td>
                      <td>
                        <span
                          className={`badge ${
                            opp.profit_percent >= 50 ? 'badge-green' : 'badge-yellow'
                          }`}
                        >
                          {opp.profit_percent.toFixed(1)}%
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {arbitrageData && arbitrageData.opportunities.length > 0 && (
            <div style={{ marginTop: 16, padding: '12px 16px', background: 'var(--bg-secondary)', borderRadius: 8 }}>
              <div style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
                <strong>Note:</strong> Profit calculations include broker fees (3% buy + 3% sell) and sales tax (8%).
                Trip time assumes 2 minutes per jump (round trip = 2× route jumps).
              </div>
            </div>
          )}
        </div>
      )}

      {!selectedItem && (
        <div className="card">
          <div className="empty-state">
            <Search size={48} />
            <p>Search for an item to find enhanced arbitrage opportunities</p>
            <p className="neutral" style={{ fontSize: 14, marginTop: 8 }}>
              Now with route planning, cargo calculations, and profitability analysis
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
