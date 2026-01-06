# Battle Report - Pilot Intelligence Redesign

> **Ziel:** Battle Report aus Kapselpilot-Perspektive neu gestalten mit actionable intelligence

## Problem

Aktueller Battle Report ist zu "News-Stil":
- Gruppierung nach Regionen (zu allgemein)
- Keine Capital Kills hervorgehoben
- Keine High-Value Einzelkills
- Keine Zeitinformation
- Keine Sicherheitsstatus-Info
- Keine Gank-Zone Warnung

**Ein Pilot braucht:**
- Heißeste SYSTEME (nicht Regionen)
- Capital/Supercapital Highlights
- High-Value Targets
- Zeitliche Activity
- Security Status
- Actionable Intelligence

---

## Neue Struktur

### **Hauptübersicht** (sofort sichtbar):

1. **🔥 HOT ZONES** - Top 10 heißeste Systeme
   - System Name + Region (in Klammern)
   - Security Status (farbcodiert)
   - Kills + ISK destroyed
   - Dominant Ship Type
   - Special Flags (Gate Camp, Gank Zone, Capital Fight)

2. **💀 CAPITAL CARNAGE** - Zusammenfassung
   - Titans destroyed + total ISK
   - Supercarriers destroyed + total ISK
   - Carriers destroyed + total ISK
   - Dreadnoughts destroyed + total ISK

3. **💰 HIGH-VALUE KILLS** - Top 10 teuerste Einzelkills
   - ISK Value
   - Ship Type + Name
   - System (mit Sec Status)
   - Ob Gank (HighSec kill)

4. **🚨 DANGER ZONES** - Wo Industrials sterben
   - System
   - Industrials/Freighters killed
   - Total Value
   - Warning Level

5. **📊 SHIP META** - Was fliegt?
   - Ship Type Categories (Capital/BS/Cruiser/etc)
   - Anzahl + ISK
   - Bar Chart Visualization

6. **⏰ ACTIVITY TIMELINE** - Wann ist Action?
   - Stündliche Verteilung
   - Peak Time Indicator

### **Details** (aufklappbar):

**Pro SECURITY-ZONE:**
- NullSec (0.0 and below)
- LowSec (0.1-0.4)
- HighSec (0.5-1.0)

Dann Systeme innerhalb gruppiert, jeweils mit:
- System Info (Name, Sec, Region, Const)
- Activity (Kills, ISK, Ships)
- Top Kills in diesem System

---

## Backend Änderungen

### Neue Datenfelder benötigt:

```python
{
  "period": "24h",
  "global": {
    "total_kills": 1401,
    "total_isk_destroyed": 258706880284.28,
    "peak_hour_utc": 14,  # NEW
    "peak_kills_per_hour": 156  # NEW
  },

  # NEW: Top Systems (global, nicht pro Region)
  "hot_zones": [
    {
      "system_id": 30002048,
      "system_name": "Bei",
      "region_name": "Metropolis",
      "constellation_name": "Brybier",  # NEW
      "security_status": 0.4,  # NEW
      "kills": 39,
      "total_isk_destroyed": 12345678900,
      "dominant_ship_type": "Cruiser",  # NEW
      "flags": ["gate_camp"],  # NEW: special indicators
      "top_ships": [...]  # Ships destroyed here
    }
  ],

  # NEW: Capital Kills Summary
  "capital_kills": {
    "titans": {
      "count": 3,
      "total_isk": 892000000000,
      "kills": [  # Individual kills
        {
          "killmail_id": 123456,
          "ship_name": "Erebus",
          "victim": "Player Name",
          "isk_destroyed": 89200000000,
          "system_name": "M2-XFE",
          "security": 0.0
        }
      ]
    },
    "supercarriers": {...},
    "carriers": {...},
    "dreadnoughts": {...},
    "force_auxiliaries": {...}
  },

  # NEW: High-Value Individual Kills (Top 20)
  "high_value_kills": [
    {
      "rank": 1,
      "killmail_id": 123456,
      "isk_destroyed": 89200000000,
      "ship_type": "Titan",
      "ship_name": "Erebus",
      "victim": "Player Name",
      "system_id": 30001001,
      "system_name": "M2-XFE",
      "region_name": "Delve",
      "security_status": 0.0,
      "is_gank": false,  # True if HighSec kill
      "time_utc": "2026-01-06T14:23:15Z"
    }
  ],

  # NEW: Danger Zones (where industrials die)
  "danger_zones": [
    {
      "system_name": "Uedama",
      "region_name": "The Forge",
      "security_status": 0.5,
      "industrials_killed": 34,
      "freighters_killed": 12,
      "total_value": 45200000000,
      "warning_level": "EXTREME"  # EXTREME/HIGH/MODERATE
    }
  ],

  # NEW: Ship Type Breakdown
  "ship_breakdown": {
    "capitals": {
      "count": 67,
      "total_isk": 892000000000
    },
    "battleships": {...},
    "cruisers": {...},
    "frigates": {...}
    # ... etc
  },

  # NEW: Hourly Activity
  "timeline": [
    {
      "hour_utc": 0,
      "kills": 45,
      "isk_destroyed": 12345678900
    },
    # ... 24 hours
  ],

  # Existing: Regions (jetzt als Detail-View)
  "regions": [...]
}
```

### Backend Implementation:

**File: `services/zkillboard/zkill_live_service.py`**

Erweitern mit:
1. `get_security_status(system_id)` - aus mapSolarSystems DB
2. `get_constellation_name(system_id)` - aus DB
3. `extract_capital_kills(killmails)` - Filter Capitals
4. `calculate_hourly_timeline(killmails)` - Group by hour
5. `identify_danger_zones(killmails)` - Find industrial gank zones
6. `categorize_ships(killmails)` - Group by ship category

---

## Frontend Redesign

### Hauptübersicht:

```typescript
<div>
  {/* Hero Stats */}
  <div className="hero-stats">
    <StatCard icon="🔥" label="Total Kills" value={report.global.total_kills} />
    <StatCard icon="💰" label="ISK Destroyed" value={formatISK(report.global.total_isk_destroyed)} />
    <StatCard icon="⏰" label="Peak Hour" value={`${report.global.peak_hour_utc}:00 UTC`} />
  </div>

  {/* HOT ZONES */}
  <HotZonesTable zones={report.hot_zones} />

  {/* CAPITAL CARNAGE */}
  <CapitalKillsSummary capitals={report.capital_kills} />

  {/* HIGH-VALUE KILLS */}
  <HighValueKillsTable kills={report.high_value_kills} />

  {/* DANGER ZONES */}
  <DangerZonesAlert zones={report.danger_zones} />

  {/* SHIP META */}
  <ShipBreakdownChart breakdown={report.ship_breakdown} />

  {/* TIMELINE */}
  <ActivityTimeline timeline={report.timeline} />

  {/* DETAILS (collapsible by security zone) */}
  <SecurityZoneDetails
    nullsec={filterBySec(report.hot_zones, 0, 0)}
    lowsec={filterBySec(report.hot_zones, 0.1, 0.4)}
    highsec={filterBySec(report.hot_zones, 0.5, 1.0)}
  />
</div>
```

### Komponenten:

1. **HotZonesTable.tsx** - Top Systems Tabelle
2. **CapitalKillsSummary.tsx** - Capital Kills Cards
3. **HighValueKillsTable.tsx** - Top Kills Liste
4. **DangerZonesAlert.tsx** - Warning Cards
5. **ShipBreakdownChart.tsx** - Bar Chart
6. **ActivityTimeline.tsx** - Hourly Activity Chart

---

## Security Status Farbcodierung

```typescript
function getSecColor(sec: number): string {
  if (sec >= 1.0) return '#2FEFEF'; // Bright cyan (1.0)
  if (sec >= 0.9) return '#48F0C0'; // ...
  if (sec >= 0.8) return '#00EF47';
  if (sec >= 0.7) return '#00F000';
  if (sec >= 0.6) return '#8FEF2F';
  if (sec >= 0.5) return '#EFEF00'; // Yellow (0.5)
  if (sec >= 0.4) return '#D77700';
  if (sec >= 0.3) return '#F06000';
  if (sec >= 0.1) return '#F04800'; // Orange/Red
  return '#F00000'; // Red (0.0 and below)
}
```

---

## Implementation Steps

### Phase 1: Backend Data Collection
1. Add security_status lookup from mapSolarSystems
2. Add constellation_name lookup
3. Implement capital kills extraction
4. Implement high-value kills extraction
5. Implement danger zones identification
6. Implement ship categorization
7. Implement hourly timeline
8. Create new endpoint structure

### Phase 2: Frontend Redesign
1. Create new component structure
2. Implement HotZonesTable
3. Implement CapitalKillsSummary
4. Implement HighValueKillsTable
5. Implement DangerZonesAlert
6. Implement ShipBreakdownChart
7. Implement ActivityTimeline
8. Wire everything together

### Phase 3: Testing
1. Verify data accuracy
2. Test with real killmail data
3. Performance optimization
4. Mobile responsiveness

---

## Notes

**Wichtig:**
- Alle ISK-Werte in Milliarden (B) oder Millionen (M) formatieren
- Security Status mit EVE-Standard Farben
- Timestamps in UTC
- Gank Detection: Kills in HighSec (>=0.5) mit hohem Wert
- Capital Definition: Titans, Supers, Carriers, Dreads, FAX

**Ship Categories:**
- Capitals: Titan, Supercarrier, Carrier, Dreadnought, FAX
- Subcapitals: BS, BC, Cruiser, Destroyer, Frigate
- Industrials: Freighter, Jump Freighter, Industrial, Mining Barge, Exhumer
- Pods: Capsule

**Future Enhancements:**
- Killmail Links zu zKillboard
- System Links zu DotLan
- Alliance/Corp involvement
- Doctrine Detection (coordinated ship types)
