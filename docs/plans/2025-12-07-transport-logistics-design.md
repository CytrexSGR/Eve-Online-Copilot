# Transport & Logistics System Design

**Datum:** 2025-12-07
**Status:** Approved
**Scope:** Shopping Planner Erweiterung + Grundlagen für Produktionsplanung

---

## 1. Übersicht

Erweiterung des Shopping Planners um:
1. **Produktmengen** - Runs/Quantity für Endprodukte festlegen
2. **Cargo-Berechnung** - Transportvolumen früh sichtbar
3. **Transport-Optionen** - Welcher Character mit welchem Schiff
4. **Skill-basierte Schiffszuweisung** - Automatisch prüfen wer was fliegen kann
5. **Routen-Optimierung** - Safe vs Risky Routes mit Metriken

---

## 2. Datenbank-Änderungen

### 2.1 Erweiterung `shopping_list_items`

```sql
ALTER TABLE shopping_list_items
    ADD COLUMN is_product BOOLEAN DEFAULT FALSE,
    ADD COLUMN runs INT DEFAULT 1,
    ADD COLUMN me_level INT DEFAULT 10,
    ADD COLUMN te_level INT DEFAULT 20,
    ADD COLUMN volume_per_unit NUMERIC(20,4),
    ADD COLUMN total_volume NUMERIC(20,2);

COMMENT ON COLUMN shopping_list_items.is_product IS 'TRUE = Endprodukt (hat Blueprint), FALSE = Material';
COMMENT ON COLUMN shopping_list_items.runs IS 'Anzahl Production Runs (nur für Produkte)';
COMMENT ON COLUMN shopping_list_items.me_level IS 'Material Efficiency des Blueprints';
COMMENT ON COLUMN shopping_list_items.te_level IS 'Time Efficiency des Blueprints';
```

### 2.2 Neue Tabelle `character_capabilities`

Cached die Schiff-Fähigkeiten aller Characters (täglich aktualisiert).

```sql
CREATE TABLE character_capabilities (
    id SERIAL PRIMARY KEY,
    character_id BIGINT NOT NULL,
    character_name VARCHAR(255),
    type_id INT NOT NULL,
    ship_name VARCHAR(255),
    ship_group VARCHAR(100),          -- 'Industrial', 'Freighter', 'Blockade Runner', etc.
    cargo_capacity FLOAT,
    location_id BIGINT,
    location_name VARCHAR(255),
    can_fly BOOLEAN DEFAULT FALSE,
    missing_skills JSONB,             -- Array von {skill_name, required_level, current_level}
    last_synced TIMESTAMP DEFAULT NOW(),

    CONSTRAINT unique_char_ship_location UNIQUE (character_id, type_id, location_id)
);

CREATE INDEX idx_char_capabilities_char ON character_capabilities(character_id);
CREATE INDEX idx_char_capabilities_location ON character_capabilities(location_id);
CREATE INDEX idx_char_capabilities_can_fly ON character_capabilities(can_fly);
```

---

## 3. Backend API Endpoints

### 3.1 Character Logistics

**`GET /api/character/{id}/ships`**
```json
{
  "character_id": 526379435,
  "character_name": "Artallus",
  "ships": [
    {
      "type_id": 28850,
      "name": "Rhea",
      "group": "Jump Freighter",
      "cargo_capacity": 350000,
      "location": "Jita IV - Moon 4 - Caldari Navy Assembly Plant",
      "location_id": 60003760,
      "can_fly": true
    }
  ]
}
```

**`GET /api/character/{id}/logistics-capability`**
```json
{
  "character_id": 526379435,
  "can_fly": {
    "industrial": true,
    "blockade_runner": true,
    "deep_space_transport": true,
    "freighter": false,
    "jump_freighter": true
  },
  "missing_skills": {
    "freighter": [
      {"skill": "Gallente Freighter", "required": 1, "current": 0}
    ]
  }
}
```

**`POST /api/characters/sync-capabilities`**
- Manueller Trigger für Skill-Sync
- Wird auch vom Cron Job aufgerufen

### 3.2 Shopping List Erweiterungen

**`PATCH /api/shopping/items/{item_id}/runs`**
```json
{
  "runs": 10,
  "me_level": 10
}
```
Response: Neu berechnete Materialien + Cargo-Volumen

**`GET /api/shopping/lists/{id}/cargo-summary`**
```json
{
  "list_id": 42,
  "products": [
    {"name": "Drake", "runs": 10, "volume_m3": 2500000}
  ],
  "materials": {
    "total_items": 47,
    "total_volume_m3": 45230,
    "volume_formatted": "45.2K m³",
    "breakdown_by_region": {
      "the_forge": {"volume_m3": 32100, "item_count": 35},
      "domain": {"volume_m3": 13130, "item_count": 12}
    }
  }
}
```

### 3.3 Transport Options

**`GET /api/shopping/lists/{id}/transport-options?safe_only=true`**
```json
{
  "total_volume_m3": 45230,
  "route_summary": "Isikemi → Jita → Amarr → Isikemi",
  "options": [
    {
      "id": 1,
      "characters": [
        {
          "id": 526379435,
          "name": "Artallus",
          "ship_type_id": 28850,
          "ship_name": "Rhea",
          "ship_location": "Jita"
        }
      ],
      "trips": 1,
      "flight_time_min": 45,
      "capacity_m3": 350000,
      "capacity_used_pct": 12.9,
      "risk_score": 0,
      "risk_label": "Safe",
      "dangerous_systems": [],
      "isk_per_trip": 890000000,
      "route": [
        {"from": "Isikemi", "to": "Jita", "jumps": 3, "security": "highsec"},
        {"from": "Jita", "to": "Amarr", "jumps": 9, "security": "highsec"},
        {"from": "Amarr", "to": "Isikemi", "jumps": 12, "security": "highsec"}
      ]
    },
    {
      "id": 2,
      "characters": [
        {
          "id": 1117367444,
          "name": "Cytrex",
          "ship_type_id": 12729,
          "ship_name": "Prorator",
          "ship_location": "Isikemi"
        }
      ],
      "trips": 5,
      "flight_time_min": 200,
      "capacity_m3": 10000,
      "capacity_used_pct": 90.5,
      "risk_score": 2,
      "risk_label": "Low Risk",
      "dangerous_systems": ["Aufay", "Balle"],
      "isk_per_trip": 178000000
    }
  ],
  "filters_available": ["fewest_trips", "fastest", "single_char", "lowest_risk"]
}
```

---

## 4. Frontend UI

### 4.1 Shopping List Header - Erweitert

```
┌─────────────────────────────────────────────────────────────────┐
│ Drake Production                                    [Edit] [Del] │
├─────────────────────────────────────────────────────────────────┤
│ Products:                                                        │
│   Drake ×[10▼] ME:[10▼]                            = 2.5M m³    │
│   [+ Add Product]                                                │
├─────────────────────────────────────────────────────────────────┤
│ Materials: 47 items                                              │
│ Total Cargo: 45,230 m³  [████████░░] fits DST                   │
│                                                                  │
│ [List View] [Compare Regions] [Transport]                        │
└─────────────────────────────────────────────────────────────────┘
```

### 4.2 Transport Tab - Neues Dashboard

```
┌─────────────────────────────────────────────────────────────────┐
│ Transport Options                                                │
├─────────────────────────────────────────────────────────────────┤
│ Total Cargo: 45,230 m³   Route: Isikemi → Jita → Amarr → Home   │
│                                                                  │
│ ◉ Safe routes only   ○ Include risky routes                     │
│                                                                  │
│ Filter: [Wenigste Trips] [Schnellste] [Ein Char] [Niedrig Risiko]│
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│ ┌─ Option 1 ──────────────────────────────────── RECOMMENDED ─┐ │
│ │ Artallus → Rhea (Jump Freighter)                            │ │
│ │ Trips: 1    Zeit: 45 min    Auslastung: 12.9%               │ │
│ │ Risiko: ✅ Safe    ISK/Trip: 890M                           │ │
│ │                                              [Select] [Detail]│ │
│ └─────────────────────────────────────────────────────────────┘ │
│                                                                  │
│ ┌─ Option 2 ─────────────────────────────────────────────────┐ │
│ │ Cytrex → Prorator (Blockade Runner)                        │ │
│ │ Trips: 5    Zeit: 3h 20m    Auslastung: 90.5%              │ │
│ │ Risiko: ⚠️ 2 Lowsec    ISK/Trip: 178M                      │ │
│ │                                              [Select] [Detail]│ │
│ └─────────────────────────────────────────────────────────────┘ │
│                                                                  │
│ ┌─ Option 3 ─────────────────────────────────────────────────┐ │
│ │ Cytrex → Nereus (Industrial)                               │ │
│ │ Trips: 10   Zeit: 6h 40m    Auslastung: 90.5%              │ │
│ │ Risiko: ✅ Safe    ISK/Trip: 89M                           │ │
│ │                                              [Select] [Detail]│ │
│ └─────────────────────────────────────────────────────────────┘ │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 4.3 Detail-Panel bei Klick auf Option

```
┌─────────────────────────────────────────────────────────────────┐
│ Route Detail: Artallus mit Rhea                                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│ Leg 1: Isikemi → Jita (3 jumps, ~6 min)                         │
│   ├── Isikemi (0.78)                                            │
│   ├── Maurasi (0.94)                                            │
│   ├── Perimeter (0.95)                                          │
│   └── Jita (0.95) ★ PICKUP: 32,100 m³                          │
│                                                                  │
│ Leg 2: Jita → Amarr (9 jumps, ~18 min)                          │
│   └── [...] ★ PICKUP: 13,130 m³                                │
│                                                                  │
│ Leg 3: Amarr → Isikemi (12 jumps, ~24 min)                      │
│   └── [...] ★ DELIVERY                                         │
│                                                                  │
│ ─────────────────────────────────────────────────────────────── │
│ Summary:                                                         │
│   Total Jumps: 24        Total Time: ~48 min                    │
│   Cargo: 45,230 m³       Ship Capacity: 350,000 m³              │
│   Value at Risk: 890,000,000 ISK                                │
│                                                                  │
│                                          [Use This Option]       │
└─────────────────────────────────────────────────────────────────┘
```

---

## 5. Transport-Options Algorithmus

### 5.1 Hauptlogik

```python
def calculate_transport_options(shopping_list_id: int, safe_only: bool = True):
    # 1. Daten sammeln
    list_data = get_shopping_list_with_volumes(shopping_list_id)
    total_volume = sum(item.total_volume for item in list_data.items if not item.is_product)
    regions_needed = get_regions_with_items(list_data)

    # 2. Verfügbare Schiffe holen
    all_characters = get_authenticated_characters()
    available_ships = []

    for char in all_characters:
        ships = get_character_ships(char.id)  # Aus character_capabilities
        for ship in ships:
            if ship.can_fly and ship.location in RELEVANT_LOCATIONS:
                available_ships.append(ship)

    # 3. Route berechnen
    home_system = "Isikemi"
    route = calculate_optimal_route(home_system, regions_needed, safe_only)

    # 4. Optionen generieren
    options = []

    for ship in available_ships:
        trips = ceil(total_volume / ship.cargo_capacity)
        flight_time = calculate_flight_time(route, ship.ship_group)
        risk_score = calculate_risk_score(route)
        isk_per_trip = total_volume / trips * average_isk_per_m3

        options.append({
            'character': ship.character,
            'ship': ship,
            'trips': trips,
            'flight_time_min': flight_time * trips,
            'capacity_used_pct': (total_volume / (ship.cargo_capacity * trips)) * 100,
            'risk_score': risk_score,
            'isk_per_trip': list_data.total_cost / trips
        })

    # 5. Multi-Character Optionen (parallel fliegen)
    if len(all_characters) > 1:
        options.extend(calculate_parallel_options(available_ships, total_volume, route))

    # 6. Sortieren und zurückgeben
    return sorted(options, key=lambda x: (x['trips'], x['flight_time_min']))
```

### 5.2 Risiko-Score Berechnung

```python
def calculate_risk_score(route: List[System]) -> dict:
    dangerous_systems = []

    for system in route:
        if system.security < 0.5:
            dangerous_systems.append({
                'name': system.name,
                'security': system.security,
                'recent_kills': get_recent_hauler_kills(system.id, days=7)
            })

    score = len(dangerous_systems)

    # Bonus-Malus für aktive Kills
    for sys in dangerous_systems:
        if sys['recent_kills'] > 5:
            score += 2
        elif sys['recent_kills'] > 0:
            score += 1

    label = "Safe" if score == 0 else "Low Risk" if score <= 2 else "Medium Risk" if score <= 5 else "High Risk"

    return {
        'score': score,
        'label': label,
        'dangerous_systems': dangerous_systems
    }
```

### 5.3 Flugzeit-Schätzung

```python
FLIGHT_TIME_PER_JUMP = {
    'Shuttle': 1.0,        # min
    'Frigate': 1.5,
    'Industrial': 2.0,
    'Blockade Runner': 1.5,  # Schnell + Cloak
    'Deep Space Transport': 2.5,
    'Freighter': 3.5,       # Langsam, Align-Zeit
    'Jump Freighter': 2.0,  # Mit Cynos schneller, aber hier konservativ
}

def calculate_flight_time(route: List[Leg], ship_group: str) -> int:
    time_per_jump = FLIGHT_TIME_PER_JUMP.get(ship_group, 2.0)
    total_jumps = sum(leg.jumps for leg in route)

    # Docking/Undocking Zeit pro Hub
    docking_time = len(route) * 2  # 2 min pro Stop

    return int(total_jumps * time_per_jump + docking_time)
```

---

## 6. Cron Job: Character Capability Sync

**Datei:** `jobs/character_capability_sync.py`
**Schedule:** Täglich 04:00 UTC

### 6.1 Ablauf

```python
async def sync_all_character_capabilities():
    characters = get_all_authenticated_characters()

    for char in characters:
        try:
            # 1. Assets holen
            assets = await esi_client.get_character_assets(char.id)

            # 2. Schiffe filtern (categoryID = 6 in SDE)
            ships = filter_ships_from_assets(assets)

            # 3. Skills holen
            skills = await esi_client.get_character_skills(char.id)

            # 4. Für jedes Schiff prüfen
            for ship in ships:
                requirements = get_ship_skill_requirements(ship.type_id)  # Aus SDE
                can_fly, missing = check_skill_requirements(skills, requirements)

                upsert_character_capability(
                    character_id=char.id,
                    character_name=char.name,
                    type_id=ship.type_id,
                    ship_name=ship.name,
                    ship_group=get_ship_group(ship.type_id),
                    cargo_capacity=get_cargo_capacity(ship.type_id),
                    location_id=ship.location_id,
                    location_name=resolve_location_name(ship.location_id),
                    can_fly=can_fly,
                    missing_skills=missing
                )

            log.info(f"Synced {len(ships)} ships for {char.name}")

        except Exception as e:
            log.error(f"Failed to sync {char.name}: {e}")
```

### 6.2 Skill Requirements aus SDE

```python
def get_ship_skill_requirements(type_id: int) -> List[dict]:
    """
    Holt Skill-Requirements aus dgmTypeAttributes

    Attribute IDs:
    - 182: requiredSkill1
    - 183: requiredSkill1Level
    - 184: requiredSkill2
    - 185: requiredSkill2Level
    - etc.
    """
    query = '''
        SELECT
            t."typeName",
            rs1."typeName" as skill1_name,
            a1.value as skill1_level,
            rs2."typeName" as skill2_name,
            a2.value as skill2_level,
            rs3."typeName" as skill3_name,
            a3.value as skill3_level
        FROM "invTypes" t
        LEFT JOIN "dgmTypeAttributes" a1 ON t."typeID" = a1."typeID" AND a1."attributeID" = 182
        LEFT JOIN "invTypes" rs1 ON a1.value = rs1."typeID"
        LEFT JOIN "dgmTypeAttributes" al1 ON t."typeID" = al1."typeID" AND al1."attributeID" = 277
        -- ... weitere JOINs für Skill 2, 3
        WHERE t."typeID" = %s
    '''
    # Return structured requirements
```

---

## 7. Metriken & Filter

### 7.1 Dashboard Metriken (Top 5)

| Metrik | Beschreibung | Sortierung |
|--------|--------------|------------|
| **Risiko-Score** | Anzahl Lowsec + Killmail-Aktivität | Aufsteigend (0 = best) |
| **Gesamte Flugzeit** | Jumps × Zeit/Jump × Trips | Aufsteigend |
| **Kapazitätsauslastung** | Volume / (Capacity × Trips) | Info only |
| **Anzahl Charaktere** | Wie viele Chars parallel | Aufsteigend |
| **ISK pro Trip** | Gesamtwert / Trips | Info (Risiko-Indikator) |

### 7.2 Filter-Optionen

- **Wenigste Trips** - Sortiert nach `trips ASC`
- **Schnellste** - Sortiert nach `flight_time_min ASC`
- **Ein Char** - Filtert `characters.length == 1`
- **Niedrigstes Risiko** - Sortiert nach `risk_score ASC`

---

## 8. Routen-Optionen

### 8.1 Safe vs Risky Toggle

**Safe only (Default):**
- Route nur durch Highsec (≥0.5)
- Längere Routen möglich
- Alle Schiffstypen erlaubt

**Include risky:**
- Kürzeste Route, auch durch Lowsec
- Warnung bei gefährlichen Systemen
- Schiff-Empfehlung: Blockade Runner/Covert Ops für Lowsec-Legs

### 8.2 Route-Berechnung

Nutzt bestehenden `route_service.py` mit A*-Algorithmus.

Erweiterung:
```python
def calculate_route(from_system: str, to_system: str, safe_only: bool = True):
    if safe_only:
        # Nur Systeme mit security >= 0.5
        return a_star_route(from_system, to_system, security_filter=0.5)
    else:
        return a_star_route(from_system, to_system, security_filter=None)
```

---

## 9. Zukünftige Erweiterungen (Phase 2+)

### 9.1 Make vs Buy Entscheidungen

Für jedes Material mit Blueprint:
- Prüfen ob Character Blueprint besitzt
- Kosten Eigenproduktion vs Marktpreis vergleichen
- Slot-Verfügbarkeit berücksichtigen
- Empfehlung: "Kaufen spart 2M ISK" oder "Selbst bauen spart 5M ISK + 2h"

### 9.2 Blueprint-Verfügbarkeit

```sql
CREATE TABLE character_blueprints (
    character_id BIGINT,
    type_id INT,                    -- Blueprint type_id
    product_type_id INT,            -- Was kann damit gebaut werden
    location_id BIGINT,
    is_original BOOLEAN,            -- BPO vs BPC
    runs_remaining INT,             -- Nur für BPC
    me_level INT,
    te_level INT,
    last_synced TIMESTAMP
);
```

### 9.3 Produktionsplanung

- Slot-Management (wie viele Industry Slots frei?)
- Zeitplanung (wann ist Produktion fertig?)
- Queue-Optimierung (Reihenfolge der Jobs)
- Material-Reservierung

### 9.4 Skill-Gap Analyse

- Welche Skills fehlen für bestimmte Schiffe?
- Skill-Plan generieren
- Training-Zeit berechnen
- Prioritäten setzen (Industrie vs Logistik vs Combat)

### 9.5 Logistik-Lücken erkennen

- Welche Schiffstypen fehlen in der Corp?
- Empfehlungen: "Ein Freighter würde 80% der Routen abdecken"
- Kosten/Nutzen Analyse für Schiffskäufe

---

## 10. Implementation Reihenfolge

### Phase 1: Basis (Diese Iteration)
1. DB Migration - `shopping_list_items` erweitern
2. DB Migration - `character_capabilities` Tabelle
3. Cron Job - Character Capability Sync
4. API - `/api/shopping/lists/{id}/cargo-summary`
5. API - `/api/shopping/lists/{id}/transport-options`
6. Frontend - Produkt Runs/ME im Shopping List Header
7. Frontend - Cargo-Volumen Anzeige
8. Frontend - Transport Tab mit Options Dashboard

### Phase 2: Optimierung
9. Multi-Character parallel Transport
10. Killmail-Integration für Risiko-Score
11. Route-Detail mit System-Liste

### Phase 3: Produktion (Später)
12. Blueprint-Sync
13. Make vs Buy Analyse
14. Produktionsplanung

---

## 11. Offene Fragen

1. **Location Resolution:** Wie lösen wir `location_id` zu Namen auf? (Station Names aus SDE + Citadels aus ESI)
2. **Citadel-Access:** Können wir prüfen ob Character Docking Rights hat?
3. **Jump Freighter Cynos:** Sollen wir Cyno-Routen separat berechnen?

---

## Anhang: Relevante Locations

```python
RELEVANT_LOCATIONS = {
    # Home System
    'Isikemi': 30000119,

    # Trade Hubs
    'Jita': 30000142,
    'Amarr': 30002187,
    'Dodixie': 30002659,
    'Rens': 30002510,
    'Hek': 30002053,
}

# Stations in diesen Systemen werden als "relevant" für Schiffe betrachtet
```
