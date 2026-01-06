# War Reports Overview

## Available Reports

EVE Co-Pilot now includes **4 automated Telegram reports** for combat intelligence:

### 1. 24h Battle Report (Existing)
**Schedule:** Every 10 minutes
**Purpose:** Regional battle statistics and combat overview

**Data Included:**
- Total kills and ISK destroyed per region
- Top 5 most active regions
- Top systems per region
- Most destroyed ship types
- Most destroyed items/modules

**Cron Job:** `*/10 * * * * /home/cytrex/eve_copilot/jobs/cron_telegram_report.sh`

---

### 2. War Profiteering Daily Digest (NEW)
**Schedule:** Daily at 06:00 UTC
**Purpose:** Market opportunities from destroyed items

**Data Included:**
- Top 20 most-destroyed items by market value
- Quantity destroyed in last 24h
- Current Jita market price per item
- Total opportunity value (quantity × price)
- Sorted by highest profit potential

**Use Case:** Stock these items in combat zones for war profiteering

**Cron Job:** `0 6 * * * /home/cytrex/eve_copilot/jobs/cron_war_profiteering.sh`

**Files:**
- Method: `zkillboard_live_service.py::get_war_profiteering_report()`
- Telegram: `jobs/telegram_war_profiteering.py`
- Cron: `jobs/cron_war_profiteering.sh`

---

### 3. Alliance War Tracker (NEW)
**Schedule:** Every 30 minutes
**Purpose:** Track active alliance conflicts with metrics

**Data Included:**
- Top 5 active alliance wars by total kills
- Kill/death ratio per conflict
- ISK efficiency percentage
- Winner determination (winning/losing/contested)
- Number of active combat systems
- Alliance names via ESI API

**Use Case:** Monitor major conflicts and predict outcomes

**Cron Job:** `*/30 * * * * /home/cytrex/eve_copilot/jobs/cron_alliance_wars.sh`

**Files:**
- Method: `zkillboard_live_service.py::get_alliance_war_tracker()`
- Telegram: `jobs/telegram_alliance_wars.py`
- Cron: `jobs/cron_alliance_wars.sh`

---

### 4. Trade Route Danger Map (NEW)
**Schedule:** Daily at 08:00 UTC
**Purpose:** Hauler safety analysis for HighSec trade routes

**Data Included:**
- 5 major trade routes (Jita↔Amarr, Jita↔Dodixie, etc.)
- Danger score per system (0-100 scale)
- Gate camp detection (4+ attackers)
- Kills in last 24h per system
- Route danger classification (SAFE/LOW/MODERATE/HIGH/EXTREME)
- Most dangerous system per route

**Danger Score Calculation:**
- Kill frequency: 0-40 points (1 per kill, capped at 40)
- Average ship value: 0-30 points (1 per 100M ISK)
- Gate camps: +30 points if >20% multi-attacker kills

**Use Case:** Plan safe hauling routes, avoid gate camps

**Cron Job:** `0 8 * * * /home/cytrex/eve_copilot/jobs/cron_trade_routes.sh`

**Files:**
- Method: `zkillboard_live_service.py::get_trade_route_danger_map()`
- Telegram: `jobs/telegram_trade_routes.py`
- Cron: `jobs/cron_trade_routes.sh`

---

## Installation

### 1. Make Scripts Executable
```bash
chmod +x /home/cytrex/eve_copilot/jobs/cron_war_profiteering.sh
chmod +x /home/cytrex/eve_copilot/jobs/cron_alliance_wars.sh
chmod +x /home/cytrex/eve_copilot/jobs/cron_trade_routes.sh
```

### 2. Add to Crontab
```bash
crontab -e
```

Add these lines:
```cron
# War Profiteering Daily Digest (06:00 UTC daily)
0 6 * * * /home/cytrex/eve_copilot/jobs/cron_war_profiteering.sh

# Alliance War Tracker (every 30 minutes)
*/30 * * * * /home/cytrex/eve_copilot/jobs/cron_alliance_wars.sh

# Trade Route Danger Map (08:00 UTC daily)
0 8 * * * /home/cytrex/eve_copilot/jobs/cron_trade_routes.sh
```

### 3. Verify Logs
```bash
tail -f /home/cytrex/eve_copilot/logs/war_profiteering.log
tail -f /home/cytrex/eve_copilot/logs/alliance_wars.log
tail -f /home/cytrex/eve_copilot/logs/trade_routes.log
```

---

## Testing

Run reports manually for testing:

```bash
# Test War Profiteering
python3 /home/cytrex/eve_copilot/jobs/telegram_war_profiteering.py

# Test Alliance Wars
python3 /home/cytrex/eve_copilot/jobs/telegram_alliance_wars.py

# Test Trade Routes
python3 /home/cytrex/eve_copilot/jobs/telegram_trade_routes.py
```

All reports send to Telegram channel: `-1003469769939` (infinimind-eve)

---

## Technical Details

### Data Sources
- **Redis:** 24h killmail hot storage (52,000+ kills)
- **PostgreSQL:** EVE SDE (ship/item names, market prices, systems, regions)
- **ESI API:** Alliance names (async calls with rate limiting)
- **Route Service:** A* pathfinding for HighSec routes

### Performance
- Battle Report: Cached 10 minutes (74x faster when cached)
- Alliance Wars: Async ESI calls for alliance names
- Trade Routes: Lazy-loaded route graph (8,437 systems)

### Architecture
All 3 new reports follow the same pattern:
1. Service method in `zkillboard_live_service.py`
2. Telegram formatter in `jobs/telegram_*.py`
3. Cron wrapper in `jobs/cron_*.sh`
4. Logs to `logs/*.log`

---

## Next Steps (Optional)

1. **Add API Endpoints** for web access to reports
2. **Dashboard Integration** - display reports in frontend
3. **User Preferences** - configure report frequency per user
4. **Historical Tracking** - store report snapshots for trend analysis

---

Last Updated: 2026-01-06
