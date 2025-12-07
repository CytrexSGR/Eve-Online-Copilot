import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { ShoppingCart, Plus, Trash2, Check, Copy, ChevronRight, X, Map, BarChart3, RefreshCw, MousePointer, Eye } from 'lucide-react';
import { api } from '../api';
import { formatISK, formatQuantity } from '../utils/format';

interface ShoppingList {
  id: number;
  name: string;
  status: string;
  total_cost: number | null;
  item_count: number;
  purchased_count: number;
  created_at: string;
}

interface ShoppingItem {
  id: number;
  type_id: number;
  item_name: string;
  quantity: number;
  target_region: string | null;
  target_price: number | null;
  actual_price: number | null;
  is_purchased: boolean;
}

interface ShoppingListDetail extends ShoppingList {
  items: ShoppingItem[];
}

interface RegionData {
  unit_price: number | null;
  total: number | null;
  volume: number;
  has_stock: boolean;
}

interface ComparisonItem {
  id: number;
  type_id: number;
  item_name: string;
  quantity: number;
  current_region: string | null;
  current_price: number | null;
  regions: Record<string, RegionData>;
  cheapest_region: string | null;
  cheapest_price: number | null;
}

interface RegionalComparison {
  list: { id: number; name: string; status: string };
  items: ComparisonItem[];
  region_totals: Record<string, { total: number; display_name: string; jumps?: number; travel_time?: string }>;
  optimal_route: {
    regions: Record<string, { item_name: string; quantity: number; price: number; total: number }[]>;
    total_cost: number;
    savings_vs_single_region: Record<string, number>;
  };
  home_system: string;
}

interface RouteSystem {
  name: string;
  security: number;
}

interface RouteLeg {
  from: string;
  to: string;
  jumps: number;
  systems?: RouteSystem[];
}

interface ShoppingRoute {
  total_jumps: number;
  route: RouteLeg[];
  order: string[];
  error?: string;
}

interface OrderSnapshot {
  rank: number;
  price: number;
  volume: number;
  location_id: number;
  issued: string | null;
}

interface OrderRegionData {
  display_name: string;
  sells: OrderSnapshot[];
  buys: OrderSnapshot[];
  updated_at: string | null;
}

interface OrderSnapshotResponse {
  type_id: number;
  regions: Record<string, OrderRegionData>;
}

const REGION_NAMES: Record<string, string> = {
  the_forge: 'Jita',
  domain: 'Amarr',
  heimatar: 'Rens',
  sinq_laison: 'Dodixie',
  metropolis: 'Hek',
};

const REGION_ORDER = ['the_forge', 'domain', 'heimatar', 'sinq_laison', 'metropolis'];

const CORP_ID = 98785281;

// Available starting systems
const START_SYSTEMS = [
  { name: 'Isikemi', value: 'isikemi' },
  { name: 'Jita', value: 'jita' },
  { name: 'Amarr', value: 'amarr' },
  { name: 'Rens', value: 'rens' },
  { name: 'Dodixie', value: 'dodixie' },
  { name: 'Hek', value: 'hek' },
];

// Component to display order details popup
function OrderDetailsPopup({
  typeId,
  itemName,
  region,
  onClose
}: {
  typeId: number;
  itemName: string;
  region: string;
  onClose: () => void;
}) {
  const { data, isLoading } = useQuery<OrderSnapshotResponse>({
    queryKey: ['order-snapshots', typeId, region],
    queryFn: async () => {
      const response = await api.get(`/api/shopping/orders/${typeId}`, {
        params: { region }
      });
      return response.data;
    }
  });

  const regionData = data?.regions?.[region];

  return (
    <div
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        backgroundColor: 'rgba(0,0,0,0.7)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 1000
      }}
      onClick={onClose}
    >
      <div
        className="card"
        style={{
          maxWidth: 600,
          maxHeight: '80vh',
          overflow: 'auto',
          padding: 20
        }}
        onClick={e => e.stopPropagation()}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
          <h3 style={{ margin: 0 }}>{itemName} - {REGION_NAMES[region] || region}</h3>
          <button className="btn btn-secondary" onClick={onClose} style={{ padding: '4px 8px' }}>
            <X size={16} />
          </button>
        </div>

        {isLoading ? (
          <div className="neutral">Loading orders...</div>
        ) : !regionData || regionData.sells.length === 0 ? (
          <div className="neutral">No order data available</div>
        ) : (
          <>
            <h4 style={{ marginBottom: 8 }}>Sell Orders (Top 10)</h4>
            <table className="data-table" style={{ width: '100%', marginBottom: 16 }}>
              <thead>
                <tr>
                  <th>#</th>
                  <th style={{ textAlign: 'right' }}>Price</th>
                  <th style={{ textAlign: 'right' }}>Volume</th>
                  <th style={{ textAlign: 'right' }}>Issued</th>
                </tr>
              </thead>
              <tbody>
                {regionData.sells.map((order) => (
                  <tr key={order.rank}>
                    <td>{order.rank}</td>
                    <td style={{ textAlign: 'right' }}>{formatISK(order.price)}</td>
                    <td style={{ textAlign: 'right' }}>{formatQuantity(order.volume)}</td>
                    <td style={{ textAlign: 'right', fontSize: 11 }} className="neutral">
                      {order.issued ? new Date(order.issued).toLocaleDateString() : '-'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>

            {regionData.buys.length > 0 && (
              <>
                <h4 style={{ marginBottom: 8 }}>Buy Orders (Top 10)</h4>
                <table className="data-table" style={{ width: '100%' }}>
                  <thead>
                    <tr>
                      <th>#</th>
                      <th style={{ textAlign: 'right' }}>Price</th>
                      <th style={{ textAlign: 'right' }}>Volume</th>
                      <th style={{ textAlign: 'right' }}>Issued</th>
                    </tr>
                  </thead>
                  <tbody>
                    {regionData.buys.map((order) => (
                      <tr key={order.rank}>
                        <td>{order.rank}</td>
                        <td style={{ textAlign: 'right' }}>{formatISK(order.price)}</td>
                        <td style={{ textAlign: 'right' }}>{formatQuantity(order.volume)}</td>
                        <td style={{ textAlign: 'right', fontSize: 11 }} className="neutral">
                          {order.issued ? new Date(order.issued).toLocaleDateString() : '-'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </>
            )}

            {regionData.updated_at && (
              <div className="neutral" style={{ marginTop: 12, fontSize: 11 }}>
                Updated: {new Date(regionData.updated_at).toLocaleString()}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}

// Component to display shopping route with optimized travel path
function ShoppingRouteDisplay({
  items,
  homeSystem: initialHomeSystem
}: {
  items: ComparisonItem[];
  homeSystem: string;
}) {
  const [expandedLegs, setExpandedLegs] = useState<Set<number>>(new Set());
  const [homeSystem, setHomeSystem] = useState(initialHomeSystem);
  const [includeReturn, setIncludeReturn] = useState(true);

  // Group items by their currently selected region
  const selectedRouteByRegion: Record<string, { item_name: string; quantity: number; total: number }[]> = {};
  let selectedTotal = 0;

  for (const item of items) {
    if (item.current_region && item.current_price) {
      if (!selectedRouteByRegion[item.current_region]) {
        selectedRouteByRegion[item.current_region] = [];
      }
      const total = item.current_price * item.quantity;
      selectedRouteByRegion[item.current_region].push({
        item_name: item.item_name,
        quantity: item.quantity,
        total
      });
      selectedTotal += total;
    }
  }

  const selectedRegions = Object.keys(selectedRouteByRegion);

  // Fetch optimal route through selected hubs
  const { data: routeData } = useQuery<ShoppingRoute>({
    queryKey: ['shopping-route', selectedRegions.sort().join(','), homeSystem, includeReturn],
    queryFn: async () => {
      if (selectedRegions.length === 0) return { total_jumps: 0, route: [], order: [] };
      const response = await api.get('/api/shopping/route', {
        params: {
          regions: selectedRegions.join(','),
          home_system: homeSystem,
          return_home: includeReturn
        }
      });
      return response.data;
    },
    enabled: selectedRegions.length > 0,
  });

  const toggleLeg = (idx: number) => {
    setExpandedLegs(prev => {
      const next = new Set(prev);
      if (next.has(idx)) {
        next.delete(idx);
      } else {
        next.add(idx);
      }
      return next;
    });
  };

  const getSecurityColor = (sec: number) => {
    if (sec >= 0.5) return 'var(--accent-green)';
    if (sec > 0) return 'var(--accent-yellow)';
    return 'var(--accent-red)';
  };

  if (selectedRegions.length === 0) return null;

  // Order regions by optimal route (filter out home system at start and end)
  const orderedRegions = routeData?.order?.filter((r, idx, arr) => {
    // Remove first element (home system)
    if (idx === 0) return false;
    // Remove last element if it's the return trip (same as first)
    if (idx === arr.length - 1 && r.toLowerCase() === arr[0].toLowerCase()) return false;
    return true;
  }) || selectedRegions;

  return (
    <div className="card" style={{ marginTop: 16 }}>
      <div className="card-header">
        <span className="card-title">
          <Map size={18} style={{ marginRight: 8 }} />
          Shopping Route
        </span>
        <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
          {routeData && routeData.total_jumps > 0 && (
            <span className="badge badge-blue">
              {routeData.total_jumps} jumps total
            </span>
          )}
          <span className="isk" style={{ fontWeight: 600 }}>
            Total: {formatISK(selectedTotal)}
          </span>
        </div>
      </div>

      {/* Route options */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        gap: 16,
        padding: '8px 0',
        borderBottom: '1px solid var(--border)',
        flexWrap: 'wrap'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <label className="neutral" style={{ fontSize: 12 }}>Start:</label>
          <select
            value={homeSystem}
            onChange={(e) => setHomeSystem(e.target.value)}
            style={{
              padding: '4px 8px',
              background: 'var(--bg-dark)',
              border: '1px solid var(--border)',
              borderRadius: 4,
              color: 'var(--text-primary)',
              fontSize: 12
            }}
          >
            {START_SYSTEMS.map(sys => (
              <option key={sys.value} value={sys.value}>{sys.name}</option>
            ))}
          </select>
        </div>
        <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 12, cursor: 'pointer' }}>
          <input
            type="checkbox"
            checked={includeReturn}
            onChange={(e) => setIncludeReturn(e.target.checked)}
            style={{ accentColor: 'var(--accent-blue)' }}
          />
          <span>Include return trip</span>
        </label>
      </div>

      {/* Route visualization with expandable system list */}
      {routeData?.route && routeData.route.length > 0 && (
        <div style={{ padding: '12px 0', marginBottom: 12, borderBottom: '1px solid var(--border)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
            <span style={{ fontWeight: 500 }}>{homeSystem}</span>
            {routeData.route.map((leg, idx) => (
              <span key={idx} style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <span className="neutral">→</span>
                <button
                  onClick={() => toggleLeg(idx)}
                  className="badge badge-blue"
                  style={{
                    fontSize: 10,
                    cursor: 'pointer',
                    border: 'none',
                    background: expandedLegs.has(idx) ? 'var(--accent-blue)' : undefined
                  }}
                  title="Click to show systems"
                >
                  {leg.jumps}j {expandedLegs.has(idx) ? '▼' : '▶'}
                </button>
                <span className="neutral">→</span>
                <span style={{ fontWeight: 500 }}>{leg.to}</span>
              </span>
            ))}
          </div>

          {/* Expanded system lists */}
          {routeData.route.map((leg, idx) => (
            expandedLegs.has(idx) && leg.systems && (
              <div
                key={`systems-${idx}`}
                style={{
                  marginTop: 8,
                  marginLeft: 16,
                  padding: 8,
                  background: 'var(--bg-dark)',
                  borderRadius: 6,
                  fontSize: 12
                }}
              >
                <div style={{ fontWeight: 500, marginBottom: 4 }}>
                  {leg.from} → {leg.to} ({leg.jumps} jumps)
                </div>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                  {leg.systems.map((sys, sIdx) => (
                    <span
                      key={sIdx}
                      style={{
                        padding: '2px 6px',
                        background: 'var(--bg-card)',
                        borderRadius: 4,
                        borderLeft: `3px solid ${getSecurityColor(sys.security)}`
                      }}
                    >
                      {sys.name}
                      <span className="neutral" style={{ marginLeft: 4, fontSize: 10 }}>
                        {sys.security.toFixed(1)}
                      </span>
                    </span>
                  ))}
                </div>
              </div>
            )
          ))}
        </div>
      )}

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 16 }}>
        {orderedRegions.map((regionOrHub) => {
          // Handle both region keys and hub names from route
          const region = regionOrHub.toLowerCase() === 'jita' ? 'the_forge' :
                        regionOrHub.toLowerCase() === 'amarr' ? 'domain' :
                        regionOrHub.toLowerCase() === 'rens' ? 'heimatar' :
                        regionOrHub.toLowerCase() === 'dodixie' ? 'sinq_laison' :
                        regionOrHub.toLowerCase() === 'hek' ? 'metropolis' :
                        regionOrHub;
          const items = selectedRouteByRegion[region];
          if (!items) return null;

          const routeLeg = routeData?.route?.find(r => r.to.toLowerCase() === regionOrHub.toLowerCase());

          return (
            <div
              key={region}
              style={{
                padding: 12,
                background: 'var(--bg-dark)',
                borderRadius: 8,
              }}
            >
              <div style={{ fontWeight: 600, marginBottom: 8 }}>
                {REGION_NAMES[region] || region}
                <span className="neutral" style={{ fontWeight: 400, marginLeft: 8 }}>
                  ({items.length} items)
                </span>
                {routeLeg && (
                  <span className="badge badge-blue" style={{ marginLeft: 8 }}>
                    {routeLeg.jumps} jumps
                  </span>
                )}
              </div>
              {items.map((item, idx) => (
                <div
                  key={idx}
                  style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    fontSize: 12,
                    padding: '4px 0',
                    borderTop: idx > 0 ? '1px solid var(--border)' : undefined,
                  }}
                >
                  <span>{item.item_name} x{formatQuantity(item.quantity)}</span>
                  <span className="isk">{formatISK(item.total)}</span>
                </div>
              ))}
              <div
                style={{
                  marginTop: 8,
                  paddingTop: 8,
                  borderTop: '1px solid var(--border)',
                  fontWeight: 500,
                }}
              >
                Subtotal: {formatISK(items.reduce((sum, i) => sum + i.total, 0))}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

export default function ShoppingPlanner() {
  const queryClient = useQueryClient();
  const [selectedListId, setSelectedListId] = useState<number | null>(null);
  const [newListName, setNewListName] = useState('');
  const [showNewListForm, setShowNewListForm] = useState(false);
  const [viewMode, setViewMode] = useState<'list' | 'compare'>('list');
  const [interactionMode, setInteractionMode] = useState<'select' | 'orders'>('select');
  const [orderPopup, setOrderPopup] = useState<{ typeId: number; itemName: string; region: string } | null>(null);

  // Fetch all shopping lists
  const { data: lists, isLoading } = useQuery<ShoppingList[]>({
    queryKey: ['shopping-lists', CORP_ID],
    queryFn: async () => {
      const response = await api.get('/api/shopping/lists', {
        params: { corporation_id: CORP_ID }
      });
      return response.data;
    },
  });

  // Fetch selected list details
  const { data: selectedList } = useQuery<ShoppingListDetail>({
    queryKey: ['shopping-list', selectedListId],
    queryFn: async () => {
      const response = await api.get(`/api/shopping/lists/${selectedListId}`);
      return response.data;
    },
    enabled: !!selectedListId,
  });

  // Fetch regional comparison
  const { data: comparison, isLoading: isLoadingComparison, refetch: refetchComparison } = useQuery<RegionalComparison>({
    queryKey: ['shopping-comparison', selectedListId],
    queryFn: async () => {
      const response = await api.get(`/api/shopping/lists/${selectedListId}/regional-comparison`);
      return response.data;
    },
    enabled: !!selectedListId && viewMode === 'compare',
  });

  // Create list mutation
  const createList = useMutation({
    mutationFn: async (name: string) => {
      const response = await api.post('/api/shopping/lists', {
        name,
        corporation_id: CORP_ID
      });
      return response.data;
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['shopping-lists'] });
      setSelectedListId(data.id);
      setNewListName('');
      setShowNewListForm(false);
    },
  });

  // Delete list mutation
  const deleteList = useMutation({
    mutationFn: async (listId: number) => {
      await api.delete(`/api/shopping/lists/${listId}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['shopping-lists'] });
      setSelectedListId(null);
    },
  });

  // Mark purchased mutation
  const markPurchased = useMutation({
    mutationFn: async (itemId: number) => {
      await api.post(`/api/shopping/items/${itemId}/purchased`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['shopping-list', selectedListId] });
      queryClient.invalidateQueries({ queryKey: ['shopping-lists'] });
    },
  });

  // Unmark purchased mutation
  const unmarkPurchased = useMutation({
    mutationFn: async (itemId: number) => {
      await api.delete(`/api/shopping/items/${itemId}/purchased`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['shopping-list', selectedListId] });
      queryClient.invalidateQueries({ queryKey: ['shopping-lists'] });
    },
  });

  // Remove item mutation
  const removeItem = useMutation({
    mutationFn: async (itemId: number) => {
      await api.delete(`/api/shopping/items/${itemId}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['shopping-list', selectedListId] });
      queryClient.invalidateQueries({ queryKey: ['shopping-lists'] });
    },
  });

  // Update item region mutation
  const updateItemRegion = useMutation({
    mutationFn: async ({ itemId, region, price }: { itemId: number; region: string; price?: number }) => {
      await api.patch(`/api/shopping/items/${itemId}/region`, null, {
        params: { region, price }
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['shopping-list', selectedListId] });
      queryClient.invalidateQueries({ queryKey: ['shopping-comparison', selectedListId] });
    },
  });

  // Apply optimal regions to all items
  const applyOptimalRegions = async () => {
    if (!comparison?.items) return;
    for (const item of comparison.items) {
      if (item.cheapest_region && item.cheapest_price) {
        await updateItemRegion.mutateAsync({
          itemId: item.id,
          region: item.cheapest_region,
          price: item.cheapest_price
        });
      }
    }
    queryClient.invalidateQueries({ queryKey: ['shopping-lists'] });
  };

  // Apply single region to all items
  const applyRegionToAll = async (region: string) => {
    if (!comparison?.items) return;
    for (const item of comparison.items) {
      const regionData = item.regions[region];
      if (regionData?.unit_price) {
        await updateItemRegion.mutateAsync({
          itemId: item.id,
          region,
          price: regionData.unit_price
        });
      }
    }
    queryClient.invalidateQueries({ queryKey: ['shopping-lists'] });
  };

  // Export to clipboard
  const handleExport = async (region?: string) => {
    if (!selectedListId) return;
    const response = await api.get(`/api/shopping/lists/${selectedListId}/export`, {
      params: region ? { region } : {}
    });
    navigator.clipboard.writeText(response.data.content);
    alert('Copied to clipboard in EVE Multibuy format!');
  };

  // Group items by region
  const itemsByRegion = selectedList?.items?.reduce((acc, item) => {
    const region = item.target_region || 'unassigned';
    if (!acc[region]) acc[region] = [];
    acc[region].push(item);
    return acc;
  }, {} as Record<string, ShoppingItem[]>) || {};

  if (isLoading) {
    return (
      <div className="loading">
        <div className="spinner"></div>
        Loading shopping lists...
      </div>
    );
  }

  return (
    <div>
      <div className="page-header">
        <div>
          <h1>Shopping Planner</h1>
          <p>Manage shopping lists for your production materials</p>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '300px 1fr', gap: 24 }}>
        {/* Lists Sidebar */}
        <div>
          <div className="card">
            <div className="card-header">
              <span className="card-title">Shopping Lists</span>
              <button
                className="btn btn-primary"
                style={{ padding: '6px 12px' }}
                onClick={() => setShowNewListForm(true)}
              >
                <Plus size={16} />
              </button>
            </div>

            {showNewListForm && (
              <div style={{ marginBottom: 16, display: 'flex', gap: 8 }}>
                <input
                  type="text"
                  placeholder="List name..."
                  value={newListName}
                  onChange={(e) => setNewListName(e.target.value)}
                  style={{ flex: 1, padding: '8px 12px', background: 'var(--bg-dark)', border: '1px solid var(--border)', borderRadius: 6, color: 'var(--text-primary)' }}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' && newListName.trim()) {
                      createList.mutate(newListName.trim());
                    }
                  }}
                />
                <button
                  className="btn btn-primary"
                  disabled={!newListName.trim()}
                  onClick={() => createList.mutate(newListName.trim())}
                >
                  <Check size={16} />
                </button>
                <button
                  className="btn btn-secondary"
                  onClick={() => { setShowNewListForm(false); setNewListName(''); }}
                >
                  <X size={16} />
                </button>
              </div>
            )}

            {lists?.length === 0 ? (
              <div className="empty-state" style={{ padding: 20 }}>
                <ShoppingCart size={32} style={{ opacity: 0.3 }} />
                <p className="neutral">No shopping lists yet</p>
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                {lists?.map((list) => (
                  <div
                    key={list.id}
                    className={`region-card ${selectedListId === list.id ? 'best' : ''}`}
                    style={{ cursor: 'pointer' }}
                    onClick={() => setSelectedListId(list.id)}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <div>
                        <div style={{ fontWeight: 500 }}>{list.name}</div>
                        <div className="neutral" style={{ fontSize: 12 }}>
                          {list.purchased_count}/{list.item_count} items
                        </div>
                      </div>
                      <ChevronRight size={16} className="neutral" />
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* List Details */}
        <div>
          {!selectedListId ? (
            <div className="card">
              <div className="empty-state">
                <ShoppingCart size={48} style={{ opacity: 0.3 }} />
                <p className="neutral">Select a shopping list or create a new one</p>
              </div>
            </div>
          ) : !selectedList ? (
            <div className="loading">
              <div className="spinner"></div>
              Loading list...
            </div>
          ) : (
            <>
              {/* List Header */}
              <div className="card" style={{ marginBottom: 16 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div>
                    <h2 style={{ margin: 0 }}>{selectedList.name}</h2>
                    <div className="neutral" style={{ marginTop: 4 }}>
                      {selectedList.items?.length || 0} items
                      {selectedList.total_cost && ` • ${formatISK(selectedList.total_cost)} total`}
                    </div>
                  </div>
                  <div style={{ display: 'flex', gap: 8 }}>
                    {/* View Toggle */}
                    <div style={{ display: 'flex', background: 'var(--bg-dark)', borderRadius: 6, padding: 2 }}>
                      <button
                        className={`btn ${viewMode === 'list' ? 'btn-primary' : 'btn-secondary'}`}
                        style={{ padding: '6px 12px', borderRadius: 4 }}
                        onClick={() => setViewMode('list')}
                      >
                        <ShoppingCart size={16} />
                      </button>
                      <button
                        className={`btn ${viewMode === 'compare' ? 'btn-primary' : 'btn-secondary'}`}
                        style={{ padding: '6px 12px', borderRadius: 4 }}
                        onClick={() => setViewMode('compare')}
                        title="Compare Regions"
                      >
                        <BarChart3 size={16} />
                      </button>
                    </div>
                    <button className="btn btn-secondary" onClick={() => handleExport()}>
                      <Copy size={16} /> Export All
                    </button>
                    <button
                      className="btn btn-secondary"
                      style={{ color: 'var(--accent-red)' }}
                      onClick={() => {
                        if (confirm('Delete this shopping list?')) {
                          deleteList.mutate(selectedList.id);
                        }
                      }}
                    >
                      <Trash2 size={16} />
                    </button>
                  </div>
                </div>
              </div>

              {/* View Content */}
              {viewMode === 'list' ? (
                /* Standard List View */
                Object.keys(itemsByRegion).length === 0 ? (
                  <div className="card">
                    <div className="empty-state">
                      <p className="neutral">No items in this list yet.</p>
                      <p className="neutral" style={{ fontSize: 12 }}>
                        Add items from the Materials Overview page.
                      </p>
                    </div>
                  </div>
                ) : (
                  Object.entries(itemsByRegion).map(([region, items]) => {
                    const regionTotal = items.reduce(
                      (sum, item) => sum + (item.target_price || 0) * item.quantity,
                      0
                    );
                    const unpurchasedItems = items.filter((i) => !i.is_purchased);

                    return (
                      <div key={region} className="card" style={{ marginBottom: 16 }}>
                        <div className="card-header">
                          <span className="card-title">
                            {REGION_NAMES[region] || region}
                            <span className="neutral" style={{ fontWeight: 400, marginLeft: 8 }}>
                              ({items.length} items • {formatISK(regionTotal)})
                            </span>
                          </span>
                          {unpurchasedItems.length > 0 && (
                            <button
                              className="btn btn-secondary"
                              style={{ padding: '4px 8px', fontSize: 12 }}
                              onClick={() => handleExport(region)}
                            >
                              <Copy size={14} /> Copy
                            </button>
                          )}
                        </div>

                        <div className="table-container">
                          <table>
                            <thead>
                              <tr>
                                <th style={{ width: 40 }}></th>
                                <th>Item</th>
                                <th>Quantity</th>
                                <th>Unit Price</th>
                                <th>Total</th>
                                <th style={{ width: 40 }}></th>
                              </tr>
                            </thead>
                            <tbody>
                              {items.map((item) => (
                                <tr
                                  key={item.id}
                                  style={{ opacity: item.is_purchased ? 0.5 : 1 }}
                                >
                                  <td>
                                    <button
                                      className="btn-icon"
                                      onClick={() =>
                                        item.is_purchased
                                          ? unmarkPurchased.mutate(item.id)
                                          : markPurchased.mutate(item.id)
                                      }
                                      style={{
                                        color: item.is_purchased
                                          ? 'var(--accent-green)'
                                          : 'var(--text-secondary)',
                                      }}
                                    >
                                      <Check size={16} />
                                    </button>
                                  </td>
                                  <td style={{ textDecoration: item.is_purchased ? 'line-through' : 'none' }}>
                                    {item.item_name}
                                  </td>
                                  <td>{formatQuantity(item.quantity)}</td>
                                  <td className="isk">{formatISK(item.target_price, false)}</td>
                                  <td className="isk">
                                    {formatISK((item.target_price || 0) * item.quantity)}
                                  </td>
                                  <td>
                                    <button
                                      className="btn-icon"
                                      onClick={() => removeItem.mutate(item.id)}
                                    >
                                      <Trash2 size={14} />
                                    </button>
                                  </td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      </div>
                    );
                  })
                )
              ) : (
                /* Regional Comparison View */
                isLoadingComparison ? (
                  <div className="loading">
                    <div className="spinner"></div>
                    Loading regional prices...
                  </div>
                ) : !comparison?.items?.length ? (
                  <div className="card">
                    <div className="empty-state">
                      <p className="neutral">No items to compare.</p>
                    </div>
                  </div>
                ) : (
                  <>
                    {/* Region Totals Summary */}
                    <div className="stats-grid" style={{ marginBottom: 16 }}>
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
                              onClick={() => applyRegionToAll(region)}
                              disabled={updateItemRegion.isPending}
                            >
                              Apply All
                            </button>
                          </div>
                        );
                      })}
                      <div className="stat-card" style={{ border: '1px solid var(--accent-blue)' }}>
                        <div className="stat-label">Optimal (Multi-Hub)</div>
                        <div className="stat-value isk positive">
                          {formatISK(comparison.optimal_route.total_cost)}
                        </div>
                        <button
                          className="btn btn-primary"
                          style={{ marginTop: 8, padding: '4px 8px', fontSize: 11 }}
                          onClick={applyOptimalRegions}
                          disabled={updateItemRegion.isPending}
                        >
                          Apply Optimal
                        </button>
                      </div>
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
                          <button
                            className="btn btn-secondary"
                            style={{ padding: '4px 8px' }}
                            onClick={() => refetchComparison()}
                          >
                            <RefreshCw size={14} />
                          </button>
                        </div>
                      </div>
                      <div className="table-container">
                        <table>
                          <thead>
                            <tr>
                              <th>Item</th>
                              <th>Qty</th>
                              {REGION_ORDER.map((region) => (
                                <th key={region}>{REGION_NAMES[region]}</th>
                              ))}
                              <th>Selected</th>
                            </tr>
                          </thead>
                          <tbody>
                            {comparison.items.map((item) => (
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
                                      style={{
                                        cursor: data?.unit_price ? 'pointer' : 'default',
                                        background: isSelected ? 'var(--bg-hover)' : undefined,
                                        borderLeft: isSelected ? '2px solid var(--accent-blue)' : undefined,
                                      }}
                                      onClick={(e) => {
                                        e.stopPropagation();
                                        if (!data?.unit_price) return;
                                        if (updateItemRegion.isPending) return; // Prevent double-clicks during mutation
                                        if (interactionMode === 'select') {
                                          updateItemRegion.mutate({
                                            itemId: item.id,
                                            region,
                                            price: data.unit_price
                                          });
                                        } else {
                                          setOrderPopup({ typeId: item.type_id, itemName: item.item_name, region });
                                        }
                                      }}
                                      title={interactionMode === 'select'
                                        ? (data?.has_stock ? 'Click to select this region' : 'Low stock - Click to select anyway')
                                        : (data?.has_stock ? 'Click to view orders' : 'Low stock - Click to view orders')}
                                    >
                                      {data?.total ? (
                                        <>
                                          <div>{formatISK(data.total)}</div>
                                          <div style={{ fontSize: 10, color: 'var(--text-secondary)' }}>
                                            @{formatISK(data.unit_price || 0)}/u
                                          </div>
                                          <div
                                            className={`neutral ${!data.has_stock ? 'negative' : ''}`}
                                            style={{ fontSize: 10 }}
                                          >
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
                    <ShoppingRouteDisplay
                      items={comparison.items}
                      homeSystem={comparison.home_system}
                    />
                  </>
                )
              )}
            </>
          )}
        </div>
      </div>

      {/* Order Details Popup */}
      {orderPopup && (
        <OrderDetailsPopup
          typeId={orderPopup.typeId}
          itemName={orderPopup.itemName}
          region={orderPopup.region}
          onClose={() => setOrderPopup(null)}
        />
      )}
    </div>
  );
}
