/**
 * Shopping System Type Definitions
 *
 * Consolidated types for both Shopping Wizard and Shopping Planner
 */

// ============================================================
// Shopping Lists
// ============================================================

export interface ShoppingList {
  id: number;
  name: string;
  status: string;
  total_cost: number | null;
  item_count: number;
  purchased_count: number;
  created_at: string;
}

export interface ShoppingListDetail extends ShoppingList {
  items: ShoppingListItem[];
  products?: ShoppingListItem[];
  standalone_items?: ShoppingListItem[];
}

// ============================================================
// Shopping Items (Planner - Persisted Lists)
// ============================================================

export interface ShoppingListItem {
  id: number;
  type_id: number;
  item_name: string;
  quantity: number;
  target_region: string | null;
  target_price: number | null;
  actual_price: number | null;
  is_purchased: boolean;
  is_product?: boolean;
  runs?: number;
  me_level?: number;
  parent_item_id?: number | null;
  build_decision?: string | null;
  output_per_run?: number;
  materials?: ShoppingListItem[];
  sub_products?: ShoppingListItem[];
  materials_calculated?: boolean;
}

// ============================================================
// Shopping Items (Wizard - Temporary Calculations)
// ============================================================

export interface WizardShoppingItem {
  type_id: number;
  item_name: string;
  quantity: number;
  category: 'sub_component' | 'material';
  jita_sell: number | null;
  total_cost: number | null;
}

// ============================================================
// Production & Materials
// ============================================================

export interface ProductInfo {
  type_id: number;
  name: string;
  runs: number;
  me_level: number;
  output_per_run: number;
  total_output: number;
}

export interface SubComponent {
  type_id: number;
  item_name: string;
  quantity: number;
  base_quantity: number;
  volume: number;
  has_blueprint: boolean;
  default_decision: 'buy' | 'build';
}

export interface Material {
  type_id: number;
  item_name: string;
  quantity: number;
  base_quantity: number;
  volume: number;
  has_blueprint: boolean;
}

export interface ShoppingTotals {
  sub_components: number;
  raw_materials: number;
  grand_total: number;
}

export interface CalculateMaterialsResponse {
  product: {
    id?: number;
    type_id: number;
    name?: string; // For wizard
    item_name?: string; // For planner
    runs: number;
    me_level: number;
    output_per_run: number;
    total_output: number;
  };
  materials: Material[];
  sub_products: SubComponent[];
  sub_components?: SubComponent[]; // Alias for compatibility
  shopping_list?: WizardShoppingItem[]; // For wizard
  totals?: ShoppingTotals; // For wizard
}

export type Decision = 'buy' | 'build';
export type Decisions = Record<string, Decision>;

// ============================================================
// Regional Pricing & Comparison
// ============================================================

export interface RegionData {
  unit_price: number | null;
  price?: number | null; // Alias for unit_price (for compatibility)
  total: number | null;
  volume: number;
  has_stock: boolean;
}

// Alias for compatibility with Wizard
export type RegionalPrice = RegionData;

export interface ComparisonItem {
  id: number;
  type_id: number;
  item_name: string;
  quantity: number;
  current_region: string | null;
  current_price: number | null;
  regions: Record<string, RegionData>;
  cheapest_region: string | null;
  cheapest_price: number | null;
}

export interface RegionalComparison {
  list: { id: number; name: string; status: string };
  items: ComparisonItem[];
  region_totals: Record<string, {
    total: number;
    display_name: string;
    jumps?: number;
    travel_time?: string;
  }>;
  optimal_route: {
    regions: Record<string, Array<{
      item_name: string;
      quantity: number;
      price: number;
      total: number;
    }>>;
    total_cost: number;
    savings_vs_single_region: Record<string, number>;
  };
  home_system: string;
}

// ============================================================
// Wizard Comparison Types
// ============================================================

export interface RegionComparison {
  type_id: number;
  item_name: string;
  quantity: number;
  prices: Record<string, RegionalPrice>;
  best_region: string | null;
}

export interface OptimalRouteStop {
  region: string;
  region_name: string;
  items: Array<{
    type_id: number;
    item_name: string;
    quantity: number;
    price: number;
    total: number;
  }>;
  subtotal: number;
  jumps_from_previous?: number;
}

export interface OptimalRoute {
  stops: OptimalRouteStop[];
  total: number;
  jita_only_total: number;
  savings: number;
  savings_percent: number;
}

export interface CompareRegionsResponse {
  comparison: RegionComparison[];
  optimal_route: OptimalRoute;
}

// ============================================================
// Routing & Navigation
// ============================================================

export interface RouteSystem {
  name: string;
  security: number;
}

export interface RouteLeg {
  from: string;
  to: string;
  jumps: number;
  systems?: RouteSystem[];
}

export interface ShoppingRoute {
  total_jumps: number;
  route: RouteLeg[];
  order: string[];
  error?: string;
}

// ============================================================
// Market Orders
// ============================================================

export interface OrderSnapshot {
  rank: number;
  price: number;
  volume: number;
  location_id: number;
  issued: string | null;
}

export interface OrderRegionData {
  display_name: string;
  sells: OrderSnapshot[];
  buys: OrderSnapshot[];
  updated_at: string | null;
}

export interface OrderSnapshotResponse {
  type_id: number;
  regions: Record<string, OrderRegionData>;
}

// ============================================================
// Cargo & Transport
// ============================================================

export interface CargoSummary {
  list_id: number;
  products: Array<{
    type_id: number;
    item_name: string;
    runs: number;
    total_volume: number;
    me_level: number;
    output_per_run: number;
  }>;
  materials: {
    total_items: number;
    total_volume_m3: number;
    volume_formatted: string;
    breakdown_by_region: Record<string, {
      volume_m3: number;
      item_count: number;
    }>;
  };
}

export interface TransportOption {
  id: number;
  characters: Array<{
    id: number;
    name: string;
    ship_type_id: number;
    ship_name: string;
    ship_group: string;
    ship_location: string;
  }>;
  trips: number;
  flight_time_min: number;
  flight_time_formatted: string;
  capacity_m3: number;
  capacity_used_pct: number;
  risk_score: number;
  risk_label: string;
  dangerous_systems: string[];
  isk_per_trip: number;
}

export interface TransportOptions {
  total_volume_m3: number;
  volume_formatted: string;
  route_summary: string;
  options: TransportOption[];
  filters_available: string[];
  message?: string;
}

// ============================================================
// Wizard State
// ============================================================

export interface WizardState {
  currentStep: 1 | 2 | 3 | 4;
  product: ProductInfo | null;
  subComponents: SubComponent[];
  decisions: Decisions;
  shoppingList: WizardShoppingItem[];
  totals: ShoppingTotals | null;
  regionalComparison: CompareRegionsResponse | null;
}

// ============================================================
// Constants
// ============================================================

export const REGION_NAMES: Record<string, string> = {
  the_forge: 'Jita',
  domain: 'Amarr',
  heimatar: 'Rens',
  sinq_laison: 'Dodixie',
  metropolis: 'Hek',
};

export const REGION_ORDER = ['the_forge', 'domain', 'heimatar', 'sinq_laison', 'metropolis'] as const;

export const CORP_ID = 98785281;

export const START_SYSTEMS = [
  { name: 'Isikemi', value: 'isikemi' },
  { name: 'Jita', value: 'jita' },
  { name: 'Amarr', value: 'amarr' },
  { name: 'Rens', value: 'rens' },
  { name: 'Dodixie', value: 'dodixie' },
  { name: 'Hek', value: 'hek' },
] as const;
