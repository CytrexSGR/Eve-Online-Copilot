"""
Unit tests for Route Service Models

Following TDD: Tests written first, then implement models.
"""

import pytest
from pydantic import ValidationError

from src.services.route.models import (
    SystemInfo,
    RouteSystemInfo,
    TravelTime,
    RouteResult,
    RouteLeg,
    MultiHubRoute,
    HubDistance,
    HubDistances,
    RouteWithDanger,
)


class TestSystemInfo:
    """Test SystemInfo model"""

    def test_create_system_info(self):
        """Test creating a valid SystemInfo"""
        system = SystemInfo(
            system_id=30000142,
            name="Jita",
            security=0.95,
            region_id=10000002,
            is_trade_hub=True,
            hub_name="jita"
        )

        assert system.system_id == 30000142
        assert system.name == "Jita"
        assert system.security == 0.95
        assert system.region_id == 10000002
        assert system.is_trade_hub is True
        assert system.hub_name == "jita"

    def test_system_info_defaults(self):
        """Test SystemInfo with default values"""
        system = SystemInfo(
            system_id=30000001,
            name="Test System",
            security=0.5,
            region_id=10000001
        )

        assert system.is_trade_hub is False
        assert system.hub_name is None

    def test_system_id_must_be_positive(self):
        """Test that system_id must be > 0"""
        with pytest.raises(ValidationError) as exc_info:
            SystemInfo(
                system_id=0,
                name="Invalid",
                security=0.5,
                region_id=10000001
            )

        assert "system_id" in str(exc_info.value)

    def test_security_bounds(self):
        """Test security must be between -1.0 and 1.0"""
        # Valid boundaries
        SystemInfo(system_id=1, name="Low", security=-1.0, region_id=1)
        SystemInfo(system_id=2, name="High", security=1.0, region_id=1)

        # Invalid: too low
        with pytest.raises(ValidationError) as exc_info:
            SystemInfo(system_id=3, name="TooLow", security=-1.1, region_id=1)
        assert "security" in str(exc_info.value)

        # Invalid: too high
        with pytest.raises(ValidationError) as exc_info:
            SystemInfo(system_id=4, name="TooHigh", security=1.1, region_id=1)
        assert "security" in str(exc_info.value)


class TestRouteSystemInfo:
    """Test RouteSystemInfo model (extends SystemInfo)"""

    def test_create_route_system_info(self):
        """Test creating RouteSystemInfo with additional fields"""
        system = RouteSystemInfo(
            system_id=30000142,
            name="Jita",
            security=0.95,
            region_id=10000002,
            is_trade_hub=True,
            hub_name="jita",
            jump_number=5,
            danger_score=2.5,
            kills_24h=10
        )

        assert system.jump_number == 5
        assert system.danger_score == 2.5
        assert system.kills_24h == 10

    def test_route_system_info_defaults(self):
        """Test RouteSystemInfo default values"""
        system = RouteSystemInfo(
            system_id=30000142,
            name="Jita",
            security=0.95,
            region_id=10000002,
            jump_number=0
        )

        assert system.danger_score == 0.0
        assert system.kills_24h == 0

    def test_jump_number_non_negative(self):
        """Test jump_number must be >= 0"""
        # Valid
        RouteSystemInfo(
            system_id=1,
            name="Test",
            security=0.5,
            region_id=1,
            jump_number=0
        )

        # Invalid
        with pytest.raises(ValidationError) as exc_info:
            RouteSystemInfo(
                system_id=1,
                name="Test",
                security=0.5,
                region_id=1,
                jump_number=-1
            )
        assert "jump_number" in str(exc_info.value)


class TestTravelTime:
    """Test TravelTime model"""

    def test_create_travel_time(self):
        """Test creating TravelTime"""
        travel = TravelTime(
            jumps=10,
            estimated_seconds=400,
            estimated_minutes=6.7,
            formatted="10 jumps (~7 min)"
        )

        assert travel.jumps == 10
        assert travel.estimated_seconds == 400
        assert travel.estimated_minutes == 6.7
        assert travel.formatted == "10 jumps (~7 min)"

    def test_jumps_non_negative(self):
        """Test jumps must be >= 0"""
        # Valid
        TravelTime(jumps=0, estimated_seconds=0, estimated_minutes=0.0, formatted="0 jumps")

        # Invalid
        with pytest.raises(ValidationError) as exc_info:
            TravelTime(jumps=-1, estimated_seconds=0, estimated_minutes=0.0, formatted="")
        assert "jumps" in str(exc_info.value)


class TestRouteResult:
    """Test RouteResult model"""

    def test_create_route_result(self):
        """Test creating RouteResult with systems"""
        systems = [
            RouteSystemInfo(
                system_id=1,
                name="Start",
                security=0.5,
                region_id=1,
                jump_number=0
            ),
            RouteSystemInfo(
                system_id=2,
                name="End",
                security=0.6,
                region_id=1,
                jump_number=1
            ),
        ]

        travel = TravelTime(
            jumps=1,
            estimated_seconds=40,
            estimated_minutes=0.7,
            formatted="1 jump (~1 min)"
        )

        route = RouteResult(
            systems=systems,
            total_jumps=1,
            travel_time=travel
        )

        assert len(route.systems) == 2
        assert route.total_jumps == 1
        assert route.travel_time.jumps == 1


class TestRouteLeg:
    """Test RouteLeg model"""

    def test_create_route_leg_without_systems(self):
        """Test creating RouteLeg without system details"""
        leg = RouteLeg(
            from_name="Jita",
            to_name="Amarr",
            jumps=15
        )

        assert leg.from_name == "Jita"
        assert leg.to_name == "Amarr"
        assert leg.jumps == 15
        assert leg.systems is None

    def test_create_route_leg_with_systems(self):
        """Test creating RouteLeg with system details"""
        systems = [
            {"name": "Jita", "security": 0.95},
            {"name": "Perimeter", "security": 0.90},
        ]

        leg = RouteLeg(
            from_name="Jita",
            to_name="Perimeter",
            jumps=1,
            systems=systems
        )

        assert leg.systems == systems
        assert len(leg.systems) == 2


class TestMultiHubRoute:
    """Test MultiHubRoute model"""

    def test_create_multi_hub_route(self):
        """Test creating MultiHubRoute"""
        legs = [
            RouteLeg(from_name="Isikemi", to_name="Jita", jumps=3),
            RouteLeg(from_name="Jita", to_name="Amarr", jumps=15),
        ]

        route = MultiHubRoute(
            total_jumps=18,
            route_legs=legs,
            order=["Isikemi", "Jita", "Amarr"],
            return_home=False
        )

        assert route.total_jumps == 18
        assert len(route.route_legs) == 2
        assert route.order == ["Isikemi", "Jita", "Amarr"]
        assert route.return_home is False

    def test_multi_hub_route_with_return(self):
        """Test MultiHubRoute with return_home=True"""
        legs = [
            RouteLeg(from_name="Isikemi", to_name="Jita", jumps=3),
            RouteLeg(from_name="Jita", to_name="Isikemi", jumps=3),
        ]

        route = MultiHubRoute(
            total_jumps=6,
            route_legs=legs,
            order=["Isikemi", "Jita", "Isikemi"],
            return_home=True
        )

        assert route.return_home is True
        assert route.order[0] == route.order[-1]


class TestHubDistance:
    """Test HubDistance model"""

    def test_create_hub_distance_reachable(self):
        """Test creating HubDistance for reachable hub"""
        dist = HubDistance(
            jumps=10,
            time="10 jumps (~7 min)",
            reachable=True
        )

        assert dist.jumps == 10
        assert dist.time == "10 jumps (~7 min)"
        assert dist.reachable is True

    def test_create_hub_distance_unreachable(self):
        """Test creating HubDistance for unreachable hub"""
        dist = HubDistance(
            jumps=None,
            time="No HighSec route",
            reachable=False
        )

        assert dist.jumps is None
        assert dist.time == "No HighSec route"
        assert dist.reachable is False


class TestHubDistances:
    """Test HubDistances model"""

    def test_create_hub_distances(self):
        """Test creating HubDistances result"""
        distances = {
            "jita": HubDistance(jumps=3, time="3 jumps (~2 min)", reachable=True),
            "amarr": HubDistance(jumps=15, time="15 jumps (~10 min)", reachable=True),
            "rens": HubDistance(jumps=None, time="No HighSec route", reachable=False),
        }

        result = HubDistances(
            from_system="Isikemi",
            from_system_id=30001365,
            distances=distances
        )

        assert result.from_system == "Isikemi"
        assert result.from_system_id == 30001365
        assert len(result.distances) == 3
        assert result.distances["jita"].jumps == 3
        assert result.distances["rens"].reachable is False


class TestRouteWithDanger:
    """Test RouteWithDanger model"""

    def test_create_route_with_danger(self):
        """Test creating RouteWithDanger"""
        route = [
            RouteSystemInfo(
                system_id=1,
                name="Safe",
                security=0.9,
                region_id=1,
                jump_number=0,
                danger_score=1.0,
                kills_24h=2
            ),
            RouteSystemInfo(
                system_id=2,
                name="Dangerous",
                security=0.5,
                region_id=1,
                jump_number=1,
                danger_score=8.0,
                kills_24h=50
            ),
        ]

        dangerous_systems = [
            {"name": "Dangerous", "kills": 50, "score": 8.0}
        ]

        result = RouteWithDanger(
            route=route,
            total_danger_score=9.0,
            average_danger=4.5,
            dangerous_systems=dangerous_systems,
            warning=True
        )

        assert len(result.route) == 2
        assert result.total_danger_score == 9.0
        assert result.average_danger == 4.5
        assert len(result.dangerous_systems) == 1
        assert result.warning is True

    def test_route_with_danger_no_warnings(self):
        """Test RouteWithDanger with safe route"""
        route = [
            RouteSystemInfo(
                system_id=1,
                name="Safe1",
                security=0.9,
                region_id=1,
                jump_number=0,
                danger_score=0.5,
                kills_24h=1
            ),
            RouteSystemInfo(
                system_id=2,
                name="Safe2",
                security=0.9,
                region_id=1,
                jump_number=1,
                danger_score=1.0,
                kills_24h=2
            ),
        ]

        result = RouteWithDanger(
            route=route,
            total_danger_score=1.5,
            average_danger=0.75,
            dangerous_systems=[],
            warning=False
        )

        assert result.warning is False
        assert len(result.dangerous_systems) == 0
