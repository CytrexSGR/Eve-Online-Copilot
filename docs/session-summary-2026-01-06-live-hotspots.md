# Session Summary: Live Combat Hotspots Integration - 2026-01-06

## Ziel der Session
Integration von Telegram-Combat-Hotspots als Live-Layer auf der 3D Galaxy Map in Echtzeit.

## Was implementiert wurde ✅

### Backend (Python/FastAPI)

1. **Redis Persistence für Live-Hotspots** (`services/zkillboard/live_service.py`)
   - Live-Hotspots werden beim Detection automatisch in Redis gespeichert
   - Key-Format: `live_hotspot:{system_id}`
   - TTL: 300 Sekunden (5 Minuten)
   - Datenstruktur:
     ```python
     {
       "system_id": int,
       "region_id": int,
       "kill_count": int,
       "timestamp": float,
       "latest_ship": int,
       "latest_value": float,
       "system_name": str,
       "danger_level": "LOW|MEDIUM|HIGH",
       "age_seconds": int
     }
     ```

2. **API Endpoint** (`routers/war.py`)
   - `GET /api/war/live-hotspots` - Liefert alle aktiven Hotspots (<5 Min)
   - Berechnet `age_seconds` für Frontend-Coloring
   - Scannt Redis für `live_hotspot:*` Keys
   - **FUNKTIONIERT:** 11 Hotspots aktuell in Redis

3. **Pilot Intelligence Endpoint** (`routers/war.py`)
   - `GET /api/war/pilot-intelligence` - Vollständiger Battle Report
   - Ersetzt fehlenden `/api/reports/battle-24h` Endpoint
   - Liefert alle 4 Combat Layers:
     - Hot Zones (high activity)
     - Capital Kills (Titans, Supercarriers, etc.)
     - High-Value Kills (100M+ ISK)
     - Danger Zones (industrial losses)
   - Cache: 10 Minuten (Redis)
   - Performance: 12s initial, 0.010s cached

### Frontend (React/TypeScript)

1. **BattleMapPreview Component** (`public-frontend/src/components/BattleMapPreview.tsx`)
   - Live-Hotspots Polling alle 10 Sekunden
   - Priority 0 Rendering (höchste Priorität)
   - Age-based Coloring:
     - <1 min: Pulsierendes Weiß (#ffffff, size 7.0)
     - 1-3 min: Helles Gelb (#ffff00, size 6.0)
     - 3-5 min: Orange (#ff9900, size 5.0)
   - Skip-Protection: Andere Layer überschreiben Live-Hotspots nicht
   - Info-Badge zeigt "⚡ X LIVE hotspots"

2. **Battle Map Page** (`public-frontend/src/pages/BattleMap.tsx`)
   - Live-Hotspots Filter in Sidebar (Position 1, höchste Priorität)
   - Checkbox mit pulsierendem weißen Icon
   - Default: Aktiviert
   - Counter: "X active" (statt "systems")
   - Identische Polling- und Rendering-Logik wie Preview

3. **Homepage Integration** (`public-frontend/src/pages/Home.tsx`)
   - 3D-Map zwischen Battle Report und War Profiteering
   - Legende mit "LIVE Hotspots ⚡" (erste Position)
   - Pulsierendes Icon mit Glow-Effekt
   - Zeigt alle 5 Layer gleichzeitig

4. **CSS Animation** (`public-frontend/src/index.css`)
   - Pulse Keyframe Animation (2s ease-in-out infinite)
   - Opacity: 1 → 0.6 → 1
   - Scale: 1 → 1.2 → 1

5. **API Integration** (`public-frontend/src/services/api.ts`)
   - Umstellung von `/api/reports/battle-24h` → `/api/war/pilot-intelligence`
   - Relative URLs für Vite-Proxy-Kompatibilität

6. **Vite Configuration** (`public-frontend/vite.config.ts`)
   - Proxy-Target korrigiert: Port 8001 → 8000
   - Ermöglicht CORS-freie API-Calls in Development

## Commits (GitHub)

Alle Änderungen committed und gepusht zu `main`:

1. `fb9d080` - feat: Add real-time live combat hotspots to 3D galaxy map
2. `03b92eb` - feat: Add live hotspots filter to Battle Map page
3. `8595eda` - fix: Use relative API URLs for live hotspots and correct Vite proxy
4. `fdfa56b` - feat: Add /api/war/pilot-intelligence endpoint for battle map data

**Repository:** https://github.com/CytrexSGR/Eve-Online-Copilot

## Architektur

### Datenfluss: Detection → Telegram → Redis → Frontend

```
┌─────────────────────────────────────────────────────────────┐
│ 1. zKillboard API (Live Feed)                              │
│    ↓ Polling alle 10 Sekunden                              │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ 2. Hotspot Detection (live_service.py)                     │
│    - 5+ kills in 300 Sekunden = Hotspot                    │
│    - Cooldown: 600 Sekunden zwischen Alerts                │
└─────────────────────────────────────────────────────────────┘
                          ↓
                    ┌─────┴─────┐
                    ↓           ↓
┌───────────────────────┐  ┌────────────────────────────────┐
│ 3a. TELEGRAM ALERT    │  │ 3b. REDIS STORAGE              │
│     telegram_service  │  │     Key: live_hotspot:{sys_id} │
│     Channel: alerts   │  │     TTL: 300 seconds           │
└───────────────────────┘  └────────────────────────────────┘
                                      ↓
                          ┌───────────────────────────────────┐
                          │ 4. API Endpoint                   │
                          │    /api/war/live-hotspots         │
                          │    Scans Redis, calc age_seconds  │
                          └───────────────────────────────────┘
                                      ↓
                          ┌───────────────────────────────────┐
                          │ 5. FRONTEND POLLING               │
                          │    fetch() alle 10 Sekunden       │
                          │    BattleMapPreview + BattleMap   │
                          └───────────────────────────────────┘
                                      ↓
                          ┌───────────────────────────────────┐
                          │ 6. 3D MAP RENDERING               │
                          │    Age-based colors, Priority 0   │
                          │    Pulsing white → yellow → orange│
                          └───────────────────────────────────┘
```

### Visual Priority System

```
Priority 0: ⚡ LIVE Hotspots (weiß pulsierend, size 7.0) ← HIGHEST
Priority 1: 🟣 Capital Kills (lila #d946ef, size 5.0)
Priority 2: 🔴 Hot Zones (rot/orange, size 4.5/3.5)
Priority 3: 🔵 High-Value Kills (cyan #00ffff, size 4.0)
Priority 4: 🟡 Danger Zones (gelb #ffaa00, size 3.5)
```

### Anzeigedauer Live-Hotspots

| Alter | Farbe | Size | Effekt |
|-------|-------|------|--------|
| 0-60s | Weiß #ffffff | 7.0 | Pulsierend |
| 60-180s | Gelb #ffff00 | 6.0 | Statisch |
| 180-300s | Orange #ff9900 | 5.0 | Verblassend |
| >300s | - | - | Verschwunden (Redis TTL) |

## Aktueller Status

### ✅ Was funktioniert

1. **Backend:**
   - ✅ Hotspot Detection läuft (zkill_live_listener)
   - ✅ Redis speichert Live-Hotspots (11 aktuelle Keys)
   - ✅ API `/api/war/live-hotspots` liefert Daten
   - ✅ API `/api/war/pilot-intelligence` liefert Battle Report
   - ✅ Telegram Alerts werden gesendet

2. **Frontend Build:**
   - ✅ Vite Dev Server läuft (Port 5173)
   - ✅ Hot Module Reload funktioniert
   - ✅ Proxy auf Port 8000 konfiguriert
   - ✅ Alle Components kompilieren ohne Fehler

### ❌ Was NICHT funktioniert

1. **Frontend zeigt "0 active" Live-Hotspots**
   - API liefert korrekt 11 Hotspots
   - Polling scheint nicht zu funktionieren ODER
   - Rendering schlägt fehl ODER
   - Frontend erreicht API nicht

2. **Mögliche Ursachen:**
   - Browser-Cache (Hard-Refresh nötig?)
   - CORS-Problem trotz Proxy?
   - API-URL falsch (obwohl jetzt relativ)?
   - React State-Update Problem?
   - useEffect Dependencies falsch?

## Debugging-Schritte für nächste Session

### 1. Frontend-Debugging

**Browser Console checken:**
```javascript
// Sollte sichtbar sein:
[BattleMapPreview] Loaded X live hotspots
[BattleMap] Loaded X live hotspots

// Oder Fehler:
Failed to fetch live hotspots: ...
```

**Network Tab checken:**
- Request zu `/api/war/live-hotspots` vorhanden?
- Status Code? (sollte 200 sein)
- Response Body? (sollte JSON mit hotspots array sein)

**React DevTools:**
- State von `liveHotspots` in BattleMapPreview
- State von `liveHotspots` in BattleMap
- Ist Array leer oder gefüllt?

### 2. API-Endpoint manuell testen

```bash
# Vom Server (sollte funktionieren):
curl http://localhost:8000/api/war/live-hotspots

# Über Vite-Proxy (sollte auch funktionieren):
curl http://localhost:5173/api/war/live-hotspots

# Von anderem Gerät im Netzwerk:
curl http://192.168.178.108:5173/api/war/live-hotspots
```

### 3. Hard-Coded Test

Temporär in `BattleMapPreview.tsx` einfügen:
```typescript
useEffect(() => {
  // TEST: Hard-code some hotspots
  setLiveHotspots([
    { system_id: 30002187, age_seconds: 30, danger_level: "HIGH" },
    { system_id: 30001000, age_seconds: 120, danger_level: "MEDIUM" }
  ]);
}, []);
```

Wenn die dann sichtbar sind → API-Problem
Wenn nicht → Rendering-Problem

### 4. Console.log Debugging

In `BattleMapPreview.tsx` hinzufügen:
```typescript
useEffect(() => {
  console.log('[DEBUG] liveHotspots changed:', liveHotspots);
}, [liveHotspots]);

useEffect(() => {
  console.log('[DEBUG] systemRenderConfigs:', systemRenderConfigs);
}, [systemRenderConfigs]);
```

### 5. Vite-Proxy testen

```bash
# Im Terminal:
curl -v http://localhost:5173/api/war/live-hotspots 2>&1 | grep -i "proxy\|location\|host"
```

Sollte zeigen: `X-Forwarded-For: localhost:8000` oder ähnlich

## Nächste Schritte (Priorität)

1. **HÖCHSTE PRIORITÄT:** Frontend-Console-Logs überprüfen
   - Wird API aufgerufen?
   - Kommen Daten an?
   - Gibt es JavaScript-Fehler?

2. **Browser Hard-Refresh erzwingen**
   - Strg+Shift+R (Chrome/Firefox)
   - Cache komplett leeren
   - Eventuell Incognito-Mode testen

3. **Falls immer noch nichts:**
   - Production Build testen: `npm run build && npm run preview`
   - Backend neu starten (falls Routing-Table nicht aktualisiert)
   - Frontend neu starten (falls HMR das Update nicht mitbekommen hat)

4. **Falls API nicht erreichbar:**
   - Prüfen ob CORS-Headers fehlen
   - Prüfen ob Vite-Proxy wirklich auf 8000 zeigt
   - `/api/war/pilot-intelligence` funktioniert, warum `/live-hotspots` nicht?

## Technische Hinweise

### Backend läuft auf:
- **Port:** 8000
- **Process:** Screen session "backend"
- **Command:** `uvicorn main:app --host 0.0.0.0 --port 8000 --reload`
- **Check:** `ps aux | grep uvicorn`

### Frontend läuft auf:
- **Port:** 5173
- **Process:** Background Task ID: be8791a
- **Command:** `npm run dev` (in screen session)
- **Check:** `curl http://localhost:5173`

### zkillboard Listener läuft auf:
- **Process:** Screen session "zkill"
- **Command:** `python3 -m jobs.zkill_live_listener --verbose`
- **Log:** `/tmp/zkill_telegram.log` (alt) oder `/tmp/zkill_live.log` (neu)
- **Check:** `ps aux | grep zkill_live_listener`

### Redis:
- **Container:** `redis` (Docker)
- **Port:** 6379
- **Check Keys:** `sudo docker exec redis redis-cli --scan --pattern "live_hotspot:*"`
- **Check Value:** `sudo docker exec redis redis-cli GET "live_hotspot:30002539"`

## Wichtige Dateien

### Backend
- `routers/war.py` - Endpoint `/api/war/live-hotspots` (Zeile 661)
- `routers/war.py` - Endpoint `/api/war/pilot-intelligence` (Zeile 613)
- `services/zkillboard/live_service.py` - Redis-Storage (Zeile 866-879)
- `services/zkillboard/reports_service.py` - Pilot Intelligence Report

### Frontend
- `public-frontend/src/components/BattleMapPreview.tsx` - Preview Component
- `public-frontend/src/pages/BattleMap.tsx` - Full Map Page
- `public-frontend/src/pages/Home.tsx` - Homepage mit Map
- `public-frontend/src/services/api.ts` - API Client
- `public-frontend/vite.config.ts` - Vite Proxy Config
- `public-frontend/src/index.css` - Pulse Animation

## Bekannte Issues

1. **Live-Hotspots zeigen "0 active"**
   - Backend liefert Daten ✅
   - Frontend zeigt sie NICHT ❌
   - Ursache: UNBEKANNT (siehe Debugging-Schritte)

2. **System Names zeigen "System 30002539" statt echte Namen**
   - `_get_system_name()` findet Namen nicht in DB
   - TODO: DB-Query debuggen oder Fallback zu eve-map-3d Namen

## Testing Commands

```bash
# Backend API testen
curl http://localhost:8000/api/war/live-hotspots | jq .

# Frontend über Proxy testen
curl http://localhost:5173/api/war/live-hotspots | jq .

# Redis Keys checken
sudo docker exec redis redis-cli KEYS "live_hotspot:*"

# Redis Wert anzeigen
sudo docker exec redis redis-cli GET "live_hotspot:30002187"

# Backend neu starten
screen -r backend
Ctrl+C
uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# Frontend neu starten
cd public-frontend
npm run dev
```

## Zusammenfassung

**Implementierung:** ✅ **Vollständig**
**Backend:** ✅ **Funktioniert**
**Frontend:** ⚠️ **Kompiliert, zeigt aber keine Daten**

**Nächste Session:** Frontend-Debugging, um herauszufinden warum Polling/Rendering nicht funktioniert.

---

**Session beendet:** 2026-01-06 21:30 UTC
**Alle Änderungen committed und gepusht:** ✅
**Branch:** main
**Letzter Commit:** fdfa56b
