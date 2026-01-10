"""
Stored Reports Service
Handles reading and writing pre-generated reports to PostgreSQL.
Reports are generated every 6 hours by cron and stored persistently.
"""

import json
from datetime import datetime
from typing import Dict, Optional
from src.database import get_db_connection


# Report types
REPORT_TYPES = [
    'pilot_intelligence',
    'war_profiteering',
    'alliance_wars',
    'trade_routes',
    'war_economy',
    'strategic_briefing',
    'alliance_wars_analysis',
    'war_economy_analysis'
]


def get_report(report_type: str) -> Optional[Dict]:
    """
    Get a stored report from the database.
    Returns None if report doesn't exist.
    """
    if report_type not in REPORT_TYPES:
        raise ValueError(f"Unknown report type: {report_type}")

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT report_data, generated_at
                FROM stored_reports
                WHERE report_type = %s
            """, (report_type,))

            row = cur.fetchone()
            if row:
                report_data = row[0]
                generated_at = row[1]

                # Add metadata to report
                if isinstance(report_data, dict):
                    report_data['_generated_at'] = generated_at.isoformat() if generated_at else None

                return report_data

            return None


def save_report(report_type: str, report_data: Dict, generation_time: float = None) -> bool:
    """
    Save a generated report to the database.
    Uses UPSERT to replace existing report.
    """
    if report_type not in REPORT_TYPES:
        raise ValueError(f"Unknown report type: {report_type}")

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO stored_reports (report_type, report_data, generated_at, generation_time_seconds, version)
                VALUES (%s, %s, NOW(), %s, 1)
                ON CONFLICT (report_type) DO UPDATE SET
                    report_data = EXCLUDED.report_data,
                    generated_at = NOW(),
                    generation_time_seconds = EXCLUDED.generation_time_seconds,
                    version = stored_reports.version + 1
            """, (report_type, json.dumps(report_data), generation_time))

            conn.commit()
            return True


def get_report_status() -> Dict:
    """
    Get status of all stored reports.
    Returns info about when each report was last generated.
    """
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT report_type, generated_at, generation_time_seconds, version
                FROM stored_reports
                ORDER BY report_type
            """)

            rows = cur.fetchall()

            status = {}
            for row in rows:
                report_type, generated_at, gen_time, version = row
                age_hours = (datetime.utcnow() - generated_at.replace(tzinfo=None)).total_seconds() / 3600 if generated_at else None

                status[report_type] = {
                    'generated_at': generated_at.isoformat() if generated_at else None,
                    'age_hours': round(age_hours, 1) if age_hours else None,
                    'generation_time_seconds': round(gen_time, 1) if gen_time else None,
                    'version': version,
                    'stale': age_hours > 7 if age_hours else True  # Stale if older than 7 hours
                }

            # Add missing reports
            for rt in REPORT_TYPES:
                if rt not in status:
                    status[rt] = {
                        'generated_at': None,
                        'age_hours': None,
                        'generation_time_seconds': None,
                        'version': 0,
                        'stale': True
                    }

            return status


def delete_report(report_type: str) -> bool:
    """Delete a stored report."""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM stored_reports WHERE report_type = %s", (report_type,))
            conn.commit()
            return cur.rowcount > 0
