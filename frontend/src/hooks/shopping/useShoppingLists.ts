import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import type { ShoppingList } from '../../types/shopping';
import { getShoppingLists, createShoppingList, deleteShoppingList } from '../../api/shopping';

/**
 * Hook for managing shopping lists (CRUD operations)
 */
export function useShoppingLists(corporationId?: number) {
  const queryClient = useQueryClient();

  // Fetch all shopping lists
  const lists = useQuery<ShoppingList[]>({
    queryKey: ['shopping-lists', corporationId],
    queryFn: getShoppingLists,
  });

  // Create new shopping list
  const createList = useMutation({
    mutationFn: createShoppingList,
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['shopping-lists'] });
      return data;
    },
  });

  // Delete shopping list
  const deleteList = useMutation({
    mutationFn: deleteShoppingList,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['shopping-lists'] });
    },
  });

  return {
    lists,
    createList,
    deleteList,
  };
}
