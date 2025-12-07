import { useState, useCallback } from 'react';
import { Search, Package, ArrowRight, Loader2 } from 'lucide-react';
import { api } from '../../api';
import type { ProductInfo, SubComponent, ShoppingItem, ShoppingTotals, CalculateMaterialsResponse } from './types';

interface SearchResult {
  typeID: number;
  typeName: string;
  groupID: number;
}

interface ProductDefinitionStepProps {
  initialProduct: ProductInfo | null;
  onProductSelected: (
    product: ProductInfo,
    subComponents: SubComponent[],
    shoppingList: ShoppingItem[],
    totals: ShoppingTotals
  ) => void;
}

export function ProductDefinitionStep({ initialProduct, onProductSelected }: ProductDefinitionStepProps) {
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<SearchResult[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [selectedProduct, setSelectedProduct] = useState<SearchResult | null>(
    initialProduct ? { typeID: initialProduct.type_id, typeName: initialProduct.name, groupID: 0 } : null
  );
  const [runs, setRuns] = useState(initialProduct?.runs ?? 1);
  const [meLevel, setMeLevel] = useState(initialProduct?.me_level ?? 10);
  const [isCalculating, setIsCalculating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const searchProducts = useCallback(async (query: string) => {
    if (query.length < 2) {
      setSearchResults([]);
      return;
    }

    setIsSearching(true);
    try {
      const response = await api.get('/api/items/search', { params: { q: query, limit: 15 } });
      // Filter out blueprints and special items
      const results = response.data.results.filter((item: SearchResult) =>
        !item.typeName.includes('Blueprint') &&
        item.groupID !== 517
      );
      setSearchResults(results);
    } catch {
      setSearchResults([]);
    }
    setIsSearching(false);
  }, []);

  const handleSearch = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const query = e.target.value;
    setSearchQuery(query);
    searchProducts(query);
  }, [searchProducts]);

  const handleSelectProduct = useCallback((result: SearchResult) => {
    setSelectedProduct(result);
    setSearchQuery('');
    setSearchResults([]);
    setError(null);
  }, []);

  const handleCalculate = useCallback(async () => {
    if (!selectedProduct) return;

    setIsCalculating(true);
    setError(null);

    try {
      const response = await api.post<CalculateMaterialsResponse>('/api/shopping/wizard/calculate-materials', {
        product_type_id: selectedProduct.typeID,
        runs,
        me_level: meLevel,
        decisions: null, // Initial calculation with default decisions
      });

      const data = response.data;

      onProductSelected(
        data.product,
        data.sub_components,
        data.shopping_list,
        data.totals
      );
    } catch (err) {
      console.error('Failed to calculate materials:', err);
      setError('Failed to calculate materials. This item might not have a blueprint.');
    }

    setIsCalculating(false);
  }, [selectedProduct, runs, meLevel, onProductSelected]);

  return (
    <div style={{ padding: 24 }}>
      <h2 style={{ marginBottom: 8 }}>Step 1: Product Definition</h2>
      <p className="neutral" style={{ marginBottom: 24 }}>
        Search for the item you want to manufacture and specify the number of runs.
      </p>

      {/* Product Search */}
      <div style={{ marginBottom: 24 }}>
        <label style={{ display: 'block', marginBottom: 8, fontWeight: 500 }}>
          Product to Manufacture
        </label>

        {!selectedProduct ? (
          <div style={{ position: 'relative' }}>
            <Search
              size={18}
              style={{
                position: 'absolute',
                left: 12,
                top: '50%',
                transform: 'translateY(-50%)',
                color: 'var(--text-secondary)',
              }}
            />
            <input
              type="text"
              placeholder="Search for ships, modules, components..."
              value={searchQuery}
              onChange={handleSearch}
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

            {/* Search Results Dropdown */}
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
                    <Loader2 size={18} className="spin" style={{ marginRight: 8 }} />
                    Searching...
                  </div>
                ) : (
                  searchResults.map((result) => (
                    <div
                      key={result.typeID}
                      onClick={() => handleSelectProduct(result)}
                      style={{
                        padding: '12px 16px',
                        cursor: 'pointer',
                        borderBottom: '1px solid var(--border)',
                        display: 'flex',
                        alignItems: 'center',
                        gap: 12,
                      }}
                      onMouseEnter={(e) => e.currentTarget.style.background = 'var(--bg-hover)'}
                      onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
                    >
                      <Package size={16} style={{ color: 'var(--accent-blue)' }} />
                      <span>{result.typeName}</span>
                    </div>
                  ))
                )}
              </div>
            )}

            {searchQuery.length >= 2 && searchResults.length === 0 && !isSearching && (
              <div style={{
                position: 'absolute',
                top: '100%',
                left: 0,
                right: 0,
                marginTop: 4,
                background: 'var(--bg-card)',
                border: '1px solid var(--border)',
                borderRadius: 8,
                padding: 16,
                textAlign: 'center',
                color: 'var(--text-secondary)',
              }}>
                No results found for "{searchQuery}"
              </div>
            )}
          </div>
        ) : (
          /* Selected Product Display */
          <div style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            padding: 16,
            background: 'var(--bg-dark)',
            borderRadius: 8,
            border: '1px solid var(--accent-blue)',
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
              <Package size={24} style={{ color: 'var(--accent-blue)' }} />
              <span style={{ fontSize: 18, fontWeight: 600 }}>{selectedProduct.typeName}</span>
            </div>
            <button
              onClick={() => {
                setSelectedProduct(null);
                setError(null);
              }}
              className="btn btn-secondary"
              style={{ padding: '6px 12px' }}
            >
              Change
            </button>
          </div>
        )}
      </div>

      {/* Runs and ME Level */}
      {selectedProduct && (
        <div style={{
          display: 'grid',
          gridTemplateColumns: '1fr 1fr',
          gap: 24,
          marginBottom: 24,
        }}>
          <div>
            <label style={{ display: 'block', marginBottom: 8, fontWeight: 500 }}>
              Number of Runs
            </label>
            <input
              type="number"
              min="1"
              max="10000"
              value={runs}
              onChange={(e) => setRuns(Math.max(1, parseInt(e.target.value) || 1))}
              style={{
                width: '100%',
                padding: '12px 16px',
                borderRadius: 8,
                border: '1px solid var(--border)',
                background: 'var(--bg-dark)',
                color: 'var(--text-primary)',
                fontSize: 18,
                fontWeight: 500,
              }}
            />
            <p className="neutral" style={{ marginTop: 4, fontSize: 12 }}>
              How many times to run the blueprint
            </p>
          </div>

          <div>
            <label style={{ display: 'block', marginBottom: 8, fontWeight: 500 }}>
              Material Efficiency (ME)
            </label>
            <input
              type="number"
              min="0"
              max="10"
              value={meLevel}
              onChange={(e) => setMeLevel(Math.min(10, Math.max(0, parseInt(e.target.value) || 0)))}
              style={{
                width: '100%',
                padding: '12px 16px',
                borderRadius: 8,
                border: '1px solid var(--border)',
                background: 'var(--bg-dark)',
                color: 'var(--text-primary)',
                fontSize: 18,
                fontWeight: 500,
              }}
            />
            <p className="neutral" style={{ marginTop: 4, fontSize: 12 }}>
              Blueprint ME level (0-10)
            </p>
          </div>
        </div>
      )}

      {/* Error Message */}
      {error && (
        <div style={{
          padding: 16,
          marginBottom: 24,
          background: 'rgba(255, 100, 100, 0.1)',
          border: '1px solid var(--accent-red)',
          borderRadius: 8,
          color: 'var(--accent-red)',
        }}>
          {error}
        </div>
      )}

      {/* Calculate Button */}
      {selectedProduct && (
        <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
          <button
            onClick={handleCalculate}
            disabled={isCalculating}
            className="btn btn-primary"
            style={{
              padding: '12px 24px',
              fontSize: 16,
              display: 'flex',
              alignItems: 'center',
              gap: 8,
            }}
          >
            {isCalculating ? (
              <>
                <Loader2 size={18} className="spin" />
                Calculating...
              </>
            ) : (
              <>
                Calculate Materials
                <ArrowRight size={18} />
              </>
            )}
          </button>
        </div>
      )}
    </div>
  );
}

export default ProductDefinitionStep;
