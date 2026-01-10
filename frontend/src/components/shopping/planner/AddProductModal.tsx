import { useState } from 'react';
import { X, Search } from 'lucide-react';
import { api } from '../../../api';

interface ProductSearchResult {
  typeID: number;
  typeName: string;
  groupID: number;
}

interface AddProductModalProps {
  onClose: () => void;
  onAddProduct: (typeId: number, typeName: string, quantity: number) => void;
  isAdding?: boolean;
}

export function AddProductModal({ onClose, onAddProduct, isAdding }: AddProductModalProps) {
  const [productSearch, setProductSearch] = useState('');
  const [productSearchResults, setProductSearchResults] = useState<ProductSearchResult[]>([]);
  const [selectedProduct, setSelectedProduct] = useState<{ typeID: number; typeName: string } | null>(null);
  const [runs, setRuns] = useState(1);
  const [isSearching, setIsSearching] = useState(false);

  const searchProducts = async (query: string) => {
    if (query.length < 2) {
      setProductSearchResults([]);
      return;
    }
    setIsSearching(true);
    try {
      const response = await api.get('/api/items/search', { params: { q: query, limit: 15 } });
      const results = response.data.results.filter((item: ProductSearchResult) =>
        !item.typeName.includes('Blueprint') &&
        item.groupID !== 517 // Exclude Cosmos items
      );
      setProductSearchResults(results);
    } catch {
      setProductSearchResults([]);
    }
    setIsSearching(false);
  };

  const handleAdd = () => {
    if (selectedProduct) {
      onAddProduct(selectedProduct.typeID, selectedProduct.typeName, runs);
    }
  };

  return (
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
            onClick={onClose}
            style={{ background: 'none', border: 'none', color: 'var(--text-secondary)', cursor: 'pointer' }}
          >
            <X size={20} />
          </button>
        </div>
        <div style={{ padding: 16 }}>
          {/* Search Input */}
          <div style={{ position: 'relative', marginBottom: 16 }}>
            <Search size={16} style={{
              position: 'absolute',
              left: 12,
              top: '50%',
              transform: 'translateY(-50%)',
              color: 'var(--text-secondary)'
            }} />
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
          {isSearching && (
            <div style={{ textAlign: 'center', padding: 16, color: 'var(--text-secondary)' }}>
              Searching...
            </div>
          )}

          {!selectedProduct && productSearchResults.length > 0 && (
            <div style={{ maxHeight: 300, overflow: 'auto', marginBottom: 16 }}>
              {productSearchResults.map((item) => (
                <div
                  key={item.typeID}
                  onClick={() => setSelectedProduct({ typeID: item.typeID, typeName: item.typeName })}
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
          {selectedProduct && (
            <div style={{ background: 'var(--bg-dark)', padding: 16, borderRadius: 8 }}>
              <div style={{ marginBottom: 12 }}>
                <div style={{ fontSize: 14, fontWeight: 600 }}>{selectedProduct.typeName}</div>
                <button
                  onClick={() => setSelectedProduct(null)}
                  style={{
                    fontSize: 12,
                    color: 'var(--accent-blue)',
                    background: 'none',
                    border: 'none',
                    cursor: 'pointer',
                    padding: 0,
                    marginTop: 4
                  }}
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
                  value={runs}
                  onChange={(e) => setRuns(Math.max(1, parseInt(e.target.value) || 1))}
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
                onClick={handleAdd}
                disabled={isAdding}
              >
                {isAdding ? 'Adding...' : `Add ${runs} × ${selectedProduct.typeName}`}
              </button>
            </div>
          )}

          {!selectedProduct && productSearch.length >= 2 && productSearchResults.length === 0 && !isSearching && (
            <div style={{ textAlign: 'center', padding: 16, color: 'var(--text-secondary)' }}>
              No results found for "{productSearch}"
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
