import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useCallback } from 'react';
import type { ShoppingListDetail } from '../../types/shopping';
import {
  getShoppingList,
  addShoppingItem,
  removeShoppingItem,
  markItemPurchased,
  unmarkItemPurchased,
  updateItemRuns,
  updateItemBuildDecision,
  searchItems,
} from '../../api/shopping';

/**
 * Hook for managing shopping list items
 */
export function useShoppingItems(listId: number | null) {
  const queryClient = useQueryClient();

  // Fetch selected list details
  const list = useQuery<ShoppingListDetail>({
    queryKey: ['shopping-list', listId],
    queryFn: () => getShoppingList(listId!),
    enabled: !!listId,
  });

  // Mark item as purchased
  const markPurchased = useMutation({
    mutationFn: markItemPurchased,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['shopping-list', listId] });
      queryClient.invalidateQueries({ queryKey: ['shopping-lists'] });
    },
  });

  // Unmark item as purchased
  const unmarkPurchased = useMutation({
    mutationFn: unmarkItemPurchased,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['shopping-list', listId] });
      queryClient.invalidateQueries({ queryKey: ['shopping-lists'] });
    },
  });

  // Remove item from list
  const removeItem = useMutation({
    mutationFn: removeShoppingItem,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['shopping-list', listId] });
      queryClient.invalidateQueries({ queryKey: ['shopping-cargo', listId] });
      queryClient.invalidateQueries({ queryKey: ['shopping-comparison', listId] });
      queryClient.invalidateQueries({ queryKey: ['shopping-lists'] });
    },
  });

  // Add product to list
  const addProduct = useMutation({
    mutationFn: async ({ typeId, quantity }: { typeId: number; typeName: string; quantity: number }) => {
      if (!listId) throw new Error('No list selected');
      return addShoppingItem(listId, {
        type_id: typeId,
        quantity,
        item_type: 'product',
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['shopping-list', listId] });
      queryClient.invalidateQueries({ queryKey: ['shopping-lists'] });
      queryClient.invalidateQueries({ queryKey: ['shopping-cargo', listId] });
      queryClient.invalidateQueries({ queryKey: ['shopping-comparison', listId] });
    },
  });

  // Update item runs and ME level
  const updateRuns = useMutation({
    mutationFn: ({ itemId, runs, meLevel }: { itemId: number; runs: number; meLevel: number }) => {
      return updateItemRuns(itemId, runs, meLevel);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['shopping-list', listId] });
      queryClient.invalidateQueries({ queryKey: ['shopping-cargo', listId] });
      queryClient.invalidateQueries({ queryKey: ['shopping-lists'] });
    },
  });

  // Update product build decision (BUY/BUILD toggle)
  const updateBuildDecision = useMutation({
    mutationFn: ({ itemId, decision }: { itemId: number; decision: 'buy' | 'build' }) => {
      return updateItemBuildDecision(itemId, decision);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['shopping-list', listId] });
      queryClient.invalidateQueries({ queryKey: ['shopping-cargo', listId] });
      queryClient.invalidateQueries({ queryKey: ['shopping-comparison', listId] });
      queryClient.invalidateQueries({ queryKey: ['shopping-lists'] });
    },
  });

  // Bulk update build decisions
  const bulkUpdateBuildDecision = useCallback(
    async (itemIds: number[], decision: 'buy' | 'build') => {
      // Update all items in parallel
      await Promise.all(
        itemIds.map(itemId => updateItemBuildDecision(itemId, decision))
      );
      // Invalidate queries once after all updates
      queryClient.invalidateQueries({ queryKey: ['shopping-list', listId] });
      queryClient.invalidateQueries({ queryKey: ['shopping-cargo', listId] });
      queryClient.invalidateQueries({ queryKey: ['shopping-comparison', listId] });
      queryClient.invalidateQueries({ queryKey: ['shopping-lists'] });
    },
    [listId, queryClient]
  );

  // Search items
  const searchProducts = useCallback(async (query: string) => {
    if (query.length < 2) {
      return [];
    }
    const results = await searchItems(query);
    // Filter to only show items that are likely products (not blueprints, not special items)
    return results.results.filter((item: { typeName: string; groupID: number }) =>
      !item.typeName.includes('Blueprint') &&
      item.groupID !== 517 // Exclude Cosmos items
    );
  }, []);

  return {
    list,
    markPurchased,
    unmarkPurchased,
    removeItem,
    addProduct,
    updateRuns,
    updateBuildDecision,
    bulkUpdateBuildDecision,
    searchProducts,
  };
}
