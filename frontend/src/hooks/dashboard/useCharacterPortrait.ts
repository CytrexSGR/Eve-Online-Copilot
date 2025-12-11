import { useQuery } from '@tanstack/react-query';
import axios from 'axios';

export interface UseCharacterPortraitResult {
  url: string | null;
  loading: boolean;
  error: Error | null;
}

/**
 * Hook to fetch character portrait from backend proxy
 *
 * Features:
 * - Fetches from /api/character/{id}/portrait (backend proxy to ESI)
 * - Returns px256x256 URL
 * - Caches for 24 hours
 * - Fallback to default avatar on error
 *
 * @param characterId - EVE character ID
 * @returns Portrait URL, loading state, and error state
 */
export function useCharacterPortrait(characterId: number): UseCharacterPortraitResult {
  const { data, isLoading, error } = useQuery<{ px256x256: string }>({
    queryKey: ['character', characterId, 'portrait'],
    queryFn: async () => {
      const response = await axios.get(`/api/character/${characterId}/portrait`);
      return response.data;
    },
    staleTime: 24 * 60 * 60 * 1000, // 24 hours
    gcTime: 24 * 60 * 60 * 1000, // Keep in cache for 24 hours
    retry: 1, // Retry once on failure
  });

  // Return fallback URL on error
  const url = error ? '/default-avatar.png' : (data?.px256x256 ?? null);

  return {
    url,
    loading: isLoading,
    error: error as Error | null,
  };
}
