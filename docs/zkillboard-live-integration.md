# zKillboard Live Integration

Real-time killmail streaming and combat intelligence for EVE Co-Pilot.

## Overview

The zKillboard Live Service provides real-time combat intelligence by streaming killmails from zKillboard and processing them for immediate analysis.

**Architecture:** Hybrid zKillboard API + ESI approach
- **zkillboard API**: Provides killmail IDs and metadata
- **ESI API**: Provides full killmail details
- **Redis**: Hot storage for last 24h of kills
- **PostgreSQL**: Long-term aggregated data (via daily EVE Ref batch)

## Features

### 1. Live Killmail Stream
- Polls zKillboard API every 10 seconds
- Fetches full killmail data from ESI
- Stores in Redis with 24h TTL
- Separates destroyed vs dropped items (for demand analysis)

### 2. Hotspot Detection
- Tracks kill frequency per system
- Alert threshold: **5 kills in 5 minutes**
- Sends Discord notifications for combat spikes
- Useful for identifying gate camps, battles, and PvP zones

### 3. War Profiteering / Demand Analysis
- Tracks **destroyed items only** (not dropped)
- 24h rolling window
- Identifies high-demand items for market speculation
- API endpoint: `/api/war/live/demand/top`

### 4. Regional & System Filtering
- Query kills by `region_id` or `system_id`
- Useful for localized combat intelligence
- Example: Monitor Jita's solar system for ganking activity

## API Endpoints

### GET /api/war/live/kills
Get recent killmails from live stream (last 24h).

**Parameters:**
- `system_id` (optional): Filter by solar system
- `region_id` (optional): Filter by region
- `limit` (optional, default 50): Max results

**Example:**
```bash
curl "http://localhost:8000/api/war/live/kills?region_id=10000002&limit=20"
```

**Response:**
```json
{
  "kills": [
    {
      "killmail_id": 132444185,
      "solar_system_id": 30002719,
      "region_id": 10000032,
      "ship_type_id": 670,
      "ship_value": 97526000,
      "destroyed_items": [
        {"item_type_id": 123, "quantity": 5}
      ]
    }
  ],
  "count": 20
}
```

### GET /api/war/live/hotspots
Get active combat hotspots (last hour).

**Response:**
```json
{
  "hotspots": [
    {
      "solar_system_id": 30002187,
      "region_id": 10000002,
      "kill_count": 8,
      "window_seconds": 300
    }
  ]
}
```

### GET /api/war/live/demand/{item_type_id}
Get destroyed quantity for a specific item (last 24h).

**Example:**
```bash
curl "http://localhost:8000/api/war/live/demand/2048"  # Warp Scrambler II
```

**Response:**
```json
{
  "item_type_id": 2048,
  "quantity_destroyed_24h": 157,
  "note": "Only destroyed items counted (not dropped)"
}
```

### GET /api/war/live/demand/top
Get most destroyed items in last 24h.

**Parameters:**
- `limit` (optional, default 20): Max items

**Response:**
```json
{
  "items": [
    {
      "item_type_id": 2048,
      "quantity_destroyed": 157
    }
  ]
}
```

### GET /api/war/live/stats
Get service statistics.

**Response:**
```json
{
  "total_kills_24h": 1523,
  "active_hotspots": 3,
  "redis_connected": true,
  "running": true
}
```

## Running the Service

### Start Background Listener

**Option 1: Screen Session (Recommended)**
```bash
screen -dmS zkill python3 -m jobs.zkill_live_listener --verbose
screen -r zkill  # Attach to see logs
# Ctrl+A, D to detach
```

**Option 2: Systemd Service**
```bash
sudo cp /path/to/zkill-live.service /etc/systemd/system/
sudo systemctl enable zkill-live
sudo systemctl start zkill-live
sudo systemctl status zkill-live
```

**Option 3: Direct Run (Development)**
```bash
python3 -m jobs.zkill_live_listener --verbose
```

### Test the Service

```bash
# Test the hybrid approach
python3 test_zkill_api_hybrid.py

# Check if running
curl http://localhost:8000/api/war/live/stats
```

## Configuration

Edit `zkillboard_live_service.py`:

```python
# Polling
ZKILL_POLL_INTERVAL = 10  # seconds between polls

# Hotspot Detection
HOTSPOT_WINDOW_SECONDS = 300  # 5 minutes
HOTSPOT_THRESHOLD_KILLS = 5   # 5+ kills = hotspot

# Redis
REDIS_TTL = 86400  # 24 hours
```

## Data Flow

```
┌─────────────────────────────────────────────────────┐
│            zKillboard Live Pipeline                 │
├─────────────────────────────────────────────────────┤
│                                                     │
│  [1] Poll zkillboard API                           │
│      https://zkillboard.com/api/kills/             │
│      → Get killmail_id + hash                      │
│                                                     │
│  [2] Fetch from ESI                                │
│      https://esi.evetech.net/.../killmails/...     │
│      → Get full killmail (system, ship, items)     │
│                                                     │
│  [3] Parse & Separate Items                        │
│      → Destroyed items (market demand)             │
│      → Dropped items (no demand)                   │
│                                                     │
│  [4] Store in Redis (24h TTL)                      │
│      → By system timeline                          │
│      → By region timeline                          │
│      → By item demand                              │
│                                                     │
│  [5] Detect Hotspots                               │
│      → 5+ kills in 5 min?                          │
│      → Send Discord alert                          │
│                                                     │
└─────────────────────────────────────────────────────┘
```

## Use Cases

### 1. War Profiteering
Monitor what's being destroyed in active war zones and stock up on those items in nearby trade hubs.

```bash
# Get most destroyed items
curl "http://localhost:8000/api/war/live/demand/top?limit=20"

# Check specific module demand
curl "http://localhost:8000/api/war/live/demand/2048"  # Warp Scrambler II
```

### 2. Combat Hotspot Monitoring
Get alerted when combat spikes in a system (gate camps, battles).

```bash
# Check active hotspots
curl "http://localhost:8000/api/war/live/hotspots"
```

Discord will receive:
```
⚠️ Combat Hotspot Detected
System: Rancer
Kills: 8 in 5 minutes
Latest: Caracal (45,000,000 ISK)
```

### 3. Regional PvP Analysis
Track combat activity in specific regions.

```bash
# Get recent kills in The Forge (Jita region)
curl "http://localhost:8000/api/war/live/kills?region_id=10000002&limit=50"
```

### 4. Ganking Tracking
Monitor high-value kills in high-sec trade routes.

```bash
# Filter by system (e.g., Uedama - common ganking system)
curl "http://localhost:8000/api/war/live/kills?system_id=30002768&limit=20"
```

## Performance

- **Polling Rate**: 10 seconds (configurable)
- **ESI Calls**: 1 per new kill (cached by ESI)
- **Redis Memory**: ~100MB for 1500 kills/hour over 24h
- **CPU**: Minimal (<5% on single core)

## Troubleshooting

### No kills appearing
```bash
# Check service status
curl http://localhost:8000/api/war/live/stats

# Expected:
{
  "total_kills_24h": 1500+,  # Should increase over time
  "redis_connected": true,
  "running": true
}
```

### Redis not connected
```bash
# Check Redis
docker ps | grep redis

# Start if not running
docker start eve_redis
```

### Service not running
```bash
# Check if listener is running
ps aux | grep zkill_live_listener

# Restart
screen -dmS zkill python3 -m jobs.zkill_live_listener --verbose
```

## Future Enhancements

- [ ] WebSocket support (if zkillboard re-enables it)
- [ ] Player tracking (alert when specific players are killed)
- [ ] Alliance war tracking (alert on alliance member kills)
- [ ] Historical kill replay (backfill from zkillboard archives)
- [ ] Frontend dashboard for live kill feed

## Credits

- **zKillboard**: https://zkillboard.com/
- **ESI API**: https://esi.evetech.net/
- **EVE Ref**: https://everef.net/ (for daily batch archives)
