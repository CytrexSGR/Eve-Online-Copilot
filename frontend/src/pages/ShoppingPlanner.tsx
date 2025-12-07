import { useState, useMemo, useCallback } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { ShoppingCart, Plus, Trash2, Check, Copy, ChevronRight, X, Map, RefreshCw, MousePointer, Eye, ArrowUpDown, Package, Truck, Calculator, ChevronDown, ChevronUp, Search, BarChart3 } from 'lucide-react';
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
  is_product?: boolean;
  runs?: number;
  me_level?: number;
  parent_item_id?: number | null;
  build_decision?: string | null;
  output_per_run?: number;
  materials?: ShoppingItem[];
  sub_products?: ShoppingItem[];
  materials_calculated?: boolean;
}

interface CalculateMaterialsResponse {
  product: {
    id: number;
    type_id: number;
    item_name: string;
    runs: number;
    me_level: number;
    output_per_run: number;
    total_output: number;
  };
  materials: Array<{
    type_id: number;
    item_name: string;
    quantity: number;
    base_quantity: number;
    volume: number;
    has_blueprint: boolean;
  }>;
  sub_products: Array<{
    type_id: number;
    item_name: string;
    quantity: number;
    base_quantity: number;
    volume: number;
    has_blueprint: boolean;
    default_decision: string;
  }>;
}

interface ShoppingListDetail extends ShoppingList {
  items: ShoppingItem[];
  products?: ShoppingItem[];
  standalone_items?: ShoppingItem[];
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

interface CargoSummary {
  list_id: number;
  products: Array<{
    type_id: number;
    item_name: string;
    runs: number;
    total_volume: number;
    me_level: number;
    output_per_run: number;
  }>;
  materials: {
    total_items: number;
    total_volume_m3: number;
    volume_formatted: string;
    breakdown_by_region: Record<string, { volume_m3: number; item_count: number }>;
  };
}

interface TransportOption {
  id: number;
  characters: Array<{
    id: number;
    name: string;
    ship_type_id: number;
    ship_name: string;
    ship_group: string;
    ship_location: string;
  }>;
  trips: number;
  flight_time_min: number;
  flight_time_formatted: string;
  capacity_m3: number;
  capacity_used_pct: number;
  risk_score: number;
  risk_label: string;
  dangerous_systems: string[];
  isk_per_trip: number;
}

interface TransportOptions {
  total_volume_m3: number;
  volume_formatted: string;
  route_summary: string;
  options: TransportOption[];
  filters_available: string[];
  message?: string;
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

// Recursive Sub-Product Component
interface SubProductTreeProps {
  subProduct: ShoppingItem;
  depth: number;
  updateBuildDecision: any;
  onBulkUpdate: (itemIds: number[], decision: 'buy' | 'build') => void;
}

function SubProductTree({ subProduct, depth, updateBuildDecision, onBulkUpdate }: SubProductTreeProps) {
  // Collect all descendant IDs for bulk operations
  const collectDescendantIds = (item: ShoppingItem): number[] => {
    const ids = [item.id];
    if (item.sub_products) {
      item.sub_products.forEach(sp => {
        ids.push(...collectDescendantIds(sp));
      });
    }
    return ids;
  };

  const descendantIds = collectDescendantIds(subProduct);

  return (
    <div style={{ marginLeft: depth * 16, marginBottom: 8 }}>
      <div
        style={{
          padding: '8px 12px',
          background: 'var(--bg-dark)',
          borderRadius: 6,
          borderLeft: `3px solid ${subProduct.build_decision === 'build' ? 'var(--accent-green)' : 'var(--accent-blue)'}`,
        }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            {/* BUY/BUILD Toggle */}
            <div style={{
              display: 'flex',
              background: 'var(--bg-darker)',
              borderRadius: 4,
              padding: 1,
              border: '1px solid var(--border)'
            }}>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  updateBuildDecision.mutate({ itemId: subProduct.id, decision: 'buy' });
                }}
                disabled={updateBuildDecision.isPending}
                style={{
                  padding: '2px 8px',
                  borderRadius: 3,
                  border: 'none',
                  fontSize: 10,
                  fontWeight: 600,
                  cursor: 'pointer',
                  background: subProduct.build_decision !== 'build' ? 'var(--accent-blue)' : 'transparent',
                  color: subProduct.build_decision !== 'build' ? 'white' : 'var(--text-secondary)',
                  transition: 'all 0.15s'
                }}
                title="Buy from market"
              >
                BUY
              </button>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  updateBuildDecision.mutate({ itemId: subProduct.id, decision: 'build' });
                }}
                disabled={updateBuildDecision.isPending}
                style={{
                  padding: '2px 8px',
                  borderRadius: 3,
                  border: 'none',
                  fontSize: 10,
                  fontWeight: 600,
                  cursor: 'pointer',
                  background: subProduct.build_decision === 'build' ? 'var(--accent-green)' : 'transparent',
                  color: subProduct.build_decision === 'build' ? 'white' : 'var(--text-secondary)',
                  transition: 'all 0.15s'
                }}
                title="Build from materials"
              >
                BUILD
              </button>
            </div>
            <div>
              <span style={{ fontWeight: 500, fontSize: 13 }}>{subProduct.item_name}</span>
              <span className="neutral" style={{ marginLeft: 8, fontWeight: 400, fontSize: 12 }}>
                x{formatQuantity(subProduct.quantity)}
              </span>
            </div>
          </div>

          {/* Bulk Actions - only show if has sub-products */}
          {subProduct.sub_products && subProduct.sub_products.length > 0 && (
            <div style={{ display: 'flex', gap: 4 }}>
              <button
                className="btn-icon"
                onClick={() => onBulkUpdate(descendantIds, 'buy')}
                style={{ fontSize: 9, padding: '2px 6px' }}
                title="Set all to BUY"
              >
                All BUY
              </button>
              <button
                className="btn-icon"
                onClick={() => onBulkUpdate(descendantIds, 'build')}
                style={{ fontSize: 9, padding: '2px 6px' }}
                title="Set all to BUILD"
              >
                All BUILD
              </button>
            </div>
          )}
        </div>

        {/* Show materials if BUILD decision */}
        {subProduct.build_decision === 'build' && subProduct.materials && subProduct.materials.length > 0 && (
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4, marginTop: 8 }}>
            {subProduct.materials.map((mat) => (
              <span
                key={mat.id}
                style={{
                  padding: '2px 6px',
                  background: 'var(--bg-darker)',
                  borderRadius: 4,
                  fontSize: 11
                }}
              >
                {mat.item_name}: {formatQuantity(mat.quantity)}
              </span>
            ))}
          </div>
        )}

        {/* Recursively render sub-products if BUILD decision */}
        {subProduct.build_decision === 'build' && subProduct.sub_products && subProduct.sub_products.length > 0 && (
          <div style={{ marginTop: 8 }}>
            {subProduct.sub_products.map((sp) => (
              <SubProductTree
                key={sp.id}
                subProduct={sp}
                depth={depth + 1}
                updateBuildDecision={updateBuildDecision}
                onBulkUpdate={onBulkUpdate}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

export default function ShoppingPlanner() {
  const queryClient = useQueryClient();
  const [selectedListId, setSelectedListId] = useState<number | null>(null);
  const [newListName, setNewListName] = useState('');
  const [showNewListForm, setShowNewListForm] = useState(false);
  const [viewMode, setViewMode] = useState<'list' | 'compare' | 'transport'>('list');
  const [interactionMode, setInteractionMode] = useState<'select' | 'orders'>('select');
  const [orderPopup, setOrderPopup] = useState<{ typeId: number; itemName: string; region: string } | null>(null);
  const [compareSort, setCompareSort] = useState<'name' | 'quantity'>('name');
  const [showRegionTotals, setShowRegionTotals] = useState(false);
  const [showSubProductModal, setShowSubProductModal] = useState(false);
  const [pendingMaterials, setPendingMaterials] = useState<CalculateMaterialsResponse | null>(null);
  const [subProductDecisions, setSubProductDecisions] = useState<Record<number, 'buy' | 'build'>>({});
  const [expandedProducts, setExpandedProducts] = useState<Set<number>>(new Set());

  // Global runs multiplier
  const [globalRuns, setGlobalRuns] = useState(1);

  // Add Product Modal state
  const [showAddProductModal, setShowAddProductModal] = useState(false);

  const [productSearch, setProductSearch] = useState('');
  const [productSearchResults, setProductSearchResults] = useState<Array<{ typeID: number; typeName: string; groupID: number }>>([]);
  const [selectedProductType, setSelectedProductType] = useState<{ typeID: number; typeName: string } | null>(null);
  const [newProductRuns, setNewProductRuns] = useState(1);
  const [isSearchingProducts, setIsSearchingProducts] = useState(false);

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

  // Fetch regional comparison (when modal is open)
  const { data: comparison, isLoading: isLoadingComparison, refetch: refetchComparison } = useQuery<RegionalComparison>({
    queryKey: ['shopping-comparison', selectedListId],
    queryFn: async () => {
      const response = await api.get(`/api/shopping/lists/${selectedListId}/regional-comparison`);
      return response.data;
    },
    enabled: !!selectedListId && viewMode === 'compare',
  });

  // Fetch cargo summary
  const { data: cargoSummary } = useQuery<CargoSummary>({
    queryKey: ['shopping-cargo', selectedListId],
    queryFn: async () => {
      const response = await api.get(`/api/shopping/lists/${selectedListId}/cargo-summary`);
      return response.data;
    },
    enabled: !!selectedListId,
  });

  // Transport state and query
  const [safeRoutesOnly, setSafeRoutesOnly] = useState(true);
  const [transportFilter, setTransportFilter] = useState<string>('');

  const { data: transportOptions, isLoading: isLoadingTransport } = useQuery<TransportOptions>({
    queryKey: ['shopping-transport', selectedListId, safeRoutesOnly],
    queryFn: async () => {
      const response = await api.get(`/api/shopping/lists/${selectedListId}/transport-options`, {
        params: { safe_only: safeRoutesOnly }
      });
      return response.data;
    },
    enabled: !!selectedListId && viewMode === 'transport',
  });

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
      queryClient.invalidateQueries({ queryKey: ['shopping-cargo', selectedListId] });
      queryClient.invalidateQueries({ queryKey: ['shopping-comparison', selectedListId] });
      queryClient.invalidateQueries({ queryKey: ['shopping-lists'] });
    },
  });

  // Add product mutation
  const addProduct = useMutation({
    mutationFn: async ({ typeId, typeName, quantity }: { typeId: number; typeName: string; quantity: number }) => {
      const response = await api.post(`/api/shopping/lists/${selectedListId}/items`, {
        type_id: typeId,
        item_name: typeName,
        quantity
      });
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['shopping-list', selectedListId] });
      queryClient.invalidateQueries({ queryKey: ['shopping-lists'] });
      queryClient.invalidateQueries({ queryKey: ['shopping-cargo', selectedListId] });
      queryClient.invalidateQueries({ queryKey: ['shopping-comparison', selectedListId] });
      // Reset modal state
      setShowAddProductModal(false);
      setProductSearch('');
      setProductSearchResults([]);
      setSelectedProductType(null);
      setNewProductRuns(1);
    },
  });

  // Search products function
  const searchProducts = async (query: string) => {
    if (query.length < 2) {
      setProductSearchResults([]);
      return;
    }
    setIsSearchingProducts(true);
    try {
      const response = await api.get('/api/items/search', { params: { q: query, limit: 15 } });
      // Filter to only show items that are likely products (not blueprints, not special items)
      const results = response.data.results.filter((item: { typeName: string; groupID: number }) =>
        !item.typeName.includes('Blueprint') &&
        item.groupID !== 517 // Exclude Cosmos items
      );
      setProductSearchResults(results);
    } catch {
      setProductSearchResults([]);
    }
    setIsSearchingProducts(false);
  };

  // Update item runs/ME mutation
  const updateItemRuns = useMutation({
    mutationFn: async ({ itemId, runs, meLevel }: { itemId: number; runs: number; meLevel: number }) => {
      await api.patch(`/api/shopping/items/${itemId}/runs`, { runs, me_level: meLevel });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['shopping-list', selectedListId] });
      queryClient.invalidateQueries({ queryKey: ['shopping-cargo', selectedListId] });
      queryClient.invalidateQueries({ queryKey: ['shopping-lists'] });
    },
  });

  // Update product build decision (BUY/BUILD toggle)
  const updateBuildDecision = useMutation({
    mutationFn: async ({ itemId, decision }: { itemId: number; decision: 'buy' | 'build' }) => {
      await api.patch(`/api/shopping/items/${itemId}/build-decision`, { decision });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['shopping-list', selectedListId] });
      queryClient.invalidateQueries({ queryKey: ['shopping-cargo', selectedListId] });
      queryClient.invalidateQueries({ queryKey: ['shopping-comparison', selectedListId] });
      queryClient.invalidateQueries({ queryKey: ['shopping-lists'] });
    },
  });

  // Bulk update build decisions
  const handleBulkBuildDecision = useCallback(async (itemIds: number[], decision: 'buy' | 'build') => {
    // Update all items in parallel
    await Promise.all(
      itemIds.map(itemId =>
        api.patch(`/api/shopping/items/${itemId}/build-decision`, { decision })
      )
    );
    // Invalidate queries once after all updates
    queryClient.invalidateQueries({ queryKey: ['shopping-list', selectedListId] });
    queryClient.invalidateQueries({ queryKey: ['shopping-cargo', selectedListId] });
    queryClient.invalidateQueries({ queryKey: ['shopping-comparison', selectedListId] });
    queryClient.invalidateQueries({ queryKey: ['shopping-lists'] });
  }, [selectedListId, queryClient]);

  // Calculate materials mutation
  const calculateMaterials = useMutation({
    mutationFn: async (itemId: number) => {
      const response = await api.post<CalculateMaterialsResponse>(`/api/shopping/items/${itemId}/calculate-materials`);
      return response.data;
    },
    onSuccess: (data) => {
      if (data.sub_products.length > 0) {
        // Show modal for sub-product decisions
        setPendingMaterials(data);
        const defaults: Record<number, 'buy' | 'build'> = {};
        data.sub_products.forEach(sp => { defaults[sp.type_id] = 'buy'; });
        setSubProductDecisions(defaults);
        setShowSubProductModal(true);
      } else {
        // No sub-products, apply directly
        applyMaterials.mutate({
          itemId: data.product.id,
          materials: data.materials,
          subProductDecisions: []
        });
      }
    },
  });

  // Apply materials mutation
  const applyMaterials = useMutation({
    mutationFn: async ({ itemId, materials, subProductDecisions }: {
      itemId: number;
      materials: Array<{ type_id: number; item_name: string; quantity: number }>;
      subProductDecisions: Array<{ type_id: number; item_name: string; quantity: number; decision: string }>;
    }) => {
      const response = await api.post(`/api/shopping/items/${itemId}/apply-materials`, {
        materials,
        sub_product_decisions: subProductDecisions
      });
      return response.data;
    },
    onSuccess: () => {
      setShowSubProductModal(false);
      setPendingMaterials(null);
      queryClient.invalidateQueries({ queryKey: ['shopping-list', selectedListId] });
      queryClient.invalidateQueries({ queryKey: ['shopping-cargo', selectedListId] });
      queryClient.invalidateQueries({ queryKey: ['shopping-comparison', selectedListId] });
      queryClient.invalidateQueries({ queryKey: ['shopping-lists'] });
    },
  });

  // Handle apply materials with sub-product decisions
  const handleApplyWithDecisions = () => {
    if (!pendingMaterials) return;
    const subDecisions = pendingMaterials.sub_products.map(sp => ({
      type_id: sp.type_id,
      item_name: sp.item_name,
      quantity: sp.quantity,
      decision: subProductDecisions[sp.type_id] || 'buy'
    }));
    applyMaterials.mutate({
      itemId: pendingMaterials.product.id,
      materials: pendingMaterials.materials,
      subProductDecisions: subDecisions
    });
  };

  // Toggle product expansion
  const toggleProductExpanded = (productId: number) => {
    setExpandedProducts(prev => {
      const next = new Set(prev);
      if (next.has(productId)) {
        next.delete(productId);
      } else {
        next.add(productId);
      }
      return next;
    });
  };

  // Update item region mutation with optimistic updates
  // This prevents table row shifting during re-renders which caused wrong row selection
  const updateItemRegion = useMutation({
    mutationFn: async ({ itemId, region, price }: { itemId: number; region: string; price?: number }) => {
      await api.patch(`/api/shopping/items/${itemId}/region`, null, {
        params: { region, price }
      });
      return { itemId, region, price };
    },
    onMutate: async ({ itemId, region, price }) => {
      // Cancel any outgoing refetches to prevent overwriting optimistic update
      await queryClient.cancelQueries({ queryKey: ['shopping-comparison', selectedListId] });
      await queryClient.cancelQueries({ queryKey: ['shopping-list', selectedListId] });

      // Snapshot previous values for rollback
      const previousComparison = queryClient.getQueryData<RegionalComparison>(['shopping-comparison', selectedListId]);
      const previousList = queryClient.getQueryData(['shopping-list', selectedListId]);

      // Optimistically update comparison data
      if (previousComparison) {
        queryClient.setQueryData<RegionalComparison>(['shopping-comparison', selectedListId], {
          ...previousComparison,
          items: previousComparison.items.map(item =>
            item.id === itemId
              ? { ...item, current_region: region, current_price: price ?? null }
              : item
          )
        });
      }

      // Optimistically update list data
      if (previousList) {
        queryClient.setQueryData(['shopping-list', selectedListId], (old: typeof previousList) => ({
          ...old,
          items: (old as { items: ShoppingItem[] }).items?.map((item: ShoppingItem) =>
            item.id === itemId
              ? { ...item, target_region: region, target_price: price }
              : item
          )
        }));
      }

      return { previousComparison, previousList };
    },
    onError: (_err, _variables, context) => {
      // Rollback on error
      if (context?.previousComparison) {
        queryClient.setQueryData(['shopping-comparison', selectedListId], context.previousComparison);
      }
      if (context?.previousList) {
        queryClient.setQueryData(['shopping-list', selectedListId], context.previousList);
      }
    },
    onSettled: () => {
      // Refetch after mutation settles to ensure consistency
      // Using a small delay to prevent immediate re-render during user interaction
      setTimeout(() => {
        queryClient.invalidateQueries({ queryKey: ['shopping-list', selectedListId] });
        queryClient.invalidateQueries({ queryKey: ['shopping-comparison', selectedListId] });
      }, 200);
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

  // Aggregated shopping list - combine all items by type_id (no region separation)
  const aggregatedShoppingList = useMemo(() => {
    if (!selectedList?.items) return [];

    // Aggregate by type_id
    const aggregated: Record<number, ShoppingItem & { aggregatedQuantity: number }> = {};

    for (const item of selectedList.items) {
      // Skip main products (is_product=true with no parent) - they are displayed in Products section
      if (item.is_product && !item.parent_item_id) continue;

      // Skip sub-products with build_decision='build' - you're building them, not buying
      // Their materials will appear in the list instead
      if (item.is_product && item.parent_item_id && item.build_decision === 'build') continue;

      if (aggregated[item.type_id]) {
        // Add to existing item's quantity
        aggregated[item.type_id].aggregatedQuantity += item.quantity;
      } else {
        // First occurrence of this type_id
        aggregated[item.type_id] = { ...item, aggregatedQuantity: item.quantity };
      }
    }

    // Convert to array and apply global runs multiplier
    return Object.values(aggregated).map(item => ({
      ...item,
      quantity: item.aggregatedQuantity * globalRuns,
    })).sort((a, b) => a.item_name.localeCompare(b.item_name));
  }, [selectedList?.items, globalRuns]);

  // Calculate total cost for aggregated list
  const aggregatedTotal = useMemo(() => {
    return aggregatedShoppingList.reduce(
      (sum, item) => sum + (item.target_price || 0) * item.quantity,
      0
    );
  }, [aggregatedShoppingList]);

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
                  <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
                    <div>
                      <h2 style={{ margin: 0 }}>{selectedList.name}</h2>
                      <div className="neutral" style={{ marginTop: 4 }}>
                        {selectedList.items?.length || 0} items
                        {selectedList.total_cost && ` • ${formatISK(selectedList.total_cost)} total`}
                      </div>
                    </div>
                    {/* Cargo Summary */}
                    {cargoSummary && cargoSummary.materials.total_volume_m3 > 0 && (
                      <div style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: 8,
                        padding: '8px 12px',
                        background: 'var(--bg-dark)',
                        borderRadius: 6,
                        fontSize: 13
                      }}>
                        <Package size={16} />
                        <span>Cargo: <strong>{cargoSummary.materials.volume_formatted}</strong></span>
                        <span className="neutral">({cargoSummary.materials.total_items} items)</span>
                      </div>
                    )}
                  </div>
                  <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                    {/* Global Runs Multiplier - X1 */}
                    <div style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '6px 12px', background: 'var(--bg-dark)', borderRadius: 6 }}>
                      <span style={{ fontSize: 12 }}>×</span>
                      <input
                        type="number"
                        min="1"
                        max="1000"
                        value={globalRuns}
                        onChange={(e) => setGlobalRuns(Math.max(1, parseInt(e.target.value) || 1))}
                        style={{
                          width: 50,
                          padding: '4px 8px',
                          borderRadius: 4,
                          border: '1px solid var(--border)',
                          background: 'var(--bg-darker)',
                          color: 'var(--text-primary)',
                          fontSize: 14,
                          fontWeight: 600,
                          textAlign: 'center'
                        }}
                        title="Global runs multiplier"
                      />
                    </div>

                    {/* View Mode Tabs */}
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
                    <button
                      className={`btn ${viewMode === 'transport' ? 'btn-primary' : 'btn-secondary'}`}
                      onClick={() => setViewMode('transport')}
                      disabled={!cargoSummary || cargoSummary.materials.total_volume_m3 === 0}
                      title={!cargoSummary || cargoSummary.materials.total_volume_m3 === 0
                        ? 'Add items to see transport options'
                        : 'Plan transport'}
                    >
                      <Truck size={16} style={{ marginRight: 6 }} />
                      Transport
                    </button>
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

              {/* Products Section - with material calculation */}
              {selectedList && (
                <div className="card" style={{ marginBottom: 16 }}>
                  <div className="card-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span className="card-title">
                      <Package size={18} style={{ marginRight: 8 }} />
                      Products ({selectedList.products?.length || 0})
                    </span>
                    <button
                      className="btn btn-primary"
                      style={{ padding: '6px 12px', fontSize: 12 }}
                      onClick={() => setShowAddProductModal(true)}
                    >
                      <Plus size={14} style={{ marginRight: 4 }} />
                      Add Product
                    </button>
                  </div>
                  <div style={{ padding: 16 }}>
                    {(!selectedList.products || selectedList.products.length === 0) ? (
                      <div style={{ textAlign: 'center', padding: '24px 0', color: 'var(--text-secondary)' }}>
                        <Package size={32} style={{ opacity: 0.5, marginBottom: 8 }} />
                        <div>No products yet</div>
                        <div style={{ fontSize: 12, marginTop: 4 }}>Click "Add Product" to add a ship, module or other buildable item</div>
                      </div>
                    ) : (
                      <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                        {/* Calculate/Recalculate Materials buttons */}
                        <div style={{ display: 'flex', gap: 8, marginBottom: 8 }}>
                          {selectedList.products.some(p => !p.materials_calculated) && (
                            <button
                              className="btn btn-primary"
                              onClick={async () => {
                                for (const product of selectedList.products || []) {
                                  if (!product.materials_calculated) {
                                    calculateMaterials.mutate(product.id);
                                  }
                                }
                              }}
                              disabled={calculateMaterials.isPending}
                            >
                              <Calculator size={16} style={{ marginRight: 8 }} />
                              Calculate Materials
                            </button>
                          )}
                          {selectedList.products.some(p => p.materials_calculated) && (
                            <button
                              className="btn"
                              style={{ background: 'var(--bg-darker)', border: '1px solid var(--border-color)' }}
                              onClick={async () => {
                                if (confirm('Recalculate all materials? This will update quantities based on current runs/ME settings.')) {
                                  for (const product of selectedList.products || []) {
                                    calculateMaterials.mutate(product.id);
                                  }
                                }
                              }}
                              disabled={calculateMaterials.isPending}
                            >
                              <RefreshCw size={16} style={{ marginRight: 8 }} />
                              Recalculate All
                            </button>
                          )}
                        </div>
                        {selectedList.products.map((product) => (
                        <div key={product.id} style={{ borderRadius: 8, overflow: 'hidden' }}>
                          {/* Product Row - Main product (always BUILD) */}
                          <div
                            style={{
                              display: 'flex',
                              alignItems: 'center',
                              justifyContent: 'space-between',
                              padding: '10px 16px',
                              background: 'var(--bg-dark)',
                              borderRadius: product.materials_calculated ? '8px 8px 0 0' : 8,
                              borderLeft: '3px solid var(--accent-green)'
                            }}
                          >
                            {/* Left: Expand + Name + Info */}
                            <div style={{ display: 'flex', alignItems: 'center', gap: 10, flex: 1 }}>
                              {product.materials_calculated && (
                                <button
                                  onClick={() => toggleProductExpanded(product.id)}
                                  style={{
                                    background: 'none',
                                    border: 'none',
                                    color: 'var(--text-secondary)',
                                    cursor: 'pointer',
                                    padding: 4
                                  }}
                                >
                                  {expandedProducts.has(product.id) ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                                </button>
                              )}
                              <div style={{ minWidth: 200 }}>
                                <div style={{ fontWeight: 600, fontSize: 14 }}>{product.item_name}</div>
                                <div className="neutral" style={{ fontSize: 11 }}>
                                  {product.runs || 1} runs × {product.output_per_run || 1} = {(product.runs || 1) * (product.output_per_run || 1)} units
                                </div>
                              </div>
                            </div>

                            {/* Middle: Controls */}
                            <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
                              {/* Runs */}
                              <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                                <label style={{ fontSize: 11, color: 'var(--text-secondary)' }}>Runs:</label>
                                <input
                                  type="number"
                                  min="1"
                                  max="1000"
                                  defaultValue={product.runs || 1}
                                  style={{
                                    width: 50,
                                    padding: '4px 6px',
                                    borderRadius: 4,
                                    border: '1px solid var(--border)',
                                    background: 'var(--bg-darker)',
                                    color: 'inherit',
                                    fontSize: 12
                                  }}
                                  onBlur={(e) => {
                                    const newRuns = parseInt(e.target.value) || 1;
                                    if (newRuns !== product.runs) {
                                      updateItemRuns.mutate({ itemId: product.id, runs: newRuns, meLevel: product.me_level || 10 });
                                    }
                                  }}
                                  onKeyDown={(e) => {
                                    if (e.key === 'Enter') {
                                      (e.target as HTMLInputElement).blur();
                                    }
                                  }}
                                />
                              </div>

                              {/* ME */}
                              <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                                <label style={{ fontSize: 11, color: 'var(--text-secondary)' }}>ME:</label>
                                <input
                                  type="number"
                                  min="0"
                                  max="10"
                                  defaultValue={product.me_level || 10}
                                  style={{
                                    width: 40,
                                    padding: '4px 6px',
                                    borderRadius: 4,
                                    border: '1px solid var(--border)',
                                    background: 'var(--bg-darker)',
                                    color: 'inherit',
                                    fontSize: 12
                                  }}
                                  onBlur={(e) => {
                                    const newME = parseInt(e.target.value) || 10;
                                    if (newME !== product.me_level) {
                                      updateItemRuns.mutate({ itemId: product.id, runs: product.runs || 1, meLevel: newME });
                                    }
                                  }}
                                  onKeyDown={(e) => {
                                    if (e.key === 'Enter') {
                                      (e.target as HTMLInputElement).blur();
                                    }
                                  }}
                                />
                              </div>

                              {/* Status Badge */}
                              {product.materials_calculated ? (
                                <span className="badge badge-green" style={{ fontSize: 10 }}>Materials calculated</span>
                              ) : (
                                <span className="badge" style={{ fontSize: 10, background: 'var(--bg-darker)' }}>Not calculated</span>
                              )}

                              {/* Calculate Button */}
                              <button
                                className="btn btn-primary"
                                style={{ padding: '5px 10px', fontSize: 11 }}
                                onClick={() => calculateMaterials.mutate(product.id)}
                                disabled={calculateMaterials.isPending}
                              >
                                <Calculator size={12} style={{ marginRight: 4 }} />
                                {product.materials_calculated ? 'Recalculate' : 'Calculate'}
                              </button>

                              {/* Delete */}
                              <button
                                className="btn-icon"
                                style={{ color: 'var(--accent-red)' }}
                                onClick={() => {
                                  if (confirm(`Remove ${product.item_name} and its materials?`)) {
                                    removeItem.mutate(product.id);
                                  }
                                }}
                                title="Remove product"
                              >
                                <Trash2 size={14} />
                              </button>
                            </div>
                          </div>

                          {/* Materials List (expandable) */}
                          {product.materials_calculated && expandedProducts.has(product.id) && (
                            <div style={{
                              background: 'var(--bg-darker)',
                              padding: '12px 16px',
                              borderRadius: '0 0 8px 8px',
                              borderTop: '1px solid var(--border-color)'
                            }}>
                              {product.materials && product.materials.length > 0 && (
                                <div style={{ marginBottom: 12 }}>
                                  <div style={{ fontSize: 12, fontWeight: 500, marginBottom: 8, color: 'var(--text-secondary)' }}>
                                    Materials ({product.materials.length})
                                  </div>
                                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 8 }}>
                                    {product.materials.map((mat) => (
                                      <div
                                        key={mat.id}
                                        style={{
                                          display: 'flex',
                                          justifyContent: 'space-between',
                                          padding: '6px 10px',
                                          background: 'var(--bg-dark)',
                                          borderRadius: 4,
                                          fontSize: 12
                                        }}
                                      >
                                        <span>{mat.item_name}</span>
                                        <span className="isk">{formatQuantity(mat.quantity)}</span>
                                      </div>
                                    ))}
                                  </div>
                                </div>
                              )}

                              {product.sub_products && product.sub_products.length > 0 && (
                                <div>
                                  <div style={{ fontSize: 12, fontWeight: 500, marginBottom: 8, color: 'var(--text-secondary)' }}>
                                    Sub-Components ({product.sub_products.length})
                                  </div>
                                  {product.sub_products.map((subProduct) => (
                                    <SubProductTree
                                      key={subProduct.id}
                                      subProduct={subProduct}
                                      depth={0}
                                      updateBuildDecision={updateBuildDecision}
                                      onBulkUpdate={handleBulkBuildDecision}
                                    />
                                  ))}
                                </div>
                              )}
                            </div>
                          )}
                        </div>
                      ))}
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* Add Product Modal */}
              {showAddProductModal && (
                <div className="modal-overlay" style={{
                  position: 'fixed',
                  top: 0,
                  left: 0,
                  right: 0,
                  bottom: 0,
                  background: 'rgba(0,0,0,0.7)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  zIndex: 1000
                }}>
                  <div className="card" style={{ width: 500, maxHeight: '80vh', overflow: 'auto' }}>
                    <div className="card-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <span className="card-title">Add Product</span>
                      <button
                        onClick={() => {
                          setShowAddProductModal(false);
                          setProductSearch('');
                          setProductSearchResults([]);
                          setSelectedProductType(null);
                          setNewProductRuns(1);
                        }}
                        style={{ background: 'none', border: 'none', color: 'var(--text-secondary)', cursor: 'pointer' }}
                      >
                        <X size={20} />
                      </button>
                    </div>
                    <div style={{ padding: 16 }}>
                      {/* Search Input */}
                      <div style={{ position: 'relative', marginBottom: 16 }}>
                        <Search size={16} style={{ position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)', color: 'var(--text-secondary)' }} />
                        <input
                          type="text"
                          placeholder="Search for ships, modules..."
                          value={productSearch}
                          onChange={(e) => {
                            setProductSearch(e.target.value);
                            searchProducts(e.target.value);
                          }}
                          style={{
                            width: '100%',
                            padding: '10px 10px 10px 36px',
                            borderRadius: 6,
                            border: '1px solid var(--border-color)',
                            background: 'var(--bg-darker)',
                            color: 'inherit'
                          }}
                          autoFocus
                        />
                      </div>

                      {/* Search Results */}
                      {isSearchingProducts && (
                        <div style={{ textAlign: 'center', padding: 16, color: 'var(--text-secondary)' }}>
                          Searching...
                        </div>
                      )}

                      {!selectedProductType && productSearchResults.length > 0 && (
                        <div style={{ maxHeight: 300, overflow: 'auto', marginBottom: 16 }}>
                          {productSearchResults.map((item) => (
                            <div
                              key={item.typeID}
                              onClick={() => setSelectedProductType({ typeID: item.typeID, typeName: item.typeName })}
                              style={{
                                padding: '10px 12px',
                                cursor: 'pointer',
                                borderRadius: 4,
                                marginBottom: 4,
                                background: 'var(--bg-dark)',
                                transition: 'background 0.15s'
                              }}
                              onMouseEnter={(e) => e.currentTarget.style.background = 'var(--bg-darker)'}
                              onMouseLeave={(e) => e.currentTarget.style.background = 'var(--bg-dark)'}
                            >
                              {item.typeName}
                            </div>
                          ))}
                        </div>
                      )}

                      {/* Selected Product - Runs Input */}
                      {selectedProductType && (
                        <div style={{ background: 'var(--bg-dark)', padding: 16, borderRadius: 8 }}>
                          <div style={{ marginBottom: 12 }}>
                            <div style={{ fontSize: 14, fontWeight: 600 }}>{selectedProductType.typeName}</div>
                            <button
                              onClick={() => setSelectedProductType(null)}
                              style={{ fontSize: 12, color: 'var(--accent-blue)', background: 'none', border: 'none', cursor: 'pointer', padding: 0, marginTop: 4 }}
                            >
                              Change selection
                            </button>
                          </div>
                          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                            <label style={{ fontSize: 13 }}>Runs (Quantity):</label>
                            <input
                              type="number"
                              min="1"
                              max="10000"
                              value={newProductRuns}
                              onChange={(e) => setNewProductRuns(Math.max(1, parseInt(e.target.value) || 1))}
                              style={{
                                width: 100,
                                padding: '8px 12px',
                                borderRadius: 4,
                                border: '1px solid var(--border-color)',
                                background: 'var(--bg-darker)',
                                color: 'inherit'
                              }}
                            />
                          </div>
                          <button
                            className="btn btn-primary"
                            style={{ width: '100%', marginTop: 16 }}
                            onClick={() => {
                              addProduct.mutate({
                                typeId: selectedProductType.typeID,
                                typeName: selectedProductType.typeName,
                                quantity: newProductRuns
                              });
                            }}
                            disabled={addProduct.isPending}
                          >
                            {addProduct.isPending ? 'Adding...' : `Add ${newProductRuns} × ${selectedProductType.typeName}`}
                          </button>
                        </div>
                      )}

                      {!selectedProductType && productSearch.length >= 2 && productSearchResults.length === 0 && !isSearchingProducts && (
                        <div style={{ textAlign: 'center', padding: 16, color: 'var(--text-secondary)' }}>
                          No results found for "{productSearch}"
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              )}

              {/* View Content */}
              {viewMode === 'list' && (
                /* Aggregated Shopping List - Single Table */
                <div className="card">
                  <div className="card-header">
                    <span className="card-title">
                      <ShoppingCart size={18} style={{ marginRight: 8 }} />
                      Shopping List
                      <span className="neutral" style={{ fontWeight: 400, marginLeft: 8 }}>
                        ({aggregatedShoppingList.length} items • {formatISK(aggregatedTotal)})
                      </span>
                    </span>
                    {aggregatedShoppingList.length > 0 && (
                      <button
                        className="btn btn-secondary"
                        style={{ padding: '6px 12px' }}
                        onClick={() => handleExport()}
                      >
                        <Copy size={14} style={{ marginRight: 6 }} /> Copy
                      </button>
                    )}
                  </div>

                  {aggregatedShoppingList.length === 0 ? (
                    <div className="empty-state" style={{ padding: 40 }}>
                      <ShoppingCart size={48} style={{ opacity: 0.3, marginBottom: 12 }} />
                      <p className="neutral">No items in this list yet.</p>
                      <p className="neutral" style={{ fontSize: 12 }}>
                        Add a product above and calculate materials.
                      </p>
                    </div>
                  ) : (
                    <div className="table-container">
                      <table>
                        <thead>
                          <tr>
                            <th style={{ width: 40 }}></th>
                            <th>Item</th>
                            <th style={{ textAlign: 'right' }}>Quantity</th>
                            <th style={{ textAlign: 'right' }}>Unit Price</th>
                            <th style={{ textAlign: 'right' }}>Total</th>
                            <th style={{ width: 40 }}></th>
                          </tr>
                        </thead>
                        <tbody>
                          {aggregatedShoppingList.map((item) => (
                            <tr
                              key={item.type_id}
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
                              <td style={{ textAlign: 'right' }}>{formatQuantity(item.quantity)}</td>
                              <td style={{ textAlign: 'right' }} className="isk">
                                {formatISK(item.target_price, false)}
                              </td>
                              <td style={{ textAlign: 'right' }} className="isk">
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
                        <tfoot>
                          <tr style={{ background: 'var(--bg-dark)', fontWeight: 600 }}>
                            <td colSpan={4} style={{ textAlign: 'right', padding: '12px 16px' }}>
                              Total
                            </td>
                            <td style={{ textAlign: 'right', padding: '12px 16px' }} className="isk">
                              {formatISK(aggregatedTotal)}
                            </td>
                            <td></td>
                          </tr>
                        </tfoot>
                      </table>
                    </div>
                  )}
                </div>
              )}

                            {viewMode === 'compare' && (
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
                                                  applyRegionToAll(region);
                                                }}
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
                                            onClick={(e) => {
                                              e.stopPropagation();
                                              applyOptimalRegions();
                                            }}
                                            disabled={updateItemRegion.isPending}
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
                                                      // Use data attributes to ensure we get the correct item
                                                      // even if React re-renders during the event
                                                      const target = e.currentTarget;
                                                      const itemId = Number(target.dataset.itemId);
                                                      const typeId = Number(target.dataset.typeId);
                                                      const itemName = target.dataset.itemName || '';
                                                      const clickedRegion = target.dataset.region || '';
                                                      const price = target.dataset.price ? Number(target.dataset.price) : undefined;

                                                      if (!price) return;
                                                      if (updateItemRegion.isPending) return;

                                                      if (interactionMode === 'select') {
                                                        updateItemRegion.mutate({
                                                          itemId,
                                                          region: clickedRegion,
                                                          price
                                                        });
                                                      } else {
                                                        setOrderPopup({ typeId, itemName, region: clickedRegion });
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



              {viewMode === 'transport' && (
                /* Transport Options View */
                <div className="card">
                  <div className="card-header">
                    <span className="card-title">
                      <Truck size={18} style={{ marginRight: 8 }} />
                      Transport Options
                    </span>
                    <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                      <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 13 }}>
                        <input
                          type="checkbox"
                          checked={safeRoutesOnly}
                          onChange={(e) => setSafeRoutesOnly(e.target.checked)}
                        />
                        Safe routes only
                      </label>
                    </div>
                  </div>

                  {isLoadingTransport ? (
                    <div className="loading">
                      <div className="spinner"></div>
                      Calculating transport options...
                    </div>
                  ) : transportOptions?.options.length === 0 ? (
                    <div style={{ padding: 20, textAlign: 'center' }}>
                      <p className="neutral">{transportOptions?.message || 'No transport options available'}</p>
                      <p style={{ fontSize: 12, marginTop: 8 }}>
                        Run the capability sync to update available ships.
                      </p>
                    </div>
                  ) : (
                    <>
                      {/* Summary Header */}
                      <div style={{
                        padding: '12px 16px',
                        background: 'var(--bg-dark)',
                        borderBottom: '1px solid var(--border-color)',
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center'
                      }}>
                        <div>
                          <strong>{transportOptions?.volume_formatted}</strong>
                          <span className="neutral" style={{ marginLeft: 8 }}>
                            {transportOptions?.route_summary}
                          </span>
                        </div>
                        <div style={{ display: 'flex', gap: 4 }}>
                          {['fewest_trips', 'fastest', 'lowest_risk'].map(filter => (
                            <button
                              key={filter}
                              className={`btn btn-small ${transportFilter === filter ? 'btn-primary' : 'btn-secondary'}`}
                              onClick={() => setTransportFilter(transportFilter === filter ? '' : filter)}
                              style={{ padding: '4px 8px', fontSize: 11 }}
                            >
                              {filter === 'fewest_trips' ? 'Fewest Trips' :
                               filter === 'fastest' ? 'Fastest' : 'Lowest Risk'}
                            </button>
                          ))}
                        </div>
                      </div>

                      {/* Options List */}
                      <div style={{ padding: 16, display: 'flex', flexDirection: 'column', gap: 12 }}>
                        {transportOptions?.options.map((option, idx) => (
                            <div
                              key={option.id}
                              style={{
                                padding: 16,
                                background: 'var(--bg-dark)',
                                borderRadius: 8,
                                border: idx === 0 ? '2px solid var(--accent-blue)' : '1px solid var(--border-color)'
                              }}
                            >
                              {idx === 0 && (
                                <span className="badge badge-blue" style={{ marginBottom: 8, display: 'inline-block' }}>
                                  RECOMMENDED
                                </span>
                              )}

                              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                                <div>
                                  <div style={{ fontWeight: 600, marginBottom: 4 }}>
                                    {option.characters[0]?.name} → {option.characters[0]?.ship_name}
                                  </div>
                                  <div className="neutral" style={{ fontSize: 12 }}>
                                    {option.characters[0]?.ship_group} • {option.characters[0]?.ship_location}
                                  </div>
                                </div>

                                <div style={{ textAlign: 'right' }}>
                                  <span className={option.risk_score === 0 ? 'positive' : option.risk_score <= 2 ? 'neutral' : 'negative'}>
                                    {option.risk_score === 0 ? '✅' : '⚠️'} {option.risk_label}
                                  </span>
                                </div>
                              </div>

                              <div style={{
                                display: 'grid',
                                gridTemplateColumns: 'repeat(4, 1fr)',
                                gap: 16,
                                marginTop: 12,
                                paddingTop: 12,
                                borderTop: '1px solid var(--border-color)'
                              }}>
                                <div>
                                  <div className="neutral" style={{ fontSize: 11 }}>Trips</div>
                                  <div style={{ fontWeight: 600 }}>{option.trips}</div>
                                </div>
                                <div>
                                  <div className="neutral" style={{ fontSize: 11 }}>Time</div>
                                  <div style={{ fontWeight: 600 }}>{option.flight_time_formatted}</div>
                                </div>
                                <div>
                                  <div className="neutral" style={{ fontSize: 11 }}>Capacity Used</div>
                                  <div style={{ fontWeight: 600 }}>{option.capacity_used_pct}%</div>
                                </div>
                                <div>
                                  <div className="neutral" style={{ fontSize: 11 }}>Ship Capacity</div>
                                  <div style={{ fontWeight: 600 }}>{(option.capacity_m3 / 1000).toFixed(0)}K m³</div>
                                </div>
                              </div>
                            </div>
                          ))}
                      </div>
                    </>
                  )}
                </div>
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

      {/* Regional Comparison Modal - REMOVED - Now inline panel */}
      {false && (
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
          onClick={() => setShowCompareModal(false)}
        >
          <div
            className="card"
            style={{
              width: '95vw',
              maxWidth: 1400,
              maxHeight: '90vh',
              overflow: 'auto',
              padding: 24
            }}
            onClick={e => e.stopPropagation()}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
              <h2 style={{ margin: 0, display: 'flex', alignItems: 'center', gap: 12 }}>
                <Map size={24} />
                Regional Price Comparison
              </h2>
              <button
                className="btn btn-secondary"
                onClick={() => setShowCompareModal(false)}
                style={{ padding: '6px 12px' }}
              >
                <X size={18} />
              </button>
            </div>

            {isLoadingComparison ? (
              <div className="loading" style={{ padding: 40 }}>
                <div className="spinner"></div>
                Loading regional prices...
              </div>
            ) : !comparison?.items?.length ? (
              <div className="empty-state" style={{ padding: 40 }}>
                <p className="neutral">No items to compare. Calculate materials first.</p>
              </div>
            ) : (
              <>
                {/* Region Totals Summary */}
                <div className="stats-grid" style={{ marginBottom: 20 }}>
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
                <div style={{ marginBottom: 20 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
                    <h3 style={{ margin: 0 }}>Price Comparison</h3>
                    <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
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

                  <div className="table-container" style={{ maxHeight: 400, overflow: 'auto' }}>
                    <table>
                      <thead>
                        <tr>
                          <th
                            style={{ cursor: 'pointer', userSelect: 'none' }}
                            onClick={() => setCompareSort('name')}
                          >
                            Item {compareSort === 'name' && <ArrowUpDown size={12} />}
                          </th>
                          <th
                            style={{ cursor: 'pointer', userSelect: 'none' }}
                            onClick={() => setCompareSort('quantity')}
                          >
                            Qty {compareSort === 'quantity' && <ArrowUpDown size={12} />}
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
                                    const target = e.currentTarget;
                                    const itemId = Number(target.dataset.itemId);
                                    const typeId = Number(target.dataset.typeId);
                                    const itemName = target.dataset.itemName || '';
                                    const clickedRegion = target.dataset.region || '';
                                    const price = target.dataset.price ? Number(target.dataset.price) : undefined;

                                    if (!price) return;
                                    if (updateItemRegion.isPending) return;

                                    if (interactionMode === 'select') {
                                      updateItemRegion.mutate({ itemId, region: clickedRegion, price });
                                    } else {
                                      setOrderPopup({ typeId, itemName, region: clickedRegion });
                                    }
                                  }}
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

                {/* Shopping Route */}
                <ShoppingRouteDisplay
                  items={comparison.items}
                  homeSystem={comparison.home_system}
                />

                {/* Close Button */}
                <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: 20, paddingTop: 16, borderTop: '1px solid var(--border)' }}>
                  <button
                    className="btn btn-primary"
                    onClick={() => setShowCompareModal(false)}
                    style={{ padding: '10px 24px' }}
                  >
                    Done
                  </button>
                </div>
              </>
            )}
          </div>
        </div>
      )}

      {/* Sub-Product Decision Modal */}
      {showSubProductModal && pendingMaterials && (
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
          onClick={() => setShowSubProductModal(false)}
        >
          <div
            className="card"
            style={{
              maxWidth: 500,
              maxHeight: '80vh',
              overflow: 'auto',
              padding: 20
            }}
            onClick={e => e.stopPropagation()}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
              <h3 style={{ margin: 0 }}>Sub-Components Found</h3>
              <button className="btn btn-secondary" onClick={() => setShowSubProductModal(false)} style={{ padding: '4px 8px' }}>
                <X size={16} />
              </button>
            </div>

            <p className="neutral" style={{ marginBottom: 12 }}>
              These materials can be built from blueprints. Choose for each whether to buy or build:
            </p>

            {/* Select All buttons */}
            <div style={{ display: 'flex', gap: 8, marginBottom: 12 }}>
              <button
                className="btn btn-secondary"
                style={{ flex: 1, padding: '6px 12px', fontSize: 12 }}
                onClick={() => {
                  const allBuy: Record<number, 'buy' | 'build'> = {};
                  pendingMaterials.sub_products.forEach(sp => { allBuy[sp.type_id] = 'buy'; });
                  setSubProductDecisions(allBuy);
                }}
              >
                Select All: Buy
              </button>
              <button
                className="btn btn-secondary"
                style={{ flex: 1, padding: '6px 12px', fontSize: 12 }}
                onClick={() => {
                  const allBuild: Record<number, 'buy' | 'build'> = {};
                  pendingMaterials.sub_products.forEach(sp => { allBuild[sp.type_id] = 'build'; });
                  setSubProductDecisions(allBuild);
                }}
              >
                Select All: Build
              </button>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: 12, marginBottom: 20, maxHeight: 400, overflowY: 'auto' }}>
              {pendingMaterials.sub_products.map(sp => (
                <div
                  key={sp.type_id}
                  style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    padding: '10px 12px',
                    background: 'var(--bg-dark)',
                    borderRadius: 6
                  }}
                >
                  <div>
                    <div style={{ fontWeight: 500 }}>{sp.item_name}</div>
                    <div className="neutral" style={{ fontSize: 12 }}>x{formatQuantity(sp.quantity)}</div>
                  </div>
                  <select
                    value={subProductDecisions[sp.type_id] || 'buy'}
                    onChange={e => setSubProductDecisions({
                      ...subProductDecisions,
                      [sp.type_id]: e.target.value as 'buy' | 'build'
                    })}
                    style={{
                      padding: '6px 10px',
                      background: 'var(--bg-darker)',
                      border: '1px solid var(--border-color)',
                      borderRadius: 4,
                      color: 'inherit'
                    }}
                  >
                    <option value="buy">Buy</option>
                    <option value="build">Build</option>
                  </select>
                </div>
              ))}
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8 }}>
              <button
                className="btn btn-secondary"
                onClick={() => setShowSubProductModal(false)}
              >
                Cancel
              </button>
              <button
                className="btn btn-primary"
                onClick={handleApplyWithDecisions}
                disabled={applyMaterials.isPending}
              >
                {applyMaterials.isPending ? 'Applying...' : 'Apply Materials'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
