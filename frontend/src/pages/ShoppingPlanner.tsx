import { useState, useMemo } from 'react';
import { ShoppingCart } from 'lucide-react';
import { api } from '../api';
import type {
  ShoppingListItem as ShoppingItem,
  CalculateMaterialsResponse,
} from '../types/shopping';
import { CORP_ID } from '../types/shopping';

// Component imports
import {
  ListsSidebar,
  ListHeader,
  ProductsSection,
  AddProductModal,
  ShoppingListTable,
  SubProductModal,
  OrderDetailsModal,
  ComparisonView,
  TransportView,
} from '../components/shopping/planner';

// Hook imports
import { useShoppingLists } from '../hooks/shopping/useShoppingLists';
import { useShoppingItems } from '../hooks/shopping/useShoppingItems';
import { useRegionalComparison } from '../hooks/shopping/useRegionalComparison';
import { useTransportPlanning } from '../hooks/shopping/useTransportPlanning';
import { useShoppingMutations, useProductMutations } from '../hooks/shopping/useShoppingMutations';

export default function ShoppingPlanner() {
  // Selection state
  const [selectedListId, setSelectedListId] = useState<number | null>(null);
  const [newListName, setNewListName] = useState('');
  const [showNewListForm, setShowNewListForm] = useState(false);
  const [viewMode, setViewMode] = useState<'list' | 'compare' | 'transport'>('list');

  // Modal state
  const [orderPopup, setOrderPopup] = useState<{ typeId: number; itemName: string; region: string } | null>(null);
  const [showAddProductModal, setShowAddProductModal] = useState(false);
  const [showSubProductModal, setShowSubProductModal] = useState(false);
  const [pendingMaterials, setPendingMaterials] = useState<CalculateMaterialsResponse | null>(null);
  const [subProductDecisions, setSubProductDecisions] = useState<Record<number, 'buy' | 'build'>>({});

  // UI state
  const [expandedProducts, setExpandedProducts] = useState<Set<number>>(new Set());
  const [globalRuns, setGlobalRuns] = useState(1);

  // Data hooks
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

  // Mutations
  const {
    createList,
    deleteList,
    markPurchased,
    unmarkPurchased,
    removeItem,
    updateItemRuns,
    updateBuildDecision,
    handleBulkBuildDecision
  } = useShoppingMutations(
    selectedListId,
    setSelectedListId,
    setNewListName,
    setShowNewListForm,
    CORP_ID
  );

  const handleMaterialsCalculated = (data: CalculateMaterialsResponse) => {
    if (data.sub_products.length > 0) {
      setPendingMaterials(data);
      const defaults: Record<number, 'buy' | 'build'> = {};
      data.sub_products.forEach(sp => { defaults[sp.type_id] = 'buy'; });
      setSubProductDecisions(defaults);
      setShowSubProductModal(true);
    } else if (data.product.id) {
      applyMaterials.mutate({
        itemId: data.product.id,
        materials: data.materials,
        subProductDecisions: []
      });
    }
  };

  const { addProduct, calculateMaterials, applyMaterials } = useProductMutations(
    selectedListId,
    handleMaterialsCalculated
  );

  // Extract data from query results
  const listsData = lists.data;
  const isLoading = lists.isLoading;
  const selectedListData = selectedList.data;
  const cargoSummaryData = cargoSummary.data;
  const comparisonData = comparison.data;

  // Handlers
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

  const handleExport = async () => {
    if (!selectedListId) return;
    const response = await api.get(`/api/shopping/lists/${selectedListId}/export`);
    navigator.clipboard.writeText(response.data.content);
    alert('Copied to clipboard in EVE Multibuy format!');
  };

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
    setShowSubProductModal(false);
    setPendingMaterials(null);
  };

  const handleAddProduct = (typeId: number, typeName: string, quantity: number) => {
    addProduct.mutate({ typeId, typeName, quantity });
    setShowAddProductModal(false);
  };

  // Aggregated shopping list
  const aggregatedShoppingList = useMemo(() => {
    if (!selectedListData?.items) return [];

    const aggregated: Record<number, ShoppingItem & { aggregatedQuantity: number }> = {};

    for (const item of selectedListData.items) {
      if (item.is_product && !item.parent_item_id) continue;
      if (item.is_product && item.parent_item_id && item.build_decision === 'build') continue;

      if (aggregated[item.type_id]) {
        aggregated[item.type_id].aggregatedQuantity += item.quantity;
      } else {
        aggregated[item.type_id] = { ...item, aggregatedQuantity: item.quantity };
      }
    }

    return Object.values(aggregated).map(item => ({
      ...item,
      quantity: item.aggregatedQuantity * globalRuns,
    })).sort((a, b) => a.item_name.localeCompare(b.item_name));
  }, [selectedListData?.items, globalRuns]);

  const aggregatedTotal = useMemo(() => {
    return aggregatedShoppingList.reduce(
      (sum, item) => sum + (item.target_price || 0) * item.quantity,
      0
    );
  }, [aggregatedShoppingList]);

  // Loading state
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
        <ListsSidebar
          lists={listsData}
          selectedListId={selectedListId}
          onSelectList={setSelectedListId}
          showNewListForm={showNewListForm}
          setShowNewListForm={setShowNewListForm}
          newListName={newListName}
          setNewListName={setNewListName}
          onCreateList={(name) => createList.mutate(name)}
          isCreating={createList.isPending}
        />

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
          ) : selectedListData && (
            <>
              <ListHeader
                list={selectedListData}
                cargoSummary={cargoSummaryData}
                viewMode={viewMode}
                setViewMode={setViewMode}
                globalRuns={globalRuns}
                setGlobalRuns={setGlobalRuns}
                onExport={handleExport}
                onDelete={() => {
                  if (confirm('Delete this shopping list?')) {
                    deleteList.mutate(selectedListData.id);
                  }
                }}
              />

              <ProductsSection
                list={selectedListData}
                expandedProducts={expandedProducts}
                toggleProductExpanded={toggleProductExpanded}
                onAddProduct={() => setShowAddProductModal(true)}
                onCalculateMaterials={(id) => calculateMaterials.mutate(id)}
                onCalculateAllMaterials={() => {
                  selectedListData.products?.forEach(p => {
                    if (!p.materials_calculated) {
                      calculateMaterials.mutate(p.id);
                    }
                  });
                }}
                onRecalculateAll={() => {
                  if (confirm('Recalculate all materials?')) {
                    selectedListData.products?.forEach(p => calculateMaterials.mutate(p.id));
                  }
                }}
                onUpdateRuns={(id, runs, meLevel) => updateItemRuns.mutate({ itemId: id, runs, meLevel })}
                onRemoveProduct={(id) => removeItem.mutate(id)}
                updateBuildDecision={updateBuildDecision}
                onBulkBuildDecision={handleBulkBuildDecision}
                isCalculating={calculateMaterials.isPending}
              />

              {viewMode === 'list' && (
                <ShoppingListTable
                  items={aggregatedShoppingList}
                  totalCost={aggregatedTotal}
                  onMarkPurchased={(id) => markPurchased.mutate(id)}
                  onUnmarkPurchased={(id) => unmarkPurchased.mutate(id)}
                  onRemoveItem={(id) => removeItem.mutate(id)}
                  onExport={handleExport}
                />
              )}

              {viewMode === 'compare' && (
                <ComparisonView
                  comparison={comparisonData}
                  isLoading={comparison.isLoading}
                  onRefetch={() => comparison.refetch()}
                  onApplyOptimalRegions={applyOptimalRegions}
                  onApplyRegionToAll={applyRegionToAll}
                  onSelectRegion={(itemId, region, price) => updateItemRegion.mutate({ itemId, region, price })}
                  onViewOrders={(typeId, itemName, region) => setOrderPopup({ typeId, itemName, region })}
                  isUpdating={updateItemRegion.isPending}
                />
              )}

              {viewMode === 'transport' && (
                <TransportView
                  transportOptions={transportOptions.data}
                  isLoading={transportOptions.isLoading}
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

      {/* Modals */}
      {showAddProductModal && (
        <AddProductModal
          onClose={() => setShowAddProductModal(false)}
          onAddProduct={handleAddProduct}
          isAdding={addProduct.isPending}
        />
      )}

      {orderPopup && (
        <OrderDetailsModal
          typeId={orderPopup.typeId}
          itemName={orderPopup.itemName}
          region={orderPopup.region}
          onClose={() => setOrderPopup(null)}
        />
      )}

      {showSubProductModal && pendingMaterials && (
        <SubProductModal
          pendingMaterials={pendingMaterials}
          subProductDecisions={subProductDecisions}
          setSubProductDecisions={setSubProductDecisions}
          onClose={() => {
            setShowSubProductModal(false);
            setPendingMaterials(null);
          }}
          onApply={handleApplyWithDecisions}
          isApplying={applyMaterials.isPending}
        />
      )}
    </div>
  );
}
