import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Search, Factory, Package, TrendingUp, Clock, ShoppingCart, Download, Zap, Info } from 'lucide-react';
import { api, searchItems } from '../api';
import { formatISK, formatQuantity } from '../utils/format';
import { Tooltip } from '../components/Tooltip';

// ============================================================
// Interfaces
// ============================================================

interface SearchResult {
  typeID: number;
  typeName: string;
}

interface Material {
  type_id: number;
  name: string;
  base_quantity: number;
  adjusted_quantity: number;
  me_savings: number;
}

interface MaterialsData {
  item_type_id: number;
  item_name: string;
  runs: number;
  me_level: number;
  materials: Material[];
  total_materials: number;
}

interface EconomicsData {
  type_id: number;
  item_name: string;
  region_id: number;
  region_name: string;
  costs: {
    material_cost: number;
    job_cost: number;
    total_cost: number;
  };
  market: {
    sell_price: number;
    buy_price: number;
  };
  profitability: {
    profit_sell: number;
    profit_buy: number;
    roi_sell_percent: number;
    roi_buy_percent: number;
  };
  production_time: number; // seconds
}

interface RegionComparison {
  region_id: number;
  region_name: string;
  roi_percent: number;
  profit: number;
}

interface RegionsData {
  type_id: number;
  item_name: string;
  regions: RegionComparison[];
  best_region: {
    region_id: number;
    region_name: string;
  };
}

interface Opportunity {
  type_id: number;
  name: string;
  roi_percent: number;
  profit: number;
}

interface OpportunitiesData {
  region_id: number;
  region_name: string;
  opportunities: Opportunity[];
  total_count: number;
}

// ============================================================
// Constants
// ============================================================

const REGIONS: Array<{ id: number; name: string; key: string }> = [
  { id: 10000002, name: 'The Forge (Jita)', key: 'the_forge' },
  { id: 10000043, name: 'Domain (Amarr)', key: 'domain' },
  { id: 10000030, name: 'Heimatar (Rens)', key: 'heimatar' },
  { id: 10000032, name: 'Sinq Laison (Dodixie)', key: 'sinq_laison' },
  { id: 10000042, name: 'Metropolis (Hek)', key: 'metropolis' },
];

const REGION_ID_TO_NAME: Record<number, string> = {
  10000002: 'The Forge',
  10000043: 'Domain',
  10000030: 'Heimatar',
  10000032: 'Sinq Laison',
  10000042: 'Metropolis',
};

// ============================================================
// Utility Functions
// ============================================================

function formatTime(seconds: number): string {
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  if (hours > 0) {
    return `${hours}h ${minutes}m`;
  }
  return `${minutes}m`;
}

// ============================================================
// Component
// ============================================================

export default function ProductionPlanner() {
  // State
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedItem, setSelectedItem] = useState<SearchResult | null>(null);
  const [showResults, setShowResults] = useState(false);
  const [meLevel, setMeLevel] = useState(10);
  const [teLevel, setTeLevel] = useState(20);
  const [runs, setRuns] = useState(1);
  const [selectedRegion, setSelectedRegion] = useState(10000002); // The Forge

  // ============================================================
  // API Queries
  // ============================================================

  // Search items
  const { data: searchResults } = useQuery<SearchResult[]>({
    queryKey: ['itemSearch', searchQuery],
    queryFn: () => searchItems(searchQuery),
    enabled: searchQuery.length >= 2,
    staleTime: 60000,
  });

  // Get materials
  const { data: materialsData, isLoading: materialsLoading } = useQuery<MaterialsData>({
    queryKey: ['production-materials-v2', selectedItem?.typeID, meLevel, runs],
    queryFn: async () => {
      const response = await api.get(`/api/production/chains/${selectedItem!.typeID}/materials`, {
        params: { me: meLevel, runs }
      });
      return response.data;
    },
    enabled: !!selectedItem,
    staleTime: 60000,
  });

  // Get economics for selected region
  const { data: economicsData, isLoading: economicsLoading } = useQuery<EconomicsData>({
    queryKey: ['production-economics-v2', selectedItem?.typeID, selectedRegion, meLevel, teLevel],
    queryFn: async () => {
      const response = await api.get(`/api/production/economics/${selectedItem!.typeID}`, {
        params: { region_id: selectedRegion, me: meLevel, te: teLevel }
      });
      return response.data;
    },
    enabled: !!selectedItem,
    retry: false, // Don't retry if no economics data
    staleTime: 300000, // 5 minutes
  });

  // Get multi-region comparison
  const { data: regionsData } = useQuery<RegionsData>({
    queryKey: ['production-regions-v2', selectedItem?.typeID],
    queryFn: async () => {
      const response = await api.get(`/api/production/economics/${selectedItem!.typeID}/regions`);
      return response.data;
    },
    enabled: !!selectedItem,
    retry: false,
    staleTime: 300000,
  });

  // Get similar profitable opportunities
  const { data: opportunitiesData } = useQuery<OpportunitiesData>({
    queryKey: ['production-opportunities-v2', selectedRegion],
    queryFn: async () => {
      const response = await api.get('/api/production/economics/opportunities', {
        params: {
          region_id: selectedRegion,
          min_roi: 10,
          min_profit: 1000000,
          limit: 10
        }
      });
      return response.data;
    },
    enabled: !!selectedItem, // Only fetch when item selected
    retry: false,
    staleTime: 300000,
  });

  // ============================================================
  // Handlers
  // ============================================================

  const handleSelectItem = (item: SearchResult) => {
    setSelectedItem(item);
    setSearchQuery(item.typeName);
    setShowResults(false);
  };

  const handleExportMultibuy = () => {
    if (!materialsData) return;
    const lines = materialsData.materials.map(
      mat => `${mat.name} ${mat.adjusted_quantity * runs}`
    );
    navigator.clipboard.writeText(lines.join('\n'));
    alert('Copied to clipboard in EVE Multibuy format!');
  };

  const handleAddToShoppingList = async () => {
    if (!selectedItem || !materialsData) return;

    try {
      // Create new shopping list
      const listResponse = await api.post('/api/shopping/lists', {
        name: `${selectedItem.typeName} Production (${runs} runs)`,
        corporation_id: 98785281 // MINDI
      });

      const listId = listResponse.data.id;

      // Add product item
      await api.post(`/api/shopping/lists/${listId}/items`, {
        type_id: selectedItem.typeID,
        item_name: selectedItem.typeName,
        quantity: runs,
        is_product: true,
        me_level: meLevel,
        runs: runs
      });

      alert(`Added to shopping list! Redirecting...`);
      window.location.href = `/shopping-lists?list=${listId}`;
    } catch (error) {
      console.error('Failed to create shopping list:', error);
      alert('Failed to create shopping list. See console for details.');
    }
  };

  // ============================================================
  // Computed Values
  // ============================================================

  const isLoading = materialsLoading || economicsLoading;

  // Calculate production time with TE savings
  const baseProductionTime = economicsData?.production_time || 0;
  const teSavings = Math.floor(baseProductionTime * (teLevel / 100));
  const actualProductionTime = baseProductionTime - teSavings;

  // ============================================================
  // Render
  // ============================================================

  return (
    <div>
      {/* Page Header */}
      <div className="page-header">
        <h1>Production Planner</h1>
        <p>Plan production with accurate costs, profitability, and time calculations</p>
      </div>

      {/* Search and Filters */}
      <div className="card">
        <div className="filters">
          {/* Item Search */}
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
                onBlur={() => setTimeout(() => setShowResults(false), 200)}
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

          {/* Region Selector */}
          <div className="filter-group">
            <label>Region</label>
            <select
              value={selectedRegion}
              onChange={(e) => setSelectedRegion(Number(e.target.value))}
            >
              {REGIONS.map((region) => (
                <option key={region.id} value={region.id}>
                  {region.name}
                </option>
              ))}
            </select>
          </div>

          {/* ME Level */}
          <div className="filter-group">
            <label>
              ME Level
              <Tooltip content={
                <div style={{ maxWidth: 200, whiteSpace: 'normal' }}>
                  <strong>Material Efficiency</strong><br />
                  Each level reduces material requirements by 1%<br />
                  ME 10 = 10% material savings
                </div>
              }>
                <Info size={14} style={{ marginLeft: 4, opacity: 0.6, cursor: 'help' }} />
              </Tooltip>
            </label>
            <select
              value={meLevel}
              onChange={(e) => setMeLevel(Number(e.target.value))}
            >
              {[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10].map((level) => (
                <option key={level} value={level}>ME {level}</option>
              ))}
            </select>
          </div>

          {/* TE Level */}
          <div className="filter-group">
            <label>
              TE Level
              <Tooltip content={
                <div style={{ maxWidth: 200, whiteSpace: 'normal' }}>
                  <strong>Time Efficiency</strong><br />
                  Each level reduces production time by 1%<br />
                  TE 20 = 20% faster production
                </div>
              }>
                <Info size={14} style={{ marginLeft: 4, opacity: 0.6, cursor: 'help' }} />
              </Tooltip>
            </label>
            <select
              value={teLevel}
              onChange={(e) => setTeLevel(Number(e.target.value))}
            >
              {[0, 2, 4, 6, 8, 10, 12, 14, 16, 18, 20].map((level) => (
                <option key={level} value={level}>TE {level}</option>
              ))}
            </select>
          </div>

          {/* Runs */}
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

      {/* Loading State */}
      {isLoading && (
        <div className="card">
          <div className="loading">
            <div className="spinner"></div>
            Calculating production plan...
          </div>
        </div>
      )}

      {/* Economics Data Available */}
      {economicsData && materialsData && (
        <>
          {/* Summary Stats */}
          <div className="stats-grid">
            <div className="stat-card">
              <div className="stat-label">Material Cost</div>
              <div className="stat-value isk">{formatISK(economicsData.costs.material_cost * runs)}</div>
            </div>
            <div className="stat-card">
              <div className="stat-label">Job Cost</div>
              <div className="stat-value isk">{formatISK(economicsData.costs.job_cost * runs)}</div>
            </div>
            <div className="stat-card">
              <div className="stat-label">Total Cost</div>
              <div className="stat-value isk">{formatISK(economicsData.costs.total_cost * runs)}</div>
            </div>
            <div className="stat-card">
              <div className="stat-label">Sell Price</div>
              <div className="stat-value isk positive">{formatISK(economicsData.market.sell_price * runs)}</div>
            </div>
            <div className="stat-card">
              <div className="stat-label">Profit (Sell)</div>
              <div className={`stat-value ${economicsData.profitability.profit_sell > 0 ? 'positive' : 'negative'}`}>
                {economicsData.profitability.profit_sell > 0 ? '+' : ''}
                {formatISK(economicsData.profitability.profit_sell * runs)}
              </div>
            </div>
            <div className="stat-card">
              <div className="stat-label">ROI</div>
              <div className={`stat-value ${economicsData.profitability.roi_sell_percent > 0 ? 'positive' : 'negative'}`}>
                {economicsData.profitability.roi_sell_percent.toFixed(1)}%
              </div>
            </div>
            <div className="stat-card">
              <div className="stat-label">Production Time</div>
              <div className="stat-value">
                <Clock size={18} style={{ display: 'inline', marginRight: 4 }} />
                {formatTime(actualProductionTime * runs)}
              </div>
              <div className="neutral" style={{ fontSize: 12, marginTop: 4 }}>
                per run: {formatTime(actualProductionTime)}
              </div>
            </div>
            <div className="stat-card">
              <div className="stat-label">Time Saved (TE{teLevel})</div>
              <div className="stat-value positive">
                <Zap size={18} style={{ display: 'inline', marginRight: 4 }} />
                {formatTime(teSavings * runs)}
              </div>
              <div className="neutral" style={{ fontSize: 12, marginTop: 4 }}>
                {teLevel}% reduction
              </div>
            </div>
          </div>

          {/* Multi-Region Comparison */}
          {regionsData && regionsData.regions.length > 0 && (
            <div className="card">
              <h3 style={{ marginBottom: 16 }}>
                <TrendingUp size={18} style={{ marginRight: 8 }} />
                Regional Comparison
              </h3>
              <div className="region-grid">
                {regionsData.regions.map((region) => (
                  <div
                    key={region.region_id}
                    className={`region-card ${region.region_id === regionsData.best_region.region_id ? 'best' : ''}`}
                  >
                    <div className="region-name">
                      {region.region_name}
                      {region.region_id === regionsData.best_region.region_id && (
                        <span className="badge badge-green" style={{ marginLeft: 8 }}>Best</span>
                      )}
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', gap: 16, marginTop: 8 }}>
                      <div>
                        <div className="neutral" style={{ fontSize: 12 }}>Profit</div>
                        <div className={`stat-value ${region.profit > 0 ? 'positive' : 'negative'}`} style={{ fontSize: 16 }}>
                          {formatISK(region.profit * runs)}
                        </div>
                      </div>
                      <div>
                        <div className="neutral" style={{ fontSize: 12 }}>ROI</div>
                        <div className={region.roi_percent > 0 ? 'positive' : 'negative'} style={{ fontSize: 16, fontWeight: 600 }}>
                          {region.roi_percent.toFixed(1)}%
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Materials Table */}
          <div className="card">
            <h3 style={{ marginBottom: 16 }}>
              <Package size={18} style={{ marginRight: 8 }} />
              Required Materials (×{runs} runs)
            </h3>
            <div className="table-container">
              <table>
                <thead>
                  <tr>
                    <th>Material</th>
                    <th>Base Qty</th>
                    <th>With ME{meLevel}</th>
                    <th>Total (×{runs})</th>
                    <th>ME Savings</th>
                  </tr>
                </thead>
                <tbody>
                  {materialsData.materials.map((mat) => (
                    <tr key={mat.type_id}>
                      <td><strong>{mat.name}</strong></td>
                      <td className="neutral">{formatQuantity(mat.base_quantity)}</td>
                      <td>{formatQuantity(mat.adjusted_quantity)}</td>
                      <td className="positive">{formatQuantity(mat.adjusted_quantity * runs)}</td>
                      <td className="positive">
                        {mat.me_savings > 0 ? '-' : ''}{formatQuantity(mat.me_savings * runs)}
                      </td>
                    </tr>
                  ))}
                  <tr style={{ fontWeight: 'bold', background: 'var(--bg-dark)' }}>
                    <td colSpan={3}>Total Materials</td>
                    <td className="positive">{materialsData.total_materials}</td>
                    <td></td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>

          {/* Similar Opportunities */}
          {opportunitiesData && opportunitiesData.opportunities.length > 0 && (
            <div className="card">
              <h3 style={{ marginBottom: 16 }}>
                <Factory size={18} style={{ marginRight: 8 }} />
                Similar Profitable Items in {REGION_ID_TO_NAME[selectedRegion]}
              </h3>
              <div className="table-container">
                <table>
                  <thead>
                    <tr>
                      <th>Item</th>
                      <th>ROI</th>
                      <th>Profit</th>
                      <th>Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    {opportunitiesData.opportunities.slice(0, 5).map((opp) => (
                      <tr key={opp.type_id}>
                        <td>{opp.name}</td>
                        <td className="positive">{opp.roi_percent.toFixed(1)}%</td>
                        <td className="isk positive">{formatISK(opp.profit)}</td>
                        <td>
                          <button
                            className="btn btn-primary btn-sm"
                            onClick={() => {
                              setSelectedItem({ typeID: opp.type_id, typeName: opp.name });
                              setSearchQuery(opp.name);
                            }}
                          >
                            View
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Action Buttons */}
          <div className="card">
            <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
              <button className="btn btn-primary" onClick={handleAddToShoppingList}>
                <ShoppingCart size={16} style={{ marginRight: 8 }} />
                Add to Shopping List
              </button>
              <button className="btn btn-secondary" onClick={handleExportMultibuy}>
                <Download size={16} style={{ marginRight: 8 }} />
                Export Multibuy
              </button>
            </div>
          </div>
        </>
      )}

      {/* Materials Only (No Economics Data) */}
      {materialsData && !economicsData && !economicsLoading && (
        <>
          <div className="card">
            <div className="alert alert-warning">
              <strong>Economics data not available</strong>
              <p className="neutral" style={{ marginTop: 8 }}>
                Material list is available, but profitability analysis requires economics data to be populated.
                Contact administrator to run the economics updater.
              </p>
            </div>
          </div>

          {/* Materials Table (Simple Version) */}
          <div className="card">
            <h3 style={{ marginBottom: 16 }}>
              <Package size={18} style={{ marginRight: 8 }} />
              Required Materials (×{runs} runs)
            </h3>
            <div className="table-container">
              <table>
                <thead>
                  <tr>
                    <th>Material</th>
                    <th>Base Qty</th>
                    <th>With ME{meLevel}</th>
                    <th>Total (×{runs})</th>
                    <th>ME Savings</th>
                  </tr>
                </thead>
                <tbody>
                  {materialsData.materials.map((mat) => (
                    <tr key={mat.type_id}>
                      <td><strong>{mat.name}</strong></td>
                      <td className="neutral">{formatQuantity(mat.base_quantity)}</td>
                      <td>{formatQuantity(mat.adjusted_quantity)}</td>
                      <td className="positive">{formatQuantity(mat.adjusted_quantity * runs)}</td>
                      <td className="positive">
                        {mat.me_savings > 0 ? '-' : ''}{formatQuantity(mat.me_savings * runs)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Action Buttons (Limited) */}
          <div className="card">
            <div style={{ display: 'flex', gap: 12 }}>
              <button className="btn btn-primary" onClick={handleAddToShoppingList}>
                <ShoppingCart size={16} style={{ marginRight: 8 }} />
                Add to Shopping List
              </button>
              <button className="btn btn-secondary" onClick={handleExportMultibuy}>
                <Download size={16} style={{ marginRight: 8 }} />
                Export Multibuy
              </button>
            </div>
          </div>
        </>
      )}

      {/* No Item Selected */}
      {!selectedItem && !isLoading && (
        <div className="card">
          <div className="empty-state">
            <Factory size={48} />
            <h3>Search for an item to plan production</h3>
            <p className="neutral">
              Enter an item name above to see production costs, profitability, and material requirements.
            </p>
          </div>
        </div>
      )}

      {/* Error State (No Blueprint) */}
      {selectedItem && !materialsData && !isLoading && (
        <div className="card">
          <div className="empty-state">
            <p>No blueprint found for this item.</p>
            <p className="neutral">Try searching for a manufacturable item (ships, modules, ammunition, etc.).</p>
          </div>
        </div>
      )}
    </div>
  );
}
