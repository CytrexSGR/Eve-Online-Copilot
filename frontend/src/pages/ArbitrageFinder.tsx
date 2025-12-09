import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { TrendingUp, ArrowRight, Package, Shield, AlertTriangle, Folder, FolderOpen, ChevronDown } from 'lucide-react';
import { getEnhancedArbitrage, type EnhancedArbitrageResponse, api } from '../api';
import { ItemsTable } from '../components/arbitrage/ItemsTable';

interface Item {
  typeID: number;
  typeName: string;
  groupID: number;
  volume: number | null;
  basePrice: number | null;
}

interface MarketTreeNode {
  id: number | null;
  count: number;
  children?: Record<string, MarketTreeNode>;
}

interface MarketTreeResponse {
  tree: Record<string, MarketTreeNode>;
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
  selected: { id: number | null; name: string; path: string[]; isLeaf: boolean } | null;
  onToggle: (path: string) => void;
  onSelect: (id: number | null, name: string, path: string[], isLeaf: boolean) => void;
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
          onSelect(node.id, name, currentPath, !hasChildren);
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

export default function ArbitrageFinder() {
  // Selected item state (replaces searchQuery + selectedItem)
  const [selectedItem, setSelectedItem] = useState<Item | null>(null);
  const [minProfit, setMinProfit] = useState(5);
  const [shipType, setShipType] = useState('industrial');

  // Market Group Tree state
  const [selectedGroup, setSelectedGroup] = useState<{ id: number | null; name: string; path: string[]; isLeaf: boolean } | null>(null);
  const [expandedNodes, setExpandedNodes] = useState<Record<string, boolean>>({});

  // Load market tree
  const { data: marketTree } = useQuery<MarketTreeResponse>({
    queryKey: ['marketTree'],
    queryFn: async () => {
      const response = await api.get('/api/hunter/market-tree');
      return response.data;
    },
  });

  // Load all items for selected group (using market_group_id since the tree uses market groups)
  const { data: groupItems, isLoading: isLoadingItems } = useQuery<Item[]>({
    queryKey: ['groupItems', selectedGroup?.id],
    queryFn: async () => {
      const response = await api.get('/api/items/search', {
        params: {
          q: '',
          market_group_id: selectedGroup!.id,
        },
      });
      return response.data.results;
    },
    enabled: !!selectedGroup?.id,
  });

  // Get enhanced arbitrage opportunities
  const { data: arbitrageData, isLoading, error } = useQuery<EnhancedArbitrageResponse>({
    queryKey: ['enhancedArbitrage', selectedItem?.typeID, minProfit, shipType],
    queryFn: () => getEnhancedArbitrage(selectedItem!.typeID, minProfit, shipType),
    enabled: !!selectedItem,
  });


  return (
    <div>
      <h1>Arbitrage Finder</h1>
      <p className="subtitle">Find profitable trading opportunities across regions with route planning and cargo optimization</p>

      {/* Top Panel: Market Groups Tree (Horizontal) */}
      <div className="card" style={{ marginBottom: '1rem', maxHeight: '300px', overflowY: 'auto' }}>
        <h3 style={{ margin: 0, marginBottom: '1rem' }}>Market Groups</h3>
        {marketTree && (
          <div>
            {Object.entries(marketTree.tree).map(([name, node]) => (
              <TreeNode
                key={name}
                name={name}
                node={node}
                level={0}
                expanded={expandedNodes}
                selected={selectedGroup}
                onToggle={(path) => {
                  setExpandedNodes(prev => ({
                    ...prev,
                    [path]: !prev[path]
                  }));
                }}
                onSelect={(id, name, path, isLeaf) => {
                  setSelectedGroup({ id, name, path, isLeaf });
                  setSelectedItem(null); // Clear selected item when changing group
                }}
                path={[]}
              />
            ))}
          </div>
        )}
      </div>

      {/* Bottom Panels: Items (left) and Arbitrage (right) */}
      <div style={{ display: 'flex', gap: '1rem', height: 'calc(100vh - 400px)' }}>

        {/* Center Panel: Items Table */}
        {selectedGroup ? (
          <ItemsTable
            items={groupItems || []}
            selectedItemId={selectedItem?.typeID || null}
            onSelectItem={setSelectedItem}
            groupName={selectedGroup.path.join(' > ')}
            isLoading={isLoadingItems}
          />
        ) : (
          <div className="card" style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <div style={{ textAlign: 'center', color: 'var(--text-muted)' }}>
              <Package size={48} style={{ marginBottom: '1rem', opacity: 0.5 }} />
              <p>Select a market group to view items</p>
            </div>
          </div>
        )}

        {/* Right Panel: Arbitrage Details */}
        {selectedItem ? (
          <div className="card" style={{ flex: 1.5, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
            <div style={{ padding: '1rem', borderBottom: '1px solid var(--border)' }}>
              <h3 style={{ margin: 0, marginBottom: '1rem' }}>
                Arbitrage Opportunities: {selectedItem.typeName}
              </h3>

              {/* Ship Type and Min Profit Controls */}
              <div style={{ display: 'flex', gap: '1rem', marginBottom: '1rem' }}>
                <div style={{ flex: 1 }}>
                  <label>Ship Type:</label>
                  <select
                    value={shipType}
                    onChange={(e) => setShipType(e.target.value)}
                    style={{ width: '100%' }}
                  >
                    {SHIP_TYPES.map(ship => (
                      <option key={ship.value} value={ship.value}>
                        {ship.label}
                      </option>
                    ))}
                  </select>
                </div>
                <div style={{ flex: 1 }}>
                  <label>Min Profit per Unit:</label>
                  <input
                    type="number"
                    value={minProfit}
                    onChange={(e) => setMinProfit(Number(e.target.value))}
                    min="0"
                    step="1"
                    style={{ width: '100%' }}
                  />
                </div>
              </div>

              {/* Item Info */}
              {arbitrageData && (
                <div style={{ display: 'flex', gap: '2rem', padding: '1rem', background: 'var(--background-alt)', borderRadius: '4px' }}>
                  <div>
                    <div style={{ fontSize: '0.875rem', color: 'var(--text-muted)' }}>Item Volume</div>
                    <div><strong>{arbitrageData.item_volume ? formatVolume(arbitrageData.item_volume) : 'N/A'}</strong></div>
                  </div>
                  <div>
                    <div style={{ fontSize: '0.875rem', color: 'var(--text-muted)' }}>Ship Capacity</div>
                    <div><strong>{formatVolume(arbitrageData.ship_capacity)}</strong></div>
                  </div>
                  <div>
                    <div style={{ fontSize: '0.875rem', color: 'var(--text-muted)' }}>Opportunities Found</div>
                    <div><strong>{arbitrageData.opportunities.length}</strong></div>
                  </div>
                </div>
              )}
            </div>

            {/* Opportunities Table */}
            <div style={{ flex: 1, overflow: 'auto' }}>
              {isLoading ? (
                <div style={{ padding: '2rem', textAlign: 'center' }}>
                  <div className="loading">Loading arbitrage opportunities...</div>
                </div>
              ) : error ? (
                <div style={{ padding: '2rem', textAlign: 'center', color: 'var(--negative)' }}>
                  Error loading opportunities: {(error as Error).message}
                </div>
              ) : arbitrageData && arbitrageData.opportunities.length > 0 ? (
                <table className="data-table">
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
                    {arbitrageData.opportunities.map((opp, idx) => {
                      const buyRegion = REGION_NAMES[opp.buy_region] || opp.buy_region;
                      const sellRegion = REGION_NAMES[opp.sell_region] || opp.sell_region;

                      return (
                        <tr key={idx}>
                          <td>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                              <span>{buyRegion}</span>
                              <ArrowRight size={14} />
                              <span>{sellRegion}</span>
                            </div>
                          </td>
                          <td>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                              {getSafetyIcon(opp.route?.safety || 'unknown')}
                              {getSafetyBadge(opp.route?.safety || 'unknown')}
                            </div>
                          </td>
                          <td>{opp.route?.jumps || 0}</td>
                          <td>{opp.route?.time_minutes || 0} min</td>
                          <td>{opp.cargo?.units_per_trip.toLocaleString() || 0}</td>
                          <td className="positive">{formatISK(opp.cargo?.gross_profit_per_trip || 0)}</td>
                          <td><strong className="positive">{formatISK(opp.profitability?.net_profit || 0)}</strong></td>
                          <td>{formatISK(opp.cargo?.isk_per_m3 || 0)}</td>
                          <td className="positive">{formatISK(opp.profitability?.profit_per_hour || 0)}</td>
                          <td className="positive">{opp.profitability?.roi_percent?.toFixed(1) || '0.0'}%</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              ) : (
                <div style={{ padding: '2rem', textAlign: 'center', color: 'var(--text-muted)' }}>
                  <TrendingUp size={48} style={{ marginBottom: '1rem', opacity: 0.5 }} />
                  <p>No profitable arbitrage opportunities found</p>
                  <p style={{ fontSize: '0.875rem' }}>Try adjusting the minimum profit or ship type</p>
                </div>
              )}
            </div>
          </div>
        ) : (
          <div className="card" style={{ flex: 1.5, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <div style={{ textAlign: 'center', color: 'var(--text-muted)' }}>
              <TrendingUp size={48} style={{ marginBottom: '1rem', opacity: 0.5 }} />
              <p>Select an item to view arbitrage opportunities</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
