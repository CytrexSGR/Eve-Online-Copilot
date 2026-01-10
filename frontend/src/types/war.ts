/**
 * War Room TypeScript Types
 *
 * Types for war room API responses and data structures.
 */

// ==================== Demand Analysis Types ====================

export interface DemandItem {
  type_id: number;
  name: string;
  quantity: number;
  market_stock: number;
  gap: number;
}

export interface DemandAnalysis {
  region_id: number;
  days: number;
  ships_lost: DemandItem[];
  items_lost: DemandItem[];
  market_gaps: DemandItem[];
}

// ==================== Heatmap Types ====================

export interface HeatmapPoint {
  system_id: number;
  name: string;
  region_id: number;
  region: string;
  security: number;
  x: number;
  z: number;
  kills: number;
}

// ==================== Doctrine Detection Types ====================

export interface DoctrineDetection {
  date: string;
  system_id: number;
  system_name: string;
  ship_type_id: number;
  ship_name: string;
  fleet_size: number;
  estimated_alliance?: string;
}

// ==================== Danger Scoring Types ====================

export interface DangerScore {
  system_id: number;
  danger_score: number;
  kills_24h: number;
  is_dangerous: boolean;
}

// ==================== Conflict Intel Types ====================

export interface ConflictIntel {
  alliance_id: number;
  alliance_name: string;
  enemy_alliances: string[];
  total_losses: number;
  active_fronts: number;
}

// ==================== Regional Summary Types ====================

export interface RegionalSummary {
  region_id: number;
  region_name: string;
  active_systems: number;
  total_kills: number;
  total_value: number;
}

// ==================== Top Ships Types ====================

export interface TopShip {
  type_id: number;
  name: string;
  group: string;
  quantity: number;
  value: number;
}

export interface TopShipsResponse {
  ships: TopShip[];
}

// ==================== Faction Warfare Types ====================

export interface FWHotspot {
  solar_system_id: number;
  solar_system_name: string;
  region_name: string;
  contested_percent: number;
  owner_faction_name: string;
  occupier_faction_name: string;
}

export interface FWHotspotsResponse {
  hotspots: FWHotspot[];
}

// ==================== Ships Destroyed Types ====================

export interface ShipLoss {
  type_id: number;
  name: string;
  quantity: number;
  market_stock: number;
  gap: number;
  avg_price?: number;
  total_value?: number;
}

export interface ShipsDestroyedResponse {
  ships_lost: ShipLoss[];
  items_lost: DemandItem[];
  market_gaps: DemandItem[];
  region_id: number;
  days: number;
}

// ==================== Market Gaps Types ====================

export interface MarketGap {
  type_id: number;
  name: string;
  destroyed: number;
  market_stock: number;
  gap: number;
  buy_price: number;
  sell_price: number;
  margin: number;
}
