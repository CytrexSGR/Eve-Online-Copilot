import { Star } from 'lucide-react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from '../api';

interface BookmarkButtonProps {
  typeId: number;
  itemName: string;
  corporationId?: number;
  size?: number;
}

const MINDI_CORP_ID = 98785281;

export default function BookmarkButton({
  typeId,
  itemName,
  corporationId = MINDI_CORP_ID,
  size = 18
}: BookmarkButtonProps) {
  const queryClient = useQueryClient();

  const { data: checkData } = useQuery({
    queryKey: ['bookmark-check', typeId, corporationId],
    queryFn: async () => {
      const params = new URLSearchParams();
      if (corporationId) params.append('corporation_id', String(corporationId));
      const response = await api.get(`/api/bookmarks/check/${typeId}?${params}`);
      return response.data;
    },
  });

  const isBookmarked = checkData?.is_bookmarked ?? false;
  const bookmarkId = checkData?.bookmark?.id;

  const createMutation = useMutation({
    mutationFn: async () => {
      return api.post('/api/bookmarks', {
        type_id: typeId,
        item_name: itemName,
        corporation_id: corporationId,
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['bookmark-check', typeId] });
      queryClient.invalidateQueries({ queryKey: ['bookmarks'] });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: async () => {
      return api.delete(`/api/bookmarks/${bookmarkId}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['bookmark-check', typeId] });
      queryClient.invalidateQueries({ queryKey: ['bookmarks'] });
    },
  });

  const handleClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (isBookmarked && bookmarkId) {
      deleteMutation.mutate();
    } else {
      createMutation.mutate();
    }
  };

  const isLoading = createMutation.isPending || deleteMutation.isPending;

  return (
    <button
      className={`bookmark-btn ${isBookmarked ? 'active' : ''}`}
      onClick={handleClick}
      disabled={isLoading}
      title={isBookmarked ? 'Remove bookmark' : 'Add bookmark'}
    >
      <Star
        size={size}
        fill={isBookmarked ? 'var(--accent-yellow)' : 'none'}
        color={isBookmarked ? 'var(--accent-yellow)' : 'currentColor'}
      />
    </button>
  );
}
