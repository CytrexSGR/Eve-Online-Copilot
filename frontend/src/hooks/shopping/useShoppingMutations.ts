import { useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../../api';
import type { CalculateMaterialsResponse } from '../../types/shopping';

export function useShoppingMutations(
  selectedListId: number | null,
  setSelectedListId: (id: number | null) => void,
  setNewListName: (name: string) => void,
  setShowNewListForm: (show: boolean) => void,
  corporationId: number
) {
  const queryClient = useQueryClient();

  const createList = useMutation({
    mutationFn: async (name: string) => {
      const response = await api.post('/api/shopping/lists', {
        name,
        corporation_id: corporationId
      });
      return response.data;
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['shopping-lists'] });
      setSelectedListId(data.id);
      setNewListName('');
      setShowNewListForm(false);
    },
  });

  const deleteList = useMutation({
    mutationFn: async (listId: number) => {
      await api.delete(`/api/shopping/lists/${listId}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['shopping-lists'] });
      setSelectedListId(null);
    },
  });

  const markPurchased = useMutation({
    mutationFn: async (itemId: number) => {
      await api.post(`/api/shopping/items/${itemId}/purchased`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['shopping-list', selectedListId] });
      queryClient.invalidateQueries({ queryKey: ['shopping-lists'] });
    },
  });

  const unmarkPurchased = useMutation({
    mutationFn: async (itemId: number) => {
      await api.delete(`/api/shopping/items/${itemId}/purchased`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['shopping-list', selectedListId] });
      queryClient.invalidateQueries({ queryKey: ['shopping-lists'] });
    },
  });

  const removeItem = useMutation({
    mutationFn: async (itemId: number) => {
      await api.delete(`/api/shopping/items/${itemId}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['shopping-list', selectedListId] });
      queryClient.invalidateQueries({ queryKey: ['shopping-cargo', selectedListId] });
      queryClient.invalidateQueries({ queryKey: ['shopping-comparison', selectedListId] });
      queryClient.invalidateQueries({ queryKey: ['shopping-lists'] });
    },
  });

  const updateItemRuns = useMutation({
    mutationFn: async ({ itemId, runs, meLevel }: { itemId: number; runs: number; meLevel: number }) => {
      await api.patch(`/api/shopping/items/${itemId}/runs`, { runs, me_level: meLevel });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['shopping-list', selectedListId] });
      queryClient.invalidateQueries({ queryKey: ['shopping-cargo', selectedListId] });
      queryClient.invalidateQueries({ queryKey: ['shopping-lists'] });
    },
  });

  const updateBuildDecision = useMutation({
    mutationFn: async ({ itemId, decision }: { itemId: number; decision: 'buy' | 'build' }) => {
      await api.patch(`/api/shopping/items/${itemId}/build-decision`, { decision });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['shopping-list', selectedListId] });
      queryClient.invalidateQueries({ queryKey: ['shopping-cargo', selectedListId] });
      queryClient.invalidateQueries({ queryKey: ['shopping-comparison', selectedListId] });
      queryClient.invalidateQueries({ queryKey: ['shopping-lists'] });
    },
  });

  const handleBulkBuildDecision = async (itemIds: number[], decision: 'buy' | 'build') => {
    await Promise.all(
      itemIds.map(itemId =>
        api.patch(`/api/shopping/items/${itemId}/build-decision`, { decision })
      )
    );
    queryClient.invalidateQueries({ queryKey: ['shopping-list', selectedListId] });
    queryClient.invalidateQueries({ queryKey: ['shopping-cargo', selectedListId] });
    queryClient.invalidateQueries({ queryKey: ['shopping-comparison', selectedListId] });
    queryClient.invalidateQueries({ queryKey: ['shopping-lists'] });
  };

  return {
    createList,
    deleteList,
    markPurchased,
    unmarkPurchased,
    removeItem,
    updateItemRuns,
    updateBuildDecision,
    handleBulkBuildDecision,
    queryClient
  };
}

export function useProductMutations(
  selectedListId: number | null,
  onMaterialsCalculated?: (data: CalculateMaterialsResponse) => void
) {
  const queryClient = useQueryClient();

  const addProduct = useMutation({
    mutationFn: async ({ typeId, typeName, quantity }: { typeId: number; typeName: string; quantity: number }) => {
      const response = await api.post(`/api/shopping/lists/${selectedListId}/items`, {
        type_id: typeId,
        item_name: typeName,
        quantity
      });
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['shopping-list', selectedListId] });
      queryClient.invalidateQueries({ queryKey: ['shopping-lists'] });
      queryClient.invalidateQueries({ queryKey: ['shopping-cargo', selectedListId] });
      queryClient.invalidateQueries({ queryKey: ['shopping-comparison', selectedListId] });
    },
  });

  const calculateMaterials = useMutation({
    mutationFn: async (itemId: number) => {
      const response = await api.post<CalculateMaterialsResponse>(`/api/shopping/items/${itemId}/calculate-materials`);
      return response.data;
    },
    onSuccess: (data) => {
      if (onMaterialsCalculated) {
        onMaterialsCalculated(data);
      }
    },
  });

  const applyMaterials = useMutation({
    mutationFn: async ({ itemId, materials, subProductDecisions }: {
      itemId: number;
      materials: Array<{ type_id: number; item_name: string; quantity: number }>;
      subProductDecisions: Array<{ type_id: number; item_name: string; quantity: number; decision: string }>;
    }) => {
      const response = await api.post(`/api/shopping/items/${itemId}/apply-materials`, {
        materials,
        sub_product_decisions: subProductDecisions
      });
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['shopping-list', selectedListId] });
      queryClient.invalidateQueries({ queryKey: ['shopping-cargo', selectedListId] });
      queryClient.invalidateQueries({ queryKey: ['shopping-comparison', selectedListId] });
      queryClient.invalidateQueries({ queryKey: ['shopping-lists'] });
    },
  });

  return {
    addProduct,
    calculateMaterials,
    applyMaterials
  };
}
