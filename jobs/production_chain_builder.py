"""
Production Chain Builder

Builds production_dependencies and production_chains tables from EVE SDE data.
Uses bottom-up approach: Raw Materials → Components → T1 → T2 → T3

Usage:
    python3 -m jobs.production_chain_builder --batch=raw_materials
    python3 -m jobs.production_chain_builder --batch=basic_components
    python3 -m jobs.production_chain_builder --batch=t1_items
    python3 -m jobs.production_chain_builder --item=648  # Build for single item (Drake)
"""

import sys
import argparse
from typing import List, Dict, Set, Tuple
from src.database import get_db_connection
from services.production.chain_repository import ProductionChainRepository


# Batch hierarchy configuration
BATCH_CONFIGS = {
    'all': {
        'name': 'All Manufacturable Items',
        'description': 'Process all items that have manufacturing blueprints',
    },
    't1_ships': {
        'name': 'T1 Ships',
        'description': 'Tech I ships',
        'group_ids': [25, 26, 27, 28, 29, 30, 31, 237, 324, 419, 420, 513, 540, 541, 543, 547, 830, 831, 832, 833, 834, 893, 894, 941, 963, 1022, 1201, 1202, 1283, 1527],
    },
    't2_items': {
        'name': 'T2 Items',
        'description': 'T2 Ships, Modules, Charges',
        'meta_group_id': 2,  # Tech II
    }
}


class ProductionChainBuilder:
    """Builds production chains from EVE SDE data"""

    def __init__(self):
        self.repo = ProductionChainRepository()
        self.processed_items: Set[int] = set()

    def get_items_for_batch(self, batch_name: str) -> List[int]:
        """Get list of item type IDs for a batch"""
        if batch_name not in BATCH_CONFIGS:
            print(f"Unknown batch: {batch_name}")
            return []

        config = BATCH_CONFIGS[batch_name]
        items = []

        try:
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    # Build WHERE clause based on config
                    where_clauses = []
                    params = []

                    if 'group_ids' in config and config['group_ids']:
                        placeholders = ','.join(['%s'] * len(config['group_ids']))
                        where_clauses.append(f't."groupID" IN ({placeholders})')
                        params.extend(config['group_ids'])

                    if 'market_group_ids' in config:
                        placeholders = ','.join(['%s'] * len(config['market_group_ids']))
                        where_clauses.append(f't."marketGroupID" IN ({placeholders})')
                        params.extend(config['market_group_ids'])

                    if 'meta_group_id' in config:
                        where_clauses.append('t."metaGroupID" = %s')
                        params.append(config['meta_group_id'])

                    # Get items that have blueprints (can be manufactured)
                    query = f"""
                        SELECT DISTINCT iap."productTypeID"
                        FROM "industryActivityProducts" iap
                        JOIN "invTypes" t ON iap."productTypeID" = t."typeID"
                        WHERE iap."activityID" = 1  -- Manufacturing
                        {f"AND ({' OR '.join(where_clauses)})" if where_clauses else ''}
                        AND t."published" = 1
                        ORDER BY iap."productTypeID"
                    """

                    cursor.execute(query, params)
                    rows = cursor.fetchall()
                    items = [row[0] for row in rows]

            print(f"Found {len(items)} items for batch '{batch_name}'")
            return items

        except Exception as e:
            print(f"Error getting items for batch: {e}")
            return []

    def build_dependencies(self, item_type_id: int) -> bool:
        """
        Build direct dependencies for an item from SDE

        Args:
            item_type_id: Item to build dependencies for

        Returns:
            True if successful
        """
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    # Get materials from SDE
                    cursor.execute("""
                        SELECT
                            iam."materialTypeID",
                            iam."quantity"
                        FROM "industryActivityMaterials" iam
                        WHERE iam."typeID" = (
                            SELECT "typeID"
                            FROM "industryActivityProducts"
                            WHERE "productTypeID" = %s
                            AND "activityID" = 1
                            LIMIT 1
                        )
                        AND iam."activityID" = 1
                    """, (item_type_id,))

                    materials = cursor.fetchall()

                    if not materials:
                        # No materials = raw material
                        return True

                    # Save each dependency
                    for material_type_id, quantity in materials:
                        # Check if material is a raw material (has no blueprint)
                        cursor.execute("""
                            SELECT COUNT(*)
                            FROM "industryActivityProducts"
                            WHERE "productTypeID" = %s
                            AND "activityID" = 1
                        """, (material_type_id,))

                        is_raw = cursor.fetchone()[0] == 0

                        self.repo.save_dependency(
                            item_type_id=item_type_id,
                            material_type_id=material_type_id,
                            base_quantity=quantity,
                            activity_id=1,
                            is_raw_material=is_raw
                        )

            return True

        except Exception as e:
            print(f"Error building dependencies for {item_type_id}: {e}")
            return False

    def build_complete_chain(self, item_type_id: int, depth: int = 0, path: List[int] = None) -> Dict[int, float]:
        """
        Recursively build complete production chain to raw materials

        Args:
            item_type_id: Item to build chain for
            depth: Current recursion depth
            path: Path taken to reach this item

        Returns:
            Dict mapping raw_material_type_id -> total quantity
        """
        if path is None:
            path = [item_type_id]

        # Prevent infinite loops
        if depth > 20:
            print(f"Warning: Max depth reached for {item_type_id}")
            return {}

        # Circular dependency check
        if item_type_id in path[:-1]:
            print(f"Warning: Circular dependency detected: {path}")
            return {}

        # Get direct dependencies
        dependencies = self.repo.get_direct_dependencies(item_type_id)

        if not dependencies:
            # This is a raw material
            return {item_type_id: 1.0}

        # Accumulate raw materials from all dependencies
        total_raw_materials: Dict[int, float] = {}

        for dep in dependencies:
            material_id = dep['material_type_id']
            quantity = dep['base_quantity']

            if dep['is_raw_material']:
                # Direct raw material
                total_raw_materials[material_id] = total_raw_materials.get(material_id, 0) + quantity
            else:
                # Recursively get materials for this component
                sub_materials = self.build_complete_chain(
                    material_id,
                    depth + 1,
                    path + [material_id]
                )

                # Multiply quantities and accumulate
                for raw_id, raw_qty in sub_materials.items():
                    total_qty = quantity * raw_qty
                    total_raw_materials[raw_id] = total_raw_materials.get(raw_id, 0) + total_qty

        return total_raw_materials

    def build_item(self, item_type_id: int) -> bool:
        """
        Build complete production data for a single item

        Args:
            item_type_id: Item to build

        Returns:
            True if successful
        """
        if item_type_id in self.processed_items:
            return True

        print(f"Building chain for item {item_type_id}...")

        # Step 1: Build direct dependencies
        if not self.build_dependencies(item_type_id):
            return False

        # Step 2: Build complete chain
        raw_materials = self.build_complete_chain(item_type_id)

        if not raw_materials:
            # Item might be a raw material itself
            print(f"  -> Item {item_type_id} is a raw material")
            self.processed_items.add(item_type_id)
            return True

        # Step 3: Save complete chains
        max_depth = 0
        for raw_material_id, total_quantity in raw_materials.items():
            # Calculate depth for this path
            # (Simplified: we use recursion depth as proxy)
            chain_depth = 1  # Will be improved with actual path tracking

            path_str = f"{item_type_id}->{raw_material_id}"

            self.repo.save_chain(
                item_type_id=item_type_id,
                raw_material_type_id=raw_material_id,
                base_quantity=total_quantity,
                chain_depth=chain_depth,
                path=path_str
            )

        print(f"  -> Saved {len(raw_materials)} raw material dependencies")
        self.processed_items.add(item_type_id)
        return True

    def build_batch(self, batch_name: str) -> Tuple[int, int]:
        """
        Build production chains for an entire batch

        Args:
            batch_name: Name of batch to build

        Returns:
            Tuple of (successful_count, failed_count)
        """
        items = self.get_items_for_batch(batch_name)

        if not items:
            print(f"No items found for batch '{batch_name}'")
            return 0, 0

        print(f"\nBuilding batch '{batch_name}': {BATCH_CONFIGS[batch_name]['description']}")
        print(f"Processing {len(items)} items...\n")

        success_count = 0
        fail_count = 0

        for i, item_type_id in enumerate(items, 1):
            if i % 100 == 0:
                print(f"Progress: {i}/{len(items)} items processed")

            if self.build_item(item_type_id):
                success_count += 1
            else:
                fail_count += 1

        print(f"\nBatch '{batch_name}' completed:")
        print(f"  Success: {success_count}")
        print(f"  Failed: {fail_count}")

        return success_count, fail_count


def main():
    parser = argparse.ArgumentParser(description='Build production chains from EVE SDE')
    parser.add_argument('--batch', help='Batch name to process')
    parser.add_argument('--item', type=int, help='Single item type ID to process')
    parser.add_argument('--list-batches', action='store_true', help='List available batches')

    args = parser.parse_args()

    if args.list_batches:
        print("\nAvailable batches:")
        for batch_name, config in BATCH_CONFIGS.items():
            print(f"  {batch_name:20s} - {config['description']}")
        return

    builder = ProductionChainBuilder()

    if args.item:
        print(f"Building chain for single item: {args.item}")
        success = builder.build_item(args.item)
        sys.exit(0 if success else 1)

    elif args.batch:
        if args.batch not in BATCH_CONFIGS:
            print(f"Error: Unknown batch '{args.batch}'")
            print("Use --list-batches to see available batches")
            sys.exit(1)

        success_count, fail_count = builder.build_batch(args.batch)
        sys.exit(0 if fail_count == 0 else 1)

    else:
        print("Error: Specify --batch, --item, or --list-batches")
        parser.print_help()
        sys.exit(1)


if __name__ == '__main__':
    main()
