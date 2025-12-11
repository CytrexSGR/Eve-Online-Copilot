import axios from 'axios';

// In development, use Vite proxy. In production, use relative path.
const API_BASE = '';

export const api = axios.create({
  baseURL: API_BASE,
  timeout: 300000, // 5 minutes for long scans
});

// Types
export interface ScanResult {
  blueprint_id: number;
  product_id: number;
  product_name: string;
  category: string;
  difficulty: number;
  material_cost: number;
  sell_price: number;
  profit: number;
  roi: number;
  volume_available: number;
  materials: Material[];
}

export interface Material {
  type_id: number;
  name: string;
  quantity: number;
  price: number;
  total: number;
  source: string;
}

export interface ArbitrageOpportunity {
  type_id: number;
  buy_region: string;
  buy_price: number;
  sell_region: string;
  sell_price: number;
  profit_per_unit: number;
  profit_percent: number;
  buy_volume_available: number;
  sell_volume_demand: number;
}

export interface EnhancedArbitrageOpportunity extends ArbitrageOpportunity {
  route?: {
    jumps: number;
    safety: 'safe' | 'caution' | 'dangerous';
    time_minutes: number;
    has_lowsec: boolean;
    has_nullsec: boolean;
  };
  cargo?: {
    unit_volume: number;
    units_per_trip: number;
    gross_profit_per_trip: number;
    isk_per_m3: number;
    ship_type: string;
    ship_capacity: number;
    fill_percent: number;
  };
  profitability?: {
    gross_profit: number;
    broker_fees: number;
    sales_tax: number;
    total_fees: number;
    net_profit: number;
    roi_percent: number;
    profit_per_hour: number | null;
  };
}

export interface EnhancedArbitrageResponse {
  type_id: number;
  item_name: string;
  item_volume: number | null;
  min_profit_percent: number;
  ship_type: string;
  ship_capacity: number;
  opportunities: EnhancedArbitrageOpportunity[];
  opportunity_count: number;
}

export interface RegionPrices {
  type_id: number;
  item_name: string;
  prices_by_region: Record<string, {
    region_id: number;
    lowest_sell: number | null;
    highest_buy: number | null;
    sell_volume: number;
    buy_volume: number;
  }>;
  best_buy_region: string;
  best_buy_price: number;
  best_sell_region: string;
  best_sell_price: number;
}

export interface ProductionOptimization {
  type_id: number;
  item_name: string;
  me_level: number;
  materials: {
    type_id: number;
    name: string;
    base_quantity: number;
    adjusted_quantity: number;
    prices_by_region: Record<string, number>;
  }[];
  production_cost_by_region: Record<string, number>;
  cheapest_production_region: string;
  cheapest_production_cost: number;
  product_prices: Record<string, {
    lowest_sell: number;
    highest_buy: number;
  }>;
  best_sell_region: string;
  best_sell_price: number;
}

// API Functions
export async function runMarketScan(params: {
  maxDifficulty?: number;
  minRoi?: number;
  minProfit?: number;
  top?: number;
}): Promise<ScanResult[]> {
  const response = await api.get('/api/hunter/scan', { params });
  return response.data.results || [];
}

export async function getItemArbitrage(typeId: number, minProfit = 5): Promise<ArbitrageOpportunity[]> {
  const response = await api.get(`/api/market/arbitrage/${typeId}`, {
    params: { min_profit: minProfit }
  });
  return response.data.opportunities || [];
}

export async function getEnhancedArbitrage(
  typeId: number,
  minProfit = 5,
  shipType = 'industrial'
): Promise<EnhancedArbitrageResponse> {
  const response = await api.get(`/api/arbitrage/enhanced/${typeId}`, {
    params: {
      min_profit: minProfit,
      ship_type: shipType
    }
  });
  return response.data;
}

export async function compareRegionPrices(typeId: number): Promise<RegionPrices> {
  const response = await api.get(`/api/market/compare/${typeId}`);
  return response.data;
}

export async function optimizeProduction(typeId: number, me = 10): Promise<ProductionOptimization> {
  const response = await api.get(`/api/production/optimize/${typeId}`, {
    params: { me }
  });
  return response.data;
}

export async function searchItems(query: string) {
  const response = await api.get('/api/items/search', {
    params: { q: query }
  });
  return response.data.results || [];
}

export async function getRegions() {
  const response = await api.get('/api/regions');
  return response.data;
}

// War Room API
export async function getWarLosses(regionId: number, days = 7) {
  const response = await api.get(`/api/war/losses/${regionId}`, { params: { days } });
  return response.data;
}

export async function getWarDemand(regionId: number, days = 7) {
  const response = await api.get(`/api/war/demand/${regionId}`, { params: { days } });
  return response.data;
}

export async function getWarHeatmap(days = 7, minKills = 5) {
  const response = await api.get('/api/war/heatmap', { params: { days, min_kills: minKills } });
  return response.data;
}

export async function getWarCampaigns(hours = 48) {
  const response = await api.get('/api/war/campaigns', { params: { hours } });
  return response.data;
}

export async function getFWHotspots(minContested = 50) {
  const response = await api.get('/api/war/fw/hotspots', { params: { min_contested: minContested } });
  return response.data;
}

export async function getWarDoctrines(regionId: number, days = 7) {
  const response = await api.get(`/api/war/doctrines/${regionId}`, { params: { days } });
  return response.data;
}

export async function getWarConflicts(days = 7) {
  const response = await api.get('/api/war/conflicts', { params: { days } });
  return response.data;
}

export async function getWarSummary(days = 7) {
  const response = await api.get('/api/war/summary', { params: { days } });
  return response.data;
}

export async function getTopShips(days = 7, limit = 20) {
  const response = await api.get('/api/war/top-ships', { params: { days, limit } });
  return response.data;
}

export async function getSafeRoute(fromSystem: number, toSystem: number, avoidLowsec = true, avoidNullsec = true) {
  const response = await api.get(`/api/war/route/safe/${fromSystem}/${toSystem}`, {
    params: { avoid_lowsec: avoidLowsec, avoid_nullsec: avoidNullsec }
  });
  return response.data;
}

export async function getItemCombatStats(typeId: number, days = 7) {
  const response = await api.get(`/api/war/item/${typeId}/stats`, { params: { days } });
  return response.data;
}

export async function getWarAlerts(limit = 5) {
  const response = await api.get('/api/war/alerts', { params: { limit } });
  return response.data;
}
