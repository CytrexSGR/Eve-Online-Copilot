"""
Route Service Repository

Data access layer for route calculation, solar system data, and jump graph.
"""

from typing import Dict, List, Optional, Any
from psycopg2.extras import RealDictCursor

from src.core.database import DatabasePool
from src.core.exceptions import EVECopilotError
from src.services.route.constants import SYSTEM_ID_TO_HUB


class RouteRepository:
    """
    Repository for route calculation data

    Handles loading solar system data and jump graph from database.
    Implements lazy loading pattern with caching.
    """

    def __init__(self, db: DatabasePool):
        """
        Initialize repository with database pool

        Args:
            db: DatabasePool instance for database access
        """
        self._db = db
        self._systems: Optional[Dict[int, Dict[str, Any]]] = None
        self._graph: Optional[Dict[int, List[int]]] = None
        self._loaded = False

    def load_systems(self) -> Dict[int, Dict[str, Any]]:
        """
        Load all solar systems from database

        Returns cached data if already loaded (lazy loading pattern).

        Returns:
            Dict mapping system_id to system info dict with keys:
                - name: str
                - security: float
                - region_id: int

        Raises:
            EVECopilotError: If database query fails
        """
        if self._systems is not None:
            return self._systems

        try:
            self._systems = {}

            with self._db.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute('''
                        SELECT "solarSystemID", "solarSystemName", "security", "regionID"
                        FROM "mapSolarSystems"
                    ''')

                    for row in cur.fetchall():
                        self._systems[row['solarSystemID']] = {
                            'name': row['solarSystemName'],
                            'security': float(row['security']),
                            'region_id': row['regionID']
                        }

            return self._systems

        except Exception as e:
            raise EVECopilotError(f"Failed to load systems from database: {str(e)}") from e

    def load_jump_graph(self) -> Dict[int, List[int]]:
        """
        Load bidirectional jump graph from database

        Returns cached data if already loaded (lazy loading pattern).

        Returns:
            Dict mapping system_id to list of connected system_ids

        Raises:
            EVECopilotError: If database query fails
        """
        if self._graph is not None:
            return self._graph

        try:
            self._graph = {}

            with self._db.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute('''
                        SELECT "fromSolarSystemID", "toSolarSystemID"
                        FROM "mapSolarSystemJumps"
                    ''')

                    for row in cur.fetchall():
                        from_id = row['fromSolarSystemID']
                        to_id = row['toSolarSystemID']

                        if from_id not in self._graph:
                            self._graph[from_id] = []
                        self._graph[from_id].append(to_id)

            return self._graph

        except Exception as e:
            raise EVECopilotError(f"Failed to load jump graph from database: {str(e)}") from e

    def get_system_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Find system by name (case-insensitive)

        Args:
            name: System name to search for

        Returns:
            Dict with system info or None if not found:
                - system_id: int
                - name: str
                - security: float
                - region_id: int

        Raises:
            EVECopilotError: If database query fails
        """
        try:
            with self._db.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute('''
                        SELECT "solarSystemID", "solarSystemName", "security", "regionID"
                        FROM "mapSolarSystems"
                        WHERE LOWER("solarSystemName") = LOWER(%s)
                    ''', (name,))

                    row = cur.fetchone()

                    if row is None:
                        return None

                    system_id = row['solarSystemID']
                    return {
                        'system_id': system_id,
                        'name': row['solarSystemName'],
                        'security': float(row['security']),
                        'region_id': row['regionID'],
                    }

        except Exception as e:
            raise EVECopilotError(f"Failed to find system by name '{name}': {str(e)}") from e

    def search_systems(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Search systems by partial name (case-insensitive)

        Args:
            query: Partial system name to search for
            limit: Maximum number of results (default 10)

        Returns:
            List of system dicts with keys:
                - system_id: int
                - name: str
                - security: float
                - region_id: int

        Raises:
            EVECopilotError: If database query fails
        """
        try:
            with self._db.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute('''
                        SELECT "solarSystemID", "solarSystemName", "security", "regionID"
                        FROM "mapSolarSystems"
                        WHERE LOWER("solarSystemName") LIKE LOWER(%s)
                        LIMIT %s
                    ''', (f'%{query}%', limit))

                    results = []
                    for row in cur.fetchall():
                        system_id = row['solarSystemID']
                        results.append({
                            'system_id': system_id,
                            'name': row['solarSystemName'],
                            'security': float(row['security']),
                            'region_id': row['regionID'],
                        })

                    return results

        except Exception as e:
            raise EVECopilotError(f"Failed to search systems with query '{query}': {str(e)}") from e
