import { api } from '../api';

// ============================================================
// Shopping Lists
// ============================================================

export async function getShoppingLists() {
  const response = await api.get('/api/shopping/lists', {
    headers: { 'Cache-Control': 'no-cache' }
  });
  return response.data;
}

export async function getShoppingList(listId: number) {
  const response = await api.get(`/api/shopping/lists/${listId}`);
  return response.data;
}

export async function createShoppingList(name: string) {
  const response = await api.post('/api/shopping/lists', {
    name,
    status: 'planning'
  });
  return response.data;
}

export async function deleteShoppingList(listId: number) {
  await api.delete(`/api/shopping/lists/${listId}`);
}

// ============================================================
// Shopping Items
// ============================================================

export async function addShoppingItem(listId: number, item: {
  type_id: number;
  quantity: number;
  item_type: 'product' | 'material';
}) {
  const response = await api.post(`/api/shopping/lists/${listId}/items`, item);
  return response.data;
}

export async function removeShoppingItem(itemId: number) {
  await api.delete(`/api/shopping/items/${itemId}`);
}

export async function markItemPurchased(itemId: number) {
  await api.post(`/api/shopping/items/${itemId}/purchased`);
}

export async function unmarkItemPurchased(itemId: number) {
  await api.delete(`/api/shopping/items/${itemId}/purchased`);
}

export async function updateItemRuns(itemId: number, runs: number, meLevel: number) {
  await api.patch(`/api/shopping/items/${itemId}/runs`, { runs, me_level: meLevel });
}

export async function updateItemBuildDecision(itemId: number, decision: 'buy' | 'build') {
  await api.patch(`/api/shopping/items/${itemId}/build-decision`, { decision });
}

export async function applyMaterials(itemId: number, materials: Array<{
  type_id: number;
  quantity: number;
  decision: 'buy' | 'build';
}>) {
  const response = await api.post(`/api/shopping/items/${itemId}/apply-materials`, {
    materials
  });
  return response.data;
}

// ============================================================
// Regional Comparison
// ============================================================

export async function getRegionalComparison(listId: number) {
  const response = await api.get(`/api/shopping/lists/${listId}/regional-comparison`);
  return response.data;
}

export async function updateItemRegion(itemId: number, region: string, price?: number) {
  await api.patch(`/api/shopping/items/${itemId}/region`, null, {
    params: { region, price }
  });
}

// ============================================================
// Transport & Cargo
// ============================================================

export async function getCargoSummary(listId: number) {
  const response = await api.get(`/api/shopping/lists/${listId}/cargo-summary`);
  return response.data;
}

export async function getTransportOptions(listId: number, homeStationId?: number) {
  const response = await api.get(`/api/shopping/lists/${listId}/transport-options`, {
    params: homeStationId ? { home_station_id: homeStationId } : {}
  });
  return response.data;
}

export async function getShoppingRoute(params: {
  regions: string;
  home_system: string;
  return_home: boolean;
}) {
  const response = await api.get('/api/shopping/route', { params });
  return response.data;
}

// ============================================================
// Orders & Market Data
// ============================================================

export async function getOrderSnapshot(typeId: number, region: string) {
  const response = await api.get(`/api/shopping/orders/${typeId}`, {
    params: { region }
  });
  return response.data;
}

export async function searchItems(query: string) {
  const response = await api.get('/api/items/search', {
    params: { q: query, limit: 15 }
  });
  return response.data;
}

// ============================================================
// Export
// ============================================================

export async function exportShoppingList(listId: number, region?: string) {
  const response = await api.get(`/api/shopping/lists/${listId}/export`, {
    params: region ? { region } : {}
  });
  return response.data;
}
