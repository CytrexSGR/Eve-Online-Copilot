"""
EVE Co-Pilot Database Module
Handles all PostgreSQL SDE queries
"""

import psycopg2
from psycopg2.extras import RealDictCursor
from contextlib import contextmanager
from typing import Optional, Dict, List, Any
from config import DB_CONFIG


@contextmanager
def get_db_connection():
    """Context manager for database connections"""
    conn = psycopg2.connect(**DB_CONFIG)
    try:
        yield conn
    finally:
        conn.close()


def get_item_info(type_id: int) -> dict | None:
    """Get item information from invTypes"""
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute('''
                SELECT "typeID", "typeName", "groupID", "volume", "basePrice"
                FROM "invTypes"
                WHERE "typeID" = %s
            ''', (type_id,))
            return cur.fetchone()


def get_item_by_name(name: str, group_id: Optional[int] = None) -> List[Dict[str, Any]]:
    """Get item by name (case-insensitive partial match), optionally filtered by group"""
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            if group_id is not None:
                cur.execute('''
                    SELECT "typeID", "typeName", "groupID", "volume", "basePrice"
                    FROM "invTypes"
                    WHERE "groupID" = %s
                      AND LOWER("typeName") LIKE LOWER(%s)
                      AND "published" = 1
                    ORDER BY "typeName"
                    LIMIT 50
                ''', (group_id, f'%{name}%'))
            else:
                cur.execute('''
                    SELECT "typeID", "typeName", "groupID", "volume", "basePrice"
                    FROM "invTypes"
                    WHERE LOWER("typeName") LIKE LOWER(%s)
                    LIMIT 10
                ''', (f'%{name}%',))
            return cur.fetchall()


def get_blueprint_materials(type_id: int) -> list:
    """
    Get manufacturing materials for a blueprint product
    The type_id should be the product ID, we need to find the blueprint first
    """
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # First, find the blueprint that produces this item
            # activityID 1 = Manufacturing
            cur.execute('''
                SELECT bp."typeID" as blueprint_id
                FROM "industryActivityProducts" iap
                JOIN "invTypes" bp ON iap."typeID" = bp."typeID"
                WHERE iap."productTypeID" = %s
                AND iap."activityID" = 1
                LIMIT 1
            ''', (type_id,))

            blueprint = cur.fetchone()
            if not blueprint:
                return []

            blueprint_id = blueprint['blueprint_id']

            # Get materials for this blueprint
            cur.execute('''
                SELECT
                    iam."materialTypeID" as type_id,
                    it."typeName" as material_name,
                    iam."quantity"
                FROM "industryActivityMaterials" iam
                JOIN "invTypes" it ON iam."materialTypeID" = it."typeID"
                WHERE iam."typeID" = %s
                AND iam."activityID" = 1
                ORDER BY iam."quantity" DESC
            ''', (blueprint_id,))

            return cur.fetchall()


def get_blueprint_info(type_id: int) -> dict | None:
    """Get blueprint manufacturing info including time"""
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Find blueprint for product
            cur.execute('''
                SELECT
                    iap."typeID" as blueprint_id,
                    bp."typeName" as blueprint_name,
                    ia."time" as base_time,
                    iap."quantity" as output_quantity
                FROM "industryActivityProducts" iap
                JOIN "invTypes" bp ON iap."typeID" = bp."typeID"
                JOIN "industryActivity" ia ON ia."typeID" = iap."typeID" AND ia."activityID" = 1
                WHERE iap."productTypeID" = %s
                AND iap."activityID" = 1
                LIMIT 1
            ''', (type_id,))

            return cur.fetchone()


def get_items_by_group(group_id: int) -> list:
    """Get all items in a specific group"""
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute('''
                SELECT "typeID", "typeName", "volume", "basePrice"
                FROM "invTypes"
                WHERE "groupID" = %s
                AND "published" = 1
                ORDER BY "typeName"
            ''', (group_id,))
            return cur.fetchall()


def get_group_by_name(name: str) -> list:
    """Find groups by name"""
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute('''
                SELECT g."groupID", g."groupName", c."categoryName"
                FROM "invGroups" g
                JOIN "invCategories" c ON g."categoryID" = c."categoryID"
                WHERE LOWER(g."groupName") LIKE LOWER(%s)
                LIMIT 20
            ''', (f'%{name}%',))
            return cur.fetchall()


def get_market_groups() -> list:
    """Get all market groups"""
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute('''
                SELECT "marketGroupID", "marketGroupName", "parentGroupID"
                FROM "invMarketGroups"
                ORDER BY "marketGroupName"
            ''')
            return cur.fetchall()


def get_material_composition(type_id: int) -> list:
    """Get what materials an item is made of (if it's craftable)"""
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Check if this item can be manufactured
            cur.execute('''
                SELECT
                    iap."typeID" as blueprint_id,
                    iam."materialTypeID" as material_type_id,
                    it."typeName" as material_name,
                    iam."quantity"
                FROM "industryActivityProducts" iap
                JOIN "industryActivityMaterials" iam
                    ON iam."typeID" = iap."typeID" AND iam."activityID" = 1
                JOIN "invTypes" it ON iam."materialTypeID" = it."typeID"
                WHERE iap."productTypeID" = %s
                AND iap."activityID" = 1
                ORDER BY iam."quantity" DESC
            ''', (type_id,))
            return cur.fetchall()
