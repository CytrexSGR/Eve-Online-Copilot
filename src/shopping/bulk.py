"""
Shopping List Bulk Operations.

Provides bulk add, export, and grouping operations for shopping lists.
"""

from typing import Optional, List

from psycopg2.extras import RealDictCursor

from src.database import get_db_connection


# Region ID to name mapping
REGION_ID_TO_NAME = {
    10000002: 'the_forge',
    10000043: 'domain',
    10000030: 'heimatar',
    10000032: 'sinq_laison',
    10000042: 'metropolis',
}


class ShoppingBulkMixin:
    """Mixin providing bulk operations for shopping lists."""

    def add_materials_from_production(
        self,
        list_id: int,
        type_id: int,
        me_level: int = 10,
        runs: int = 1
    ) -> List[dict]:
        """Add all materials for producing an item to the shopping list"""
        # Get materials and their cached prices in a single query
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Get materials for this product
                cur.execute("""
                    SELECT m."materialTypeID" as type_id, t."typeName" as name, m.quantity
                    FROM "invTypeMaterials" m
                    JOIN "invTypes" t ON m."materialTypeID" = t."typeID"
                    WHERE m."typeID" = %s
                """, (type_id,))
                materials = cur.fetchall()

                if not materials:
                    return []

                # Get all material type IDs
                material_ids = [m['type_id'] for m in materials]

                # Get cached prices for all materials at once
                cur.execute("""
                    SELECT type_id, region_id, lowest_sell
                    FROM market_prices
                    WHERE type_id = ANY(%s) AND lowest_sell IS NOT NULL
                """, (material_ids,))

                # Build price map: {type_id: {region_name: lowest_sell}}
                price_map = {}
                for row in cur.fetchall():
                    tid = row['type_id']
                    region_name = REGION_ID_TO_NAME.get(row['region_id'])
                    if not region_name:
                        continue
                    if tid not in price_map:
                        price_map[tid] = {}
                    price_map[tid][region_name] = float(row['lowest_sell'])

        me_factor = 1 - (me_level / 100)
        added_items = []

        for mat in materials:
            adjusted_qty = max(1, int(mat['quantity'] * me_factor * runs))

            # Get best price from cached data
            prices = price_map.get(mat['type_id'], {})
            best_region = None
            best_price = float('inf')

            for region, price in prices.items():
                if price and price < best_price:
                    best_price = price
                    best_region = region

            item = self.add_item(
                list_id=list_id,
                type_id=mat['type_id'],
                item_name=mat['name'],
                quantity=adjusted_qty,
                target_region=best_region,
                target_price=best_price if best_price != float('inf') else None
            )
            added_items.append(item)

        return added_items

    def export_multibuy(self, list_id: int, region: Optional[str] = None) -> str:
        """Export shopping list in EVE Multibuy format"""
        list_data = self.get_list_with_items(list_id)
        if not list_data:
            return ""

        lines = []
        for item in list_data['items']:
            if item['is_purchased']:
                continue
            if region and item['target_region'] != region:
                continue
            lines.append(f"{item['item_name']} {item['quantity']}")

        return "\n".join(lines)

    def get_by_region(self, list_id: int) -> dict:
        """Get shopping list items grouped by region"""
        list_data = self.get_list_with_items(list_id)
        if not list_data:
            return {}

        by_region = {}
        for item in list_data['items']:
            region = item['target_region'] or 'unassigned'
            if region not in by_region:
                by_region[region] = {
                    'items': [],
                    'total_cost': 0,
                    'item_count': 0
                }
            by_region[region]['items'].append(item)
            by_region[region]['item_count'] += 1
            if item['target_price']:
                by_region[region]['total_cost'] += item['target_price'] * item['quantity']

        return by_region
