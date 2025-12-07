import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Star, Trash2, ChevronRight } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { api } from '../api';

interface Bookmark {
  id: number;
  type_id: number;
  item_name: string;
  notes: string | null;
  tags: string[];
  priority: number;
  created_at: string;
}

const MINDI_CORP_ID = 98785281;

export default function Bookmarks() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const { data: bookmarks, isLoading } = useQuery<Bookmark[]>({
    queryKey: ['bookmarks', MINDI_CORP_ID],
    queryFn: async () => {
      const response = await api.get('/api/bookmarks', {
        params: { corporation_id: MINDI_CORP_ID }
      });
      return response.data;
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => api.delete(`/api/bookmarks/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['bookmarks'] });
    },
  });

  return (
    <div>
      <div className="page-header">
        <h1>Bookmarks</h1>
        <p>Your saved items for Minimal Industries [MINDI]</p>
      </div>

      <div className="card">
        {isLoading ? (
          <div className="loading">
            <div className="spinner"></div>
            Loading bookmarks...
          </div>
        ) : !bookmarks?.length ? (
          <div className="empty-state">
            <Star size={48} />
            <p>No bookmarks yet</p>
            <p className="neutral">Star items in the Market Scanner to add them here</p>
          </div>
        ) : (
          <div className="table-container">
            <table>
              <thead>
                <tr>
                  <th>Item</th>
                  <th>Notes</th>
                  <th>Added</th>
                  <th style={{ width: 80 }}></th>
                </tr>
              </thead>
              <tbody>
                {bookmarks.map((bookmark) => (
                  <tr
                    key={bookmark.id}
                    onClick={() => navigate(`/item/${bookmark.type_id}`)}
                    style={{ cursor: 'pointer' }}
                  >
                    <td>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                        <Star size={16} fill="var(--accent-yellow)" color="var(--accent-yellow)" />
                        <strong>{bookmark.item_name}</strong>
                      </div>
                    </td>
                    <td className="neutral">
                      {bookmark.notes || '-'}
                    </td>
                    <td className="neutral">
                      {new Date(bookmark.created_at).toLocaleDateString('de-DE')}
                    </td>
                    <td onClick={(e) => e.stopPropagation()}>
                      <button
                        className="btn-icon"
                        onClick={() => deleteMutation.mutate(bookmark.id)}
                        title="Remove bookmark"
                      >
                        <Trash2 size={16} />
                      </button>
                      <ChevronRight size={16} className="neutral" style={{ marginLeft: 8 }} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <div className="stats-grid" style={{ marginTop: 24 }}>
        <div className="stat-card">
          <div className="stat-label">Total Bookmarks</div>
          <div className="stat-value">{bookmarks?.length || 0}</div>
        </div>
      </div>
    </div>
  );
}
