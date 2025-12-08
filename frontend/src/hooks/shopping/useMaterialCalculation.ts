import { useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../../api';
import type { CalculateMaterialsResponse } from '../../types/shopping';
import { applyMaterials } from '../../api/shopping';

/**
 * Hook for calculating and applying production materials
 */
export function useMaterialCalculation(listId: number | null) {
  const queryClient = useQueryClient();

  // Calculate materials for a product
  const calculateMaterials = useMutation({
    mutationFn: async (itemId: number) => {
      const response = await api.post<CalculateMaterialsResponse>(
        `/api/shopping/items/${itemId}/calculate-materials`
      );
      return response.data;
    },
  });

  // Apply materials to shopping list
  const applyMaterialsMutation = useMutation({
    mutationFn: async ({
      itemId,
      materials,
    }: {
      itemId: number;
      materials: Array<{ type_id: number; item_name: string; quantity: number }>;
      subProductDecisions: Array<{
        type_id: number;
        item_name: string;
        quantity: number;
        decision: string;
      }>;
    }) => {
      // Convert materials format for API
      const materialsWithDecisions = materials.map(m => ({
        type_id: m.type_id,
        quantity: m.quantity,
        decision: 'buy' as const,
      }));
      return applyMaterials(itemId, materialsWithDecisions);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['shopping-list', listId] });
      queryClient.invalidateQueries({ queryKey: ['shopping-cargo', listId] });
      queryClient.invalidateQueries({ queryKey: ['shopping-comparison', listId] });
      queryClient.invalidateQueries({ queryKey: ['shopping-lists'] });
    },
  });

  return {
    calculateMaterials,
    applyMaterials: applyMaterialsMutation,
  };
}
