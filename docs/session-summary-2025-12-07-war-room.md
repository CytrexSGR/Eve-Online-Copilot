# Session-Zusammenfassung: War Room Implementation

**Datum:** 2025-12-07

## Was wurde gebaut

### 1. War Room Feature (Komplett neu)
Ein vollständiges Combat-Analyse-System für EVE Online, das Kampfdaten nutzt um Produktions- und Trading-Möglichkeiten zu identifizieren.

#### Backend Services
| Datei | Funktion |
|-------|----------|
| `killmail_service.py` | Downloads EVE Ref Killmail-Archive, aggregiert Verluste |
| `sovereignty_service.py` | Trackt Sov-Campaigns von ESI |
| `fw_service.py` | Trackt Faction Warfare Hotspots |
| `war_analyzer.py` | Kombiniert Daten für Demand-Analyse, Doctrines, Heatmaps |

#### API Endpoints (`routers/war.py`)
```
GET /api/war/losses/{region_id}      - Kampfverluste
GET /api/war/demand/{region_id}      - Demand-Analyse mit Market Gaps
GET /api/war/heatmap                 - Galaxy Heatmap-Daten
GET /api/war/campaigns               - Sov Timer/Battles
GET /api/war/fw/hotspots             - FW Hotspots
GET /api/war/doctrines/{region_id}   - Doctrine Detection
GET /api/war/conflicts               - Alliance Conflicts
GET /api/war/route/safe/{from}/{to}  - Route mit Danger Scores
GET /api/war/item/{type_id}/stats    - Combat Stats für einzelnes Item (NEU)
```

#### Datenbank-Tabellen (Migration `003_war_room.sql`)
- `system_region_map` - System→Region Mapping (8437 Systeme)
- `combat_ship_losses` - Schiffsverluste pro Tag/Region/System
- `combat_item_losses` - Item/Modul-Verluste
- `alliance_conflicts` - Allianz-Konflikte
- `sovereignty_campaigns` - Sov Timer
- `fw_system_status` - Faction Warfare Status

#### Cron Jobs
| Job | Schedule | Datei |
|-----|----------|-------|
| Sovereignty Tracker | */30 * * * * | `jobs/cron_sov_tracker.sh` |
| FW Tracker | */30 * * * * | `jobs/cron_fw_tracker.sh` |
| Killmail Fetcher | 0 6 * * * | `jobs/cron_killmail_fetcher.sh` |

#### Config (`config.py` Erweiterungen)
```python
WAR_DATA_RETENTION_DAYS = 30
WAR_DOCTRINE_MIN_FLEET_SIZE = 10
WAR_HEATMAP_MIN_KILLS = 5
WAR_EVEREF_BASE_URL = "https://data.everef.net/killmails"
```

---

### 2. War Room Integration (Heute implementiert)
Verbindung zwischen War Room und bestehenden Modulen.

#### Neue Frontend-Komponenten
| Datei | Funktion |
|-------|----------|
| `components/CollapsiblePanel.tsx` | Wiederverwendbares ausklappbares Panel |
| `components/CombatStatsPanel.tsx` | Zeigt Combat-Daten für ein Item |
| `components/ConflictAlert.tsx` | Warnung für gefährliche Routen |

#### Geänderte Frontend-Dateien
| Datei | Änderung |
|-------|----------|
| `pages/WarRoom.tsx` | Alle Items klickbar → `/item/{type_id}` |
| `pages/ItemDetail.tsx` | Komplett neu mit 4 Collapsible Panels |
| `api.ts` | `getItemCombatStats()` Funktion hinzugefügt |
| `App.tsx` | War Room Route + Navigation |

#### ItemDetail Page Struktur (Neu)
```
▼ Overview      - Icon, Name, Gruppe, "Add to List" Button
▼ Combat Stats  - Destroyed (7d), Regional Breakdown, Market Gaps
▼ Production    - Materials, Kosten pro Region, Profit
▼ Market Prices - Regionale Preise, Best Buy/Sell
```

---

## Datenstand

| Datenquelle | Status |
|-------------|--------|
| Killmails (2025-12-06) | ~13k Kills geladen |
| Sov Campaigns | 30 aktive Timer |
| FW Systems | 160 Systeme, 7 Hotspots |

---

## Dokumentation

| Datei | Inhalt |
|-------|--------|
| `docs/plans/2025-12-07-war-room-design.md` | Design-Entscheidungen aus Brainstorming |
| `docs/plans/2025-12-07-war-room-implementation.md` | Original Implementation Plan (9 Work Packages) |
| `docs/plans/2025-12-07-war-room-integration-design.md` | Integration Design |
| `docs/plans/2025-12-07-war-room-integration.md` | Integration Implementation Plan (7 Tasks) |

---

## Wie weitermachen

### Backend starten
```bash
cd /home/cytrex/eve_copilot
/home/cytrex/.local/bin/uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### Frontend starten
```bash
cd /home/cytrex/eve_copilot/frontend
npm run dev -- --host 0.0.0.0
```

### Killmail-Daten nachladen
```bash
# Letzte 7 Tage backfillen
python3 -m jobs.killmail_fetcher --backfill 7 --verbose

# Bestimmtes Datum
python3 -m jobs.killmail_fetcher --date 2025-12-05 --verbose
```

### Testen
1. http://192.168.178.108:3000/war-room öffnen
2. Auf ein Schiff klicken (z.B. "Tornado")
3. Item Detail mit Combat Stats sehen
4. "Add to List" → Shopping Flow

---

## Offene Ideen (nicht implementiert)

- **Route Safety in Shopping** - ConflictAlert bei Routenplanung anzeigen
- **War Opportunities Scan** - Dedizierter Button im Scanner für Combat-Demand
- **Alliance Watchlist** - Bestimmte Allianzen tracken
- **2D Galaxy Map** - Visuelle Heatmap statt Tabelle
- **Production Timing Warnings** - "Schlacht in 4h, jetzt produzieren"

---

## Technische Details

### EVE Image Server (für Item Icons)
```
https://images.evetech.net/types/{type_id}/icon?size=64
https://images.evetech.net/types/{type_id}/render?size=128
```
Keine API-Calls nötig, direktes CDN, Browser cached automatisch.

### EVE Ref Killmail Bulk Data
```
https://data.everef.net/killmails/YYYY/killmails-YYYY-MM-DD.tar.bz2
```
~50-100MB pro Tag, enthält vollständige Killmail-JSON mit allen Items.

---

## Projektstruktur (aktualisiert)

```
/home/cytrex/eve_copilot/
├── main.py                          # FastAPI App
├── config.py                        # Config inkl. WAR_* Settings
├── database.py                      # PostgreSQL Connection
│
├── # War Room Services
├── killmail_service.py              # EVE Ref Killmail Processing
├── sovereignty_service.py           # ESI Sov Campaigns
├── fw_service.py                    # ESI Faction Warfare
├── war_analyzer.py                  # Demand Analysis, Doctrines
├── route_service.py                 # Routing + Danger Scores
│
├── routers/
│   ├── war.py                       # War Room API Endpoints
│   ├── shopping.py                  # Shopping Lists
│   ├── hunter.py                    # Market Scanner
│   └── ...
│
├── jobs/
│   ├── killmail_fetcher.py          # Daily Killmail Download
│   ├── sov_tracker.py               # Sov Campaign Updates
│   ├── fw_tracker.py                # FW Status Updates
│   ├── cron_killmail_fetcher.sh
│   ├── cron_sov_tracker.sh
│   └── cron_fw_tracker.sh
│
├── migrations/
│   └── 003_war_room.sql             # War Room DB Schema
│
├── frontend/src/
│   ├── pages/
│   │   ├── WarRoom.tsx              # War Room Dashboard
│   │   ├── ItemDetail.tsx           # Item Detail (4 Panels)
│   │   └── ...
│   ├── components/
│   │   ├── CollapsiblePanel.tsx     # Reusable Panel
│   │   ├── CombatStatsPanel.tsx     # Combat Stats Display
│   │   ├── ConflictAlert.tsx        # Route Danger Warning
│   │   └── ...
│   └── api.ts                       # API Functions
│
└── docs/
    ├── plans/
    │   ├── 2025-12-07-war-room-design.md
    │   ├── 2025-12-07-war-room-implementation.md
    │   ├── 2025-12-07-war-room-integration-design.md
    │   └── 2025-12-07-war-room-integration.md
    └── session-summary-2025-12-07-war-room.md  # Diese Datei
```
