export interface BattleReport {
  period: string;
  global: {
    total_kills: number;
    total_isk_destroyed: number;
    most_active_region: string;
    most_expensive_region: string;
  };
  regions: Array<{
    region_id: number;
    region_name: string;
    kills: number;
    total_isk_destroyed: number;
    avg_kill_value: number;
    top_systems: Array<{
      system_id: number;
      system_name: string;
      kills: number;
    }>;
    top_ships: Array<{
      ship_type_id: number;
      ship_name: string;
      losses: number;
    }>;
    top_destroyed_items: Array<{
      item_type_id: number;
      item_name: string;
      quantity_destroyed: number;
    }>;
  }>;
}

export interface WarProfiteeringReport {
  items: Array<{
    item_type_id: number;
    item_name: string;
    group_id: number;
    quantity_destroyed: number;
    market_price: number;
    opportunity_value: number;
  }>;
  total_items: number;
  total_opportunity_value: number;
  period: string;
}

export interface AllianceWarsReport {
  wars: Array<{
    alliance_a_id: number;
    alliance_a_name: string;
    alliance_b_id: number;
    alliance_b_name: string;
    total_kills: number;
    kills_by_a: number;
    kills_by_b: number;
    isk_destroyed_by_a: number;
    isk_destroyed_by_b: number;
    kill_ratio_a: number;
    isk_efficiency_a: number;
    active_systems: number;
    winner: string;
  }>;
  total_wars: number;
  period: string;
}

export interface TradeRoutesReport {
  timestamp: string;
  routes: Array<{
    from_hub: string;
    to_hub: string;
    from_system_id: number;
    to_system_id: number;
    total_jumps: number;
    danger_level: string;
    avg_danger_score: number;
    total_danger_score: number;
    max_danger_system: {
      system_id: number;
      system_name: string;
      danger_score: number;
    } | null;
    systems: Array<{
      system_id: number;
      system_name: string;
      security: number;
      danger_score: number;
      kills_24h: number;
      isk_destroyed_24h: number;
      gate_camp_detected: boolean;
    }>;
  }>;
  total_routes: number;
  period: string;
  danger_scale: Record<string, string>;
}
