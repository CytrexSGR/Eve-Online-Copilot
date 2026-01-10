"""
War Room Router Dependencies.

Provides dependency injection functions for all war room routers.
"""

from fastapi import Depends

from src.core.config import get_settings, Settings
from src.core.database import DatabasePool
from src.integrations.esi.client import ESIClient
from src.services.warroom.repository import WarRoomRepository
from src.services.warroom.sovereignty import SovereigntyService
from src.services.warroom.fw import FactionWarfareService
from src.services.warroom.analyzer import WarAnalyzer


def get_war_room_repository(settings: Settings = Depends(get_settings)) -> WarRoomRepository:
    """
    Dependency injection for WarRoomRepository.

    Creates shared repository instance for War Room services.
    """
    db_pool = DatabasePool(settings)
    return WarRoomRepository(db_pool)


def get_sovereignty_service(
    repository: WarRoomRepository = Depends(get_war_room_repository)
) -> SovereigntyService:
    """
    Dependency injection for SovereigntyService.

    Requires ESI client and War Room repository.
    """
    esi_client = ESIClient()
    return SovereigntyService(repository, esi_client)


def get_faction_warfare_service(
    repository: WarRoomRepository = Depends(get_war_room_repository)
) -> FactionWarfareService:
    """
    Dependency injection for FactionWarfareService.

    Requires ESI client and War Room repository.
    """
    esi_client = ESIClient()
    return FactionWarfareService(repository, esi_client)


def get_war_analyzer(
    repository: WarRoomRepository = Depends(get_war_room_repository)
) -> WarAnalyzer:
    """
    Dependency injection for WarAnalyzer.

    Requires only War Room repository.
    """
    return WarAnalyzer(repository)
