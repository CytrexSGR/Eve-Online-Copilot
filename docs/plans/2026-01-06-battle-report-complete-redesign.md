# Battle Report Pilot Intelligence - Complete Redesign

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Transform Battle Report from news-style region overview to actionable pilot intelligence with hot zones, capital kills, high-value targets, danger zones, ship meta, and activity timeline.

**Architecture:** Backend extracts and categorizes killmail data into pilot-focused intelligence sections; frontend displays actionable information with system-level granularity, security status awareness, and temporal context.

**Tech Stack:** Python (FastAPI, PostgreSQL), React + TypeScript, EVE SDE database

---

## Task 1: Add System Metadata Lookup Functions

**Files:**
- Modify: `services/zkillboard/zkill_live_service.py`
- Database: `mapSolarSystems` table (EVE SDE)

**Step 1: Add security status lookup function**

Add function to get security status from database:

```python
def get_system_security(self, system_id: int) -> float:
    """Get security status for a solar system"""
    query = """
        SELECT security
        FROM mapSolarSystems
        WHERE solarSystemID = %s
    """
    with db.get_cursor() as cur:
        cur.execute(query, (system_id,))
        result = cur.fetchone()
        return result['security'] if result else 0.0
```

**Step 2: Add constellation and region lookup function**

```python
def get_system_location_info(self, system_id: int) -> dict:
    """Get full location info for a system"""
    query = """
        SELECT
            s.solarSystemName,
            s.security,
            c.constellationName,
            r.regionName
        FROM mapSolarSystems s
        JOIN mapConstellations c ON s.constellationID = c.constellationID
        JOIN mapRegions r ON s.regionID = r.regionID
        WHERE s.solarSystemID = %s
    """
    with db.get_cursor() as cur:
        cur.execute(query, (system_id,))
        result = cur.fetchone()
        if result:
            return {
                'system_name': result['solarsystemname'],
                'security_status': float(result['security']),
                'constellation_name': result['constellationname'],
                'region_name': result['regionname']
            }
        return {}
```

**Step 3: Test with known system**

```bash
# In Python shell
from services.zkillboard import zkill_live_service
info = zkill_live_service.get_system_location_info(30002048)  # Bei
print(info)
# Expected: {'system_name': 'Bei', 'security_status': 0.4, 'constellation_name': '...', 'region_name': 'Metropolis'}
```

**Step 4: Commit**

```bash
git add services/zkillboard/zkill_live_service.py
git commit -m "feat: add system metadata lookup functions for security and location"
```

---

## Task 2: Add Ship Category Classification

**Files:**
- Modify: `services/zkillboard/zkill_live_service.py`

**Step 1: Add ship category constants**

```python
# Ship type categories based on groupID
SHIP_CATEGORIES = {
    'titan': [30],  # Titans
    'supercarrier': [659],  # Supercarriers
    'carrier': [547],  # Carriers
    'dreadnought': [485],  # Dreadnoughts
    'force_auxiliary': [1538],  # Force Auxiliaries
    'battleship': [27, 898, 900],  # Battleships, Black Ops, Marauders
    'battlecruiser': [419, 540],  # Battlecruisers, Command Ships
    'cruiser': [26, 358, 894, 906, 963],  # Cruisers, HACs, Recons, etc
    'destroyer': [420, 541],  # Destroyers, Interdictors
    'frigate': [25, 324, 831, 893],  # Frigates, AFs, Interceptors, etc
    'freighter': [513, 902],  # Freighters, Jump Freighters
    'industrial': [28, 463],  # Industrials, Mining Barges
    'exhumer': [543],  # Exhumers
    'capsule': [29]  # Capsules/Pods
}
```

**Step 2: Add ship category lookup function**

```python
def get_ship_category(self, group_id: int) -> str:
    """Determine ship category from group ID"""
    for category, group_ids in SHIP_CATEGORIES.items():
        if group_id in group_ids:
            return category
    return 'other'
```

**Step 3: Add is_capital check function**

```python
def is_capital_ship(self, group_id: int) -> bool:
    """Check if ship is a capital"""
    capital_categories = ['titan', 'supercarrier', 'carrier', 'dreadnought', 'force_auxiliary']
    return self.get_ship_category(group_id) in capital_categories
```

**Step 4: Add is_industrial check function**

```python
def is_industrial_ship(self, group_id: int) -> bool:
    """Check if ship is industrial/hauler"""
    industrial_categories = ['freighter', 'industrial', 'exhumer']
    return self.get_ship_category(group_id) in industrial_categories
```

**Step 5: Test categorization**

```bash
# Test with known ship types
category = zkill_live_service.get_ship_category(30)  # Titans
print(category)  # Expected: 'titan'
is_cap = zkill_live_service.is_capital_ship(30)
print(is_cap)  # Expected: True
```

**Step 6: Commit**

```bash
git add services/zkillboard/zkill_live_service.py
git commit -m "feat: add ship category classification system"
```

---

## Task 3: Extract Capital Kills from Killmails

**Files:**
- Modify: `services/zkillboard/zkill_live_service.py`

**Step 1: Add capital kills extraction function**

```python
def extract_capital_kills(self, killmails: list) -> dict:
    """Extract and categorize capital kills"""
    capitals = {
        'titans': {'count': 0, 'total_isk': 0, 'kills': []},
        'supercarriers': {'count': 0, 'total_isk': 0, 'kills': []},
        'carriers': {'count': 0, 'total_isk': 0, 'kills': []},
        'dreadnoughts': {'count': 0, 'total_isk': 0, 'kills': []},
        'force_auxiliaries': {'count': 0, 'total_isk': 0, 'kills': []}
    }

    for km in killmails:
        group_id = km.get('victim', {}).get('group_id')
        if not group_id:
            continue

        category = self.get_ship_category(group_id)
        if category not in capitals:
            continue

        # Get system info
        system_id = km.get('solar_system_id')
        system_info = self.get_system_location_info(system_id) if system_id else {}

        kill_data = {
            'killmail_id': km.get('killmail_id'),
            'ship_name': km.get('victim', {}).get('ship_type_name', 'Unknown'),
            'victim': km.get('victim', {}).get('character_name', 'Unknown'),
            'isk_destroyed': float(km.get('zkb', {}).get('totalValue', 0)),
            'system_name': system_info.get('system_name', 'Unknown'),
            'region_name': system_info.get('region_name', 'Unknown'),
            'security_status': system_info.get('security_status', 0.0),
            'time_utc': km.get('killmail_time', '')
        }

        # Add to category
        key = category + 's' if not category.endswith('y') else category.replace('y', 'ies')
        if key in capitals:
            capitals[key]['count'] += 1
            capitals[key]['total_isk'] += kill_data['isk_destroyed']
            capitals[key]['kills'].append(kill_data)

    # Sort kills by ISK value
    for cat_data in capitals.values():
        cat_data['kills'].sort(key=lambda x: x['isk_destroyed'], reverse=True)

    return capitals
```

**Step 2: Test with sample killmail data**

```python
# Get recent killmails from cache
killmails = zkill_live_service._get_cached_killmails()
capitals = zkill_live_service.extract_capital_kills(killmails)
print(f"Titans: {capitals['titans']['count']}")
print(f"Total ISK: {capitals['titans']['total_isk']}")
```

**Step 3: Commit**

```bash
git add services/zkillboard/zkill_live_service.py
git commit -m "feat: add capital kills extraction and categorization"
```

---

## Task 4: Extract High-Value Individual Kills

**Files:**
- Modify: `services/zkillboard/zkill_live_service.py`

**Step 1: Add high-value kills extraction**

```python
def extract_high_value_kills(self, killmails: list, limit: int = 20) -> list:
    """Extract top N highest value kills"""
    high_value = []

    for km in killmails:
        system_id = km.get('solar_system_id')
        system_info = self.get_system_location_info(system_id) if system_id else {}

        isk_value = float(km.get('zkb', {}).get('totalValue', 0))
        security = system_info.get('security_status', 0.0)

        # Gank detection: high-value kill in HighSec
        is_gank = security >= 0.5 and isk_value > 1_000_000_000  # 1B ISK threshold

        kill_data = {
            'killmail_id': km.get('killmail_id'),
            'isk_destroyed': isk_value,
            'ship_type': self.get_ship_category(km.get('victim', {}).get('group_id', 0)),
            'ship_name': km.get('victim', {}).get('ship_type_name', 'Unknown'),
            'victim': km.get('victim', {}).get('character_name', 'Unknown'),
            'system_id': system_id,
            'system_name': system_info.get('system_name', 'Unknown'),
            'region_name': system_info.get('region_name', 'Unknown'),
            'security_status': security,
            'is_gank': is_gank,
            'time_utc': km.get('killmail_time', '')
        }

        high_value.append(kill_data)

    # Sort by ISK value and take top N
    high_value.sort(key=lambda x: x['isk_destroyed'], reverse=True)

    # Add rank
    for idx, kill in enumerate(high_value[:limit], 1):
        kill['rank'] = idx

    return high_value[:limit]
```

**Step 2: Test extraction**

```python
killmails = zkill_live_service._get_cached_killmails()
top_kills = zkill_live_service.extract_high_value_kills(killmails, limit=10)
print(f"Top kill: {top_kills[0]['isk_destroyed']/1e9:.2f}B ISK")
print(f"Ship: {top_kills[0]['ship_name']}")
print(f"Gank: {top_kills[0]['is_gank']}")
```

**Step 3: Commit**

```bash
git add services/zkillboard/zkill_live_service.py
git commit -m "feat: add high-value kills extraction with gank detection"
```

---

## Task 5: Identify Danger Zones (Industrial Kill Hotspots)

**Files:**
- Modify: `services/zkillboard/zkill_live_service.py`

**Step 1: Add danger zone identification**

```python
def identify_danger_zones(self, killmails: list, min_kills: int = 3) -> list:
    """Identify systems where industrials/freighters are dying"""
    system_industrial_kills = {}

    for km in killmails:
        group_id = km.get('victim', {}).get('group_id')
        if not self.is_industrial_ship(group_id):
            continue

        system_id = km.get('solar_system_id')
        if not system_id:
            continue

        if system_id not in system_industrial_kills:
            system_info = self.get_system_location_info(system_id)
            system_industrial_kills[system_id] = {
                'system_name': system_info.get('system_name', 'Unknown'),
                'region_name': system_info.get('region_name', 'Unknown'),
                'security_status': system_info.get('security_status', 0.0),
                'industrials_killed': 0,
                'freighters_killed': 0,
                'total_value': 0,
                'kills': []
            }

        isk_value = float(km.get('zkb', {}).get('totalValue', 0))
        system_industrial_kills[system_id]['total_value'] += isk_value
        system_industrial_kills[system_id]['kills'].append(km)

        # Count by type
        ship_cat = self.get_ship_category(group_id)
        if ship_cat == 'freighter':
            system_industrial_kills[system_id]['freighters_killed'] += 1
        else:
            system_industrial_kills[system_id]['industrials_killed'] += 1

    # Filter systems with minimum kills and calculate warning levels
    danger_zones = []
    for sys_id, data in system_industrial_kills.items():
        total_kills = data['industrials_killed'] + data['freighters_killed']
        if total_kills < min_kills:
            continue

        # Warning level based on kills and value
        if total_kills >= 20 or data['total_value'] > 50_000_000_000:
            warning_level = 'EXTREME'
        elif total_kills >= 10 or data['total_value'] > 20_000_000_000:
            warning_level = 'HIGH'
        else:
            warning_level = 'MODERATE'

        data['warning_level'] = warning_level
        danger_zones.append(data)

    # Sort by total value
    danger_zones.sort(key=lambda x: x['total_value'], reverse=True)

    return danger_zones
```

**Step 2: Test danger zone identification**

```python
killmails = zkill_live_service._get_cached_killmails()
dangers = zkill_live_service.identify_danger_zones(killmails)
if dangers:
    print(f"Top danger zone: {dangers[0]['system_name']}")
    print(f"  Freighters: {dangers[0]['freighters_killed']}")
    print(f"  Value: {dangers[0]['total_value']/1e9:.2f}B")
    print(f"  Warning: {dangers[0]['warning_level']}")
```

**Step 3: Commit**

```bash
git add services/zkillboard/zkill_live_service.py
git commit -m "feat: add danger zone identification for industrial kills"
```

---

## Task 6: Calculate Ship Type Breakdown

**Files:**
- Modify: `services/zkillboard/zkill_live_service.py`

**Step 1: Add ship breakdown calculation**

```python
def calculate_ship_breakdown(self, killmails: list) -> dict:
    """Calculate kills and ISK by ship category"""
    breakdown = {}

    for km in killmails:
        group_id = km.get('victim', {}).get('group_id', 0)
        category = self.get_ship_category(group_id)

        if category not in breakdown:
            breakdown[category] = {
                'count': 0,
                'total_isk': 0
            }

        breakdown[category]['count'] += 1
        breakdown[category]['total_isk'] += float(km.get('zkb', {}).get('totalValue', 0))

    # Sort by ISK value
    sorted_breakdown = dict(sorted(
        breakdown.items(),
        key=lambda x: x[1]['total_isk'],
        reverse=True
    ))

    return sorted_breakdown
```

**Step 2: Test breakdown**

```python
killmails = zkill_live_service._get_cached_killmails()
breakdown = zkill_live_service.calculate_ship_breakdown(killmails)
for category, data in list(breakdown.items())[:5]:
    print(f"{category}: {data['count']} kills, {data['total_isk']/1e9:.2f}B ISK")
```

**Step 3: Commit**

```bash
git add services/zkillboard/zkill_live_service.py
git commit -m "feat: add ship type breakdown calculation"
```

---

## Task 7: Calculate Hourly Activity Timeline

**Files:**
- Modify: `services/zkillboard/zkill_live_service.py`

**Step 1: Add timeline calculation**

```python
from datetime import datetime

def calculate_hourly_timeline(self, killmails: list) -> list:
    """Calculate kills and ISK per hour (UTC)"""
    hourly_data = {hour: {'hour_utc': hour, 'kills': 0, 'isk_destroyed': 0}
                   for hour in range(24)}

    for km in killmails:
        time_str = km.get('killmail_time', '')
        if not time_str:
            continue

        try:
            # Parse ISO 8601 timestamp
            dt = datetime.fromisoformat(time_str.replace('Z', '+00:00'))
            hour = dt.hour

            hourly_data[hour]['kills'] += 1
            hourly_data[hour]['isk_destroyed'] += float(km.get('zkb', {}).get('totalValue', 0))
        except:
            continue

    # Convert to list and sort by hour
    timeline = list(hourly_data.values())
    timeline.sort(key=lambda x: x['hour_utc'])

    return timeline
```

**Step 2: Add peak hour calculation**

```python
def find_peak_activity(self, timeline: list) -> dict:
    """Find hour with most kills"""
    if not timeline:
        return {'hour': 0, 'kills': 0}

    peak = max(timeline, key=lambda x: x['kills'])
    return {
        'hour_utc': peak['hour_utc'],
        'kills_per_hour': peak['kills'],
        'isk_per_hour': peak['isk_destroyed']
    }
```

**Step 3: Test timeline**

```python
killmails = zkill_live_service._get_cached_killmails()
timeline = zkill_live_service.calculate_hourly_timeline(killmails)
peak = zkill_live_service.find_peak_activity(timeline)
print(f"Peak hour: {peak['hour_utc']}:00 UTC")
print(f"Kills: {peak['kills_per_hour']}")
```

**Step 4: Commit**

```bash
git add services/zkillboard/zkill_live_service.py
git commit -m "feat: add hourly activity timeline calculation"
```

---

## Task 8: Build Hot Zones (Top Systems)

**Files:**
- Modify: `services/zkillboard/zkill_live_service.py`

**Step 1: Add hot zones extraction**

```python
def extract_hot_zones(self, killmails: list, limit: int = 15) -> list:
    """Extract top N most active systems"""
    system_activity = {}

    for km in killmails:
        system_id = km.get('solar_system_id')
        if not system_id:
            continue

        if system_id not in system_activity:
            system_info = self.get_system_location_info(system_id)
            system_activity[system_id] = {
                'system_id': system_id,
                'system_name': system_info.get('system_name', 'Unknown'),
                'region_name': system_info.get('region_name', 'Unknown'),
                'constellation_name': system_info.get('constellation_name', 'Unknown'),
                'security_status': system_info.get('security_status', 0.0),
                'kills': 0,
                'total_isk_destroyed': 0,
                'ship_types': {},
                'flags': []
            }

        system_activity[system_id]['kills'] += 1
        system_activity[system_id]['total_isk_destroyed'] += float(km.get('zkb', {}).get('totalValue', 0))

        # Track ship types
        ship_name = km.get('victim', {}).get('ship_type_name', 'Unknown')
        if ship_name not in system_activity[system_id]['ship_types']:
            system_activity[system_id]['ship_types'][ship_name] = 0
        system_activity[system_id]['ship_types'][ship_name] += 1

    # Determine dominant ship type and flags for each system
    for sys_data in system_activity.values():
        if sys_data['ship_types']:
            dominant = max(sys_data['ship_types'].items(), key=lambda x: x[1])
            sys_data['dominant_ship_type'] = dominant[0]
        else:
            sys_data['dominant_ship_type'] = 'Unknown'

        # Add flags
        if sys_data['kills'] >= 20:
            sys_data['flags'].append('high_activity')
        if sys_data['total_isk_destroyed'] > 10_000_000_000:  # 10B
            sys_data['flags'].append('high_value')

        # Remove ship_types dict (not needed in output)
        del sys_data['ship_types']

    # Sort by kills and take top N
    hot_zones = sorted(system_activity.values(), key=lambda x: x['kills'], reverse=True)[:limit]

    return hot_zones
```

**Step 2: Test hot zones**

```python
killmails = zkill_live_service._get_cached_killmails()
hot_zones = zkill_live_service.extract_hot_zones(killmails, limit=10)
for zone in hot_zones[:3]:
    print(f"{zone['system_name']} ({zone['security_status']:.1f}): {zone['kills']} kills")
```

**Step 3: Commit**

```bash
git add services/zkillboard/zkill_live_service.py
git commit -m "feat: add hot zones extraction for top systems"
```

---

## Task 9: Create New Battle Report Builder Function

**Files:**
- Modify: `services/zkillboard/zkill_live_service.py`

**Step 1: Add comprehensive battle report builder**

```python
def build_pilot_intelligence_report(self) -> dict:
    """Build complete pilot intelligence battle report"""
    # Get cached killmails
    killmails = self._get_cached_killmails()

    if not killmails:
        return self._empty_pilot_report()

    # Calculate all intelligence sections
    timeline = self.calculate_hourly_timeline(killmails)
    peak_activity = self.find_peak_activity(timeline)
    hot_zones = self.extract_hot_zones(killmails, limit=15)
    capital_kills = self.extract_capital_kills(killmails)
    high_value_kills = self.extract_high_value_kills(killmails, limit=20)
    danger_zones = self.identify_danger_zones(killmails, min_kills=3)
    ship_breakdown = self.calculate_ship_breakdown(killmails)

    # Calculate global stats
    total_kills = len(killmails)
    total_isk = sum(float(km.get('zkb', {}).get('totalValue', 0)) for km in killmails)

    return {
        'period': '24h',
        'global': {
            'total_kills': total_kills,
            'total_isk_destroyed': total_isk,
            'peak_hour_utc': peak_activity['hour_utc'],
            'peak_kills_per_hour': peak_activity['kills_per_hour']
        },
        'hot_zones': hot_zones,
        'capital_kills': capital_kills,
        'high_value_kills': high_value_kills,
        'danger_zones': danger_zones,
        'ship_breakdown': ship_breakdown,
        'timeline': timeline,
        'regions': self._build_region_summary(killmails)  # Keep for backwards compat
    }

def _empty_pilot_report(self) -> dict:
    """Return empty report structure"""
    return {
        'period': '24h',
        'global': {'total_kills': 0, 'total_isk_destroyed': 0, 'peak_hour_utc': 0, 'peak_kills_per_hour': 0},
        'hot_zones': [],
        'capital_kills': {
            'titans': {'count': 0, 'total_isk': 0, 'kills': []},
            'supercarriers': {'count': 0, 'total_isk': 0, 'kills': []},
            'carriers': {'count': 0, 'total_isk': 0, 'kills': []},
            'dreadnoughts': {'count': 0, 'total_isk': 0, 'kills': []},
            'force_auxiliaries': {'count': 0, 'total_isk': 0, 'kills': []}
        },
        'high_value_kills': [],
        'danger_zones': [],
        'ship_breakdown': {},
        'timeline': [],
        'regions': []
    }
```

**Step 2: Update public API endpoint**

Modify: `public_api/routers/reports.py`

```python
@router.get("/battle-24h")
async def get_battle_report() -> Dict:
    """
    24-Hour Battle Report - Pilot Intelligence

    Returns actionable combat intelligence from pilot perspective:
    - Hot zones (top systems)
    - Capital kills summary
    - High-value individual kills
    - Danger zones for haulers
    - Ship type breakdown
    - Hourly activity timeline

    Cache: 10 minutes
    """
    try:
        report = zkill_live_service.build_pilot_intelligence_report()
        return report
    except redis.RedisError as e:
        raise HTTPException(
            status_code=503,
            detail="Redis connection error. Reports temporarily unavailable."
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate battle report: {str(e)}"
        )
```

**Step 3: Test complete report**

```bash
curl -s http://localhost:8001/api/reports/battle-24h | python3 -m json.tool | head -100
```

Expected: New structure with hot_zones, capital_kills, etc.

**Step 4: Commit**

```bash
git add services/zkillboard/zkill_live_service.py public_api/routers/reports.py
git commit -m "feat: implement complete pilot intelligence report builder"
```

---

## Task 10: Update Frontend TypeScript Types

**Files:**
- Modify: `public-frontend/src/types/reports.ts`

**Step 1: Add new report type definitions**

```typescript
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
  victim: string;
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
  victim: string;
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
  regions: any[];  // Keep for backwards compat
}
```

**Step 2: Test TypeScript compilation**

```bash
cd public-frontend
npm run build
```

Expected: No TypeScript errors

**Step 3: Commit**

```bash
git add public-frontend/src/types/reports.ts
git commit -m "feat: add TypeScript types for pilot intelligence report"
```

---

## Task 11: Create Security Status Color Utility

**Files:**
- Create: `public-frontend/src/utils/security.ts`

**Step 1: Create security color function**

```typescript
/**
 * Get EVE Online standard security status color
 */
export function getSecurityColor(sec: number): string {
  if (sec >= 1.0) return '#2FEFEF';  // Bright cyan
  if (sec >= 0.9) return '#48F0C0';
  if (sec >= 0.8) return '#00EF47';
  if (sec >= 0.7) return '#00F000';
  if (sec >= 0.6) return '#8FEF2F';
  if (sec >= 0.5) return '#EFEF00';  // Yellow (HighSec boundary)
  if (sec >= 0.4) return '#D77700';
  if (sec >= 0.3) return '#F06000';
  if (sec >= 0.2) return '#F04800';
  if (sec >= 0.1) return '#D73000';
  return '#F00000';  // Red (NullSec)
}

/**
 * Get security zone label
 */
export function getSecurityZone(sec: number): string {
  if (sec >= 0.5) return 'HighSec';
  if (sec >= 0.1) return 'LowSec';
  return 'NullSec';
}

/**
 * Format security status display
 */
export function formatSecurity(sec: number): string {
  return sec.toFixed(1);
}
```

**Step 2: Create formatting utilities**

```typescript
/**
 * Format ISK value
 */
export function formatISK(value: number): string {
  if (value >= 1_000_000_000_000) {
    return `${(value / 1_000_000_000_000).toFixed(2)}T ISK`;
  }
  if (value >= 1_000_000_000) {
    return `${(value / 1_000_000_000).toFixed(2)}B ISK`;
  }
  if (value >= 1_000_000) {
    return `${(value / 1_000_000).toFixed(1)}M ISK`;
  }
  return `${(value / 1_000).toFixed(0)}K ISK`;
}
```

**Step 3: Test utilities**

Create test file to verify colors:

```typescript
console.log(getSecurityColor(1.0));  // Should be cyan
console.log(getSecurityColor(0.5));  // Should be yellow
console.log(getSecurityColor(0.0));  // Should be red
console.log(formatISK(89_200_000_000));  // "89.20B ISK"
```

**Step 4: Commit**

```bash
git add public-frontend/src/utils/security.ts
git commit -m "feat: add security status color and formatting utilities"
```

---

## Task 12: Create Hot Zones Component

**Files:**
- Create: `public-frontend/src/components/HotZonesTable.tsx`

**Step 1: Create hot zones table component**

```typescript
import { getSecurityColor, formatSecurity, formatISK } from '../utils/security';
import type { HotZone } from '../types/reports';

interface HotZonesTableProps {
  zones: HotZone[];
}

export function HotZonesTable({ zones }: HotZonesTableProps) {
  if (!zones || zones.length === 0) {
    return <div>No hot zones detected</div>;
  }

  return (
    <div className="card">
      <h2 style={{ marginBottom: '1rem' }}>🔥 Hot Zones - Top Combat Systems</h2>
      <p style={{ color: 'var(--text-secondary)', marginBottom: '1.5rem' }}>
        Most active systems in the last 24 hours
      </p>

      <div style={{ overflowX: 'auto' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr style={{ borderBottom: '2px solid var(--border-color)', textAlign: 'left' }}>
              <th style={{ padding: '0.75rem' }}>Rank</th>
              <th style={{ padding: '0.75rem' }}>System</th>
              <th style={{ padding: '0.75rem' }}>Region</th>
              <th style={{ padding: '0.75rem', textAlign: 'center' }}>Sec</th>
              <th style={{ padding: '0.75rem', textAlign: 'right' }}>Kills</th>
              <th style={{ padding: '0.75rem', textAlign: 'right' }}>ISK Destroyed</th>
              <th style={{ padding: '0.75rem' }}>Dominant Ship</th>
            </tr>
          </thead>
          <tbody>
            {zones.map((zone, idx) => (
              <tr
                key={zone.system_id}
                style={{
                  borderBottom: '1px solid var(--border-color)',
                  background: idx % 2 === 0 ? 'var(--bg-elevated)' : 'transparent'
                }}
              >
                <td style={{ padding: '0.75rem', fontWeight: 700, color: 'var(--accent-blue)' }}>
                  #{idx + 1}
                </td>
                <td style={{ padding: '0.75rem', fontWeight: 600 }}>
                  {zone.system_name}
                  {zone.flags.includes('high_activity') && (
                    <span style={{ marginLeft: '0.5rem', fontSize: '0.75rem', color: 'var(--danger)' }}>
                      🔥
                    </span>
                  )}
                </td>
                <td style={{ padding: '0.75rem', fontSize: '0.875rem', color: 'var(--text-secondary)' }}>
                  {zone.region_name}
                </td>
                <td style={{ padding: '0.75rem', textAlign: 'center' }}>
                  <span
                    style={{
                      padding: '0.25rem 0.5rem',
                      borderRadius: '4px',
                      fontSize: '0.875rem',
                      fontWeight: 700,
                      color: 'black',
                      background: getSecurityColor(zone.security_status)
                    }}
                  >
                    {formatSecurity(zone.security_status)}
                  </span>
                </td>
                <td style={{ padding: '0.75rem', textAlign: 'right', fontWeight: 600, color: 'var(--accent-blue)' }}>
                  {zone.kills.toLocaleString()}
                </td>
                <td style={{ padding: '0.75rem', textAlign: 'right', fontFamily: 'monospace', fontWeight: 600 }}>
                  {formatISK(zone.total_isk_destroyed)}
                </td>
                <td style={{ padding: '0.75rem', fontSize: '0.875rem' }}>
                  {zone.dominant_ship_type}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
```

**Step 2: Test component renders**

```bash
npm run dev
# Navigate to battle report and verify table displays
```

**Step 3: Commit**

```bash
git add public-frontend/src/components/HotZonesTable.tsx
git commit -m "feat: create hot zones table component"
```

---

*[Plan continues with Tasks 13-20 for remaining components: CapitalKillsSummary, HighValueKillsTable, DangerZonesAlert, ShipBreakdownChart, ActivityTimeline, and final BattleReport page integration]*

---

## Notes

**Ship Group IDs müssen aus DB geladen werden:**
- Query: `SELECT groupID FROM invTypes WHERE typeID = ?`
- Needed for ship categorization

**Killmail Structure:**
```json
{
  "killmail_id": 123456,
  "solar_system_id": 30002048,
  "killmail_time": "2026-01-06T14:23:15Z",
  "victim": {
    "ship_type_id": 670,
    "group_id": 29,
    "character_name": "Pilot Name"
  },
  "zkb": {
    "totalValue": 12345678
  }
}
```

**Performance:**
- Cache system location lookups (constellation/region names)
- Limit top kills lists (20 max for high-value, 15 for hot zones)
- Use indexed queries on mapSolarSystems

**Future Enhancements:**
- Killmail links to zKillboard: `https://zkillboard.com/kill/{killmail_id}/`
- System links to DotLan: `https://evemaps.dotlan.net/system/{system_name}`
- Real-time updates via WebSocket
- Historical comparison (24h vs 7d)
