/**
 * Shopping Wizard Types
 *
 * Re-exports from central types/shopping.ts for backward compatibility
 */

export type {
  ProductInfo,
  SubComponent,
  Material,
  WizardShoppingItem as ShoppingItem,
  ShoppingTotals,
  RegionalPrice,
  RegionComparison,
  OptimalRouteStop,
  OptimalRoute,
  CalculateMaterialsResponse,
  CompareRegionsResponse,
  Decision,
  Decisions,
  WizardState,
} from '../../types/shopping';

export {
  REGION_NAMES,
  REGION_ORDER,
} from '../../types/shopping';
