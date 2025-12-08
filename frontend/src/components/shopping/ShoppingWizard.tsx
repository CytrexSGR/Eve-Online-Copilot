import { useState, useCallback } from 'react';
import { Wand2, Search, Package, Loader2, ShoppingCart, Wrench, Boxes, Map, TrendingDown, Copy, Check } from 'lucide-react';
import { api } from '../../api';
import { formatISK, formatQuantity } from '../../utils/format';
import type {
  ProductInfo,
  SubComponent,
  Decisions,
  Decision,
  ShoppingItem,
  ShoppingTotals,
  CalculateMaterialsResponse,
  CompareRegionsResponse,
} from './types';

const REGION_NAMES: Record<string, string> = {
  the_forge: 'Jita',
  domain: 'Amarr',
  heimatar: 'Rens',
  sinq_laison: 'Dodixie',
  metropolis: 'Hek',
};

const REGION_ORDER = ['the_forge', 'domain', 'heimatar', 'sinq_laison', 'metropolis'];

interface SearchResult {
  typeID: number;
  typeName: string;
  groupID: number;
}

// Toggle Button Component
function ToggleButton({ value, onChange, disabled }: { value: Decision; onChange: (v: Decision) => void; disabled?: boolean }) {
  return (
    <div style={{ display: 'flex', background: 'var(--bg-darker)', borderRadius: 6, padding: 2 }}>
      <button
        onClick={() => onChange('buy')}
        disabled={disabled}
        style={{
          padding: '4px 10px',
          borderRadius: 4,
          border: 'none',
          background: value === 'buy' ? 'var(--accent-blue)' : 'transparent',
          color: value === 'buy' ? 'white' : 'var(--text-secondary)',
          cursor: disabled ? 'not-allowed' : 'pointer',
          display: 'flex',
          alignItems: 'center',
          gap: 4,
          fontSize: 12,
          fontWeight: 500,
        }}
      >
        <ShoppingCart size={12} />
        BUY
      </button>
      <button
        onClick={() => onChange('build')}
        disabled={disabled}
        style={{
          padding: '4px 10px',
          borderRadius: 4,
          border: 'none',
          background: value === 'build' ? 'var(--accent-green)' : 'transparent',
          color: value === 'build' ? 'white' : 'var(--text-secondary)',
          cursor: disabled ? 'not-allowed' : 'pointer',
          display: 'flex',
          alignItems: 'center',
          gap: 4,
          fontSize: 12,
          fontWeight: 500,
        }}
      >
        <Wrench size={12} />
        BUILD
      </button>
    </div>
  );
}

export function ShoppingWizard() {
  // Product Selection State
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<SearchResult[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [selectedProduct, setSelectedProduct] = useState<SearchResult | null>(null);
  const [runs, setRuns] = useState(1);
  const [meLevel, setMeLevel] = useState(10);

  // Calculated Data State
  const [isCalculating, setIsCalculating] = useState(false);
  const [product, setProduct] = useState<ProductInfo | null>(null);
  const [subComponents, setSubComponents] = useState<SubComponent[]>([]);
  const [decisions, setDecisions] = useState<Decisions>({});
  const [shoppingList, setShoppingList] = useState<ShoppingItem[]>([]);
  const [totals, setTotals] = useState<ShoppingTotals | null>(null);

  // Regional Comparison State
  const [isLoadingComparison, setIsLoadingComparison] = useState(false);
  const [comparison, setComparison] = useState<CompareRegionsResponse | null>(null);
  const [copiedRegion, setCopiedRegion] = useState<string | null>(null);

  // Search products
  const searchProducts = useCallback(async (query: string) => {
    if (query.length < 2) {
      setSearchResults([]);
      return;
    }
    setIsSearching(true);
    try {
      const response = await api.get('/api/items/search', { params: { q: query, limit: 15 } });
      const results = response.data.results.filter((item: SearchResult) =>
        !item.typeName.includes('Blueprint') && item.groupID !== 517
      );
      setSearchResults(results);
    } catch {
      setSearchResults([]);
    }
    setIsSearching(false);
  }, []);

  // Calculate materials
  const calculateMaterials = useCallback(async (productTypeId: number, productRuns: number, productME: number, currentDecisions: Decisions) => {
    setIsCalculating(true);
    setComparison(null); // Reset comparison when recalculating

    try {
      const response = await api.post<CalculateMaterialsResponse>('/api/shopping/wizard/calculate-materials', {
        product_type_id: productTypeId,
        runs: productRuns,
        me_level: productME,
        decisions: Object.keys(currentDecisions).length > 0 ? currentDecisions : null,
      });

      const data = response.data;

      // Wizard endpoint always returns these fields with proper types
      const subComponents = data.sub_components || [];
      const shoppingList = data.shopping_list || [];

      setProduct(data.product as ProductInfo);
      setSubComponents(subComponents);
      setShoppingList(shoppingList);
      setTotals(data.totals || null);

      // Initialize decisions if not set
      if (Object.keys(currentDecisions).length === 0) {
        const initialDecisions: Decisions = {};
        subComponents.forEach(sc => {
          initialDecisions[sc.type_id.toString()] = 'buy';
        });
        setDecisions(initialDecisions);
      }

      // Auto-load regional comparison
      loadComparison(shoppingList);
    } catch (err) {
      console.error('Failed to calculate materials:', err);
    }

    setIsCalculating(false);
  }, []);

  // Load regional comparison
  const loadComparison = useCallback(async (items: ShoppingItem[]) => {
    if (items.length === 0) return;

    setIsLoadingComparison(true);
    try {
      const response = await api.post<CompareRegionsResponse>('/api/shopping/wizard/compare-regions', {
        items: items.map(item => ({ type_id: item.type_id, quantity: item.quantity })),
      });
      setComparison(response.data);
    } catch (err) {
      console.error('Failed to load comparison:', err);
    }
    setIsLoadingComparison(false);
  }, []);

  // Handle product selection
  const handleSelectProduct = useCallback((result: SearchResult) => {
    setSelectedProduct(result);
    setSearchQuery('');
    setSearchResults([]);
    calculateMaterials(result.typeID, runs, meLevel, {});
  }, [runs, meLevel, calculateMaterials]);

  // Handle runs/ME change
  const handleParameterChange = useCallback((newRuns: number, newME: number) => {
    setRuns(newRuns);
    setMeLevel(newME);
    if (selectedProduct) {
      calculateMaterials(selectedProduct.typeID, newRuns, newME, decisions);
    }
  }, [selectedProduct, decisions, calculateMaterials]);

  // Handle decision change
  const handleDecisionChange = useCallback((typeId: number, decision: Decision) => {
    const newDecisions = { ...decisions, [typeId.toString()]: decision };
    setDecisions(newDecisions);
    if (selectedProduct) {
      calculateMaterials(selectedProduct.typeID, runs, meLevel, newDecisions);
    }
  }, [selectedProduct, runs, meLevel, decisions, calculateMaterials]);

  // Handle select all
  const handleSelectAll = useCallback((decision: Decision) => {
    const newDecisions: Decisions = {};
    subComponents.forEach(sc => {
      newDecisions[sc.type_id.toString()] = decision;
    });
    setDecisions(newDecisions);
    if (selectedProduct) {
      calculateMaterials(selectedProduct.typeID, runs, meLevel, newDecisions);
    }
  }, [selectedProduct, runs, meLevel, subComponents, calculateMaterials]);

  // Export to clipboard
  const handleExport = useCallback((region?: string) => {
    let itemsToExport: Array<{ item_name: string; quantity: number }> = [];

    if (region && comparison) {
      const stop = comparison.optimal_route.stops.find(s => s.region === region);
      if (stop) {
        itemsToExport = stop.items.map(item => ({ item_name: item.item_name, quantity: item.quantity }));
      }
    } else {
      itemsToExport = shoppingList.map(item => ({ item_name: item.item_name, quantity: item.quantity }));
    }

    const content = itemsToExport.map(item => `${item.item_name} ${item.quantity}`).join('\n');
    navigator.clipboard.writeText(content);
    setCopiedRegion(region || 'all');
    setTimeout(() => setCopiedRegion(null), 2000);
  }, [comparison, shoppingList]);

  // Reset
  const handleReset = useCallback(() => {
    setSelectedProduct(null);
    setProduct(null);
    setSubComponents([]);
    setDecisions({});
    setShoppingList([]);
    setTotals(null);
    setComparison(null);
    setRuns(1);
    setMeLevel(10);
  }, []);

  // Separate items by category
  const subComponentItems = shoppingList.filter(item => item.category === 'sub_component');
  const materialItems = shoppingList.filter(item => item.category === 'material');

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <Wand2 size={28} />
            Shopping Wizard
          </h1>
          <p>Plan your manufacturing shopping - all steps visible at once</p>
        </div>
        {product && (
          <button className="btn btn-secondary" onClick={handleReset}>
            Start Over
          </button>
        )}
      </div>

      {/* SECTION 1: Product Definition */}
      <div className="card" style={{ marginBottom: 16 }}>
        <div className="card-header">
          <span className="card-title">
            <Package size={18} style={{ marginRight: 8 }} />
            1. Product Definition
          </span>
        </div>
        <div style={{ padding: 16 }}>
          {!selectedProduct ? (
            <div style={{ position: 'relative', maxWidth: 500 }}>
              <Search size={18} style={{ position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)', color: 'var(--text-secondary)' }} />
              <input
                type="text"
                placeholder="Search for ships, modules, components..."
                value={searchQuery}
                onChange={(e) => { setSearchQuery(e.target.value); searchProducts(e.target.value); }}
                style={{
                  width: '100%',
                  padding: '12px 12px 12px 40px',
                  borderRadius: 8,
                  border: '1px solid var(--border)',
                  background: 'var(--bg-dark)',
                  color: 'var(--text-primary)',
                  fontSize: 15,
                }}
                autoFocus
              />
              {(searchResults.length > 0 || isSearching) && (
                <div style={{
                  position: 'absolute',
                  top: '100%',
                  left: 0,
                  right: 0,
                  marginTop: 4,
                  background: 'var(--bg-card)',
                  border: '1px solid var(--border)',
                  borderRadius: 8,
                  maxHeight: 300,
                  overflow: 'auto',
                  zIndex: 100,
                  boxShadow: '0 4px 12px rgba(0,0,0,0.3)',
                }}>
                  {isSearching ? (
                    <div style={{ padding: 16, textAlign: 'center', color: 'var(--text-secondary)' }}>
                      <Loader2 size={18} className="spin" style={{ marginRight: 8 }} />Searching...
                    </div>
                  ) : (
                    searchResults.map((result) => (
                      <div
                        key={result.typeID}
                        onClick={() => handleSelectProduct(result)}
                        style={{ padding: '12px 16px', cursor: 'pointer', borderBottom: '1px solid var(--border)' }}
                        onMouseEnter={(e) => e.currentTarget.style.background = 'var(--bg-hover)'}
                        onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
                      >
                        {result.typeName}
                      </div>
                    ))
                  )}
                </div>
              )}
            </div>
          ) : (
            <div style={{ display: 'flex', alignItems: 'center', gap: 24, flexWrap: 'wrap' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '8px 16px', background: 'var(--bg-dark)', borderRadius: 8, border: '1px solid var(--accent-blue)' }}>
                <Package size={20} style={{ color: 'var(--accent-blue)' }} />
                <span style={{ fontSize: 16, fontWeight: 600 }}>{selectedProduct.typeName}</span>
                <button onClick={handleReset} className="btn btn-secondary" style={{ padding: '4px 8px', marginLeft: 8 }}>Change</button>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <label>Runs:</label>
                <input
                  type="number"
                  min="1"
                  max="10000"
                  value={runs}
                  onChange={(e) => handleParameterChange(Math.max(1, parseInt(e.target.value) || 1), meLevel)}
                  style={{ width: 80, padding: '8px 12px', borderRadius: 6, border: '1px solid var(--border)', background: 'var(--bg-dark)', color: 'var(--text-primary)' }}
                />
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <label>ME:</label>
                <input
                  type="number"
                  min="0"
                  max="10"
                  value={meLevel}
                  onChange={(e) => handleParameterChange(runs, Math.min(10, Math.max(0, parseInt(e.target.value) || 0)))}
                  style={{ width: 60, padding: '8px 12px', borderRadius: 6, border: '1px solid var(--border)', background: 'var(--bg-dark)', color: 'var(--text-primary)' }}
                />
              </div>
              {product && (
                <div className="neutral">
                  Output: <strong>{product.total_output}x {product.name}</strong>
                </div>
              )}
              {isCalculating && <Loader2 size={18} className="spin" />}
            </div>
          )}
        </div>
      </div>

      {/* SECTION 2: Sub-Components (only if there are any) */}
      {subComponents.length > 0 && (
        <div className="card" style={{ marginBottom: 16 }}>
          <div className="card-header">
            <span className="card-title">
              <Wrench size={18} style={{ marginRight: 8 }} />
              2. Sub-Components - Buy or Build?
            </span>
            <div style={{ display: 'flex', gap: 8 }}>
              <button onClick={() => handleSelectAll('buy')} className="btn btn-secondary" style={{ padding: '4px 12px', fontSize: 12 }} disabled={isCalculating}>
                <ShoppingCart size={14} style={{ marginRight: 4 }} /> All BUY
              </button>
              <button onClick={() => handleSelectAll('build')} className="btn btn-secondary" style={{ padding: '4px 12px', fontSize: 12 }} disabled={isCalculating}>
                <Wrench size={14} style={{ marginRight: 4 }} /> All BUILD
              </button>
            </div>
          </div>
          <div style={{ padding: 16, display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: 8 }}>
            {subComponents.map((component) => (
              <div
                key={component.type_id}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  padding: '8px 12px',
                  background: 'var(--bg-dark)',
                  borderRadius: 6,
                  borderLeft: `3px solid ${decisions[component.type_id.toString()] === 'build' ? 'var(--accent-green)' : 'var(--accent-blue)'}`,
                }}
              >
                <div>
                  <div style={{ fontWeight: 500, fontSize: 13 }}>{component.item_name}</div>
                  <div className="neutral" style={{ fontSize: 11 }}>x{formatQuantity(component.quantity)}</div>
                </div>
                <ToggleButton
                  value={decisions[component.type_id.toString()] || 'buy'}
                  onChange={(v) => handleDecisionChange(component.type_id, v)}
                  disabled={isCalculating}
                />
              </div>
            ))}
          </div>
        </div>
      )}

      {/* SECTION 3: Shopping List */}
      {shoppingList.length > 0 && (
        <div className="card" style={{ marginBottom: 16 }}>
          <div className="card-header">
            <span className="card-title">
              <ShoppingCart size={18} style={{ marginRight: 8 }} />
              3. Shopping List
            </span>
            <button onClick={() => handleExport()} className="btn btn-secondary" style={{ padding: '6px 12px' }}>
              {copiedRegion === 'all' ? <><Check size={14} /> Copied!</> : <><Copy size={14} /> Export All</>}
            </button>
          </div>
          <div style={{ padding: 16 }}>
            <div style={{ display: 'grid', gridTemplateColumns: subComponentItems.length > 0 ? '1fr 1fr' : '1fr', gap: 16 }}>
              {/* Sub-Components to Buy */}
              {subComponentItems.length > 0 && (
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8, color: 'var(--accent-blue)' }}>
                    <ShoppingCart size={16} />
                    <span style={{ fontWeight: 600 }}>Sub-Components to Buy ({subComponentItems.length})</span>
                  </div>
                  <div style={{ background: 'var(--bg-dark)', borderRadius: 8, overflow: 'hidden' }}>
                    {subComponentItems.map((item, idx) => (
                      <div key={item.type_id} style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 12px', borderBottom: idx < subComponentItems.length - 1 ? '1px solid var(--border)' : undefined }}>
                        <span>{item.item_name} <span className="neutral">x{formatQuantity(item.quantity)}</span></span>
                        <span className="isk">{item.total_cost ? formatISK(item.total_cost) : '-'}</span>
                      </div>
                    ))}
                    <div style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 12px', background: 'var(--bg-darker)', fontWeight: 600 }}>
                      <span>Subtotal</span>
                      <span className="isk">{totals ? formatISK(totals.sub_components) : '-'}</span>
                    </div>
                  </div>
                </div>
              )}

              {/* Raw Materials */}
              {materialItems.length > 0 && (
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8, color: 'var(--accent-green)' }}>
                    <Boxes size={16} />
                    <span style={{ fontWeight: 600 }}>Raw Materials ({materialItems.length})</span>
                  </div>
                  <div style={{ background: 'var(--bg-dark)', borderRadius: 8, overflow: 'hidden', maxHeight: 300, overflowY: 'auto' }}>
                    {materialItems.map((item, idx) => (
                      <div key={item.type_id} style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 12px', borderBottom: idx < materialItems.length - 1 ? '1px solid var(--border)' : undefined }}>
                        <span>{item.item_name} <span className="neutral">x{formatQuantity(item.quantity)}</span></span>
                        <span className="isk">{item.total_cost ? formatISK(item.total_cost) : '-'}</span>
                      </div>
                    ))}
                    <div style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 12px', background: 'var(--bg-darker)', fontWeight: 600 }}>
                      <span>Subtotal</span>
                      <span className="isk">{totals ? formatISK(totals.raw_materials) : '-'}</span>
                    </div>
                  </div>
                </div>
              )}
            </div>

            {/* Grand Total */}
            <div style={{ marginTop: 16, padding: 16, background: 'var(--bg-dark)', borderRadius: 8, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ fontSize: 16, fontWeight: 600 }}>TOTAL ESTIMATED COST (Jita)</span>
              <span style={{ fontSize: 20, fontWeight: 700 }} className="isk">{totals ? formatISK(totals.grand_total) : '-'}</span>
            </div>
          </div>
        </div>
      )}

      {/* SECTION 4: Regional Comparison */}
      {shoppingList.length > 0 && (
        <div className="card">
          <div className="card-header">
            <span className="card-title">
              <Map size={18} style={{ marginRight: 8 }} />
              4. Regional Price Comparison
            </span>
            {isLoadingComparison && <Loader2 size={18} className="spin" />}
          </div>

          {isLoadingComparison ? (
            <div style={{ padding: 40, textAlign: 'center' }}>
              <Loader2 size={32} className="spin" style={{ marginBottom: 16 }} />
              <div>Loading regional prices...</div>
            </div>
          ) : comparison ? (
            <div style={{ padding: 16 }}>
              {/* Price Table */}
              <div style={{ overflow: 'auto', marginBottom: 16 }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
                  <thead>
                    <tr style={{ background: 'var(--bg-dark)' }}>
                      <th style={{ padding: '8px 12px', textAlign: 'left' }}>Item</th>
                      <th style={{ padding: '8px 12px', textAlign: 'right' }}>Qty</th>
                      {REGION_ORDER.map(region => (
                        <th key={region} style={{ padding: '8px 12px', textAlign: 'right' }}>{REGION_NAMES[region]}</th>
                      ))}
                      <th style={{ padding: '8px 12px', textAlign: 'center' }}>Best</th>
                    </tr>
                  </thead>
                  <tbody>
                    {comparison.comparison.map((item) => (
                      <tr key={item.type_id} style={{ borderBottom: '1px solid var(--border)' }}>
                        <td style={{ padding: '8px 12px' }}>{item.item_name}</td>
                        <td style={{ padding: '8px 12px', textAlign: 'right' }}>{formatQuantity(item.quantity)}</td>
                        {REGION_ORDER.map(region => {
                          const regionData = item.prices[region];
                          const isBest = region === item.best_region;
                          return (
                            <td key={region} style={{ padding: '8px 12px', textAlign: 'right', background: isBest ? 'rgba(100, 200, 100, 0.1)' : undefined }} className={isBest ? 'positive' : 'isk'}>
                              {regionData?.total ? formatISK(regionData.total) : '-'}
                            </td>
                          );
                        })}
                        <td style={{ padding: '8px 12px', textAlign: 'center' }}>
                          {item.best_region && <span className="badge badge-green" style={{ fontSize: 10 }}>{REGION_NAMES[item.best_region]}</span>}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* Optimal Route */}
              <div style={{ background: 'var(--bg-dark)', borderRadius: 8, padding: 16 }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16 }}>
                  <h4 style={{ margin: 0, display: 'flex', alignItems: 'center', gap: 8 }}>
                    <Map size={18} /> Optimal Shopping Route
                  </h4>
                  {comparison.optimal_route.savings > 0 && (
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8, color: 'var(--accent-green)' }}>
                      <TrendingDown size={18} />
                      <span style={{ fontWeight: 600 }}>Save {formatISK(comparison.optimal_route.savings)} ({comparison.optimal_route.savings_percent.toFixed(1)}%)</span>
                    </div>
                  )}
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 12 }}>
                  {comparison.optimal_route.stops.map((stop, idx) => (
                    <div key={stop.region} style={{ background: 'var(--bg-card)', borderRadius: 8, padding: 12 }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                          <span style={{ width: 24, height: 24, borderRadius: '50%', background: 'var(--accent-blue)', color: 'white', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 12, fontWeight: 600 }}>{idx + 1}</span>
                          <span style={{ fontWeight: 600 }}>{stop.region_name}</span>
                        </div>
                        <button onClick={() => handleExport(stop.region)} className="btn btn-secondary" style={{ padding: '2px 6px', fontSize: 10 }}>
                          {copiedRegion === stop.region ? <Check size={10} /> : <Copy size={10} />}
                        </button>
                      </div>
                      <div className="isk" style={{ fontWeight: 600, marginBottom: 4 }}>{formatISK(stop.subtotal)}</div>
                      <div className="neutral" style={{ fontSize: 11 }}>{stop.items.length} items</div>
                    </div>
                  ))}
                </div>

                {/* Totals */}
                <div style={{ marginTop: 16, paddingTop: 16, borderTop: '1px solid var(--border)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div>
                    <div style={{ fontSize: 14 }}>Multi-Hub Total: <strong className="isk">{formatISK(comparison.optimal_route.total)}</strong></div>
                    <div className="neutral" style={{ fontSize: 12 }}>vs Jita-only: {formatISK(comparison.optimal_route.jita_only_total)}</div>
                  </div>
                </div>
              </div>
            </div>
          ) : null}
        </div>
      )}
    </div>
  );
}

export default ShoppingWizard;
