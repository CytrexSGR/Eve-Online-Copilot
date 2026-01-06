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

export interface WarProfiteering {
  period: string;
  global: {
    total_opportunity_value: number;
    total_items_destroyed: number;
    unique_item_types: number;
    most_valuable_item: string;
  };
  items: Array<{
    item_type_id: number;
    item_name: string;
    quantity_destroyed: number;
    market_price: number;
    opportunity_value: number;
  }>;
  categories?: Array<{
    category_name: string;
    total_destroyed: number;
    total_value: number;
  }>;
}

export interface AllianceWars {
  period: string;
  global: {
    active_conflicts: number;
    total_alliances_involved: number;
    total_kills: number;
    total_isk_destroyed: number;
  };
  conflicts: Array<{
    alliance_1_id: number;
    alliance_1_name: string;
    alliance_2_id: number;
    alliance_2_name: string;
    alliance_1_kills: number;
    alliance_1_losses: number;
    alliance_1_isk_destroyed: number;
    alliance_1_isk_lost: number;
    alliance_1_efficiency: number;
    alliance_2_kills: number;
    alliance_2_losses: number;
    alliance_2_isk_destroyed: number;
    alliance_2_isk_lost: number;
    alliance_2_efficiency: number;
    duration_days: number;
    primary_regions: string[];
    active_systems: Array<{
      system_id: number;
      system_name: string;
      kills: number;
    }>;
    winner: string | null;
  }>;
  strategic_hotspots?: Array<{
    system_id: number;
    system_name: string;
    region_name: string;
    kills_24h: number;
    strategic_value: number;
  }>;
}

export interface TradeRoutes {
  period: string;
  global: {
    total_routes: number;
    dangerous_routes: number;
    avg_danger_score: number;
    gate_camps_detected: number;
  };
  routes: Array<{
    origin_system: string;
    destination_system: string;
    jumps: number;
    danger_score: number;
    total_kills: number;
    total_isk_destroyed: number;
    systems: Array<{
      system_id: number;
      system_name: string;
      security_status: number;
      danger_score: number;
      kills_24h: number;
      isk_destroyed_24h: number;
      is_gate_camp: boolean;
    }>;
  }>;
}
