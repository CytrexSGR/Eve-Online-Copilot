import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { X, Plus, ShoppingCart, Check } from 'lucide-react';
import { api } from '../api';

interface ShoppingList {
  id: number;
  name: string;
  item_count: number;
}

interface AddToListModalProps {
  isOpen: boolean;
  onClose: () => void;
  item?: {
    type_id: number;
    item_name: string;
    quantity?: number;
    target_region?: string;
    target_price?: number;
  };
  productionTypeId?: number; // For adding all materials from a blueprint
  me?: number;
  runs?: number;
}

const CORP_ID = 98785281;

export default function AddToListModal({
  isOpen,
  onClose,
  item,
  productionTypeId,
  me = 10,
  runs = 1,
}: AddToListModalProps) {
  const queryClient = useQueryClient();
  const [newListName, setNewListName] = useState('');
  const [showNewList, setShowNewList] = useState(false);
  const [selectedListId, setSelectedListId] = useState<number | null>(null);
  const [quantity, setQuantity] = useState(item?.quantity || 1);
  const [success, setSuccess] = useState(false);

  // Fetch shopping lists
  const { data: lists } = useQuery<ShoppingList[]>({
    queryKey: ['shopping-lists', CORP_ID],
    queryFn: async () => {
      const response = await api.get('/api/shopping/lists', {
        params: { corporation_id: CORP_ID }
      });
      return response.data;
    },
    enabled: isOpen,
  });

  // Create new list
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
      setShowNewList(false);
    },
  });

  // Add single item
  const addItem = useMutation({
    mutationFn: async ({ listId, itemData }: { listId: number; itemData: typeof item }) => {
      if (!itemData) return;
      await api.post(`/api/shopping/lists/${listId}/items`, {
        type_id: itemData.type_id,
        item_name: itemData.item_name,
        quantity: quantity,
        target_region: itemData.target_region,
        target_price: itemData.target_price,
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['shopping-lists'] });
      setSuccess(true);
      setTimeout(() => {
        setSuccess(false);
        onClose();
      }, 1000);
    },
  });

  // Add production materials
  const addProduction = useMutation({
    mutationFn: async ({ listId, typeId }: { listId: number; typeId: number }) => {
      await api.post(`/api/shopping/lists/${listId}/add-production/${typeId}`, null, {
        params: { me, runs }
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['shopping-lists'] });
      setSuccess(true);
      setTimeout(() => {
        setSuccess(false);
        onClose();
      }, 1000);
    },
  });

  const handleAdd = () => {
    if (!selectedListId) return;

    if (productionTypeId) {
      addProduction.mutate({ listId: selectedListId, typeId: productionTypeId });
    } else if (item) {
      addItem.mutate({ listId: selectedListId, itemData: item });
    }
  };

  if (!isOpen) return null;

  const isLoading = addItem.isPending || addProduction.isPending || createList.isPending;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" style={{ maxWidth: 400 }} onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2 style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <ShoppingCart size={20} />
            Add to Shopping List
          </h2>
          <button className="btn-close" onClick={onClose}>
            <X size={20} />
          </button>
        </div>

        <div className="modal-body">
          {success ? (
            <div style={{ textAlign: 'center', padding: 40 }}>
              <Check size={48} className="positive" />
              <p style={{ marginTop: 16 }}>Added!</p>
            </div>
          ) : (
            <>
              {/* Item Info */}
              <div style={{ marginBottom: 20, padding: 12, background: 'var(--bg-dark)', borderRadius: 8 }}>
                {productionTypeId ? (
                  <div>
                    <div className="neutral" style={{ fontSize: 12 }}>All materials for:</div>
                    <div style={{ fontWeight: 500 }}>Production ({runs} Run{runs > 1 ? 's' : ''}, ME {me})</div>
                  </div>
                ) : item ? (
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div>
                      <div style={{ fontWeight: 500 }}>{item.item_name}</div>
                      <div className="neutral" style={{ fontSize: 12 }}>Type ID: {item.type_id}</div>
                    </div>
                    <div>
                      <input
                        type="number"
                        value={quantity}
                        onChange={(e) => setQuantity(Math.max(1, parseInt(e.target.value) || 1))}
                        min={1}
                        style={{
                          width: 80,
                          padding: '6px 10px',
                          background: 'var(--bg-card)',
                          border: '1px solid var(--border)',
                          borderRadius: 6,
                          color: 'var(--text-primary)',
                          textAlign: 'right'
                        }}
                      />
                    </div>
                  </div>
                ) : null}
              </div>

              {/* List Selection */}
              <div style={{ marginBottom: 16 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                  <span className="neutral" style={{ fontSize: 12, textTransform: 'uppercase' }}>Select List</span>
                  <button
                    className="btn btn-secondary"
                    style={{ padding: '4px 8px', fontSize: 12 }}
                    onClick={() => setShowNewList(true)}
                  >
                    <Plus size={14} /> New List
                  </button>
                </div>

                {showNewList && (
                  <div style={{ display: 'flex', gap: 8, marginBottom: 12 }}>
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
                          createList.mutate(newListName.trim());
                        }
                      }}
                      autoFocus
                    />
                    <button
                      className="btn btn-primary"
                      disabled={!newListName.trim()}
                      onClick={() => createList.mutate(newListName.trim())}
                    >
                      <Check size={16} />
                    </button>
                  </div>
                )}

                <div style={{ display: 'flex', flexDirection: 'column', gap: 8, maxHeight: 200, overflowY: 'auto' }}>
                  {lists?.length === 0 ? (
                    <div className="neutral" style={{ textAlign: 'center', padding: 20 }}>
                      No lists yet
                    </div>
                  ) : (
                    lists?.map((list) => (
                      <div
                        key={list.id}
                        onClick={() => setSelectedListId(list.id)}
                        style={{
                          padding: '10px 12px',
                          background: selectedListId === list.id ? 'var(--bg-hover)' : 'var(--bg-dark)',
                          border: `1px solid ${selectedListId === list.id ? 'var(--accent-blue)' : 'var(--border)'}`,
                          borderRadius: 6,
                          cursor: 'pointer',
                          display: 'flex',
                          justifyContent: 'space-between',
                          alignItems: 'center'
                        }}
                      >
                        <span>{list.name}</span>
                        <span className="neutral" style={{ fontSize: 12 }}>{list.item_count} Items</span>
                      </div>
                    ))
                  )}
                </div>
              </div>

              {/* Add Button */}
              <button
                className="btn btn-primary"
                style={{ width: '100%' }}
                disabled={!selectedListId || isLoading}
                onClick={handleAdd}
              >
                {isLoading ? 'Adding...' : 'Add'}
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
