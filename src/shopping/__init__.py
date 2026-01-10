"""
Shopping Service Package.

This package provides shopping list management for EVE Co-Pilot.
It splits the monolithic shopping_service.py into focused modules.

Modules:
- lists: Shopping list CRUD operations
- items: Shopping list item operations
- volumes: Volume and cargo calculations
- bulk: Bulk operations (add from production, export, grouping)
- materials: Material calculation and application
- wizard: Step-based wizard workflow

Usage:
    from src.shopping import ShoppingService, shopping_service

    # Use the singleton instance
    lists = shopping_service.get_lists()

    # Or create your own instance
    service = ShoppingService()
    new_list = service.create_list("My List")
"""

from .lists import ShoppingListMixin
from .items import ShoppingItemMixin
from .volumes import ShoppingVolumeMixin
from .bulk import ShoppingBulkMixin
from .materials import ShoppingMaterialsMixin
from .wizard import ShoppingWizardMixin


class ShoppingService(
    ShoppingListMixin,
    ShoppingItemMixin,
    ShoppingVolumeMixin,
    ShoppingBulkMixin,
    ShoppingMaterialsMixin,
    ShoppingWizardMixin
):
    """
    Shopping list service combining all shopping operations.

    This class composes all mixin classes to provide a unified interface
    for shopping list management while maintaining backwards compatibility.

    Features:
    - List CRUD operations (create, get, update, delete)
    - Item management (add, update, remove, mark purchased)
    - Volume and cargo calculations
    - Bulk operations (add from production, export, grouping)
    - Material calculation with Production Chains API
    - Step-based wizard workflow for complex builds
    """
    pass


# Singleton instance for backwards compatibility
shopping_service = ShoppingService()


__all__ = [
    'ShoppingService',
    'shopping_service',
    'ShoppingListMixin',
    'ShoppingItemMixin',
    'ShoppingVolumeMixin',
    'ShoppingBulkMixin',
    'ShoppingMaterialsMixin',
    'ShoppingWizardMixin',
]
