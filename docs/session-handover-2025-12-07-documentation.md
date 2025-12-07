# Session Handover: Documentation & Refactoring Initiative

**Datum:** 2025-12-07
**Vorherige Session:** session-summary-2025-12-07-war-room.md

---

## Kontext

Der User hat entschieden, das Projekt an diesem Punkt professionell aufzuräumen, bevor es komplexer wird. Die Anwendung soll:
1. Aufgeräumt und refactored werden
2. In Docker gebracht werden
3. Vollständig dokumentiert werden
4. Git-Version Control erhalten

---

## Was wurde in dieser Session gemacht

### Neue Dokumentation erstellt

| Datei | Inhalt |
|-------|--------|
| `CLAUDE.md` | Haupt-Entwicklungsguide mit Projekt-Übersicht, Quick Start, Credentials |
| `ARCHITECTURE.md` | System-Architektur, Komponenten, Datenflüsse, Diagramme |
| `CLAUDE.backend.md` | Backend-Patterns, Database, ESI Client, API Patterns, Cron Jobs |
| `CLAUDE.frontend.md` | Frontend-Patterns, React/TypeScript, TanStack Query, Vite |

Die Dokumentation folgt dem professionellen Muster aus `/home/cytrex/Userdocs/CLAUDE*.md` mit:
- Klarer Struktur und Navigation
- Quick Reference Tabellen
- Code-Beispiele
- Troubleshooting Sections
- Critical Patterns (Anti-Patterns vermeiden)

---

## Nächste Schritte (noch nicht gemacht)

### 1. Git Repository initialisieren

```bash
cd /home/cytrex/eve_copilot
git init
git add .
git commit -m "Initial commit: EVE Co-Pilot with War Room feature"
```

**Erstelle `.gitignore`:**
```
__pycache__/
*.pyc
*.pyo
.env
tokens.json
logs/
node_modules/
dist/
.vite/
*.log
```

### 2. Docker-Containerisierung

**Geplante Struktur:**
```
eve_copilot/
├── docker-compose.yml
├── Dockerfile              # Backend
├── frontend/
│   └── Dockerfile          # Frontend
```

**docker-compose.yml (zu erstellen):**
```yaml
version: '3.8'

services:
  backend:
    build: .
    ports:
      - "8000:8000"
    depends_on:
      - db
    volumes:
      - ./:/app
      - ./tokens.json:/app/tokens.json
    environment:
      - DATABASE_URL=postgresql://eve:EvE_Pr0ject_2024@db:5432/eve_sde

  frontend:
    build: ./frontend
    ports:
      - "5173:5173"
    depends_on:
      - backend

  db:
    image: postgres:16
    environment:
      POSTGRES_DB: eve_sde
      POSTGRES_USER: eve
      POSTGRES_PASSWORD: EvE_Pr0ject_2024
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./eve_sde_dump.sql:/docker-entrypoint-initdb.d/init.sql

volumes:
  postgres_data:
```

### 3. Code Refactoring

**Identifizierte Bereiche:**
1. `main.py` ist zu groß - Bookmark-Endpoints in eigenen Router verschieben
2. `services.py` enthält Legacy-Code - aufräumen oder in spezialisierte Services aufteilen
3. Frontend TypeScript Interfaces vervollständigen (aktuell teilweise `any`)
4. Einheitliche Error-Handling Patterns durchsetzen

### 4. Testing Setup

```bash
# Backend Tests
pip install pytest pytest-asyncio httpx
mkdir tests/
# Tests für jeden Service schreiben

# Frontend Tests
cd frontend
npm install -D vitest @testing-library/react
```

---

## Aktueller Projektstand

### Backend Services (funktionsfähig)

| Service | Status | Datei |
|---------|--------|-------|
| Auth/SSO | ✅ Funktioniert | `auth.py` |
| Character API | ✅ Funktioniert | `character.py` |
| ESI Client | ✅ Funktioniert | `esi_client.py` |
| Market Service | ✅ Funktioniert | `market_service.py` |
| Production Simulator | ✅ Funktioniert | `production_simulator.py` |
| Shopping Service | ✅ Funktioniert | `shopping_service.py` |
| Bookmark Service | ✅ Funktioniert | `bookmark_service.py` |
| Route Service | ✅ Funktioniert | `route_service.py` |
| Cargo Service | ✅ Funktioniert | `cargo_service.py` |
| War Room Services | ✅ Funktioniert | `killmail_service.py`, `war_analyzer.py`, etc. |

### Frontend Pages (funktionsfähig)

| Page | Status | Datei |
|------|--------|-------|
| Market Scanner | ✅ Funktioniert | `MarketScanner.tsx` |
| Arbitrage Finder | ✅ Funktioniert | `ArbitrageFinder.tsx` |
| Production Planner | ✅ Funktioniert | `ProductionPlanner.tsx` |
| Shopping Planner | ✅ Funktioniert | `ShoppingPlanner.tsx` |
| Bookmarks | ✅ Funktioniert | `Bookmarks.tsx` |
| Materials Overview | ✅ Funktioniert | `MaterialsOverview.tsx` |
| Item Detail | ✅ Funktioniert | `ItemDetail.tsx` |
| War Room | ✅ Funktioniert | `WarRoom.tsx` |

### Cron Jobs (aktiv)

| Job | Schedule | Status |
|-----|----------|--------|
| batch_calculator | */5 min | ✅ Aktiv |
| regional_price_fetcher | */30 min | ✅ Aktiv |
| market_hunter | */5 min | ✅ Aktiv |
| sov_tracker | */30 min | ✅ Aktiv |
| fw_tracker | */30 min | ✅ Aktiv |
| killmail_fetcher | Daily 06:00 | ✅ Aktiv |

### Datenbank-Tabellen

**EVE SDE (statisch):** `invTypes`, `invGroups`, `industryActivityMaterials`, `mapSolarSystems`, etc.

**App-Tabellen (dynamisch):**
- `market_prices` - Regionale Preise
- `manufacturing_opportunities` - Berechnete Gelegenheiten
- `shopping_lists` / `shopping_list_items` - Shopping Listen
- `bookmarks` / `bookmark_lists` - Lesezeichen
- `system_region_map` - System-Region Mapping (8437 Systeme)
- `combat_ship_losses` / `combat_item_losses` - Kampfdaten
- `sovereignty_campaigns` - Sov Timer
- `fw_system_status` - FW Status

---

## Offene Features (aus War Room Session)

1. **Route Safety in Shopping** - ConflictAlert bei Routenplanung
2. **War Opportunities Scan** - Dedizierter Button für Combat-Demand
3. **Alliance Watchlist** - Bestimmte Allianzen tracken
4. **2D Galaxy Map** - Visuelle Heatmap
5. **Production Timing Warnings** - "Schlacht in 4h, jetzt produzieren"

---

## Wie weitermachen

### Option A: Docker zuerst
1. `.gitignore` erstellen
2. Git initialisieren
3. `Dockerfile` für Backend schreiben
4. `docker-compose.yml` erstellen
5. EVE SDE Dump für DB-Init vorbereiten
6. Testen

### Option B: Refactoring zuerst
1. Bookmark-Endpoints aus `main.py` in `routers/bookmarks.py` verschieben
2. `services.py` aufräumen
3. TypeScript Interfaces vervollständigen
4. Tests schreiben
5. Dann Docker

### Option C: Git zuerst
1. `.gitignore` erstellen
2. `git init`
3. Initial commit
4. Feature branches für Refactoring nutzen

**Empfehlung:** Option C zuerst (Git), dann Option B (Refactoring), dann Option A (Docker)

---

## Befehle zum Starten

```bash
# Backend
cd /home/cytrex/eve_copilot
/home/cytrex/.local/bin/uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# Frontend
cd /home/cytrex/eve_copilot/frontend
npm run dev -- --host 0.0.0.0

# Database (falls nicht läuft)
echo 'Aug2012#' | sudo -S docker start eve_db
```

---

**Erstellt:** 2025-12-07
**Für:** Nächste Claude Code Session
