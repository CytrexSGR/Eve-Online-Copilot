import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useCallback } from 'react';
import type { RegionalComparison, ShoppingListItem } from '../../types/shopping';
import {
  getRegionalComparison,
  updateItemRegion as apiUpdateItemRegion,
  exportShoppingList,
} from '../../api/shopping';

/**
 * Hook for regional price comparison and item region assignment
 */
export function useRegionalComparison(listId: number | null, enabled: boolean = false) {
  const queryClient = useQueryClient();

  // Fetch regional comparison data
  const comparison = useQuery<RegionalComparison>({
    queryKey: ['shopping-comparison', listId],
    queryFn: () => getRegionalComparison(listId!),
    enabled: !!listId && enabled,
  });

  // Update item region with optimistic updates to prevent UI jumping
  const updateItemRegion = useMutation({
    mutationFn: async ({ itemId, region, price }: { itemId: number; region: string; price?: number }) => {
      await apiUpdateItemRegion(itemId, region, price);
      return { itemId, region, price };
    },
    onMutate: async ({ itemId, region, price }) => {
      // Cancel any outgoing refetches to prevent overwriting optimistic update
      await queryClient.cancelQueries({ queryKey: ['shopping-comparison', listId] });
      await queryClient.cancelQueries({ queryKey: ['shopping-list', listId] });

      // Snapshot previous values for rollback
      const previousComparison = queryClient.getQueryData<RegionalComparison>([
        'shopping-comparison',
        listId,
      ]);
      const previousList = queryClient.getQueryData(['shopping-list', listId]);

      // Optimistically update comparison data
      if (previousComparison) {
        queryClient.setQueryData<RegionalComparison>(['shopping-comparison', listId], {
          ...previousComparison,
          items: previousComparison.items.map(item =>
            item.id === itemId ? { ...item, current_region: region, current_price: price ?? null } : item
          ),
        });
      }

      // Optimistically update list data
      if (previousList) {
        queryClient.setQueryData(['shopping-list', listId], (old: typeof previousList) => ({
          ...old,
          items: (old as { items: ShoppingListItem[] }).items?.map((item: ShoppingListItem) =>
            item.id === itemId ? { ...item, target_region: region, target_price: price } : item
          ),
        }));
      }

      return { previousComparison, previousList };
    },
    onError: (_err, _variables, context) => {
      // Rollback on error
      if (context?.previousComparison) {
        queryClient.setQueryData(['shopping-comparison', listId], context.previousComparison);
      }
      if (context?.previousList) {
        queryClient.setQueryData(['shopping-list', listId], context.previousList);
      }
    },
    onSuccess: () => {
      // Only invalidate shopping-lists to update list summaries
      // Comparison data is handled by optimistic updates above
      queryClient.invalidateQueries({ queryKey: ['shopping-lists'] });
    },
  });

  // Apply optimal regions to all items
  const applyOptimalRegions = useCallback(async () => {
    if (!comparison.data?.items) return;
    for (const item of comparison.data.items) {
      if (item.cheapest_region && item.cheapest_price) {
        await updateItemRegion.mutateAsync({
          itemId: item.id,
          region: item.cheapest_region,
          price: item.cheapest_price,
        });
      }
    }
    // Final refresh after all mutations complete
    queryClient.invalidateQueries({ queryKey: ['shopping-lists'] });
    queryClient.invalidateQueries({ queryKey: ['shopping-list', listId] });
    queryClient.invalidateQueries({ queryKey: ['shopping-comparison', listId] });
  }, [comparison.data?.items, updateItemRegion, queryClient, listId]);

  // Apply single region to all items
  const applyRegionToAll = useCallback(
    async (region: string) => {
      if (!comparison.data?.items) return;
      for (const item of comparison.data.items) {
        const regionData = item.regions[region];
        if (regionData?.unit_price) {
          await updateItemRegion.mutateAsync({
            itemId: item.id,
            region,
            price: regionData.unit_price,
          });
        }
      }
      // Final refresh after all mutations complete
      queryClient.invalidateQueries({ queryKey: ['shopping-lists'] });
      queryClient.invalidateQueries({ queryKey: ['shopping-list', listId] });
      queryClient.invalidateQueries({ queryKey: ['shopping-comparison', listId] });
    },
    [comparison.data?.items, updateItemRegion, queryClient, listId]
  );

  // Export shopping list to clipboard
  const exportList = useCallback(
    async (region?: string) => {
      if (!listId) return;
      const data = await exportShoppingList(listId, region);
      await navigator.clipboard.writeText(data.text);
      return data;
    },
    [listId]
  );

  return {
    comparison,
    updateItemRegion,
    applyOptimalRegions,
    applyRegionToAll,
    exportList,
  };
}
