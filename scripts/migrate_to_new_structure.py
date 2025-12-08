#!/usr/bin/env python3
"""
Migration script to move files to new structure.
Run this after all new services are implemented and tested.
"""

import os
import shutil
from pathlib import Path


MIGRATIONS = {
    # Move service files
    "shopping_service.py": "src/services/shopping/legacy_service.py",
    "market_service.py": "src/services/market/legacy_service.py",
    "production_simulator.py": "src/services/market/production.py",
    "killmail_service.py": "src/services/war/killmail_service.py",
    "war_analyzer.py": "src/services/war/analyzer.py",
    "route_service.py": "src/services/navigation/route_service.py",
    "cargo_service.py": "src/services/navigation/cargo_service.py",
    "material_classifier.py": "src/services/market/material_classifier.py",
    "bookmark_service.py": "src/services/character/bookmark_service.py",
    "character.py": "src/services/character/character_service.py",
    "auth.py": "src/services/auth/auth_service.py",

    # Move integrations
    "esi_client.py": "src/integrations/esi/client.py",
    "notification_service.py": "src/integrations/discord/notification_service.py",

    # Move core files
    "database.py": "src/core/legacy_database.py",
    "schemas.py": "src/models/legacy_schemas.py",

    # Move data files
    "tokens.json": "data/tokens.json",
    "auth_state.json": "data/auth_state.json",
    "scan_results.json": "data/scan_results.json",
}


def migrate_files():
    """Move files to new structure."""
    base_path = Path(__file__).parent.parent

    for old_path, new_path in MIGRATIONS.items():
        old_file = base_path / old_path
        new_file = base_path / new_path

        if not old_file.exists():
            print(f"⚠️  Skip: {old_path} (not found)")
            continue

        # Create parent directory
        new_file.parent.mkdir(parents=True, exist_ok=True)

        # Move file
        shutil.move(str(old_file), str(new_file))
        print(f"✅ Moved: {old_path} → {new_path}")


def create_compatibility_imports():
    """Create import compatibility shims for gradual migration."""
    base_path = Path(__file__).parent.parent

    shims = {
        "shopping_service.py": "from src.services.shopping.legacy_service import *",
        "market_service.py": "from src.services.market.legacy_service import *",
        "database.py": "from src.core.legacy_database import *",
    }

    for filename, import_statement in shims.items():
        shim_file = base_path / filename
        with open(shim_file, "w") as f:
            f.write(f'"""\nCompatibility shim - imports from new location.\n"""\n\n{import_statement}\n')
        print(f"📝 Created shim: {filename}")


if __name__ == "__main__":
    print("🚀 Starting migration to new structure...\n")
    migrate_files()
    print("\n📦 Creating compatibility shims...\n")
    create_compatibility_imports()
    print("\n✅ Migration complete!")
    print("\n⚠️  Remember to:")
    print("  1. Update imports in routers/")
    print("  2. Update imports in jobs/")
    print("  3. Run tests: pytest tests/")
    print("  4. Remove shims after full migration")
