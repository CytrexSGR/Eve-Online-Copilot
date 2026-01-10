import { ShoppingCart, Plus, Check, X, ChevronRight } from 'lucide-react';
import type { ShoppingListSummary } from '../../../types/shopping';

interface ListsSidebarProps {
  lists: ShoppingListSummary[] | undefined;
  selectedListId: number | null;
  onSelectList: (id: number) => void;
  showNewListForm: boolean;
  setShowNewListForm: (show: boolean) => void;
  newListName: string;
  setNewListName: (name: string) => void;
  onCreateList: (name: string) => void;
  isCreating?: boolean;
}

export function ListsSidebar({
  lists,
  selectedListId,
  onSelectList,
  showNewListForm,
  setShowNewListForm,
  newListName,
  setNewListName,
  onCreateList,
  isCreating
}: ListsSidebarProps) {
  return (
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
            style={{
              flex: 1,
              padding: '8px 12px',
              background: 'var(--bg-dark)',
              border: '1px solid var(--border)',
              borderRadius: 6,
              color: 'var(--text-primary)'
            }}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && newListName.trim()) {
                onCreateList(newListName.trim());
              }
            }}
          />
          <button
            className="btn btn-primary"
            disabled={!newListName.trim() || isCreating}
            onClick={() => onCreateList(newListName.trim())}
          >
            <Check size={16} />
          </button>
          <button
            className="btn btn-secondary"
            onClick={() => {
              setShowNewListForm(false);
              setNewListName('');
            }}
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
              onClick={() => onSelectList(list.id)}
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
  );
}
