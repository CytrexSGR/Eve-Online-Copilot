import { useState, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { Play, Star, ArrowUpDown, Filter, ChevronRight, RefreshCw, ShoppingCart, Search, X, ChevronDown, Folder, FolderOpen } from 'lucide-react';
import { api } from '../api';
import { formatISK } from '../utils/format';
import BookmarkButton from '../components/BookmarkButton';
import AddToListModal from '../components/AddToListModal';

interface ScanResult {
  blueprint_id: number;
  product_id: number;
  product_name: string;
  category: string;
  group_name: string;
  difficulty: number;
  material_cost: number;
  sell_price: number;
  profit: number;
  roi: number;
  volume_available: number;
}

interface ScanResponse {
  scan_id: string;
  results: ScanResult[];
  summary: {
    total_scanned: number;
    profitable: number;
    avg_roi: number;
  };
  cached?: boolean;
}

interface MarketTreeNode {
  id: number | null;
  count: number;
  children?: Record<string, MarketTreeNode>;
}

interface MarketTreeResponse {
  tree: Record<string, MarketTreeNode>;
}

function DifficultyStars({ level }: { level: number }) {
  return (
    <div className="difficulty">
      {[1, 2, 3, 4, 5].map((i) => (
        <Star
          key={i}
          size={14}
          className={`star ${i > level ? 'empty' : ''}`}
          fill={i <= level ? 'currentColor' : 'none'}
        />
      ))}
    </div>
  );
}

// Tree node component
function TreeNode({
  name,
  node,
  level,
  expanded,
  selected,
  onToggle,
  onSelect,
  path,
}: {
  name: string;
  node: MarketTreeNode;
  level: number;
  expanded: Record<string, boolean>;
  selected: { id: number | null; name: string; path: string[] } | null;
  onToggle: (path: string) => void;
  onSelect: (id: number | null, name: string, path: string[]) => void;
  path: string[];
}) {
  const currentPath = [...path, name];
  const pathKey = currentPath.join(' > ');
  const isExpanded = expanded[pathKey];
  const hasChildren = node.children && Object.keys(node.children).length > 0;
  const isSelected = selected?.id === node.id && selected?.name === name;

  return (
    <div style={{ marginLeft: level * 16 }}>
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 4,
          padding: '4px 8px',
          cursor: 'pointer',
          borderRadius: 4,
          background: isSelected ? 'var(--accent-blue)' : 'transparent',
          color: isSelected ? 'white' : 'inherit',
        }}
        onClick={() => {
          if (hasChildren) {
            onToggle(pathKey);
          }
          onSelect(node.id, name, currentPath);
        }}
      >
        {hasChildren ? (
          isExpanded ? <FolderOpen size={16} /> : <Folder size={16} />
        ) : (
          <div style={{ width: 16 }} />
        )}
        <span style={{ flex: 1 }}>{name}</span>
        <span style={{ fontSize: 11, opacity: 0.7 }}>({node.count})</span>
        {hasChildren && (
          <ChevronDown
            size={14}
            style={{
              transform: isExpanded ? 'rotate(180deg)' : 'rotate(0)',
              transition: 'transform 0.2s',
            }}
          />
        )}
      </div>
      {hasChildren && isExpanded && (
        <div>
          {Object.entries(node.children!).map(([childName, childNode]) => (
            <TreeNode
              key={childName}
              name={childName}
              node={childNode}
              level={level + 1}
              expanded={expanded}
              selected={selected}
              onToggle={onToggle}
              onSelect={onSelect}
              path={currentPath}
            />
          ))}
        </div>
      )}
    </div>
  );
}

export default function MarketScanner() {
  const navigate = useNavigate();
  const [searchMode, setSearchMode] = useState<'profit' | 'browse'>('profit');
  const [filters, setFilters] = useState({
    minRoi: 15,
    minProfit: 500000,
    maxDifficulty: 3,
    top: 50,
    search: '',
  });
  const [selectedMarketGroup, setSelectedMarketGroup] = useState<{
    id: number | null;
    name: string;
    path: string[];
  } | null>(null);
  const [expandedNodes, setExpandedNodes] = useState<Record<string, boolean>>({});
  const [sortField, setSortField] = useState<keyof ScanResult>('profit');
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('desc');
  const [addToListItem, setAddToListItem] = useState<{ type_id: number; item_name: string } | null>(null);

  // Fetch market tree for browse mode
  const { data: treeData } = useQuery<MarketTreeResponse>({
    queryKey: ['marketTree'],
    queryFn: async () => {
      const response = await api.get('/api/hunter/market-tree');
      return response.data;
    },
    staleTime: 10 * 60 * 1000,
  });

  const { data, isLoading, error, refetch, isFetching } = useQuery<ScanResponse>({
    queryKey: [
      'marketScan',
      searchMode,
      searchMode === 'profit' ? filters.minRoi : 0,
      searchMode === 'profit' ? filters.minProfit : 0,
      filters.maxDifficulty,
      filters.top,
      selectedMarketGroup?.id,
      filters.search,
    ],
    queryFn: async () => {
      const params: Record<string, unknown> = {
        min_roi: searchMode === 'profit' ? filters.minRoi : 0,
        min_profit: searchMode === 'profit' ? filters.minProfit : 0,
        max_difficulty: filters.maxDifficulty,
        top: filters.top,
      };

      if (searchMode === 'browse' && selectedMarketGroup?.id) {
        params.market_group = selectedMarketGroup.id;
      }

      if (filters.search) {
        params.search = filters.search;
      }

      if (searchMode === 'browse') {
        params.sort_by = 'name';
      }

      const response = await api.get('/api/hunter/scan', { params });
      return response.data;
    },
    staleTime: 5 * 60 * 1000,
  });

  const filteredAndSorted = useMemo(() => {
    if (!data?.results) return [];

    let results = [...data.results];

    results.sort((a, b) => {
      const aVal = a[sortField] ?? 0;
      const bVal = b[sortField] ?? 0;
      if (typeof aVal === 'string' && typeof bVal === 'string') {
        return sortDir === 'desc' ? bVal.localeCompare(aVal) : aVal.localeCompare(bVal);
      }
      return sortDir === 'desc' ? (bVal as number) - (aVal as number) : (aVal as number) - (bVal as number);
    });

    return results;
  }, [data?.results, sortField, sortDir]);

  const handleSort = (field: keyof ScanResult) => {
    if (sortField === field) {
      setSortDir(sortDir === 'desc' ? 'asc' : 'desc');
    } else {
      setSortField(field);
      setSortDir('desc');
    }
  };

  const toggleNode = (path: string) => {
    setExpandedNodes((prev) => ({ ...prev, [path]: !prev[path] }));
  };

  const selectNode = (id: number | null, name: string, path: string[]) => {
    setSelectedMarketGroup({ id, name, path });
  };

  const clearSelection = () => {
    setSelectedMarketGroup(null);
    setFilters((f) => ({ ...f, search: '' }));
  };

  return (
    <div>
      <div className="page-header">
        <h1>Market Scanner</h1>
        <p>Find T1 manufacturing opportunities across New Eden</p>
      </div>

      {/* Mode Toggle */}
      <div className="card" style={{ marginBottom: 16 }}>
        <div style={{ display: 'flex', gap: 8 }}>
          <button
            className={`btn ${searchMode === 'profit' ? 'btn-primary' : 'btn-secondary'}`}
            onClick={() => setSearchMode('profit')}
          >
            <Filter size={16} />
            Profit Search
          </button>
          <button
            className={`btn ${searchMode === 'browse' ? 'btn-primary' : 'btn-secondary'}`}
            onClick={() => setSearchMode('browse')}
          >
            <Search size={16} />
            Browse
          </button>
        </div>
      </div>

      {/* Filters Card */}
      <div className="card">
        <div className="card-header">
          <span className="card-title">
            <Filter size={18} style={{ marginRight: 8 }} />
            Filter
          </span>
          <button
            className="btn btn-primary"
            onClick={() => refetch()}
            disabled={isFetching}
          >
            {isFetching ? <RefreshCw size={16} className="spinning" /> : <Play size={16} />}
            {isFetching ? 'Scanning...' : 'Search'}
          </button>
        </div>

        {/* Profit Mode Filters */}
        {searchMode === 'profit' && (
          <div className="filters">
            <div className="filter-group">
              <label>Min ROI %</label>
              <input
                type="number"
                value={filters.minRoi}
                onChange={(e) => setFilters({ ...filters, minRoi: Number(e.target.value) })}
              />
            </div>

            <div className="filter-group">
              <label>Min Profit (ISK)</label>
              <input
                type="number"
                value={filters.minProfit}
                onChange={(e) => setFilters({ ...filters, minProfit: Number(e.target.value) })}
              />
            </div>

            <div className="filter-group">
              <label>Max Difficulty</label>
              <select
                value={filters.maxDifficulty}
                onChange={(e) => setFilters({ ...filters, maxDifficulty: Number(e.target.value) })}
              >
                <option value={1}>1 - Minerals only</option>
                <option value={2}>2 - + PI/Salvage</option>
                <option value={3}>3 - + Moon Materials</option>
                <option value={4}>4 - + Exploration</option>
                <option value={5}>5 - All Materials</option>
              </select>
            </div>

            <div className="filter-group">
              <label>Results</label>
              <select
                value={filters.top}
                onChange={(e) => setFilters({ ...filters, top: Number(e.target.value) })}
              >
                <option value={25}>Top 25</option>
                <option value={50}>Top 50</option>
                <option value={100}>Top 100</option>
                <option value={200}>Top 200</option>
              </select>
            </div>
          </div>
        )}

        {/* Browse Mode - Tree + Search */}
        {searchMode === 'browse' && (
          <div style={{ display: 'flex', gap: 16, padding: '16px 0' }}>
            {/* Market Tree */}
            <div
              style={{
                width: 320,
                maxHeight: 400,
                overflow: 'auto',
                background: 'var(--bg-secondary)',
                borderRadius: 8,
                padding: 8,
              }}
            >
              <div style={{ marginBottom: 8, fontWeight: 600, padding: '4px 8px' }}>
                Market Groups
              </div>
              {treeData?.tree &&
                Object.entries(treeData.tree).map(([name, node]) => (
                  <TreeNode
                    key={name}
                    name={name}
                    node={node}
                    level={0}
                    expanded={expandedNodes}
                    selected={selectedMarketGroup}
                    onToggle={toggleNode}
                    onSelect={selectNode}
                    path={[]}
                  />
                ))}
            </div>

            {/* Right Side Filters */}
            <div style={{ flex: 1 }}>
              {/* Search Input */}
              <div className="filter-group" style={{ marginBottom: 16 }}>
                <label>Search by Name</label>
                <div style={{ display: 'flex', gap: 8 }}>
                  <input
                    type="text"
                    placeholder="e.g. Hobgoblin, Raven..."
                    value={filters.search}
                    onChange={(e) => setFilters({ ...filters, search: e.target.value })}
                    style={{ flex: 1 }}
                  />
                  {filters.search && (
                    <button className="btn btn-secondary" onClick={() => setFilters({ ...filters, search: '' })}>
                      <X size={16} />
                    </button>
                  )}
                </div>
              </div>

              {/* Selected Path */}
              {selectedMarketGroup && (
                <div style={{ marginBottom: 16 }}>
                  <label style={{ display: 'block', marginBottom: 8, color: 'var(--text-secondary)' }}>
                    Selected
                  </label>
                  <div
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: 8,
                      padding: '8px 12px',
                      background: 'var(--accent-blue)',
                      color: 'white',
                      borderRadius: 8,
                    }}
                  >
                    <span style={{ flex: 1 }}>{selectedMarketGroup.path.join(' > ')}</span>
                    <X size={16} style={{ cursor: 'pointer' }} onClick={clearSelection} />
                  </div>
                </div>
              )}

              {/* Other Filters */}
              <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap' }}>
                <div className="filter-group">
                  <label>Max Difficulty</label>
                  <select
                    value={filters.maxDifficulty}
                    onChange={(e) => setFilters({ ...filters, maxDifficulty: Number(e.target.value) })}
                  >
                    <option value={1}>1 - Minerals only</option>
                    <option value={2}>2 - + PI/Salvage</option>
                    <option value={3}>3 - + Moon Materials</option>
                    <option value={4}>4 - + Exploration</option>
                    <option value={5}>5 - All Materials</option>
                  </select>
                </div>

                <div className="filter-group">
                  <label>Results</label>
                  <select
                    value={filters.top}
                    onChange={(e) => setFilters({ ...filters, top: Number(e.target.value) })}
                  >
                    <option value={50}>50</option>
                    <option value={100}>100</option>
                    <option value={200}>200</option>
                    <option value={500}>500</option>
                  </select>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Stats */}
      {data?.summary && (
        <div className="stats-grid">
          <div className="stat-card">
            <div className="stat-label">Total Blueprints</div>
            <div className="stat-value">{data.summary.total_scanned.toLocaleString()}</div>
          </div>
          <div className="stat-card">
            <div className="stat-label">Found</div>
            <div className="stat-value positive">{data.summary.profitable}</div>
          </div>
          <div className="stat-card">
            <div className="stat-label">Avg ROI</div>
            <div className="stat-value positive">{data.summary.avg_roi?.toFixed(1)}%</div>
          </div>
          <div className="stat-card">
            <div className="stat-label">Showing</div>
            <div className="stat-value">{filteredAndSorted.length}</div>
            {data.cached && <div className="neutral" style={{ fontSize: 11 }}>from cache</div>}
          </div>
        </div>
      )}

      {/* Results Table */}
      <div className="card">
        {isLoading || isFetching ? (
          <div className="loading">
            <div className="spinner"></div>
            Scanning market data...
          </div>
        ) : error ? (
          <div className="empty-state">
            <p>Error loading data. Please try again.</p>
          </div>
        ) : !data?.results?.length ? (
          <div className="empty-state">
            <Search size={48} />
            <p>No results. {searchMode === 'browse' ? 'Select a market group or search.' : 'Adjust filters or click "Search".'}</p>
          </div>
        ) : (
          <div className="table-container">
            <table>
              <thead>
                <tr>
                  <th style={{ width: 40 }}></th>
                  <th style={{ width: 40 }}></th>
                  <th className="sortable" onClick={() => handleSort('product_name' as keyof ScanResult)}>
                    Product <ArrowUpDown size={14} />
                  </th>
                  <th className="sortable" onClick={() => handleSort('category' as keyof ScanResult)}>
                    Category
                  </th>
                  <th className="sortable" onClick={() => handleSort('group_name' as keyof ScanResult)}>
                    Group <ArrowUpDown size={14} />
                  </th>
                  <th>Difficulty</th>
                  <th className="sortable" onClick={() => handleSort('material_cost')}>
                    Material Cost <ArrowUpDown size={14} />
                  </th>
                  <th className="sortable" onClick={() => handleSort('sell_price')}>
                    Sell Price <ArrowUpDown size={14} />
                  </th>
                  <th className="sortable" onClick={() => handleSort('profit')}>
                    Profit <ArrowUpDown size={14} />
                  </th>
                  <th className="sortable" onClick={() => handleSort('roi')}>
                    ROI <ArrowUpDown size={14} />
                  </th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {filteredAndSorted.map((item) => (
                  <tr
                    key={item.product_id}
                    onClick={() => navigate(`/item/${item.product_id}`)}
                    style={{ cursor: 'pointer' }}
                  >
                    <td onClick={(e) => e.stopPropagation()}>
                      <BookmarkButton typeId={item.product_id} itemName={item.product_name} />
                    </td>
                    <td onClick={(e) => e.stopPropagation()}>
                      <button
                        className="btn-icon"
                        title="Add materials to shopping list"
                        onClick={() => setAddToListItem({ type_id: item.product_id, item_name: item.product_name })}
                        style={{ color: 'var(--accent-blue)' }}
                      >
                        <ShoppingCart size={16} />
                      </button>
                    </td>
                    <td>
                      <strong>{item.product_name}</strong>
                    </td>
                    <td>
                      <span className="badge badge-blue">{item.category}</span>
                    </td>
                    <td>
                      <span className="neutral" style={{ fontSize: 12 }}>{item.group_name}</span>
                    </td>
                    <td>
                      <DifficultyStars level={item.difficulty} />
                    </td>
                    <td className="isk">{formatISK(item.material_cost)}</td>
                    <td className="isk">{formatISK(item.sell_price)}</td>
                    <td className={`isk ${item.profit > 0 ? 'positive' : item.profit < 0 ? 'negative' : ''}`}>
                      {item.profit > 0 ? '+' : ''}{formatISK(item.profit)}
                    </td>
                    <td>
                      <span className={`badge ${item.roi >= 100 ? 'badge-green' : item.roi >= 50 ? 'badge-yellow' : item.roi >= 0 ? 'badge-blue' : 'badge-red'}`}>
                        {item.roi > 1000 ? '>1000%' : `${item.roi.toFixed(0)}%`}
                      </span>
                    </td>
                    <td>
                      <ChevronRight size={16} className="neutral" />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Add to Shopping List Modal */}
      <AddToListModal
        isOpen={!!addToListItem}
        onClose={() => setAddToListItem(null)}
        productionTypeId={addToListItem?.type_id}
      />
    </div>
  );
}
