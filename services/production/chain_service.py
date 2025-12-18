"""
Production Chain Service

Business logic for production chains, material calculations, and ME adjustments.
"""

from typing import Dict, List, Any, Optional
from services.production.chain_repository import ProductionChainRepository
from database import get_db_connection


class ProductionChainService:
    """Service for production chain operations"""

    def __init__(self):
        self.repo = ProductionChainRepository()

    def get_chain_tree(self, type_id: int, format: str = 'tree') -> Dict[str, Any]:
        """
        Get complete production chain as tree or flat list

        Args:
            type_id: Item type ID
            format: 'tree' for hierarchical, 'flat' for simple list

        Returns:
            Dict with chain data in requested format
        """
        # Get item info
        item_info = self._get_item_info(type_id)
        if not item_info:
            return {'error': 'Item not found', 'type_id': type_id}

        # Get dependencies
        dependencies = self.repo.get_direct_dependencies(type_id)

        if format == 'tree':
            tree = self._build_tree(type_id, dependencies)
            return {
                'item_type_id': type_id,
                'item_name': item_info['name'],
                'tree': tree,
                'has_dependencies': len(dependencies) > 0
            }
        else:
            # Flat format
            full_chain = self.repo.get_full_chain(type_id)
            return {
                'item_type_id': type_id,
                'item_name': item_info['name'],
                'materials': full_chain,
                'total_materials': len(full_chain)
            }

    def get_materials_list(
        self,
        type_id: int,
        me: int = 0,
        runs: int = 1
    ) -> Dict[str, Any]:
        """
        Get flattened material list with ME adjustments

        Args:
            type_id: Item type ID
            me: Material Efficiency (0-10)
            runs: Number of production runs

        Returns:
            Dict with adjusted material quantities
        """
        item_info = self._get_item_info(type_id)
        if not item_info:
            return {'error': 'Item not found', 'type_id': type_id}

        # Get raw materials
        materials = self.repo.get_full_chain(type_id)

        # Apply ME and runs
        adjusted_materials = []
        for material in materials:
            base_qty = material['base_quantity'] * runs
            adjusted_qty = self._apply_me(base_qty, me)

            adjusted_materials.append({
                'type_id': material['material_type_id'],
                'name': material['material_name'],
                'base_quantity': int(base_qty),
                'adjusted_quantity': int(adjusted_qty),
                'me_savings': int(base_qty - adjusted_qty)
            })

        return {
            'item_type_id': type_id,
            'item_name': item_info['name'],
            'runs': runs,
            'me_level': me,
            'materials': adjusted_materials,
            'total_materials': len(adjusted_materials)
        }

    def get_direct_dependencies(self, type_id: int) -> Dict[str, Any]:
        """
        Get only direct material dependencies (1 level)

        Args:
            type_id: Item type ID

        Returns:
            Dict with direct dependencies
        """
        item_info = self._get_item_info(type_id)
        if not item_info:
            return {'error': 'Item not found', 'type_id': type_id}

        dependencies = self.repo.get_direct_dependencies(type_id)

        return {
            'item_type_id': type_id,
            'item_name': item_info['name'],
            'direct_materials': [
                {
                    'type_id': dep['material_type_id'],
                    'name': dep['material_name'],
                    'quantity': dep['base_quantity'],
                    'is_raw_material': dep['is_raw_material']
                }
                for dep in dependencies
            ],
            'total_direct_materials': len(dependencies)
        }

    def _apply_me(self, base_quantity: float, me_level: int) -> float:
        """
        Apply Material Efficiency reduction

        Args:
            base_quantity: Base material quantity
            me_level: ME level (0-10)

        Returns:
            Adjusted quantity with ME applied
        """
        if me_level <= 0:
            return base_quantity

        # ME formula: quantity * (1 - (ME / 100))
        reduction_factor = 1 - (me_level / 100)
        return base_quantity * reduction_factor

    def _build_tree(
        self,
        type_id: int,
        dependencies: List[Dict[str, Any]],
        depth: int = 0,
        max_depth: int = 10
    ) -> Dict[str, Any]:
        """
        Build hierarchical dependency tree

        Args:
            type_id: Current item type ID
            dependencies: Direct dependencies
            depth: Current recursion depth
            max_depth: Maximum recursion depth

        Returns:
            Tree structure
        """
        if depth >= max_depth or not dependencies:
            return {}

        tree = {}
        for dep in dependencies:
            material_id = dep['material_type_id']

            # Get sub-dependencies if not raw material
            if not dep['is_raw_material']:
                sub_deps = self.repo.get_direct_dependencies(material_id)
                children = self._build_tree(material_id, sub_deps, depth + 1, max_depth)
            else:
                children = None

            tree[material_id] = {
                'name': dep['material_name'],
                'quantity': dep['base_quantity'],
                'is_raw': dep['is_raw_material'],
                'children': children if children else []
            }

        return tree

    def _get_item_info(self, type_id: int) -> Optional[Dict[str, Any]]:
        """Get item name and basic info"""
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        SELECT "typeID", "typeName", "groupID"
                        FROM "invTypes"
                        WHERE "typeID" = %s
                    """, (type_id,))

                    row = cursor.fetchone()
                    if not row:
                        return None

                    return {
                        'type_id': row[0],
                        'name': row[1],
                        'group_id': row[2]
                    }
        except Exception as e:
            print(f"Error getting item info: {e}")
            return None
