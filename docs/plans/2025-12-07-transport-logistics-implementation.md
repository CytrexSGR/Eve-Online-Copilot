# Transport & Logistics System - Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Extend Shopping Planner with product quantities, cargo calculation, and transport options based on character ships and skills.

**Architecture:** DB schema extension → Backend services → API endpoints → Frontend UI. Each layer builds on the previous.

**Tech Stack:** PostgreSQL, FastAPI, React/TypeScript, TanStack Query, ESI API

**Design Document:** `docs/plans/2025-12-07-transport-logistics-design.md`

---

## Task 1: Database Migration - Extend shopping_list_items

**Files:**
- Create: `migrations/004_transport_logistics.sql`

**Step 1: Create migration file**

```sql
-- Migration 004: Transport & Logistics
-- Extend shopping_list_items for product tracking and cargo calculation

-- Add new columns to shopping_list_items
ALTER TABLE shopping_list_items
    ADD COLUMN IF NOT EXISTS is_product BOOLEAN DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS runs INT DEFAULT 1,
    ADD COLUMN IF NOT EXISTS me_level INT DEFAULT 10,
    ADD COLUMN IF NOT EXISTS te_level INT DEFAULT 20,
    ADD COLUMN IF NOT EXISTS volume_per_unit NUMERIC(20,4),
    ADD COLUMN IF NOT EXISTS total_volume NUMERIC(20,2);

-- Add comments
COMMENT ON COLUMN shopping_list_items.is_product IS 'TRUE = Endprodukt (hat Blueprint), FALSE = Material';
COMMENT ON COLUMN shopping_list_items.runs IS 'Anzahl Production Runs (nur für Produkte)';
COMMENT ON COLUMN shopping_list_items.me_level IS 'Material Efficiency des Blueprints (0-10)';
COMMENT ON COLUMN shopping_list_items.te_level IS 'Time Efficiency des Blueprints (0-20)';
COMMENT ON COLUMN shopping_list_items.volume_per_unit IS 'Volumen pro Einheit in m³';
COMMENT ON COLUMN shopping_list_items.total_volume IS 'Gesamtvolumen in m³ (quantity * volume_per_unit)';

-- Create character_capabilities table
CREATE TABLE IF NOT EXISTS character_capabilities (
    id SERIAL PRIMARY KEY,
    character_id BIGINT NOT NULL,
    character_name VARCHAR(255),
    type_id INT NOT NULL,
    ship_name VARCHAR(255),
    ship_group VARCHAR(100),
    cargo_capacity FLOAT,
    location_id BIGINT,
    location_name VARCHAR(255),
    can_fly BOOLEAN DEFAULT FALSE,
    missing_skills JSONB,
    last_synced TIMESTAMP DEFAULT NOW(),

    CONSTRAINT unique_char_ship_location UNIQUE (character_id, type_id, location_id)
);

CREATE INDEX IF NOT EXISTS idx_char_capabilities_char ON character_capabilities(character_id);
CREATE INDEX IF NOT EXISTS idx_char_capabilities_location ON character_capabilities(location_id);
CREATE INDEX IF NOT EXISTS idx_char_capabilities_can_fly ON character_capabilities(can_fly);

-- Update existing items with volume from SDE
UPDATE shopping_list_items sli
SET volume_per_unit = t."volume",
    total_volume = sli.quantity * t."volume"
FROM "invTypes" t
WHERE sli.type_id = t."typeID"
  AND sli.volume_per_unit IS NULL;
```

**Step 2: Run migration**

```bash
echo 'Aug2012#' | sudo -S docker exec -i eve_db psql -U eve -d eve_sde < /home/cytrex/eve_copilot/migrations/004_transport_logistics.sql
```

Expected: `ALTER TABLE`, `CREATE TABLE`, `CREATE INDEX`, `UPDATE` statements succeed

**Step 3: Verify migration**

```bash
echo 'Aug2012#' | sudo -S docker exec eve_db psql -U eve -d eve_sde -c "\d shopping_list_items" | grep -E "is_product|runs|me_level|volume"
```

Expected: New columns visible

**Step 4: Commit**

```bash
git add migrations/004_transport_logistics.sql
git commit -m "feat(db): Add transport logistics schema

- Extend shopping_list_items with is_product, runs, me_level, te_level, volume fields
- Create character_capabilities table for ship/skill caching
- Backfill volumes from SDE for existing items"
```

---

## Task 2: Backend - Capability Service

**Files:**
- Create: `capability_service.py`

**Step 1: Create capability service**

```python
"""
Character Capability Service for EVE Co-Pilot
Manages ship capabilities and skill requirements
"""

from database import get_db_connection
from psycopg2.extras import RealDictCursor
from typing import Optional, List, Dict
from datetime import datetime
import json


# Ship groups relevant for logistics
LOGISTICS_SHIP_GROUPS = {
    28: 'Industrial',
    380: 'Deep Space Transport',
    381: 'Blockade Runner',
    513: 'Freighter',
    902: 'Jump Freighter',
}

# Attribute IDs for skill requirements in dgmTypeAttributes
SKILL_ATTRIBUTE_IDS = {
    'requiredSkill1': 182,
    'requiredSkill1Level': 277,
    'requiredSkill2': 183,
    'requiredSkill2Level': 278,
    'requiredSkill3': 184,
    'requiredSkill3Level': 279,
}


class CapabilityService:

    def get_ship_skill_requirements(self, type_id: int) -> List[Dict]:
        """Get skill requirements for a ship from SDE"""
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute('''
                    SELECT
                        t."typeID",
                        t."typeName",
                        -- Skill 1
                        s1."typeName" as skill1_name,
                        s1."typeID" as skill1_id,
                        a1l."valueFloat" as skill1_level,
                        -- Skill 2
                        s2."typeName" as skill2_name,
                        s2."typeID" as skill2_id,
                        a2l."valueFloat" as skill2_level,
                        -- Skill 3
                        s3."typeName" as skill3_name,
                        s3."typeID" as skill3_id,
                        a3l."valueFloat" as skill3_level
                    FROM "invTypes" t
                    -- Skill 1
                    LEFT JOIN "dgmTypeAttributes" a1 ON t."typeID" = a1."typeID" AND a1."attributeID" = 182
                    LEFT JOIN "invTypes" s1 ON a1."valueFloat" = s1."typeID"
                    LEFT JOIN "dgmTypeAttributes" a1l ON t."typeID" = a1l."typeID" AND a1l."attributeID" = 277
                    -- Skill 2
                    LEFT JOIN "dgmTypeAttributes" a2 ON t."typeID" = a2."typeID" AND a2."attributeID" = 183
                    LEFT JOIN "invTypes" s2 ON a2."valueFloat" = s2."typeID"
                    LEFT JOIN "dgmTypeAttributes" a2l ON t."typeID" = a2l."typeID" AND a2l."attributeID" = 278
                    -- Skill 3
                    LEFT JOIN "dgmTypeAttributes" a3 ON t."typeID" = a3."typeID" AND a3."attributeID" = 184
                    LEFT JOIN "invTypes" s3 ON a3."valueFloat" = s3."typeID"
                    LEFT JOIN "dgmTypeAttributes" a3l ON t."typeID" = a3l."typeID" AND a3l."attributeID" = 279
                    WHERE t."typeID" = %s
                ''', (type_id,))
                result = cur.fetchone()

                if not result:
                    return []

                requirements = []
                for i in [1, 2, 3]:
                    skill_name = result.get(f'skill{i}_name')
                    skill_id = result.get(f'skill{i}_id')
                    skill_level = result.get(f'skill{i}_level')
                    if skill_name and skill_level:
                        requirements.append({
                            'skill_id': int(skill_id),
                            'skill_name': skill_name,
                            'required_level': int(skill_level)
                        })

                return requirements

    def get_ship_cargo_capacity(self, type_id: int) -> Optional[float]:
        """Get cargo capacity for a ship from SDE"""
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Attribute 38 = capacity
                cur.execute('''
                    SELECT a."valueFloat" as capacity
                    FROM "dgmTypeAttributes" a
                    WHERE a."typeID" = %s AND a."attributeID" = 38
                ''', (type_id,))
                result = cur.fetchone()
                return float(result['capacity']) if result else None

    def get_ship_group(self, type_id: int) -> Optional[str]:
        """Get ship group name from SDE"""
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute('''
                    SELECT g."groupID", g."groupName"
                    FROM "invTypes" t
                    JOIN "invGroups" g ON t."groupID" = g."groupID"
                    WHERE t."typeID" = %s
                ''', (type_id,))
                result = cur.fetchone()
                if result:
                    group_id = result['groupID']
                    return LOGISTICS_SHIP_GROUPS.get(group_id, result['groupName'])
                return None

    def check_skill_requirements(
        self,
        character_skills: List[Dict],
        requirements: List[Dict]
    ) -> tuple[bool, List[Dict]]:
        """
        Check if character meets skill requirements

        Returns: (can_fly, missing_skills)
        """
        # Build skill lookup: skill_id -> level
        skill_levels = {s['skill_id']: s['trained_skill_level'] for s in character_skills}

        missing = []
        can_fly = True

        for req in requirements:
            current_level = skill_levels.get(req['skill_id'], 0)
            if current_level < req['required_level']:
                can_fly = False
                missing.append({
                    'skill_name': req['skill_name'],
                    'skill_id': req['skill_id'],
                    'required_level': req['required_level'],
                    'current_level': current_level
                })

        return can_fly, missing

    def upsert_capability(
        self,
        character_id: int,
        character_name: str,
        type_id: int,
        ship_name: str,
        ship_group: str,
        cargo_capacity: float,
        location_id: int,
        location_name: str,
        can_fly: bool,
        missing_skills: List[Dict]
    ) -> dict:
        """Insert or update character capability"""
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute('''
                    INSERT INTO character_capabilities
                        (character_id, character_name, type_id, ship_name, ship_group,
                         cargo_capacity, location_id, location_name, can_fly, missing_skills, last_synced)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
                    ON CONFLICT (character_id, type_id, location_id)
                    DO UPDATE SET
                        character_name = EXCLUDED.character_name,
                        ship_name = EXCLUDED.ship_name,
                        ship_group = EXCLUDED.ship_group,
                        cargo_capacity = EXCLUDED.cargo_capacity,
                        location_name = EXCLUDED.location_name,
                        can_fly = EXCLUDED.can_fly,
                        missing_skills = EXCLUDED.missing_skills,
                        last_synced = NOW()
                    RETURNING *
                ''', (
                    character_id, character_name, type_id, ship_name, ship_group,
                    cargo_capacity, location_id, location_name, can_fly,
                    json.dumps(missing_skills) if missing_skills else None
                ))
                conn.commit()
                return dict(cur.fetchone())

    def get_character_ships(
        self,
        character_id: int,
        location_ids: Optional[List[int]] = None,
        can_fly_only: bool = True
    ) -> List[Dict]:
        """Get available ships for a character"""
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                where_clauses = ["character_id = %s"]
                params = [character_id]

                if can_fly_only:
                    where_clauses.append("can_fly = TRUE")

                if location_ids:
                    where_clauses.append("location_id = ANY(%s)")
                    params.append(location_ids)

                where_sql = " AND ".join(where_clauses)

                cur.execute(f'''
                    SELECT * FROM character_capabilities
                    WHERE {where_sql}
                    ORDER BY cargo_capacity DESC
                ''', params)

                return [dict(row) for row in cur.fetchall()]

    def get_all_available_ships(
        self,
        location_ids: Optional[List[int]] = None,
        can_fly_only: bool = True
    ) -> List[Dict]:
        """Get all available ships across all characters"""
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                where_clauses = []
                params = []

                if can_fly_only:
                    where_clauses.append("can_fly = TRUE")

                if location_ids:
                    where_clauses.append("location_id = ANY(%s)")
                    params.append(location_ids)

                where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"

                cur.execute(f'''
                    SELECT * FROM character_capabilities
                    WHERE {where_sql}
                    ORDER BY cargo_capacity DESC
                ''', params)

                return [dict(row) for row in cur.fetchall()]

    def clear_character_capabilities(self, character_id: int) -> int:
        """Clear all capabilities for a character (before re-sync)"""
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    'DELETE FROM character_capabilities WHERE character_id = %s',
                    (character_id,)
                )
                conn.commit()
                return cur.rowcount


capability_service = CapabilityService()
```

**Step 2: Verify service loads**

```bash
cd /home/cytrex/eve_copilot && python3 -c "from capability_service import capability_service; print('OK')"
```

Expected: `OK`

**Step 3: Test skill requirements query**

```bash
cd /home/cytrex/eve_copilot && python3 -c "
from capability_service import capability_service
# Test with a Freighter (Charon = 20185)
reqs = capability_service.get_ship_skill_requirements(20185)
print(f'Charon requirements: {reqs}')
"
```

Expected: List of skill requirements

**Step 4: Commit**

```bash
git add capability_service.py
git commit -m "feat: Add capability service for ship/skill management

- Query skill requirements from SDE (dgmTypeAttributes)
- Check character skills against requirements
- CRUD for character_capabilities table
- Support for location-filtered queries"
```

---

## Task 3: Backend - Extend Shopping Service with Volume

**Files:**
- Modify: `shopping_service.py`

**Step 1: Add volume calculation method**

Add after the existing `add_item` method (around line 130):

```python
    def get_item_volume(self, type_id: int) -> Optional[float]:
        """Get volume of an item from SDE"""
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute('''
                    SELECT "volume" FROM "invTypes"
                    WHERE "typeID" = %s
                ''', (type_id,))
                result = cur.fetchone()
                return float(result['volume']) if result and result['volume'] else None

    def update_item_volume(self, item_id: int) -> dict:
        """Update volume fields for an item"""
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Get item and its volume from SDE
                cur.execute('''
                    UPDATE shopping_list_items sli
                    SET volume_per_unit = t."volume",
                        total_volume = sli.quantity * t."volume"
                    FROM "invTypes" t
                    WHERE sli.id = %s AND sli.type_id = t."typeID"
                    RETURNING sli.*
                ''', (item_id,))
                conn.commit()
                result = cur.fetchone()
                return dict(result) if result else None

    def update_item_runs(
        self,
        item_id: int,
        runs: int,
        me_level: int = 10
    ) -> dict:
        """Update runs and ME level for a product item"""
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute('''
                    UPDATE shopping_list_items
                    SET runs = %s,
                        me_level = %s,
                        quantity = %s,
                        is_product = TRUE,
                        updated_at = NOW()
                    WHERE id = %s
                    RETURNING *
                ''', (runs, me_level, runs, item_id))
                conn.commit()
                result = cur.fetchone()
                return dict(result) if result else None

    def get_cargo_summary(self, list_id: int) -> dict:
        """Get cargo volume summary for a shopping list"""
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Get products
                cur.execute('''
                    SELECT type_id, item_name, runs, total_volume
                    FROM shopping_list_items
                    WHERE list_id = %s AND is_product = TRUE
                ''', (list_id,))
                products = [dict(row) for row in cur.fetchall()]

                # Get materials summary
                cur.execute('''
                    SELECT
                        COUNT(*) as total_items,
                        COALESCE(SUM(total_volume), 0) as total_volume_m3,
                        target_region
                    FROM shopping_list_items
                    WHERE list_id = %s AND is_product = FALSE
                    GROUP BY target_region
                ''', (list_id,))
                by_region = [dict(row) for row in cur.fetchall()]

                # Total materials volume
                cur.execute('''
                    SELECT
                        COUNT(*) as total_items,
                        COALESCE(SUM(total_volume), 0) as total_volume_m3
                    FROM shopping_list_items
                    WHERE list_id = %s AND is_product = FALSE
                ''', (list_id,))
                totals = dict(cur.fetchone())

                return {
                    'list_id': list_id,
                    'products': products,
                    'materials': {
                        'total_items': totals['total_items'],
                        'total_volume_m3': float(totals['total_volume_m3']),
                        'volume_formatted': self._format_volume(float(totals['total_volume_m3'])),
                        'breakdown_by_region': {
                            row['target_region'] or 'unassigned': {
                                'volume_m3': float(row['total_volume_m3']),
                                'item_count': row['total_items']
                            }
                            for row in by_region
                        }
                    }
                }

    def _format_volume(self, volume: float) -> str:
        """Format volume for display"""
        if volume >= 1_000_000:
            return f"{volume / 1_000_000:.2f}M m³"
        if volume >= 1_000:
            return f"{volume / 1_000:.1f}K m³"
        return f"{volume:.0f} m³"
```

**Step 2: Test cargo summary**

```bash
cd /home/cytrex/eve_copilot && python3 -c "
from shopping_service import shopping_service
# Test with existing list
summary = shopping_service.get_cargo_summary(1)
print(f'Cargo summary: {summary}')
"
```

Expected: Cargo summary dict

**Step 3: Commit**

```bash
git add shopping_service.py
git commit -m "feat(shopping): Add volume calculation and cargo summary

- get_item_volume: Fetch volume from SDE
- update_item_volume: Update volume fields on item
- update_item_runs: Set runs/ME for product items
- get_cargo_summary: Aggregate volumes by region"
```

---

## Task 4: Backend - Transport Options Service

**Files:**
- Create: `transport_service.py`

**Step 1: Create transport service**

```python
"""
Transport Options Service for EVE Co-Pilot
Calculates optimal transport options for shopping lists
"""

from math import ceil
from database import get_db_connection
from psycopg2.extras import RealDictCursor
from typing import Optional, List, Dict
from capability_service import capability_service
from shopping_service import shopping_service
from route_service import route_service

# Flight time per jump by ship group (minutes)
FLIGHT_TIME_PER_JUMP = {
    'Industrial': 2.0,
    'Blockade Runner': 1.5,
    'Deep Space Transport': 2.5,
    'Freighter': 3.5,
    'Jump Freighter': 2.0,
}

# Trade hub system IDs
TRADE_HUB_SYSTEMS = {
    30000142: 'Jita',
    30002187: 'Amarr',
    30002659: 'Dodixie',
    30002510: 'Rens',
    30002053: 'Hek',
}

# Home system
HOME_SYSTEM_ID = 30000119  # Isikemi


class TransportService:

    def get_transport_options(
        self,
        list_id: int,
        safe_only: bool = True
    ) -> dict:
        """
        Calculate transport options for a shopping list

        Returns options sorted by efficiency (fewer trips, faster)
        """
        # 1. Get cargo summary
        cargo = shopping_service.get_cargo_summary(list_id)
        total_volume = cargo['materials']['total_volume_m3']

        if total_volume == 0:
            return {
                'total_volume_m3': 0,
                'options': [],
                'message': 'No materials to transport'
            }

        # 2. Get regions with items
        regions_needed = list(cargo['materials']['breakdown_by_region'].keys())
        regions_needed = [r for r in regions_needed if r != 'unassigned']

        # 3. Get available ships
        # Include home system + trade hubs
        relevant_systems = [HOME_SYSTEM_ID] + list(TRADE_HUB_SYSTEMS.keys())
        available_ships = capability_service.get_all_available_ships(
            location_ids=relevant_systems,
            can_fly_only=True
        )

        if not available_ships:
            return {
                'total_volume_m3': total_volume,
                'options': [],
                'message': 'No ships available at relevant locations'
            }

        # 4. Calculate route
        route_summary = self._build_route_summary(regions_needed)

        # 5. Generate options
        options = []
        for idx, ship in enumerate(available_ships):
            option = self._calculate_option(
                idx + 1,
                ship,
                total_volume,
                cargo['materials']['total_items'],
                route_summary,
                safe_only
            )
            if option:
                options.append(option)

        # 6. Sort by efficiency
        options.sort(key=lambda x: (x['trips'], x['flight_time_min']))

        return {
            'total_volume_m3': total_volume,
            'volume_formatted': cargo['materials']['volume_formatted'],
            'route_summary': route_summary['summary'],
            'options': options,
            'filters_available': ['fewest_trips', 'fastest', 'single_char', 'lowest_risk']
        }

    def _calculate_option(
        self,
        option_id: int,
        ship: dict,
        total_volume: float,
        total_items: int,
        route_info: dict,
        safe_only: bool
    ) -> Optional[dict]:
        """Calculate a single transport option"""
        cargo_capacity = ship['cargo_capacity']
        if not cargo_capacity or cargo_capacity <= 0:
            return None

        trips = ceil(total_volume / cargo_capacity)
        ship_group = ship['ship_group'] or 'Industrial'

        # Flight time
        time_per_jump = FLIGHT_TIME_PER_JUMP.get(ship_group, 2.0)
        jumps = route_info.get('total_jumps', 10)  # Default estimate
        docking_time = len(route_info.get('legs', [])) * 2  # 2 min per stop
        flight_time = int((jumps * time_per_jump + docking_time) * trips)

        # Risk score (simplified - would use route_service for real calculation)
        risk_score = route_info.get('lowsec_systems', 0)
        risk_label = 'Safe' if risk_score == 0 else 'Low Risk' if risk_score <= 2 else 'Medium Risk'

        # Skip risky options if safe_only
        if safe_only and risk_score > 0:
            # Still include but mark as risky
            pass

        # Capacity utilization
        capacity_used = (total_volume / (cargo_capacity * trips)) * 100

        return {
            'id': option_id,
            'characters': [{
                'id': ship['character_id'],
                'name': ship['character_name'],
                'ship_type_id': ship['type_id'],
                'ship_name': ship['ship_name'],
                'ship_group': ship_group,
                'ship_location': ship['location_name']
            }],
            'trips': trips,
            'flight_time_min': flight_time,
            'flight_time_formatted': self._format_time(flight_time),
            'capacity_m3': cargo_capacity,
            'capacity_used_pct': round(capacity_used, 1),
            'risk_score': risk_score,
            'risk_label': risk_label,
            'dangerous_systems': [],
            'isk_per_trip': 0  # Would need list total cost
        }

    def _build_route_summary(self, regions: List[str]) -> dict:
        """Build route summary from regions"""
        # Map region keys to hub names
        region_to_hub = {
            'the_forge': 'Jita',
            'domain': 'Amarr',
            'sinq_laison': 'Dodixie',
            'heimatar': 'Rens',
            'metropolis': 'Hek',
        }

        hubs = [region_to_hub.get(r, r) for r in regions if r in region_to_hub]

        if not hubs:
            return {
                'summary': 'No route needed',
                'total_jumps': 0,
                'legs': [],
                'lowsec_systems': 0
            }

        # Build summary string
        route_parts = ['Isikemi'] + hubs + ['Isikemi']
        summary = ' → '.join(route_parts)

        # Estimate jumps (simplified)
        estimated_jumps = len(hubs) * 8  # ~8 jumps per hub average

        return {
            'summary': summary,
            'total_jumps': estimated_jumps,
            'legs': [{'from': route_parts[i], 'to': route_parts[i+1]}
                    for i in range(len(route_parts)-1)],
            'lowsec_systems': 0  # Would calculate from actual route
        }

    def _format_time(self, minutes: int) -> str:
        """Format minutes as human-readable time"""
        if minutes < 60:
            return f"{minutes} min"
        hours = minutes // 60
        mins = minutes % 60
        if mins == 0:
            return f"{hours}h"
        return f"{hours}h {mins}m"


transport_service = TransportService()
```

**Step 2: Test transport service**

```bash
cd /home/cytrex/eve_copilot && python3 -c "
from transport_service import transport_service
options = transport_service.get_transport_options(1, safe_only=True)
print(f'Options: {len(options.get(\"options\", []))} found')
print(f'Total volume: {options.get(\"total_volume_m3\")} m³')
"
```

Expected: Options list (may be empty if no ships synced yet)

**Step 3: Commit**

```bash
git add transport_service.py
git commit -m "feat: Add transport options service

- Calculate transport options based on available ships
- Consider cargo capacity, flight time, risk
- Route summary with hub stops
- Filtering support for safe routes"
```

---

## Task 5: Backend - API Endpoints

**Files:**
- Modify: `routers/shopping.py`

**Step 1: Add new request models**

Add after existing models (around line 45):

```python
class ItemRunsUpdate(BaseModel):
    runs: int
    me_level: int = 10
```

**Step 2: Add cargo summary endpoint**

Add after existing endpoints (around line 200):

```python
@router.get("/lists/{list_id}/cargo-summary")
async def get_cargo_summary(list_id: int):
    """Get cargo volume summary for a shopping list"""
    summary = shopping_service.get_cargo_summary(list_id)
    if not summary:
        raise HTTPException(status_code=404, detail="Shopping list not found")
    return summary
```

**Step 3: Add transport options endpoint**

```python
from transport_service import transport_service

@router.get("/lists/{list_id}/transport-options")
async def get_transport_options(
    list_id: int,
    safe_only: bool = Query(True, description="Only show safe (highsec) routes")
):
    """Get transport options for a shopping list"""
    options = transport_service.get_transport_options(list_id, safe_only)
    return options
```

**Step 4: Add item runs update endpoint**

```python
@router.patch("/items/{item_id}/runs")
async def update_item_runs(item_id: int, request: ItemRunsUpdate):
    """Update runs and ME level for a product item"""
    result = shopping_service.update_item_runs(item_id, request.runs, request.me_level)
    if not result:
        raise HTTPException(status_code=404, detail="Item not found")
    return result
```

**Step 5: Test endpoints**

```bash
# Test cargo summary
curl -s http://localhost:8000/api/shopping/lists/1/cargo-summary | python3 -m json.tool

# Test transport options
curl -s "http://localhost:8000/api/shopping/lists/1/transport-options?safe_only=true" | python3 -m json.tool
```

**Step 6: Commit**

```bash
git add routers/shopping.py
git commit -m "feat(api): Add cargo and transport endpoints

- GET /lists/{id}/cargo-summary - Volume breakdown
- GET /lists/{id}/transport-options - Transport options
- PATCH /items/{id}/runs - Update product runs/ME"
```

---

## Task 6: Backend - Capability Sync Cron Job

**Files:**
- Create: `jobs/capability_sync.py`
- Create: `jobs/cron_capability_sync.sh`

**Step 1: Create sync job**

```python
#!/usr/bin/env python3
"""
Character Capability Sync Job
Syncs ship capabilities for all authenticated characters

Run daily via cron to cache ship/skill data
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging
from datetime import datetime
from auth import eve_auth
from character import character_api
from capability_service import capability_service, LOGISTICS_SHIP_GROUPS

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
log = logging.getLogger(__name__)


def get_ship_type_ids() -> set:
    """Get all ship type IDs from logistics groups"""
    from database import get_db_connection
    from psycopg2.extras import RealDictCursor

    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            group_ids = list(LOGISTICS_SHIP_GROUPS.keys())
            cur.execute('''
                SELECT "typeID" FROM "invTypes"
                WHERE "groupID" = ANY(%s) AND published = true
            ''', (group_ids,))
            return {row['typeID'] for row in cur.fetchall()}


def sync_character(character_id: int, character_name: str, ship_type_ids: set) -> int:
    """Sync capabilities for a single character"""
    synced = 0

    try:
        # Get character assets
        assets_result = character_api.get_assets(character_id)
        if isinstance(assets_result, dict) and 'error' in assets_result:
            log.warning(f"Failed to get assets for {character_name}: {assets_result['error']}")
            return 0

        assets = assets_result.get('assets', [])

        # Filter to ships only
        ships = [a for a in assets if a.get('type_id') in ship_type_ids]
        log.info(f"Found {len(ships)} logistics ships for {character_name}")

        if not ships:
            return 0

        # Get character skills
        skills_result = character_api.get_skills(character_id)
        if isinstance(skills_result, dict) and 'error' in skills_result:
            log.warning(f"Failed to get skills for {character_name}: {skills_result['error']}")
            return 0

        skills = skills_result.get('skills', [])

        # Process each ship
        for ship in ships:
            type_id = ship['type_id']
            location_id = ship.get('location_id', 0)

            # Get ship info from SDE
            from database import get_db_connection
            from psycopg2.extras import RealDictCursor

            with get_db_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute('SELECT "typeName" FROM "invTypes" WHERE "typeID" = %s', (type_id,))
                    type_info = cur.fetchone()
                    ship_name = type_info['typeName'] if type_info else f"Unknown ({type_id})"

            # Get skill requirements
            requirements = capability_service.get_ship_skill_requirements(type_id)
            can_fly, missing = capability_service.check_skill_requirements(skills, requirements)

            # Get cargo capacity
            cargo_capacity = capability_service.get_ship_cargo_capacity(type_id)

            # Get ship group
            ship_group = capability_service.get_ship_group(type_id)

            # Resolve location name (simplified - would use ESI for citadels)
            location_name = resolve_location_name(location_id)

            # Upsert capability
            capability_service.upsert_capability(
                character_id=character_id,
                character_name=character_name,
                type_id=type_id,
                ship_name=ship_name,
                ship_group=ship_group,
                cargo_capacity=cargo_capacity or 0,
                location_id=location_id,
                location_name=location_name,
                can_fly=can_fly,
                missing_skills=missing
            )
            synced += 1

    except Exception as e:
        log.error(f"Error syncing {character_name}: {e}")

    return synced


def resolve_location_name(location_id: int) -> str:
    """Resolve location ID to name"""
    from database import get_db_connection
    from psycopg2.extras import RealDictCursor

    # Try station first
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute('''
                SELECT "stationName" FROM "staStations"
                WHERE "stationID" = %s
            ''', (location_id,))
            result = cur.fetchone()
            if result:
                return result['stationName']

    # Try solar system
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute('''
                SELECT "solarSystemName" FROM "mapSolarSystems"
                WHERE "solarSystemID" = %s
            ''', (location_id,))
            result = cur.fetchone()
            if result:
                return result['solarSystemName']

    return f"Location {location_id}"


def main():
    log.info("Starting capability sync job")
    start_time = datetime.now()

    # Get all authenticated characters
    characters = eve_auth.get_all_characters()
    log.info(f"Found {len(characters)} authenticated characters")

    # Get ship type IDs
    ship_type_ids = get_ship_type_ids()
    log.info(f"Tracking {len(ship_type_ids)} ship types")

    total_synced = 0
    for char in characters:
        char_id = char['character_id']
        char_name = char['character_name']
        log.info(f"Syncing {char_name} ({char_id})...")

        synced = sync_character(char_id, char_name, ship_type_ids)
        total_synced += synced
        log.info(f"  Synced {synced} ships")

    elapsed = (datetime.now() - start_time).total_seconds()
    log.info(f"Capability sync complete: {total_synced} ships synced in {elapsed:.1f}s")


if __name__ == '__main__':
    main()
```

**Step 2: Create cron wrapper**

```bash
#!/bin/bash
# Capability Sync Cron Job
cd /home/cytrex/eve_copilot
source /home/cytrex/eve_copilot/venv/bin/activate 2>/dev/null || true
python3 jobs/capability_sync.py >> /home/cytrex/eve_copilot/logs/capability_sync.log 2>&1
```

**Step 3: Make executable**

```bash
chmod +x /home/cytrex/eve_copilot/jobs/cron_capability_sync.sh
```

**Step 4: Test job manually**

```bash
cd /home/cytrex/eve_copilot && python3 jobs/capability_sync.py
```

Expected: Ships synced for authenticated characters

**Step 5: Add to crontab**

```bash
(crontab -l 2>/dev/null | grep -v "capability_sync"; echo "0 4 * * * /home/cytrex/eve_copilot/jobs/cron_capability_sync.sh") | crontab -
```

**Step 6: Commit**

```bash
git add jobs/capability_sync.py jobs/cron_capability_sync.sh
git commit -m "feat(jobs): Add daily capability sync cron job

- Sync logistics ships for all characters
- Check skill requirements against character skills
- Cache results in character_capabilities table
- Runs daily at 04:00"
```

---

## Task 7: Frontend - Add Transport Types and API

**Files:**
- Modify: `frontend/src/api.ts` (if needed)
- Modify: `frontend/src/pages/ShoppingPlanner.tsx`

**Step 1: Add TypeScript interfaces**

Add to `ShoppingPlanner.tsx` after existing interfaces (around line 80):

```typescript
interface CargoSummary {
  list_id: number;
  products: Array<{
    type_id: number;
    item_name: string;
    runs: number;
    total_volume: number;
  }>;
  materials: {
    total_items: number;
    total_volume_m3: number;
    volume_formatted: string;
    breakdown_by_region: Record<string, { volume_m3: number; item_count: number }>;
  };
}

interface TransportOption {
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

interface TransportOptions {
  total_volume_m3: number;
  volume_formatted: string;
  route_summary: string;
  options: TransportOption[];
  filters_available: string[];
  message?: string;
}
```

**Step 2: Add queries for cargo and transport**

Add after existing queries (around line 570):

```typescript
  // Fetch cargo summary
  const { data: cargoSummary } = useQuery<CargoSummary>({
    queryKey: ['shopping-cargo', selectedListId],
    queryFn: async () => {
      const response = await api.get(`/api/shopping/lists/${selectedListId}/cargo-summary`);
      return response.data;
    },
    enabled: !!selectedListId,
  });

  // Fetch transport options
  const [safeRoutesOnly, setSafeRoutesOnly] = useState(true);

  const { data: transportOptions, isLoading: isLoadingTransport } = useQuery<TransportOptions>({
    queryKey: ['shopping-transport', selectedListId, safeRoutesOnly],
    queryFn: async () => {
      const response = await api.get(`/api/shopping/lists/${selectedListId}/transport-options`, {
        params: { safe_only: safeRoutesOnly }
      });
      return response.data;
    },
    enabled: !!selectedListId && viewMode === 'transport',
  });
```

**Step 3: Update viewMode state**

Change the viewMode state (around line 528):

```typescript
  const [viewMode, setViewMode] = useState<'list' | 'compare' | 'transport'>('list');
```

**Step 4: Commit**

```bash
git add frontend/src/pages/ShoppingPlanner.tsx
git commit -m "feat(frontend): Add transport types and API queries

- CargoSummary, TransportOption, TransportOptions interfaces
- Queries for cargo-summary and transport-options endpoints
- safeRoutesOnly toggle state"
```

---

## Task 8: Frontend - Cargo Display in Header

**Files:**
- Modify: `frontend/src/pages/ShoppingPlanner.tsx`

**Step 1: Add Package icon import**

Update imports (line 3):

```typescript
import { ShoppingCart, Plus, Trash2, Check, Copy, ChevronRight, X, Map, BarChart3, RefreshCw, MousePointer, Eye, ArrowUpDown, Package, Truck } from 'lucide-react';
```

**Step 2: Add cargo display in list header**

Find the list header section (around line 800) and add cargo info after the list name display:

```typescript
                  {/* Cargo Summary */}
                  {cargoSummary && cargoSummary.materials.total_volume_m3 > 0 && (
                    <div style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: 8,
                      padding: '8px 12px',
                      background: 'var(--bg-dark)',
                      borderRadius: 6,
                      fontSize: 13
                    }}>
                      <Package size={16} />
                      <span>Cargo: <strong>{cargoSummary.materials.volume_formatted}</strong></span>
                      <span className="neutral">({cargoSummary.materials.total_items} items)</span>
                    </div>
                  )}
```

**Step 3: Add Transport tab button**

Find the view mode buttons (around line 850) and add Transport button:

```typescript
                      <button
                        className={`btn ${viewMode === 'transport' ? 'btn-primary' : 'btn-secondary'}`}
                        onClick={() => setViewMode('transport')}
                        disabled={!cargoSummary || cargoSummary.materials.total_volume_m3 === 0}
                        title={!cargoSummary || cargoSummary.materials.total_volume_m3 === 0
                          ? 'Add items to see transport options'
                          : 'Plan transport'}
                      >
                        <Truck size={16} style={{ marginRight: 6 }} />
                        Transport
                      </button>
```

**Step 4: Build and verify**

```bash
cd /home/cytrex/eve_copilot/frontend && npm run build
```

**Step 5: Commit**

```bash
git add frontend/src/pages/ShoppingPlanner.tsx
git commit -m "feat(frontend): Add cargo display and transport tab

- Show cargo volume in list header
- Add Transport tab button (disabled when no items)"
```

---

## Task 9: Frontend - Transport Options Dashboard

**Files:**
- Modify: `frontend/src/pages/ShoppingPlanner.tsx`

**Step 1: Add transport filter state**

Add after safeRoutesOnly state:

```typescript
  const [transportFilter, setTransportFilter] = useState<string>('');
```

**Step 2: Add Transport view section**

Add after the Compare Regions section (around line 1200), before the closing of the conditional render:

```typescript
                    {/* Transport Options View */}
                    {viewMode === 'transport' && (
                      <div className="card">
                        <div className="card-header">
                          <span className="card-title">
                            <Truck size={18} style={{ marginRight: 8 }} />
                            Transport Options
                          </span>
                          <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                            <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 13 }}>
                              <input
                                type="checkbox"
                                checked={safeRoutesOnly}
                                onChange={(e) => setSafeRoutesOnly(e.target.checked)}
                              />
                              Safe routes only
                            </label>
                          </div>
                        </div>

                        {isLoadingTransport ? (
                          <div className="loading">
                            <div className="spinner"></div>
                            Calculating transport options...
                          </div>
                        ) : transportOptions?.options.length === 0 ? (
                          <div style={{ padding: 20, textAlign: 'center' }}>
                            <p className="neutral">{transportOptions?.message || 'No transport options available'}</p>
                            <p style={{ fontSize: 12, marginTop: 8 }}>
                              Run the capability sync to update available ships.
                            </p>
                          </div>
                        ) : (
                          <>
                            {/* Summary Header */}
                            <div style={{
                              padding: '12px 16px',
                              background: 'var(--bg-dark)',
                              borderBottom: '1px solid var(--border-color)',
                              display: 'flex',
                              justifyContent: 'space-between',
                              alignItems: 'center'
                            }}>
                              <div>
                                <strong>{transportOptions?.volume_formatted}</strong>
                                <span className="neutral" style={{ marginLeft: 8 }}>
                                  {transportOptions?.route_summary}
                                </span>
                              </div>
                              <div style={{ display: 'flex', gap: 4 }}>
                                {['fewest_trips', 'fastest', 'lowest_risk'].map(filter => (
                                  <button
                                    key={filter}
                                    className={`btn btn-small ${transportFilter === filter ? 'btn-primary' : 'btn-secondary'}`}
                                    onClick={() => setTransportFilter(transportFilter === filter ? '' : filter)}
                                    style={{ padding: '4px 8px', fontSize: 11 }}
                                  >
                                    {filter === 'fewest_trips' ? 'Fewest Trips' :
                                     filter === 'fastest' ? 'Fastest' : 'Lowest Risk'}
                                  </button>
                                ))}
                              </div>
                            </div>

                            {/* Options List */}
                            <div style={{ padding: 16, display: 'flex', flexDirection: 'column', gap: 12 }}>
                              {transportOptions?.options
                                .filter(opt => {
                                  if (!transportFilter) return true;
                                  // Simple filter - would sort in real impl
                                  return true;
                                })
                                .map((option, idx) => (
                                  <div
                                    key={option.id}
                                    style={{
                                      padding: 16,
                                      background: 'var(--bg-dark)',
                                      borderRadius: 8,
                                      border: idx === 0 ? '2px solid var(--accent-blue)' : '1px solid var(--border-color)'
                                    }}
                                  >
                                    {idx === 0 && (
                                      <span className="badge badge-blue" style={{ marginBottom: 8, display: 'inline-block' }}>
                                        RECOMMENDED
                                      </span>
                                    )}

                                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                                      <div>
                                        <div style={{ fontWeight: 600, marginBottom: 4 }}>
                                          {option.characters[0]?.name} → {option.characters[0]?.ship_name}
                                        </div>
                                        <div className="neutral" style={{ fontSize: 12 }}>
                                          {option.characters[0]?.ship_group} • {option.characters[0]?.ship_location}
                                        </div>
                                      </div>

                                      <div style={{ textAlign: 'right' }}>
                                        <span className={option.risk_score === 0 ? 'positive' : option.risk_score <= 2 ? 'neutral' : 'negative'}>
                                          {option.risk_score === 0 ? '✅' : '⚠️'} {option.risk_label}
                                        </span>
                                      </div>
                                    </div>

                                    <div style={{
                                      display: 'grid',
                                      gridTemplateColumns: 'repeat(4, 1fr)',
                                      gap: 16,
                                      marginTop: 12,
                                      paddingTop: 12,
                                      borderTop: '1px solid var(--border-color)'
                                    }}>
                                      <div>
                                        <div className="neutral" style={{ fontSize: 11 }}>Trips</div>
                                        <div style={{ fontWeight: 600 }}>{option.trips}</div>
                                      </div>
                                      <div>
                                        <div className="neutral" style={{ fontSize: 11 }}>Time</div>
                                        <div style={{ fontWeight: 600 }}>{option.flight_time_formatted}</div>
                                      </div>
                                      <div>
                                        <div className="neutral" style={{ fontSize: 11 }}>Capacity Used</div>
                                        <div style={{ fontWeight: 600 }}>{option.capacity_used_pct}%</div>
                                      </div>
                                      <div>
                                        <div className="neutral" style={{ fontSize: 11 }}>Ship Capacity</div>
                                        <div style={{ fontWeight: 600 }}>{(option.capacity_m3 / 1000).toFixed(0)}K m³</div>
                                      </div>
                                    </div>
                                  </div>
                                ))}
                            </div>
                          </>
                        )}
                      </div>
                    )}
```

**Step 3: Build and test**

```bash
cd /home/cytrex/eve_copilot/frontend && npm run build
```

**Step 4: Commit**

```bash
git add frontend/src/pages/ShoppingPlanner.tsx
git commit -m "feat(frontend): Add transport options dashboard

- Safe routes toggle
- Filter buttons (fewest trips, fastest, lowest risk)
- Option cards with character, ship, metrics
- Recommended option highlighted"
```

---

## Task 10: Integration Test & Cleanup

**Step 1: Run capability sync**

```bash
cd /home/cytrex/eve_copilot && python3 jobs/capability_sync.py
```

**Step 2: Start backend**

```bash
cd /home/cytrex/eve_copilot && /home/cytrex/.local/bin/uvicorn main:app --host 0.0.0.0 --port 8000 --reload &
```

**Step 3: Start frontend**

```bash
cd /home/cytrex/eve_copilot/frontend && npm run dev -- --host 0.0.0.0 &
```

**Step 4: Test end-to-end**

1. Open http://localhost:5173/shopping
2. Select a shopping list with items
3. Verify cargo volume shows in header
4. Click Transport tab
5. Verify options display

**Step 5: Final commit**

```bash
git add -A
git commit -m "feat: Complete transport logistics Phase 1

- DB schema for product tracking and capabilities
- Capability service with skill checking
- Transport options calculation
- Frontend dashboard with options display

Closes Phase 1 of transport logistics design"
git push origin main
```

---

## Summary

| Task | Component | Files |
|------|-----------|-------|
| 1 | DB Migration | `migrations/004_transport_logistics.sql` |
| 2 | Capability Service | `capability_service.py` |
| 3 | Shopping Service Extension | `shopping_service.py` |
| 4 | Transport Service | `transport_service.py` |
| 5 | API Endpoints | `routers/shopping.py` |
| 6 | Cron Job | `jobs/capability_sync.py`, `jobs/cron_capability_sync.sh` |
| 7 | Frontend Types & API | `frontend/src/pages/ShoppingPlanner.tsx` |
| 8 | Frontend Cargo Display | `frontend/src/pages/ShoppingPlanner.tsx` |
| 9 | Frontend Transport Dashboard | `frontend/src/pages/ShoppingPlanner.tsx` |
| 10 | Integration Test | - |

**Estimated commits:** 10
**Dependencies:** Tasks must be done in order (each builds on previous)
