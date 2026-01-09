// Pilot Intelligence Battle Report Types

export interface HotZone {
  system_id: number;
  system_name: string;
  region_name: string;
  constellation_name: string;
  security_status: number;
  kills: number;
  total_isk_destroyed: number;
  dominant_ship_type: string;
  flags: string[];
}

export interface CapitalKill {
  killmail_id: number;
  ship_name: string;
  victim: number;
  isk_destroyed: number;
  system_name: string;
  region_name: string;
  security_status: number;
  time_utc: string;
}

export interface CapitalCategory {
  count: number;
  total_isk: number;
  kills: CapitalKill[];
}

export interface CapitalKills {
  titans: CapitalCategory;
  supercarriers: CapitalCategory;
  carriers: CapitalCategory;
  dreadnoughts: CapitalCategory;
  force_auxiliaries: CapitalCategory;
}

export interface HighValueKill {
  rank: number;
  killmail_id: number;
  isk_destroyed: number;
  ship_type: string;
  ship_name: string;
  victim: number;
  system_id: number;
  system_name: string;
  region_name: string;
  security_status: number;
  is_gank: boolean;
  time_utc: string;
}

export interface DangerZone {
  system_name: string;
  region_name: string;
  security_status: number;
  industrials_killed: number;
  freighters_killed: number;
  total_value: number;
  warning_level: 'EXTREME' | 'HIGH' | 'MODERATE';
}

export interface ShipCategory {
  count: number;
  total_isk: number;
}

export interface TimelineHour {
  hour_utc: number;
  kills: number;
  isk_destroyed: number;
}

export interface BattleReport {
  period: string;
  global: {
    total_kills: number;
    total_isk_destroyed: number;
    peak_hour_utc: number;
    peak_kills_per_hour: number;
  };
  hot_zones: HotZone[];
  capital_kills: CapitalKills;
  high_value_kills: HighValueKill[];
  danger_zones: DangerZone[];
  ship_breakdown: Record<string, ShipCategory>;
  timeline: TimelineHour[];
  regions: any[];  // Kept for backwards compatibility
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

export interface ShipClasses {
  capital: number;
  battleship: number;
  cruiser: number;
  frigate: number;
  destroyer: number;
  industrial: number;
  other: number;
}

export interface BiggestLoss {
  ship_type_id: number | null;
  value: number;
}

export interface CoalitionMember {
  alliance_id: number;
  name: string;
  activity: number;
}

export interface Coalition {
  name: string;
  leader_alliance_id: number;
  leader_name: string;
  member_count: number;
  members: CoalitionMember[];
  total_kills: number;
  total_losses: number;
  isk_destroyed: number;
  isk_lost: number;
  efficiency: number;
  total_activity: number;
}

export interface UnaffiliatedAlliance {
  alliance_id: number;
  name: string;
  kills: number;
  losses: number;
  isk_lost: number;
  activity: number;
}

export interface AllianceWars {
  period: string;
  global: {
    active_conflicts: number;
    total_alliances_involved: number;
    total_kills: number;
    total_isk_destroyed: number;
  };
  coalitions?: Coalition[];
  unaffiliated_alliances?: UnaffiliatedAlliance[];
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
      security?: number;
      region_name?: string;
    }>;
    winner: string | null;
    // NEW: War Intelligence Fields
    alliance_1_ship_classes?: ShipClasses;
    alliance_2_ship_classes?: ShipClasses;
    hourly_activity?: Record<number, number>;
    peak_hours?: number[];
    avg_kill_value?: number;
    alliance_1_biggest_loss?: BiggestLoss;
    alliance_2_biggest_loss?: BiggestLoss;
  }>;
  strategic_hotspots?: Array<{
    system_id: number;
    system_name: string;
    region_name: string;
    kills_24h: number;
    strategic_value: number;
  }>;
}

export interface AllianceWarsAnalysis {
  summary: string;
  insights: string[];
  trends?: string[];
  generated_at: string;
  error?: string;
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
