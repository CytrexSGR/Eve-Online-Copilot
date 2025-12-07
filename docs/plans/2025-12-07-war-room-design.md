# War Room - Feature Design

## Overview

"War Profiteering" module that analyzes combat data to identify production and trading opportunities. Destruction drives demand - when ships and modules are destroyed, they need to be replaced.

## Data Sources

### 1. EVE Ref Killmail Bulk Data (Primary)
- **URL:** `https://data.everef.net/killmails/2025/`
- **Format:** `killmails-YYYY-MM-DD.tar.bz2`
- **Size:** ~2-5 MB/day compressed, ~6,500 kills/day
- **Latency:** 24h (previous day's data)
- **Rate Limits:** None
- **Contains:** Full killmail with ship_type_id, all items destroyed/dropped, solar_system_id

### 2. ESI Sovereignty Campaigns (Predictive)
- **Endpoint:** `GET /sovereignty/campaigns/`
- **Cache:** 5 seconds
- **Contains:** Upcoming structure timers (ihub_defense, tcu_defense)
- **Use Case:** Predict where large battles will happen

### 3. ESI Faction Warfare Systems (Conflict Zones)
- **Endpoint:** `GET /fw/systems/`
- **Cache:** 1800 seconds
- **Contains:** Contested status, victory points
- **Use Case:** Identify active FW warzones with high frigate/destroyer demand

---

## Database Schema

```sql
-- Daily ship losses aggregated by region
CREATE TABLE combat_ship_losses (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL,
    region_id INTEGER NOT NULL,
    solar_system_id INTEGER NOT NULL,
    ship_type_id INTEGER NOT NULL,
    quantity INTEGER NOT NULL DEFAULT 1,
    total_value_destroyed NUMERIC(20,2) DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(date, solar_system_id, ship_type_id)
);

CREATE INDEX idx_ship_losses_date_region ON combat_ship_losses(date, region_id);
CREATE INDEX idx_ship_losses_ship ON combat_ship_losses(ship_type_id);

-- Daily item/module losses aggregated by region
CREATE TABLE combat_item_losses (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL,
    region_id INTEGER NOT NULL,
    solar_system_id INTEGER NOT NULL,
    item_type_id INTEGER NOT NULL,
    quantity_destroyed INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(date, solar_system_id, item_type_id)
);

CREATE INDEX idx_item_losses_date_region ON combat_item_losses(date, region_id);
CREATE INDEX idx_item_losses_item ON combat_item_losses(item_type_id);

-- Sovereignty campaign snapshots
CREATE TABLE sovereignty_campaigns (
    id SERIAL PRIMARY KEY,
    campaign_id INTEGER UNIQUE NOT NULL,
    event_type VARCHAR(50) NOT NULL,  -- ihub_defense, tcu_defense
    solar_system_id INTEGER NOT NULL,
    constellation_id INTEGER NOT NULL,
    defender_id INTEGER,  -- Alliance ID
    attacker_score FLOAT,
    defender_score FLOAT,
    start_time TIMESTAMP NOT NULL,
    structure_id BIGINT,
    first_seen_at TIMESTAMP DEFAULT NOW(),
    last_updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_sov_campaigns_start ON sovereignty_campaigns(start_time);
CREATE INDEX idx_sov_campaigns_system ON sovereignty_campaigns(solar_system_id);

-- Faction Warfare system status snapshots
CREATE TABLE fw_system_status (
    id SERIAL PRIMARY KEY,
    solar_system_id INTEGER NOT NULL,
    owner_faction_id INTEGER NOT NULL,
    occupier_faction_id INTEGER NOT NULL,
    contested VARCHAR(20) NOT NULL,  -- uncontested, contested, vulnerable, captured
    victory_points INTEGER NOT NULL,
    victory_points_threshold INTEGER NOT NULL,
    snapshot_time TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_fw_status_system ON fw_system_status(solar_system_id);
CREATE INDEX idx_fw_status_time ON fw_system_status(snapshot_time);

-- Cached region mapping for solar systems (for fast lookups)
-- Note: This can be derived from SDE mapSolarSystems but caching speeds up queries
CREATE TABLE system_region_map (
    solar_system_id INTEGER PRIMARY KEY,
    region_id INTEGER NOT NULL,
    constellation_id INTEGER NOT NULL,
    security_status FLOAT
);
```

---

## Backend Services

### 1. killmail_service.py
```python
class KillmailService:
    """Fetches and processes EVE Ref killmail bulk data"""

    def download_daily_archive(self, date: date) -> Path:
        """Download killmails-YYYY-MM-DD.tar.bz2"""

    def extract_and_parse(self, archive_path: Path) -> List[dict]:
        """Extract tar.bz2 and parse all JSON killmails"""

    def aggregate_by_region(self, killmails: List[dict]) -> dict:
        """Group losses by region_id, ship_type_id, item_type_id"""

    def save_to_database(self, date: date, aggregated: dict):
        """Insert/update combat_ship_losses and combat_item_losses"""

    def get_losses(self, region_id: int, days: int = 7) -> dict:
        """Query aggregated losses for analysis"""
```

### 2. sovereignty_service.py
```python
class SovereigntyService:
    """Tracks sovereignty campaigns and predicts battles"""

    def fetch_campaigns(self) -> List[dict]:
        """GET /sovereignty/campaigns/ from ESI"""

    def update_campaigns(self):
        """Sync campaigns to database, track new/changed"""

    def get_upcoming_battles(self, hours: int = 48) -> List[dict]:
        """Get campaigns with start_time in next X hours"""

    def get_region_for_system(self, solar_system_id: int) -> int:
        """Map system to region for trade hub routing"""
```

### 3. fw_service.py
```python
class FactionWarfareService:
    """Tracks Faction Warfare contested systems"""

    def fetch_fw_systems(self) -> List[dict]:
        """GET /fw/systems/ from ESI"""

    def update_status(self):
        """Snapshot current FW status to database"""

    def get_hotspots(self) -> List[dict]:
        """Systems with contested > 50% (high activity zones)"""

    def get_vulnerable_systems(self) -> List[dict]:
        """Systems close to flipping (>90% contested)"""
```

### 4. war_analyzer.py
```python
class WarAnalyzer:
    """Combines all data sources for demand analysis"""

    def analyze_demand(self, region_id: int) -> dict:
        """
        Returns:
        - top_ships_lost: [(ship_type_id, name, qty, trend)]
        - top_items_lost: [(item_type_id, name, qty, trend)]
        - market_gaps: items where losses > market_volume
        - upcoming_battles: sov campaigns in region
        - fw_hotspots: contested FW systems nearby
        """

    def detect_doctrines(self, region_id: int, days: int = 7) -> List[dict]:
        """
        Identify doctrine fleets by finding:
        - Same ship type destroyed in bulk (>10 in same system/hour)
        - Consistent module patterns across losses
        """

    def calculate_demand_score(self, type_id: int, region_id: int) -> float:
        """
        Score = (losses_7d / market_volume) * trend_multiplier
        Higher score = higher unmet demand
        """
```

---

## Cron Jobs

### 1. jobs/cron_killmail_fetcher.sh (Daily at 06:00 UTC)
```bash
#!/bin/bash
cd /home/cytrex/eve_copilot
python3 jobs/killmail_fetcher.py >> logs/killmail_fetcher.log 2>&1
```

### 2. jobs/cron_sov_tracker.sh (Every 30 min)
```bash
#!/bin/bash
cd /home/cytrex/eve_copilot
python3 jobs/sov_tracker.py >> logs/sov_tracker.log 2>&1
```

### 3. jobs/cron_fw_tracker.sh (Every 30 min)
```bash
#!/bin/bash
cd /home/cytrex/eve_copilot
python3 jobs/fw_tracker.py >> logs/fw_tracker.log 2>&1
```

---

## API Endpoints

### Router: routers/war.py

```python
# Combat Losses
GET /api/war/losses/{region_id}
    ?days=7              # Lookback period
    ?type=ships|items    # Filter by category
    → Returns aggregated losses with names and trends

GET /api/war/losses/system/{solar_system_id}
    → Losses for specific system

# Demand Analysis
GET /api/war/demand/{region_id}
    → Combined analysis: losses vs market, gaps, recommendations

GET /api/war/demand/item/{type_id}
    → Demand analysis for specific item across all regions

# Sovereignty
GET /api/war/campaigns
    ?hours=48            # Upcoming window
    → List of upcoming sovereignty battles

GET /api/war/campaigns/region/{region_id}
    → Campaigns in specific region

# Faction Warfare
GET /api/war/fw/hotspots
    → Systems with high contested status

GET /api/war/fw/status/{solar_system_id}
    → Current FW status for system

# Doctrine Detection
GET /api/war/doctrines/{region_id}
    ?days=7
    → Detected fleet doctrines based on loss patterns

# Route Safety (bonus feature)
GET /api/war/route-safety/{from_system}/{to_system}
    → Analyze kill activity along route, suggest safer alternatives
```

---

## Frontend: WarRoom.tsx

### Layout
```
┌─────────────────────────────────────────────────────────────┐
│  WAR ROOM                                    [Region: ▼]    │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────┐ │
│  │ SHIPS DESTROYED │  │ ITEMS DESTROYED │  │ MARKET GAPS │ │
│  │ (7 days)        │  │ (7 days)        │  │             │ │
│  │                 │  │                 │  │ ⚠ Ishtar    │ │
│  │ 847 Caracal  ▲  │  │ 2.1M Void S  ▲  │  │   Lost: 116 │ │
│  │ 523 Ferox    ▼  │  │ 1.8M Null S  ─  │  │   Stock: 12 │ │
│  │ 412 Hurricane   │  │ 890K Mjolnir    │  │   GAP: 104! │ │
│  │ ...             │  │ ...             │  │             │ │
│  └─────────────────┘  └─────────────────┘  └─────────────┘ │
│                                                             │
│  ┌─────────────────────────────────────────────────────────┐│
│  │ UPCOMING BATTLES (Sov Timers)                          ││
│  │                                                         ││
│  │ ⏰ 15:36 - UL-7I8 (Catch) - IHUB Defense               ││
│  │    Defender: [ALLIANCE] | Nearest Hub: Amarr (12j)     ││
│  │                                                         ││
│  │ ⏰ 22:39 - X-7OMU (Pure Blind) - TCU Defense           ││
│  │    Defender: [ALLIANCE] | Nearest Hub: Jita (8j)       ││
│  └─────────────────────────────────────────────────────────┘│
│                                                             │
│  ┌─────────────────────────────────────────────────────────┐│
│  │ FACTION WARFARE HOTSPOTS                               ││
│  │                                                         ││
│  │ 🔥 Tama (88% contested) - Caldari vs Gallente          ││
│  │ 🔥 Amamake (72% contested) - Minmatar vs Amarr         ││
│  │                                                         ││
│  │ → High demand for: Frigates, Destroyers, T1 Modules    ││
│  └─────────────────────────────────────────────────────────┘│
│                                                             │
│  ┌─────────────────────────────────────────────────────────┐│
│  │ DETECTED DOCTRINES                                     ││
│  │                                                         ││
│  │ 📋 "Ferox Fleet" - 47 identical fits destroyed         ││
│  │    Ferox + Large Shield Extender II + Magnetic Field   ││
│  │    → Expected restock demand: ~50 units                ││
│  └─────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────┘
```

---

## Implementation Order

### Phase 1: Database & Infrastructure
1. Create migration with all tables (combat_ship_losses, combat_item_losses, sovereignty_campaigns, fw_system_status, system_region_map, alliance_conflicts)
2. Populate system_region_map from SDE mapSolarSystems
3. Add War Room config settings to config.py

### Phase 2: Killmail Data Collection
4. Implement killmail_service.py (download, extract, parse, aggregate, save)
5. Create jobs/killmail_fetcher.py cron job
6. Implement backfill capability with date range support
7. Backfill last 7 days of killmail data
8. Add alliance conflict extraction during processing

### Phase 3: Sovereignty & Faction Warfare
9. Implement sovereignty_service.py (fetch campaigns, map to regions)
10. Implement fw_service.py (fetch systems, identify hotspots)
11. Create jobs/sov_tracker.py (every 30 min)
12. Create jobs/fw_tracker.py (every 30 min)

### Phase 4: Analysis Engine
13. Implement war_analyzer.py with:
    - analyze_demand() - losses vs market stock
    - detect_doctrines() - fleet pattern recognition (10+ ships)
    - calculate_demand_score() - prioritization metric
14. Add production timing warnings (rudimentary: "Sov timer in Xh")

### Phase 5: API Layer
15. Create routers/war.py with all endpoints:
    - /api/war/losses/{region_id}
    - /api/war/demand/{region_id}
    - /api/war/campaigns
    - /api/war/fw/hotspots
    - /api/war/heatmap
    - /api/war/doctrines/{region_id}
    - /api/war/conflicts (alliance vs alliance)

### Phase 6: Route Safety Integration
16. Extend route_service.py with kill data overlay
17. Add danger scoring per system (kills/24h)
18. Integrate into Shopping module route display
19. Show warnings: "⚠️ Route passes through conflict zone (47 kills/24h)"

### Phase 7: Frontend - War Room Page
20. Create WarRoom.tsx main page with:
    - 2D Scatter Galaxy Heatmap (Phase 1)
    - Region drill-down view (Phase 2)
    - Ships/Items destroyed tables
    - Market gaps panel
    - Sov timers list
    - FW hotspots list
    - Detected doctrines
21. Add navigation link to App.tsx

### Phase 8: Frontend - Contextual Integration
22. Add "Conflict Alert" component for other pages
23. Integrate into ShoppingPlanner.tsx (route warnings)
24. Integrate into ProductionPlanner.tsx (timing suggestions)

### Phase 9: Discord Notifications
25. Implement war notification triggers in notification_service.py
26. Configurable thresholds (demand score, gap units)
27. Alerts for: market gaps, sov timers, high losses

### Phase 10: Alliance Watchlist (Later)
28. Create alliance_watchlist table
29. Add management UI (add/remove/thresholds)
30. Personalized alerts for watched alliances

---

## Success Metrics

After 1 week of data collection:
- Can identify top 10 destroyed ships per region
- Can detect at least 1 doctrine fleet pattern
- Can show market gaps (losses > stock)
- Sov timers display correctly with countdown
- FW hotspots update every 30 min

---

## Additional Features (from Brainstorming)

### War Heatmap / Conflict Map
Visual representation of conflict intensity across New Eden.

**Data available:**
- Solar system coordinates (x, z) from SDE `mapSolarSystems`
- Kill counts per system from killmail data
- Security status for coloring

**Implementation options:**
1. **Simple:** SVG/Canvas 2D scatter plot with kill intensity as dot size/color
2. **Medium:** Use [eveeye map data](https://github.com/Risingson/eveeyeevemaps) for proper layout
3. **Advanced:** Interactive map with zoom, region filtering, time slider

**API Endpoint:**
```
GET /api/war/heatmap
    ?days=7
    ?min_kills=5
    → Returns [{system_id, name, region, x, z, security, kills}]
```

### Alliance Conflict Tracking
Track which alliances are at war with each other.

**Discovered conflicts (Dec 6, 2025):**
- Pandemic Legion vs The Initiative: 1078 kills
- Fraternity vs Goonswarm: 859 kills
- Fraternity vs The Initiative: 521 kills

**New table:**
```sql
CREATE TABLE alliance_conflicts (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL,
    alliance_a INTEGER NOT NULL,
    alliance_b INTEGER NOT NULL,
    kill_count INTEGER NOT NULL,
    UNIQUE(date, alliance_a, alliance_b)
);
```

**Use cases:**
- "Pandemic Legion is at war → expect HAC demand in Jita"
- "Goonswarm losing ships in Delve → Amarr hub gets busy"

### Time-of-Day Analysis
Combat activity follows player timezones.

**Peak hours (from data):**
- 02:00-05:00 UTC (AUTZ prime time)
- 18:00-22:00 UTC (EUTZ prime time)
- 00:00-03:00 UTC (USTZ prime time)

**Use case:** Schedule production jobs to complete before peak hours.

### Backfill Capability
Allow loading historical data for analysis.

```python
def backfill(self, start_date: date, end_date: date):
    """Download and process killmails for date range"""
    for d in date_range(start_date, end_date):
        if not self.has_data_for(d):
            self.download_and_process(d)
```

**Historical events to analyze:**
- B-R5RB anniversary battles
- Major alliance war starts
- Seasonal patterns (summer lull, winter wars)

---

## Configuration (config.py additions)

```python
# War Room Settings
WAR_DATA_RETENTION_DAYS = 30
WAR_DOCTRINE_MIN_FLEET_SIZE = 10
WAR_HEATMAP_MIN_KILLS = 5

# Discord Notifications (customizable thresholds)
WAR_DISCORD_ENABLED = True
WAR_DISCORD_WEBHOOK_URL = DISCORD_WEBHOOK_URL  # Reuse existing
WAR_ALERT_DEMAND_SCORE_THRESHOLD = 2.0  # losses/market_volume ratio
WAR_ALERT_MIN_GAP_UNITS = 50  # Minimum units short to trigger alert
```

---

## Resolved Questions

1. **Data retention:** 30 days (configurable)
2. **Doctrine detection:** 10 ships minimum (configurable)
3. **Discord alerts:** Prepared, customizable via config
4. **Backfill:** Implemented with date range support for historical analysis

## Design Decisions (from Brainstorming)

1. **Map Implementation:**
   - Phase 1: 2D Scatter Galaxy heatmap (quick overview)
   - Phase 2: Region drill-down with system connections (DOTLAN-style)
   - Click flow: Galaxy → Region → System details

2. **Route Safety:** Must-Have
   - Integrated directly into Shopping module route display
   - Shows kill activity along planned routes
   - Warning component for dangerous systems

3. **Production Timing:** Rudimentary
   - Simple warnings: "Sov timer in Xh in Region Y"
   - No complex scheduling, just awareness

4. **Alliance Watchlist:** Later phase
   - Full management UI (add/remove alliances)
   - Custom thresholds per alliance
   - Personalized alerts

5. **Frontend Architecture:** Hybrid
   - Dedicated `/war-room` page for deep analysis
   - Contextual "Conflict Alert" components on:
     - ShoppingPlanner (route warnings)
     - ProductionPlanner (timing suggestions)
   - Reusable components across pages
