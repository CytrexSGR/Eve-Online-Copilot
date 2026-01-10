"""
Map and Route Endpoints Router.

Provides endpoints for map data and safe route calculation.
"""

from fastapi import APIRouter, HTTPException, Query

from src.database import get_db_connection
from src.route_service import route_service

router = APIRouter()


@router.get("/map/systems")
async def get_map_systems():
    """
    Get all solar system positions for 2D map rendering.

    Returns system coordinates (x, z for 2D), region info, and security status.
    Used by Canvas 2D Battle Map for fast rendering.

    Returns:
        {
            "systems": [...],
            "total": 8437
        }
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT
                        ms."solarSystemID",
                        ms."solarSystemName",
                        ms."regionID",
                        mr."regionName",
                        ms.x,
                        ms.z,
                        ms.security
                    FROM "mapSolarSystems" ms
                    JOIN "mapRegions" mr ON mr."regionID" = ms."regionID"
                    ORDER BY ms."solarSystemID"
                """)

                rows = cur.fetchall()

                systems = []
                for row in rows:
                    system_id, system_name, region_id, region_name, x, z, security = row
                    systems.append({
                        "system_id": system_id,
                        "system_name": system_name,
                        "region_id": region_id,
                        "region_name": region_name,
                        "x": float(x),
                        "z": float(z),
                        "security": float(security) if security else 0.0
                    })

                return {
                    "systems": systems,
                    "total": len(systems)
                }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get map systems: {str(e)}")


@router.get("/route/safe/{from_system}/{to_system}")
async def get_safe_route(
    from_system: int,
    to_system: int,
    avoid_lowsec: bool = Query(True),
    avoid_nullsec: bool = Query(True)
):
    """Get route with danger analysis (legacy service)"""
    try:
        result = route_service.get_route_with_danger(
            from_system, to_system, avoid_lowsec, avoid_nullsec
        )

        if not result:
            raise HTTPException(status_code=404, detail="No route found")

        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
