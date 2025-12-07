# EVE Co-Pilot

Ein vollständiges Industrie- und Handelsanalyse-System für EVE Online mit FastAPI-Backend und React-Frontend.

## Features

### Backend (FastAPI)
- **Produktionskostenberechnung**: T1-Herstellungskosten mit ME/TE-Boni und Facility-Boni
- **Arbitrage-Finder**: Profitable Handelsmöglichkeiten zwischen Regionen
- **Market Hunter**: Automatische Suche nach profitablen T1-Produkten
- **Live-Marktdaten**: Echtzeit-Preise via ESI API mit Order-Depth-Analyse
- **Charakter-Management**: OAuth2-Authentifizierung für persönliche Daten
- **Corporation-Support**: Zugriff auf Corp-Wallets und Mitgliederlisten
- **Shopping-Listen**: Einkaufslisten mit Multi-Region-Preisvergleich
- **Routen-Berechnung**: A* Pathfinding für optimale Trade-Hub-Routen
- **Mining-Analyse**: Ore-Preise und Yield-Berechnungen

### Frontend (React + TypeScript)
- **Dashboard**: Übersicht über Wallets, Assets und Industrie-Jobs
- **Market Scanner**: Echtzeit-Marktanalyse mit Profit-Berechnung
- **Shopping Planner**: Multi-Region-Preisvergleich mit Routen-Optimierung
- **Production Planner**: Produktionsketten-Simulation
- **Materials Overview**: Materialklassifizierung und Kategorisierung
- **Arbitrage Finder**: Region-zu-Region Handelsanalyse
- **Bookmarks**: Gespeicherte Items und schneller Zugriff

## Projektstruktur

```
/home/cytrex/eve_copilot/
├── main.py                    # FastAPI Server & Haupt-Endpunkte
├── config.py                  # Konfiguration (DB, ESI, OAuth, Regions)
├── database.py                # PostgreSQL SDE-Abfragen
├── esi_client.py              # ESI API Client (Marktdaten)
├── auth.py                    # OAuth2 Authentifizierung
├── character.py               # Character & Corporation API
├── services.py                # Produktions-Business-Logik
├── market_service.py          # Markt-Analyse Services
├── shopping_service.py        # Shopping-Listen Verwaltung
├── route_service.py           # A* Routen-Berechnung
├── cargo_service.py           # Fracht-Optimierung
├── bookmark_service.py        # Lesezeichen-Verwaltung
├── notification_service.py    # Benachrichtigungen
├── material_classifier.py     # Material-Kategorisierung
├── production_simulator.py    # Produktions-Simulation
│
├── routers/
│   ├── shopping.py            # Shopping API Endpunkte
│   ├── hunter.py              # Market Hunter API
│   ├── mining.py              # Mining-Analyse API
│   └── mcp.py                 # MCP Integration
│
├── jobs/
│   ├── regional_price_fetcher.py  # Bulk-Preis-Fetcher (Cron)
│   ├── market_hunter.py           # Profit-Scanner
│   ├── batch_calculator.py        # Batch-Berechnungen
│   └── bulk_scanner.py            # Massen-Analyse
│
├── frontend/                  # React Frontend
│   ├── src/
│   │   ├── pages/
│   │   │   ├── ShoppingPlanner.tsx    # Multi-Region Shopping
│   │   │   ├── MarketScanner.tsx      # Markt-Analyse
│   │   │   ├── ProductionPlanner.tsx  # Produktions-Planung
│   │   │   ├── ArbitrageFinder.tsx    # Arbitrage-Suche
│   │   │   ├── MaterialsOverview.tsx  # Material-Übersicht
│   │   │   ├── ItemDetail.tsx         # Item-Details
│   │   │   └── Bookmarks.tsx          # Lesezeichen
│   │   ├── components/                # Wiederverwendbare Komponenten
│   │   ├── api.ts                     # API Client
│   │   └── utils/                     # Hilfsfunktionen
│   └── package.json
│
├── tokens.json                # Gespeicherte Auth-Tokens
└── auth_state.json            # OAuth State-Store
```

## Installation

### Voraussetzungen
- Python 3.11+
- Node.js 18+
- PostgreSQL 16 (Docker)
- EVE Developer Application

### Backend-Abhängigkeiten
```bash
pip3 install fastapi uvicorn psycopg2-binary requests --break-system-packages
```

### Frontend-Abhängigkeiten
```bash
cd /home/cytrex/eve_copilot/frontend
npm install
```

### Server starten

**Backend:**
```bash
cd /home/cytrex/eve_copilot
/home/cytrex/.local/bin/uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

**Frontend:**
```bash
cd /home/cytrex/eve_copilot/frontend
npm run dev
```

## API Endpunkte

### Authentifizierung
| Endpunkt | Methode | Beschreibung |
|----------|---------|--------------|
| `/api/auth/login` | GET | OAuth2-Flow starten |
| `/api/auth/callback` | GET | SSO Callback |
| `/api/auth/characters` | GET | Authentifizierte Charaktere |
| `/api/auth/scopes` | GET | Benötigte Scopes |

### Charakter
| Endpunkt | Methode | Beschreibung |
|----------|---------|--------------|
| `/api/character/{id}/wallet` | GET | Wallet-Balance |
| `/api/character/{id}/assets` | GET | Assets/Inventar |
| `/api/character/{id}/skills` | GET | Skill-Liste |
| `/api/character/{id}/orders` | GET | Markt-Orders |
| `/api/character/{id}/industry` | GET | Industrie-Jobs |
| `/api/character/{id}/blueprints` | GET | Blueprints |

### Corporation
| Endpunkt | Methode | Beschreibung |
|----------|---------|--------------|
| `/api/character/{id}/corporation/info` | GET | Corp-Info |
| `/api/character/{id}/corporation/wallet` | GET | Corp-Wallet |

### Shopping
| Endpunkt | Methode | Beschreibung |
|----------|---------|--------------|
| `/api/shopping/lists` | GET/POST | Shopping-Listen |
| `/api/shopping/lists/{id}` | GET/PATCH/DELETE | Einzelne Liste |
| `/api/shopping/lists/{id}/items` | POST | Item hinzufügen |
| `/api/shopping/lists/{id}/regional-comparison` | GET | Multi-Region Preisvergleich |
| `/api/shopping/lists/{id}/export` | GET | Multibuy-Export |
| `/api/shopping/route` | GET | Optimale Hub-Route berechnen |
| `/api/shopping/orders/{type_id}` | GET | Order-Snapshots (Top 10 Sell/Buy) |

### Markt & Produktion
| Endpunkt | Methode | Beschreibung |
|----------|---------|--------------|
| `/api/production/cost/{type_id}` | GET | Produktionskosten |
| `/api/trade/arbitrage` | GET | Arbitrage-Suche |
| `/api/market/stats/{region}/{type}` | GET | Marktstatistiken |
| `/api/market/scanner/results` | GET | Market Scanner Ergebnisse |

### Hunter
| Endpunkt | Methode | Beschreibung |
|----------|---------|--------------|
| `/api/hunter/opportunities` | GET | Profitable Opportunities |
| `/api/hunter/trigger` | POST | Hunter manuell starten |

### Mining
| Endpunkt | Methode | Beschreibung |
|----------|---------|--------------|
| `/api/mining/ore-prices` | GET | Ore-Preise |
| `/api/mining/yields` | GET | Mining Yields |

### Datenbank
| Endpunkt | Methode | Beschreibung |
|----------|---------|--------------|
| `/api/items/search?q=` | GET | Item-Suche |
| `/api/groups/search?q=` | GET | Gruppen-Suche |
| `/api/regions` | GET | Region-IDs |

## Datenbank-Schema

### Haupt-Tabellen (Custom)
```sql
-- Marktpreise Cache
market_prices (
    type_id, region_id, lowest_sell, highest_buy,
    sell_volume, buy_volume, realistic_sell, updated_at
)

-- Order Snapshots (Top 10 pro Item/Region)
market_order_snapshots (
    type_id, region_id, is_buy_order, price,
    volume_remain, location_id, issued, rank, updated_at
)

-- Shopping Listen
shopping_lists (id, name, character_id, corporation_id, status, notes, created_at)
shopping_list_items (id, list_id, type_id, item_name, quantity, target_region, target_price, ...)

-- Scanner Ergebnisse
scanner_opportunities (type_id, product_name, daily_volume, production_cost, sell_price, profit_per_unit, ...)
```

### SDE Tabellen (EVE Static Data Export)
- `invTypes` - Alle Items
- `invGroups` - Item-Gruppen
- `invCategories` - Kategorien
- `industryActivityMaterials` - Produktionsmaterialien
- `industryActivityProducts` - Produktionsoutput
- `mapSolarSystems` - Sonnensysteme
- `mapSolarSystemJumps` - System-Verbindungen
- `invMetaTypes` - Meta-Level (T1/T2/Faction)

## Cron Jobs

### Regional Price Fetcher
```bash
# Alle 15 Minuten Marktpreise aktualisieren
python3 -m jobs.regional_price_fetcher --verbose

# Nur eine Region
python3 -m jobs.regional_price_fetcher --region the_forge
```

### Market Hunter
```bash
# Cron-Job (alle 5 Minuten)
*/5 * * * * /home/cytrex/eve_copilot/jobs/cron_market_hunter.sh
```

## ESI Scopes

Benötigte Scopes für volle Funktionalität:
- `esi-wallet.read_character_wallet.v1`
- `esi-assets.read_assets.v1`
- `esi-markets.read_character_orders.v1`
- `esi-skills.read_skills.v1`
- `esi-industry.read_character_jobs.v1`
- `esi-characters.read_blueprints.v1`
- `esi-wallet.read_corporation_wallets.v1`
- `esi-corporations.read_corporation_membership.v1`
- `esi-characters.read_corporation_roles.v1`

## Region-IDs

| Region | ID | Trade Hub |
|--------|-----|-----------|
| The Forge | 10000002 | Jita |
| Domain | 10000043 | Amarr |
| Heimatar | 10000030 | Rens |
| Sinq Laison | 10000032 | Dodixie |
| Metropolis | 10000042 | Hek |

## Beispiel-Abfragen

### Produktionskosten für Hobgoblin I (ME10)
```bash
curl "http://localhost:8000/api/production/cost/2454?me_level=10"
```

### Shopping-Liste mit Preisvergleich
```bash
curl "http://localhost:8000/api/shopping/lists/1/regional-comparison?home_system=isikemi"
```

### Order-Details für Tritanium in Jita
```bash
curl "http://localhost:8000/api/shopping/orders/34?region=the_forge"
```

### Optimale Route durch Hubs
```bash
curl "http://localhost:8000/api/shopping/route?regions=the_forge,domain&home_system=isikemi&return_home=true"
```

## Frontend Features

### Shopping Planner
- Multi-Region Preisvergleich (Jita, Amarr, Rens, Dodixie, Hek)
- Stückpreis + Gesamtkosten pro Region
- Order-Details Popup (Klick auf Preiszelle)
- Optimale Routen-Berechnung mit System-Liste
- Wählbarer Startpunkt und Rückweg-Option
- "Apply All" Buttons pro Region

### Market Scanner
- Live-Profit-Berechnung für T1-Produkte
- Material-Kosten vs. Verkaufspreis
- Tägliches Handelsvolumen
- Sortierung nach Profit/Tag

## Zugangsdaten

- **API:** http://localhost:8000 (extern: http://77.24.99.81:8000)
- **Frontend:** http://localhost:3000 (extern: http://192.168.178.108:3000)
- **API Docs:** http://localhost:8000/docs

### Datenbank
- Container: `eve_db` (PostgreSQL 16)
- Host: localhost:5432
- DB: eve_sde
- User: eve
- Password: EvE_Pr0ject_2024

### EVE SSO
- Client ID: b4dbf38efae04055bc7037a63bcfd33b
- Callback: http://77.24.99.81:8000/api/auth/callback

### Authentifizierte Charaktere
| Name | Character ID | Rolle |
|------|--------------|-------|
| Artallus | 526379435 | |
| Cytrex | 1117367444 | CEO |
| Cytricia | 110592475 | |

### Corporation
- Name: Minimal Industries [MINDI]
- ID: 98785281
- CEO: Cytrex
- Home System: Isikemi
