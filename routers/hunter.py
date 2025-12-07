"""
Market Hunter Router
Endpoints for finding profitable manufacturing opportunities
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List
from database import get_db_connection

router = APIRouter(prefix="/api/hunter", tags=["Market Hunter"])


@router.get("/categories")
async def get_categories():
    """
    Get all available categories and groups for filtering.
    Returns hierarchical structure of Category -> Groups.
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT category, group_name, COUNT(*) as count
                    FROM manufacturing_opportunities
                    GROUP BY category, group_name
                    ORDER BY category, count DESC
                """)
                rows = cur.fetchall()

                # Build hierarchical structure
                categories = {}
                for row in rows:
                    cat = row[0] or "Unknown"
                    group = row[1]
                    count = row[2]

                    if cat not in categories:
                        categories[cat] = {"count": 0, "groups": []}
                    categories[cat]["count"] += count
                    categories[cat]["groups"].append({"name": group, "count": count})

                return {
                    "categories": categories,
                    "total_items": sum(c["count"] for c in categories.values())
                }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@router.get("/market-tree")
async def get_market_tree():
    """
    Get EVE Online market group hierarchy (3 levels) with item counts.
    Returns tree structure like: Ships > Frigates > Standard Frigates > Amarr
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # Get 3-level market hierarchy with item counts
                cur.execute('''
                    SELECT
                        mg1."marketGroupID" as level1_id,
                        mg1."marketGroupName" as level1,
                        mg2."marketGroupID" as level2_id,
                        mg2."marketGroupName" as level2,
                        mg3."marketGroupID" as level3_id,
                        mg3."marketGroupName" as level3,
                        COUNT(DISTINCT mo.product_id) as items
                    FROM manufacturing_opportunities mo
                    JOIN "invTypes" t ON mo.product_id = t."typeID"
                    LEFT JOIN "invMarketGroups" mg3 ON t."marketGroupID" = mg3."marketGroupID"
                    LEFT JOIN "invMarketGroups" mg2 ON mg3."parentGroupID" = mg2."marketGroupID"
                    LEFT JOIN "invMarketGroups" mg1 ON mg2."parentGroupID" = mg1."marketGroupID"
                    GROUP BY mg1."marketGroupID", mg1."marketGroupName",
                             mg2."marketGroupID", mg2."marketGroupName",
                             mg3."marketGroupID", mg3."marketGroupName"
                    ORDER BY mg1."marketGroupName", mg2."marketGroupName", mg3."marketGroupName"
                ''')
                rows = cur.fetchall()

                # Build tree structure
                tree = {}
                for row in rows:
                    level1_id, level1, level2_id, level2, level3_id, level3, items = row

                    # Handle null levels (some items may not have full hierarchy)
                    level1 = level1 or "Other"
                    level2 = level2 or "Other"
                    level3 = level3 or "Other"

                    if level1 not in tree:
                        tree[level1] = {"id": level1_id, "count": 0, "children": {}}

                    if level2 not in tree[level1]["children"]:
                        tree[level1]["children"][level2] = {"id": level2_id, "count": 0, "children": {}}

                    tree[level1]["children"][level2]["children"][level3] = {
                        "id": level3_id,
                        "count": items
                    }
                    tree[level1]["children"][level2]["count"] += items
                    tree[level1]["count"] += items

                return {"tree": tree}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@router.get("/scan")
async def hunter_scan(
    min_roi: float = Query(0, description="Minimum ROI percentage"),
    min_profit: float = Query(0, description="Minimum profit in ISK"),
    max_difficulty: int = Query(5, ge=1, le=5, description="Maximum difficulty level"),
    top: int = Query(100, ge=1, le=500, description="Number of results"),
    category: str = Query(None, description="Filter by category"),
    groups: str = Query(None, description="Comma-separated group names to filter"),
    market_group: int = Query(None, description="Filter by EVE market group ID"),
    search: str = Query(None, description="Search product name"),
    sort_by: str = Query("profit", description="Sort field: profit, roi, material_cost, sell_price, name")
):
    """
    Get T1 manufacturing opportunities from database.

    Returns results instantly from pre-calculated data.
    Data is refreshed every 5 minutes by background job.

    Filter modes:
    - Profit mode: Use min_roi, min_profit filters
    - Browse mode: Set min_roi=0, min_profit=0 and use category/groups/search/market_group
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # Build query with filters
                where_clauses = ["mo.roi >= %s", "mo.profit >= %s", "mo.difficulty <= %s"]
                params = [min_roi, min_profit, max_difficulty]
                joins = []

                if category and category != "All":
                    where_clauses.append("mo.category = %s")
                    params.append(category)

                # Group filter (comma-separated list)
                if groups:
                    group_list = [g.strip() for g in groups.split(",") if g.strip()]
                    if group_list:
                        placeholders = ", ".join(["%s"] * len(group_list))
                        where_clauses.append(f"mo.group_name IN ({placeholders})")
                        params.extend(group_list)

                # Market group filter - matches this group or any child groups
                if market_group:
                    joins.append('JOIN "invTypes" t ON mo.product_id = t."typeID"')
                    joins.append('LEFT JOIN "invMarketGroups" mg3 ON t."marketGroupID" = mg3."marketGroupID"')
                    joins.append('LEFT JOIN "invMarketGroups" mg2 ON mg3."parentGroupID" = mg2."marketGroupID"')
                    joins.append('LEFT JOIN "invMarketGroups" mg1 ON mg2."parentGroupID" = mg1."marketGroupID"')
                    where_clauses.append(
                        "(t.\"marketGroupID\" = %s OR mg3.\"parentGroupID\" = %s OR mg2.\"parentGroupID\" = %s OR mg1.\"marketGroupID\" = %s)"
                    )
                    params.extend([market_group, market_group, market_group, market_group])

                # Text search in product name
                if search:
                    where_clauses.append("mo.product_name ILIKE %s")
                    params.append(f"%{search}%")

                # Determine sort order
                sort_column = "mo.profit"
                sort_direction = "DESC"
                if sort_by == "roi":
                    sort_column = "mo.roi"
                elif sort_by == "material_cost":
                    sort_column = "mo.cheapest_material_cost"
                elif sort_by == "sell_price":
                    sort_column = "mo.best_sell_price"
                elif sort_by == "name":
                    sort_column = "mo.product_name"
                    sort_direction = "ASC"

                join_clause = " ".join(joins) if joins else ""
                query = f"""
                    SELECT
                        mo.product_id, mo.blueprint_id, mo.product_name, mo.category, mo.group_name,
                        mo.difficulty, mo.cheapest_material_cost, mo.best_sell_price, mo.profit, mo.roi,
                        mo.updated_at
                    FROM manufacturing_opportunities mo
                    {join_clause}
                    WHERE {' AND '.join(where_clauses)}
                    ORDER BY {sort_column} {sort_direction}
                    LIMIT %s
                """
                params.append(top)

                cur.execute(query, params)
                rows = cur.fetchall()

                # Get total count for stats
                cur.execute("SELECT COUNT(*), MAX(updated_at) FROM manufacturing_opportunities")
                stats_row = cur.fetchone()
                total_in_db = stats_row[0] if stats_row else 0
                last_updated = stats_row[1] if stats_row else None

                results = []
                for row in rows:
                    results.append({
                        "product_id": row[0],
                        "blueprint_id": row[1],
                        "product_name": row[2],
                        "category": row[3] or "Unknown",
                        "group_name": row[4],
                        "difficulty": row[5],
                        "material_cost": float(row[6]) if row[6] else 0,
                        "sell_price": float(row[7]) if row[7] else 0,
                        "profit": float(row[8]) if row[8] else 0,
                        "roi": min(float(row[9]), 9999) if row[9] else 0,
                        "volume_available": 0
                    })

                return {
                    "scan_id": last_updated.isoformat() if last_updated else "unknown",
                    "results": results,
                    "summary": {
                        "total_scanned": total_in_db,
                        "profitable": len(results),
                        "avg_roi": sum(r['roi'] for r in results) / len(results) if results else 0
                    },
                    "cached": True,
                    "last_updated": last_updated.isoformat() if last_updated else None
                }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
