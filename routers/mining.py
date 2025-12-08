"""
Mining Router
Endpoints for finding mining locations and ore information
"""

from fastapi import APIRouter, HTTPException, Query, Depends
from database import get_db_connection

# New refactored services (available for future integration)
from src.core.config import get_settings, Settings
from src.core.database import DatabasePool
from src.services.route.repository import RouteRepository
from src.services.route.service import RouteService
from src.services.cargo.repository import CargoRepository
from src.services.cargo.service import CargoService
from src.core.exceptions import EVECopilotError

router = APIRouter(prefix="/api/mining", tags=["Mining"])


# ============================================================
# Dependency Injection Functions
# ============================================================

def get_route_service(settings: Settings = Depends(get_settings)) -> RouteService:
    """
    Dependency injection for RouteService.

    Creates service with proper repository and database pool.
    """
    db_pool = DatabasePool(settings)
    repository = RouteRepository(db_pool)
    return RouteService(repository)


def get_cargo_service(settings: Settings = Depends(get_settings)) -> CargoService:
    """
    Dependency injection for CargoService.

    Creates service with proper repository and database pool.
    """
    db_pool = DatabasePool(settings)
    repository = CargoRepository(db_pool)
    return CargoService(repository)


# ============================================================
# Ore Data Constants
# ============================================================

# Ore spawn rules by security status (based on EVE mechanics)
ORE_BY_SECURITY = {
    "highsec": {  # 1.0 to 0.5
        "belts": ["Veldspar", "Scordite", "Pyroxeres", "Plagioclase"],
        "anomalies": ["Omber"],
        "ice": ["Blue Ice", "Clear Icicle", "Glare Crust", "White Glaze"],
    },
    "lowsec": {  # 0.4 to 0.1
        "belts": ["Veldspar", "Scordite", "Pyroxeres", "Kernite", "Omber", "Jaspet", "Hemorphite", "Hedbergite"],
        "anomalies": [],
        "ice": ["Dark Glitter", "Gelidus", "Krystallos", "Glare Crust"],
    },
    "nullsec": {  # < 0.0
        "belts": ["Veldspar", "Scordite", "Pyroxeres", "Kernite", "Omber", "Jaspet", "Hemorphite", "Hedbergite",
                  "Gneiss", "Dark Ochre", "Spodumain", "Crokite", "Bistot", "Arkonor", "Mercoxit"],
        "anomalies": [],
        "ice": ["All types including faction ice"],
    },
    "wormhole": {  # -1.0
        "belts": ["Veldspar", "Scordite", "Pyroxeres", "Gneiss", "Dark Ochre", "Spodumain", "Crokite", "Bistot", "Arkonor"],
        "anomalies": [],
        "ice": ["Class-specific"],
    },
}

# Minerals contained in each ore type
ORE_MINERALS = {
    "Veldspar": {"Tritanium": 400},
    "Scordite": {"Tritanium": 150, "Pyerite": 90},
    "Pyroxeres": {"Tritanium": 300, "Pyerite": 25, "Mexallon": 30, "Nocxium": 3},
    "Plagioclase": {"Tritanium": 100, "Pyerite": 200, "Mexallon": 70},
    "Omber": {"Tritanium": 80, "Pyerite": 100, "Isogen": 85},
    "Kernite": {"Tritanium": 120, "Mexallon": 60, "Isogen": 120},
    "Jaspet": {"Tritanium": 70, "Pyerite": 120, "Mexallon": 150, "Nocxium": 5, "Zydrine": 1},
    "Hemorphite": {"Tritanium": 200, "Pyerite": 100, "Mexallon": 120, "Isogen": 25, "Nocxium": 15, "Zydrine": 4},
    "Hedbergite": {"Tritanium": 180, "Pyerite": 72, "Isogen": 17, "Nocxium": 59, "Zydrine": 8},
    "Gneiss": {"Tritanium": 1700, "Mexallon": 1600, "Isogen": 170},
    "Dark Ochre": {"Tritanium": 8000, "Nocxium": 160, "Zydrine": 120},
    "Arkonor": {"Tritanium": 300, "Mexallon": 1200, "Megacyte": 120},
    "Bistot": {"Pyerite": 170, "Mexallon": 1200, "Megacyte": 100, "Zydrine": 200},
    "Crokite": {"Tritanium": 330, "Mexallon": 2000, "Nocxium": 530, "Zydrine": 110},
    "Spodumain": {"Tritanium": 56000, "Pyerite": 12000, "Megacyte": 140},
}


# ============================================================
# Helper Functions
# ============================================================

def get_security_class(security: float) -> str:
    """Determine security class for a given security level."""
    if security >= 0.5:
        return "highsec"
    elif security > 0:
        return "lowsec"
    elif security == -1.0:
        return "wormhole"
    else:
        return "nullsec"


def get_ore_for_security(security: float, include_anomalies: bool = False) -> list:
    """Determine which ores can spawn at a given security level."""
    sec_class = get_security_class(security)
    ores = ORE_BY_SECURITY[sec_class]["belts"].copy()
    if include_anomalies:
        ores.extend(ORE_BY_SECURITY[sec_class]["anomalies"])
    return ores


def get_ores_for_mineral(mineral: str) -> list:
    """Find which ores contain a specific mineral."""
    result = []
    for ore, minerals in ORE_MINERALS.items():
        if mineral in minerals:
            result.append({"ore": ore, "yield": minerals[mineral]})
    return sorted(result, key=lambda x: x["yield"], reverse=True)


# ============================================================
# Mining Location Endpoints
# ============================================================

@router.get("/find-mineral")
async def find_mineral_locations(
    mineral: str = Query(..., description="Mineral to find (e.g., Mexallon, Tritanium)"),
    from_system: str = Query("Isikemi", description="Starting system name"),
    max_jumps: int = Query(10, ge=1, le=20, description="Maximum jumps to search"),
    min_security: float = Query(0.5, description="Minimum security status")
):
    """
    Find the nearest systems where you can mine a specific mineral.
    Returns systems sorted by number of asteroid belts and jump distance.
    """
    # Normalize mineral name
    mineral = mineral.title()

    # Find which ores contain this mineral
    ores_with_mineral = get_ores_for_mineral(mineral)
    if not ores_with_mineral:
        raise HTTPException(status_code=404, detail=f"Unknown mineral: {mineral}")

    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # Get starting system ID
                cur.execute('''
                    SELECT "solarSystemID" FROM "mapSolarSystems"
                    WHERE LOWER("solarSystemName") = LOWER(%s)
                ''', (from_system,))
                start_row = cur.fetchone()
                if not start_row:
                    raise HTTPException(status_code=404, detail=f"System not found: {from_system}")
                start_system_id = start_row[0]

                # BFS to find systems within max_jumps
                cur.execute('''
                    WITH RECURSIVE reachable AS (
                        SELECT
                            %s::bigint as system_id,
                            0 as jumps,
                            ARRAY[%s::bigint] as path

                        UNION

                        SELECT
                            j."toSolarSystemID",
                            r.jumps + 1,
                            r.path || j."toSolarSystemID"
                        FROM reachable r
                        JOIN "mapSolarSystemJumps" j ON r.system_id = j."fromSolarSystemID"
                        WHERE r.jumps < %s
                        AND NOT j."toSolarSystemID" = ANY(r.path)
                    )
                    SELECT DISTINCT ON (s."solarSystemID")
                        s."solarSystemID",
                        s."solarSystemName",
                        s.security,
                        r.jumps,
                        reg."regionName",
                        (SELECT COUNT(*) FROM "mapDenormalize" d
                         WHERE d."solarSystemID" = s."solarSystemID" AND d."groupID" = 9) as belt_count
                    FROM reachable r
                    JOIN "mapSolarSystems" s ON r.system_id = s."solarSystemID"
                    JOIN "mapRegions" reg ON s."regionID" = reg."regionID"
                    WHERE s.security >= %s
                    ORDER BY s."solarSystemID", r.jumps
                ''', (start_system_id, start_system_id, max_jumps, min_security))

                systems = []
                for row in cur.fetchall():
                    system_id, name, security, jumps, region, belt_count = row
                    security = float(security)

                    # Check which ores can spawn here
                    available_ores = get_ore_for_security(security)

                    # Find ores that contain our mineral AND can spawn here
                    matching_ores = []
                    for ore_info in ores_with_mineral:
                        if ore_info["ore"] in available_ores:
                            matching_ores.append(ore_info)

                    if matching_ores and belt_count > 0:
                        systems.append({
                            "system_name": name,
                            "security": round(security, 2),
                            "jumps": jumps,
                            "region": region,
                            "belt_count": belt_count,
                            "ores": matching_ores,
                            "best_ore": matching_ores[0]["ore"] if matching_ores else None,
                            "best_yield": matching_ores[0]["yield"] if matching_ores else 0,
                        })

                # Sort by: jumps first, then belt count (descending)
                systems.sort(key=lambda x: (x["jumps"], -x["belt_count"]))

                return {
                    "mineral": mineral,
                    "from_system": from_system,
                    "ores_containing_mineral": ores_with_mineral,
                    "systems": systems[:30],  # Top 30 results
                    "total_found": len(systems),
                }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@router.get("/system-info")
async def get_system_mining_info(
    system: str = Query(..., description="System name")
):
    """
    Get detailed mining information for a specific system.
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute('''
                    SELECT
                        s."solarSystemID",
                        s."solarSystemName",
                        s.security,
                        r."regionName",
                        c."constellationName"
                    FROM "mapSolarSystems" s
                    JOIN "mapRegions" r ON s."regionID" = r."regionID"
                    JOIN "mapConstellations" c ON s."constellationID" = c."constellationID"
                    WHERE LOWER(s."solarSystemName") = LOWER(%s)
                ''', (system,))
                row = cur.fetchone()
                if not row:
                    raise HTTPException(status_code=404, detail=f"System not found: {system}")

                system_id, name, security, region, constellation = row
                security = float(security)

                # Get asteroid belts
                cur.execute('''
                    SELECT "itemName" FROM "mapDenormalize"
                    WHERE "solarSystemID" = %s AND "groupID" = 9
                    ORDER BY "itemName"
                ''', (system_id,))
                belts = [r[0] for r in cur.fetchall()]

                # Get expected ores
                sec_class = get_security_class(security)
                belt_ores = ORE_BY_SECURITY[sec_class]["belts"]
                anomaly_ores = ORE_BY_SECURITY[sec_class]["anomalies"]
                ice_types = ORE_BY_SECURITY[sec_class]["ice"]

                # Build mineral availability from ores
                minerals_available = {}
                for ore in belt_ores + anomaly_ores:
                    if ore in ORE_MINERALS:
                        for mineral, amount in ORE_MINERALS[ore].items():
                            if mineral not in minerals_available:
                                minerals_available[mineral] = []
                            minerals_available[mineral].append({
                                "ore": ore,
                                "yield": amount,
                                "source": "belt" if ore in belt_ores else "anomaly"
                            })

                return {
                    "system_name": name,
                    "security": round(security, 2),
                    "security_class": sec_class,
                    "region": region,
                    "constellation": constellation,
                    "belt_count": len(belts),
                    "belts": belts,
                    "belt_ores": belt_ores,
                    "anomaly_ores": anomaly_ores,
                    "ice_types": ice_types,
                    "minerals_available": minerals_available,
                }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@router.get("/ore-info")
async def get_ore_info(
    ore: str = Query(None, description="Specific ore name (optional)")
):
    """
    Get information about ores and their mineral content.
    """
    if ore:
        ore = ore.title()
        if ore not in ORE_MINERALS:
            raise HTTPException(status_code=404, detail=f"Unknown ore: {ore}")
        return {
            "ore": ore,
            "minerals": ORE_MINERALS[ore],
            "found_in": [k for k, v in ORE_BY_SECURITY.items() if ore in v]
        }

    # Return all ores
    return {
        "ores": {ore: {"minerals": minerals} for ore, minerals in ORE_MINERALS.items()},
        "security_zones": ORE_BY_SECURITY,
    }
