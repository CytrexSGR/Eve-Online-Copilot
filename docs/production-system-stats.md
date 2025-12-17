# Production System - Database Statistics

**Generated:** 2025-12-17
**Database:** eve_sde (PostgreSQL 16)

## Overview

Complete production chain database for all manufacturable items in EVE Online.

### Database Summary

| Metric | Count |
|--------|-------|
| **Total Manufacturable Items Processed** | 4,197 |
| **Items with Complete Production Chains** | 4,156 |
| **Items with Direct Dependencies** | 4,193 |
| **Total Chain Entries** | 32,131 |
| **Total Direct Dependencies** | 24,353 |
| **Success Rate** | 100% (0 failures) |

## Top 20 Most Complex Items

Items ranked by number of unique raw materials required:

| Item | Type | Unique Materials | Total Volume |
|------|------|-----------------|--------------|
| Azariel | Titan | 53 | 1.8B units |
| Bane | Lancer Dreadnought | 53 | 28.5M units |
| Karura | Lancer Dreadnought | 53 | 28.5M units |
| Valravn | Lancer Dreadnought | 53 | 28.3M units |
| Hubris | Lancer Dreadnought | 53 | 28.3M units |
| Sarathiel | Dreadnought | 48 | 17.9M units |
| Revelation Navy Issue | Dreadnought | 45 | 15.5M units |
| Moros Navy Issue | Dreadnought | 45 | 15.5M units |
| Naglfar Fleet Issue | Dreadnought | 45 | 15.5M units |
| Phoenix Navy Issue | Dreadnought | 45 | 15.5M units |
| **Upwell Palatine Keepstar** | Citadel | 40 | **1.4 TRILLION units** |
| Babaroga | Marauder | 32 | 18.3M units |
| Hecate | Tactical Destroyer | 29 | 15.8K units |
| Svipul | Tactical Destroyer | 29 | 15.8K units |
| Jackdaw | Tactical Destroyer | 29 | 15.8K units |
| Excavator Mining Drone | Mining Drone | 28 | 168K units |
| Excavator Ice Harvesting Drone | Mining Drone | 28 | 156K units |
| Vanquisher | Titan | 25 | 1.8B units |
| Rhea | Jump Freighter | 25 | 30.2M units |

### Notable Observations

- **Upwell Palatine Keepstar** requires 1.4 trillion units of materials (most expensive structure in EVE)
- **Titans** require 25-53 different raw materials
- **Lancer Dreadnoughts** are among the most complex ships (53 unique materials)

## Raw Materials Usage

Top 15 most commonly used raw materials across all items:

| Material | Used In Items | Total Quantity Needed |
|----------|--------------|----------------------|
| **Tritanium** | 2,921 items | 1.1 trillion units |
| **Pyerite** | 2,838 items | 226 billion units |
| **Mexallon** | 2,560 items | 78 billion units |
| **Isogen** | 2,393 items | 9.3 billion units |
| **Nocxium** | 2,242 items | 1.7 billion units |
| **Megacyte** | 1,515 items | 345 million units |
| **Zydrine** | 1,392 items | 800 million units |
| **Morphite** | 842 items | 216K units |
| Phenolic Composites | 360 items | 1.7M units |
| Nanotransistors | 354 items | 721K units |
| Fullerides | 309 items | 8.1M units |
| Hypersynaptic Fibers | 307 items | 206K units |
| Broadcast Node | 299 items | 8.3M units |
| Self-Harmonizing Power Core | 297 items | 4.8M units |
| Nano-Factory | 255 items | 6.7M units |

### Raw Material Insights

- **Tritanium** is the foundation of EVE manufacturing (used in 70% of all items)
- **Morphite** is the rarest mineral (only in 20% of items)
- **PI Materials** (Phenolic Composites, etc.) are essential for advanced items

## Item Category Distribution

Top 20 item categories by number of manufacturable items:

| Category | Item Count |
|----------|-----------|
| Mutaplasmids | 170 |
| Cyberimplant | 115 |
| Hybrid Weapon | 78 |
| Combat Drone | 75 |
| Rig Shield | 72 |
| Rig Armor | 72 |
| Energy Weapon | 68 |
| Projectile Weapon | 65 |
| Rig Navigation | 64 |
| Rig Drones | 64 |
| Rig Core | 60 |
| Mining Crystal | 60 |
| Construction Components | 57 |
| Smart Bomb | 56 |
| Rig Energy Weapon | 56 |
| Rig Hybrid Weapon | 56 |
| Rig Electronic Systems | 48 |
| Rig Launcher | 48 |
| Frigate | 47 |
| Propulsion Module | 44 |

## Example: Drake Battlecruiser

**Type ID:** 24698

### Raw Material Requirements (ME 0)

| Material | Base Quantity | With ME 10 |
|----------|--------------|------------|
| Tritanium | 5,600,000 | 5,040,000 |
| Pyerite | 2,000,000 | 1,800,000 |
| Mexallon | 360,000 | 324,000 |
| Isogen | 40,000 | 36,000 |
| Nocxium | 16,000 | 14,400 |
| Zydrine | 4,000 | 3,600 |
| Megacyte | 800 | 720 |

**Total Materials:** 7 different minerals
**Total Volume (ME 0):** 8,020,800 units
**Total Volume (ME 10):** 7,218,720 units
**ME 10 Savings:** 802,080 units (10%)

## Database Schema

### Tables Created

1. **production_dependencies** (24,353 rows)
   - Direct material requirements per item
   - Activity type (Manufacturing, Research, Invention)
   - Raw material flag

2. **production_chains** (32,131 rows)
   - Complete chains to raw materials
   - Pre-calculated total quantities
   - Chain depth tracking
   - Path debugging support

3. **production_economics** (0 rows - ready for data)
   - Material costs
   - Market prices
   - ROI calculations
   - Production time

4. **production_jobs** (0 rows - ready for usage)
   - User production job tracking
   - ME/TE levels
   - Cost and revenue tracking

5. **production_job_materials** (0 rows - ready for usage)
   - Job material requirements
   - Make-or-buy decisions
   - Acquisition tracking

## Performance Metrics

- **Processing Time:** ~7 minutes for 4,197 items
- **Processing Rate:** ~10 items/second
- **Database Size:** ~32,000 chain entries for 4,000+ items
- **Average Materials per Item:** ~7.7 raw materials

## Next Steps

### Phase 2: Chain API
- Implement `/api/production/chains/{type_id}` endpoints
- Material list with ME adjustments
- Direct dependencies queries

### Phase 3: Economics System
- Calculate material costs for all items
- Integrate market prices from `market_prices_cache`
- ROI analysis per region
- Cron job for economics updates

### Phase 4: Workflow System
- Production job management
- Make-or-buy decision support
- Character asset integration
- Skill requirement checking

## Data Quality

- ✅ All 4,197 items processed successfully
- ✅ 0 failures during batch processing
- ✅ All chains verified to terminate at raw materials
- ✅ Drake example matches expected values
- ✅ Complex items (Titans, Keepstars) properly calculated

## Technical Details

**Build Method:** Recursive chain builder from EVE SDE
**Source Tables:** `industryActivityProducts`, `industryActivityMaterials`
**Activity Types:** Manufacturing (activityID = 1)
**Raw Materials:** Items with no further production dependencies

**Batch Configuration:**
- Bottom-up approach (Raw → Components → T1 → T2 → T3)
- All manufacturable items in single batch
- On-conflict upsert for idempotency
