// Shared types for Shopping Wizard

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

export interface ShoppingItem {
  type_id: number;
  item_name: string;
  quantity: number;
  category: 'sub_component' | 'material';
  jita_sell: number | null;
  total_cost: number | null;
}

export interface ShoppingTotals {
  sub_components: number;
  raw_materials: number;
  grand_total: number;
}

export interface RegionalPrice {
  price: number | null;
  total: number | null;
  volume: number;
  has_stock: boolean;
}

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

export interface CalculateMaterialsResponse {
  product: ProductInfo;
  sub_components: SubComponent[];
  shopping_list: ShoppingItem[];
  totals: ShoppingTotals;
}

export interface CompareRegionsResponse {
  comparison: RegionComparison[];
  optimal_route: OptimalRoute;
}

export type Decision = 'buy' | 'build';
export type Decisions = Record<string, Decision>;

export interface WizardState {
  currentStep: 1 | 2 | 3 | 4;
  product: ProductInfo | null;
  subComponents: SubComponent[];
  decisions: Decisions;
  shoppingList: ShoppingItem[];
  totals: ShoppingTotals | null;
  regionalComparison: CompareRegionsResponse | null;
}

export const REGION_NAMES: Record<string, string> = {
  the_forge: 'Jita',
  domain: 'Amarr',
  heimatar: 'Rens',
  sinq_laison: 'Dodixie',
  metropolis: 'Hek',
};

export const REGION_ORDER = ['the_forge', 'domain', 'heimatar', 'sinq_laison', 'metropolis'];
