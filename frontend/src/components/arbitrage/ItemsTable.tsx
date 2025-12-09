// frontend/src/components/arbitrage/ItemsTable.tsx
import { useState, useMemo } from 'react';
import { Search, Package } from 'lucide-react';

interface Item {
  typeID: number;
  typeName: string;
  groupID: number;
  volume: number | null;
  basePrice: number | null;
}

interface ItemsTableProps {
  items: Item[];
  selectedItemId: number | null;
  onSelectItem: (item: Item) => void;
  groupName: string;
  isLoading?: boolean;
}

export function ItemsTable({
  items,
  selectedItemId,
  onSelectItem,
  groupName,
  isLoading = false
}: ItemsTableProps) {
  const [searchQuery, setSearchQuery] = useState('');

  // Filter items based on search query
  const filteredItems = useMemo(() => {
    if (!searchQuery) return items;
    const query = searchQuery.toLowerCase();
    return items.filter(item =>
      item.typeName.toLowerCase().includes(query)
    );
  }, [items, searchQuery]);

  if (isLoading) {
    return (
      <div className="card" style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <div className="loading">Loading items...</div>
      </div>
    );
  }

  return (
    <div className="card" style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
      {/* Header */}
      <div style={{ padding: '1rem', borderBottom: '1px solid var(--border)' }}>
        <h3 style={{ margin: 0, marginBottom: '0.5rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <Package size={20} />
          Items in {groupName}
        </h3>

        {/* Search Filter */}
        <div style={{ position: 'relative' }}>
          <Search size={16} style={{ position: 'absolute', left: '0.75rem', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
          <input
            type="text"
            placeholder="Filter items..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            style={{ paddingLeft: '2.5rem', width: '100%' }}
          />
        </div>
      </div>

      {/* Items Table */}
      <div style={{ flex: 1, overflow: 'auto' }}>
        {filteredItems.length === 0 ? (
          <div style={{ padding: '2rem', textAlign: 'center', color: 'var(--text-muted)' }}>
            {searchQuery ? 'No items match your search' : 'No items in this group'}
          </div>
        ) : (
          <table className="data-table">
            <thead>
              <tr>
                <th>Item Name</th>
                <th>Volume</th>
                <th>Base Price</th>
              </tr>
            </thead>
            <tbody>
              {filteredItems.map(item => (
                <tr
                  key={item.typeID}
                  onClick={() => onSelectItem(item)}
                  className={selectedItemId === item.typeID ? 'selected' : ''}
                  style={{ cursor: 'pointer' }}
                >
                  <td><strong>{item.typeName}</strong></td>
                  <td>{item.volume ? `${item.volume.toLocaleString()} m³` : 'N/A'}</td>
                  <td>{item.basePrice ? `${item.basePrice.toLocaleString()} ISK` : 'N/A'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Footer with count */}
      <div style={{ padding: '0.75rem', borderTop: '1px solid var(--border)', fontSize: '0.875rem', color: 'var(--text-muted)' }}>
        Showing {filteredItems.length} of {items.length} items
      </div>
    </div>
  );
}
