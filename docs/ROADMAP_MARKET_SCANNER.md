# Market Scanner Roadmap

## Aktueller Stand
- [x] Market Scanner mit DB-Backend (983 Opportunities)
- [x] Filter: ROI, Profit, Difficulty, Category
- [x] Item-Detail Modal mit Materialien und Preisen pro Region
- [x] Cronjob alle 5 Minuten für Daten-Updates

---

## Phase 1: UI/UX Verbesserungen

### 1.1 Zahlenformatierung
- [ ] Alle ISK-Werte mit Tausender-Trennzeichen (1.234.567)
- [ ] Automatische Einheiten: K, M, B (1.5M statt 1500000)
- [ ] Konsistente Formatierung in allen Ansichten

### 1.2 Detail-Ansicht als Tab statt Modal
- [ ] Neuer Tab "Item Details" im Market Scanner
- [ ] Breadcrumb-Navigation: Scanner > Item Details > Komponente
- [ ] Zurück-Button und History

### 1.3 Komponenten-Drill-Down
- [ ] Bei Klick auf Material: zeige dessen Zusammensetzung
- [ ] Rekursive Ansicht für komplexe Items
- [ ] Baum-Ansicht für verschachtelte Materialien

---

## Phase 2: Bookmark-System

### 2.1 DB-Schema
```sql
CREATE TABLE bookmarks (
    id SERIAL PRIMARY KEY,
    user_id INTEGER,  -- für später Multi-User
    type_id INTEGER NOT NULL,
    name VARCHAR(255),
    notes TEXT,
    tags VARCHAR(255)[],
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP
);

CREATE TABLE bookmark_lists (
    id SERIAL PRIMARY KEY,
    user_id INTEGER,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE bookmark_list_items (
    list_id INTEGER REFERENCES bookmark_lists(id),
    bookmark_id INTEGER REFERENCES bookmarks(id),
    position INTEGER,
    PRIMARY KEY (list_id, bookmark_id)
);
```

### 2.2 Features
- [ ] Bookmark-Icon (Stern) in Listen und Detail-Ansichten
- [ ] Quick-Bookmark mit einem Klick
- [ ] Bookmark-Listen erstellen und verwalten
- [ ] Notizen zu Bookmarks hinzufügen
- [ ] Tags für Kategorisierung
- [ ] Sidebar mit "Meine Bookmarks"

---

## Phase 3: Material-Verfügbarkeit

### 3.1 Mengen anzeigen
- [ ] Volume available pro Region für jedes Material
- [ ] Farbcodierung: Grün (genug), Gelb (knapp), Rot (zu wenig)
- [ ] Tooltip mit exakter Menge

### 3.2 Gesamt-Materialliste
- [ ] Neuer Tab "Materials Overview"
- [ ] Aggregierte Liste aller benötigten Materialien
- [ ] Vergleich: Preis und Menge pro Region
- [ ] Sortierung nach: Preis, Menge, Region
- [ ] Export als CSV/Text für Ingame-Einkauf

---

## Phase 4: Einkaufsplanung

### 4.1 Shopping List
- [ ] Neuer Tab "Shopping Planner"
- [ ] Materialien aus mehreren Items kombinieren
- [ ] Automatische Mengenberechnung
- [ ] Checkbox-System für gekaufte Items
- [ ] Preis-Summe und Gewinn-Prognose

### 4.2 Regionale Optimierung
- [ ] Beste Region für jedes Material vorschlagen
- [ ] Gesamtkosten-Vergleich: alles in einer Region vs. optimiert
- [ ] Savings-Anzeige bei Multi-Region-Einkauf

---

## Phase 5: Route & Logistik

### 5.1 Routen-Berechnung
- [ ] Integration mit EVE Route-APIs oder eigene Berechnung
- [ ] Start-System auswählbar (z.B. Jita)
- [ ] Sprünge zwischen Trade Hubs anzeigen
- [ ] Sicherheitsstatus der Route (HighSec/LowSec/NullSec)
- [ ] Warnung bei gefährlichen Routen

### 5.2 Security-Klassifizierung
- [ ] Systeme farbig markieren (Grün=High, Orange=Low, Rot=Null)
- [ ] Option: "Nur HighSec" Filter
- [ ] Autopilot-Route vs. kürzeste Route

### 5.3 Zeitkalkulation
- [ ] Geschätzte Reisezeit basierend auf:
  - Anzahl Sprünge
  - Warps pro System (geschätzt)
  - Align-Zeit (schiffsabhängig, Standard: 10s)
- [ ] Gesamtzeit für Einkaufstour

### 5.4 Frachtraum-Kalkulation
- [ ] Volumen jedes Materials (m³)
- [ ] Gesamtvolumen der Einkaufsliste
- [ ] Schiffsempfehlung basierend auf Volumen:
  - < 1.000 m³: Frigate/Destroyer
  - < 5.000 m³: Industrial
  - < 60.000 m³: Deep Space Transport
  - > 60.000 m³: Freighter / mehrere Trips
- [ ] Warnung wenn Frachtraum nicht reicht

---

## Phase 6: Erweiterte Features (Future)

### 6.1 Produktionsplanung
- [ ] Mehrere Items in Produktion planen
- [ ] Zeitliche Planung mit Slots
- [ ] Material-Reservierung

### 6.2 Profit-Tracking
- [ ] Tatsächliche Einkaufs/Verkaufspreise eingeben
- [ ] Gewinn/Verlust-Rechnung
- [ ] Historische Daten

### 6.3 Market-Alerts
- [ ] Benachrichtigung wenn Preis unter/über Schwelle
- [ ] Discord-Integration für Alerts
- [ ] Push-Notifications

---

## Technische Anforderungen

### Neue API-Endpoints
```
POST   /api/bookmarks                    - Bookmark erstellen
GET    /api/bookmarks                    - Alle Bookmarks abrufen
DELETE /api/bookmarks/{id}               - Bookmark löschen
GET    /api/bookmarks/lists              - Listen abrufen
POST   /api/bookmarks/lists              - Liste erstellen
GET    /api/materials/{type_id}/volumes  - Verfügbare Mengen
GET    /api/route/{from}/{to}            - Route berechnen
GET    /api/shopping/optimize            - Einkauf optimieren
```

### Neue DB-Tabellen
- `bookmarks` - Gespeicherte Items
- `bookmark_lists` - Bookmark-Listen
- `bookmark_list_items` - Zuordnung
- `shopping_lists` - Einkaufslisten
- `shopping_list_items` - Einkaufs-Items

### Frontend-Komponenten
- `BookmarkButton` - Stern-Icon für Bookmarking
- `BookmarkSidebar` - Sidebar mit Listen
- `MaterialsOverview` - Gesamt-Materialliste
- `ShoppingPlanner` - Einkaufsplanung
- `RouteDisplay` - Routenanzeige
- `CargoCalculator` - Frachtraum-Rechner

---

## Prioritäten

| Prio | Feature | Aufwand |
|------|---------|---------|
| 1 | Zahlenformatierung | Klein |
| 2 | Detail als Tab | Mittel |
| 3 | Material-Mengen anzeigen | Mittel |
| 4 | Bookmark-System | Mittel |
| 5 | Gesamt-Materialliste | Mittel |
| 6 | Einkaufsplanung | Groß |
| 7 | Route/Logistik | Groß |

---

## Fragen zur Klärung

1. **Multi-User**: Soll das System mehrere Benutzer unterstützen oder erstmal Single-User?
2. **Route-API**: ESI bietet keine direkte Route-API. Sollen wir:
   - Statische Daten aus SDE nutzen (komplexer)
   - Externe Services wie EVE-Scout/Dotlan nutzen
   - Vereinfachte Sprung-Schätzung (Hub-zu-Hub Distanzen)
3. **Persistence**: Sollen Einkaufslisten persistent sein (DB) oder nur Session-basiert?
4. **Schiffsauswahl**: Soll der Nutzer sein Schiff auswählen können für Cargo-Berechnung?
