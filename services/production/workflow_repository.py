"""
Production Workflow Repository

Handles database operations for production job management.
Manages job tracking, material requirements, and make-or-buy decisions.
"""

from typing import List, Dict, Any, Optional
from src.database import get_db_connection


class ProductionWorkflowRepository:
    """Repository for production workflow data access"""

    def create_job(
        self,
        character_id: int,
        item_type_id: int,
        blueprint_type_id: int,
        me_level: int,
        te_level: int,
        runs: int,
        facility_id: Optional[int] = None,
        system_id: Optional[int] = None,
        total_cost: Optional[float] = None,
        expected_revenue: Optional[float] = None
    ) -> Optional[int]:
        """
        Create a new production job

        Returns:
            Job ID if successful, None otherwise
        """
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        INSERT INTO production_jobs
                        (character_id, item_type_id, blueprint_type_id,
                         me_level, te_level, runs, facility_id, system_id,
                         total_cost, expected_revenue, status)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'planned')
                        RETURNING id
                    """, (character_id, item_type_id, blueprint_type_id,
                          me_level, te_level, runs, facility_id, system_id,
                          total_cost, expected_revenue))

                    result = cursor.fetchone()
                    conn.commit()
                    return result[0] if result else None
        except Exception as e:
            print(f"Error creating job: {e}")
            return None

    def add_job_material(
        self,
        job_id: int,
        material_type_id: int,
        quantity_needed: int,
        decision: str,
        cost_per_unit: Optional[float] = None,
        total_cost: Optional[float] = None
    ) -> Optional[int]:
        """Add a material requirement to a job"""
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        INSERT INTO production_job_materials
                        (job_id, material_type_id, quantity_needed, decision,
                         cost_per_unit, total_cost)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        RETURNING id
                    """, (job_id, material_type_id, quantity_needed, decision,
                          cost_per_unit, total_cost))

                    result = cursor.fetchone()
                    conn.commit()
                    return result[0] if result else None
        except Exception as e:
            print(f"Error adding job material: {e}")
            return None

    def get_jobs(
        self,
        character_id: int,
        status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get jobs for a character, optionally filtered by status"""
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    if status:
                        cursor.execute("""
                            SELECT
                                pj.id,
                                pj.item_type_id,
                                t."typeName",
                                pj.runs,
                                pj.status,
                                pj.me_level,
                                pj.te_level,
                                pj.total_cost,
                                pj.expected_revenue,
                                pj.actual_revenue,
                                pj.started_at,
                                pj.completed_at,
                                pj.created_at
                            FROM production_jobs pj
                            JOIN "invTypes" t ON pj.item_type_id = t."typeID"
                            WHERE pj.character_id = %s AND pj.status = %s
                            ORDER BY pj.created_at DESC
                        """, (character_id, status))
                    else:
                        cursor.execute("""
                            SELECT
                                pj.id,
                                pj.item_type_id,
                                t."typeName",
                                pj.runs,
                                pj.status,
                                pj.me_level,
                                pj.te_level,
                                pj.total_cost,
                                pj.expected_revenue,
                                pj.actual_revenue,
                                pj.started_at,
                                pj.completed_at,
                                pj.created_at
                            FROM production_jobs pj
                            JOIN "invTypes" t ON pj.item_type_id = t."typeID"
                            WHERE pj.character_id = %s
                            ORDER BY pj.created_at DESC
                        """, (character_id,))

                    rows = cursor.fetchall()
                    return [
                        {
                            'job_id': row[0],
                            'item_type_id': row[1],
                            'item_name': row[2],
                            'runs': row[3],
                            'status': row[4],
                            'me_level': row[5],
                            'te_level': row[6],
                            'total_cost': float(row[7]) if row[7] else None,
                            'expected_revenue': float(row[8]) if row[8] else None,
                            'actual_revenue': float(row[9]) if row[9] else None,
                            'started_at': row[10],
                            'completed_at': row[11],
                            'created_at': row[12]
                        }
                        for row in rows
                    ]
        except Exception as e:
            print(f"Error getting jobs: {e}")
            return []

    def update_job(
        self,
        job_id: int,
        status: Optional[str] = None,
        actual_revenue: Optional[float] = None
    ) -> bool:
        """Update job status and/or actual revenue"""
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    updates = []
                    params = []

                    if status:
                        updates.append("status = %s")
                        params.append(status)

                        if status == 'active':
                            updates.append("started_at = NOW()")
                        elif status == 'completed':
                            updates.append("completed_at = NOW()")

                    if actual_revenue is not None:
                        updates.append("actual_revenue = %s")
                        params.append(actual_revenue)

                    if not updates:
                        return False

                    params.append(job_id)
                    query = f"""
                        UPDATE production_jobs
                        SET {', '.join(updates)}
                        WHERE id = %s
                    """

                    cursor.execute(query, params)
                    conn.commit()
                    return True
        except Exception as e:
            print(f"Error updating job: {e}")
            return False
