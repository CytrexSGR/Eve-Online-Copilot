import { useState, useCallback, useMemo } from 'react';
import { useQueryClient, useMutation } from '@tanstack/react-query';
import { ShoppingCart, Plus, Trash2, Check, Copy, ChevronRight, X, RefreshCw, Package, Truck, Calculator, ChevronDown, ChevronUp, Search, BarChart3 } from 'lucide-react';
import { api } from '../api';
import { formatISK, formatQuantity } from '../utils/format';
import type {
  ShoppingListItem as ShoppingItem,
  CalculateMaterialsResponse,
} from '../types/shopping';
import {
  CORP_ID,
} from '../types/shopping';

// Component imports
import { OrderDetailsModal } from '../components/shopping/planner/OrderDetailsModal';
import { SubProductTree } from '../components/shopping/planner/SubProductTree';
import { ComparisonView } from '../components/shopping/planner/ComparisonView';
import { TransportView } from '../components/shopping/planner/TransportView';

// Hook imports
import { useShoppingLists } from '../hooks/shopping/useShoppingLists';
import { useShoppingItems } from '../hooks/shopping/useShoppingItems';
import { useRegionalComparison } from '../hooks/shopping/useRegionalComparison';
import { useTransportPlanning } from '../hooks/shopping/useTransportPlanning';
export default function ShoppingPlanner() {
  const queryClient = useQueryClient();
  const [selectedListId, setSelectedListId] = useState<number | null>(null);
  const [newListName, setNewListName] = useState('');
  const [showNewListForm, setShowNewListForm] = useState(false);
  const [viewMode, setViewMode] = useState<'list' | 'compare' | 'transport'>('list');
  const [orderPopup, setOrderPopup] = useState<{ typeId: number; itemName: string; region: string } | null>(null);
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

  // Use custom hooks for data fetching
  const { lists } = useShoppingLists(CORP_ID);
  const { list: selectedList } = useShoppingItems(selectedListId);
  const {
    comparison,
    updateItemRegion,
    applyOptimalRegions,
    applyRegionToAll
  } = useRegionalComparison(selectedListId, viewMode === 'compare');
  const {
    cargoSummary,
    transportOptions,
    safeRoutesOnly,
    setSafeRoutesOnly,
    transportFilter,
    setTransportFilter
  } = useTransportPlanning(selectedListId, viewMode === 'transport');

  // Extract data and loading states from query results
  const listsData = lists.data;
  const isLoading = lists.isLoading;
  const selectedListData = selectedList.data;
  const cargoSummaryData = cargoSummary.data;
  const comparisonData = comparison.data;
  const isLoadingComparison = comparison.isLoading;
  const refetchComparison = comparison.refetch;
  const transportOptionsData = transportOptions.data;
  const isLoadingTransport = transportOptions.isLoading;

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
        if (data.product.id) {
          applyMaterials.mutate({
            itemId: data.product.id,
            materials: data.materials,
            subProductDecisions: []
          });
        }
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
    if (!pendingMaterials || !pendingMaterials.product.id) return;
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
    if (!selectedListData?.items) return [];

    // Aggregate by type_id
    const aggregated: Record<number, ShoppingItem & { aggregatedQuantity: number }> = {};

    for (const item of selectedListData.items) {
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
  }, [selectedListData?.items, globalRuns]);

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

            {listsData?.length === 0 ? (
              <div className="empty-state" style={{ padding: 20 }}>
                <ShoppingCart size={32} style={{ opacity: 0.3 }} />
                <p className="neutral">No shopping lists yet</p>
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                {listsData?.map((list) => (
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
                      <h2 style={{ margin: 0 }}>{selectedListData?.name}</h2>
                      <div className="neutral" style={{ marginTop: 4 }}>
                        {selectedListData?.items?.length || 0} items
                        {selectedListData?.total_cost && ` • ${formatISK(selectedListData?.total_cost)} total`}
                      </div>
                    </div>
                    {/* Cargo Summary */}
                    {cargoSummaryData && cargoSummaryData.materials.total_volume_m3 > 0 && (
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
                        <span>Cargo: <strong>{cargoSummaryData.materials.volume_formatted}</strong></span>
                        <span className="neutral">({cargoSummaryData.materials.total_items} items)</span>
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
                      disabled={!cargoSummaryData || cargoSummaryData.materials.total_volume_m3 === 0}
                      title={!cargoSummaryData || cargoSummaryData.materials.total_volume_m3 === 0
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
                          if (selectedListData?.id) {
                            deleteList.mutate(selectedListData.id);
                          }
                        }
                      }}
                    >
                      <Trash2 size={16} />
                    </button>
                  </div>
                </div>
              </div>

              {/* Products Section - with material calculation */}
              {selectedListData && (
                <div className="card" style={{ marginBottom: 16 }}>
                  <div className="card-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span className="card-title">
                      <Package size={18} style={{ marginRight: 8 }} />
                      Products ({selectedListData?.products?.length || 0})
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
                    {(!selectedListData?.products || selectedListData?.products.length === 0) ? (
                      <div style={{ textAlign: 'center', padding: '24px 0', color: 'var(--text-secondary)' }}>
                        <Package size={32} style={{ opacity: 0.5, marginBottom: 8 }} />
                        <div>No products yet</div>
                        <div style={{ fontSize: 12, marginTop: 4 }}>Click "Add Product" to add a ship, module or other buildable item</div>
                      </div>
                    ) : (
                      <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                        {/* Calculate/Recalculate Materials buttons */}
                        <div style={{ display: 'flex', gap: 8, marginBottom: 8 }}>
                          {selectedListData?.products.some(p => !p.materials_calculated) && (
                            <button
                              className="btn btn-primary"
                              onClick={async () => {
                                for (const product of selectedListData?.products || []) {
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
                          {selectedListData?.products.some(p => p.materials_calculated) && (
                            <button
                              className="btn"
                              style={{ background: 'var(--bg-darker)', border: '1px solid var(--border-color)' }}
                              onClick={async () => {
                                if (confirm('Recalculate all materials? This will update quantities based on current runs/ME settings.')) {
                                  for (const product of selectedListData?.products || []) {
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
                        {selectedListData?.products.map((product) => (
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
                              <ComparisonView
                                comparison={comparisonData}
                                isLoading={isLoadingComparison}
                                onRefetch={() => refetchComparison()}
                                onApplyOptimalRegions={applyOptimalRegions}
                                onApplyRegionToAll={applyRegionToAll}
                                onSelectRegion={(itemId, region, price) => updateItemRegion.mutate({ itemId, region, price })}
                                onViewOrders={(typeId, itemName, region) => setOrderPopup({ typeId, itemName, region })}
                                isUpdating={updateItemRegion.isPending}
                              />
                            )}



              {viewMode === 'transport' && (
                <TransportView
                  transportOptions={transportOptionsData}
                  isLoading={isLoadingTransport}
                  safeRoutesOnly={safeRoutesOnly}
                  setSafeRoutesOnly={setSafeRoutesOnly}
                  transportFilter={transportFilter}
                  setTransportFilter={setTransportFilter}
                />
              )}
            </>
          )}
        </div>
      </div>

      {/* Order Details Modal */}
      {orderPopup && (
        <OrderDetailsModal
          typeId={orderPopup.typeId}
          itemName={orderPopup.itemName}
          region={orderPopup.region}
          onClose={() => setOrderPopup(null)}
        />
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
