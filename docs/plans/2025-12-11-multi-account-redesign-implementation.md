# EVE Co-Pilot 2.0 - Multi-Account Redesign Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Transform EVE Co-Pilot from single-character focus to flexible 3-account management with Dashboard-first UX.

**Architecture:** Backend aggregation services feed new Dashboard page with opportunities from Market Hunter, Arbitrage, and War Room. Frontend refactored from 14 pages to 5 activity-based sections with nested routing. Character selection only appears when needed (during actions).

**Tech Stack:** FastAPI (Python 3.11+), React 19 + TypeScript 5.9, Vite 7, TanStack React Query 5, PostgreSQL 16

---

## Prerequisites

**Read these documents first:**
- `/home/cytrex/eve_copilot/docs/plans/2025-12-11-multi-account-redesign-design.md` - Full design specification
- `/home/cytrex/eve_copilot/CLAUDE.md` - Development guide
- `/home/cytrex/eve_copilot/CLAUDE.backend.md` - Backend patterns
- `/home/cytrex/eve_copilot/CLAUDE.frontend.md` - Frontend patterns

**Character IDs for testing:**
- Artallus: 526379435
- Cytrex: 1117367444
- Cytricia: 110592475

**Base Directory:** `/home/cytrex/eve_copilot/`

---

## Phase 1: Backend - Dashboard Aggregation Service

### Task 1.1: Create Dashboard Service Structure

**Files:**
- Create: `services/dashboard_service.py`
- Create: `tests/services/test_dashboard_service.py`

**Step 1: Write the failing test**

Create `tests/services/test_dashboard_service.py`:

```python
import pytest
from services.dashboard_service import DashboardService

@pytest.fixture
def dashboard_service():
    return DashboardService()

def test_get_opportunities_returns_list(dashboard_service):
    """Should return a list of opportunities"""
    result = dashboard_service.get_opportunities()
    assert isinstance(result, list)

def test_get_opportunities_includes_production(dashboard_service):
    """Should include production opportunities"""
    result = dashboard_service.get_opportunities()
    production_ops = [op for op in result if op['category'] == 'production']
    assert len(production_ops) > 0

def test_get_opportunities_includes_trade(dashboard_service):
    """Should include trade opportunities"""
    result = dashboard_service.get_opportunities()
    trade_ops = [op for op in result if op['category'] == 'trade']
    assert len(trade_ops) > 0

def test_get_opportunities_includes_war_demand(dashboard_service):
    """Should include war demand opportunities"""
    result = dashboard_service.get_opportunities()
    war_ops = [op for op in result if op['category'] == 'war_demand']
    assert len(war_ops) > 0

def test_opportunities_sorted_by_priority(dashboard_service):
    """Should sort by category priority: production > trade > war_demand"""
    result = dashboard_service.get_opportunities()
    categories = [op['category'] for op in result[:10]]

    # Production should appear before trade and war_demand
    if 'production' in categories and 'trade' in categories:
        assert categories.index('production') < categories.index('trade')
```

**Step 2: Run test to verify it fails**

```bash
cd /home/cytrex/eve_copilot
pytest tests/services/test_dashboard_service.py -v
```

Expected: FAIL with "ModuleNotFoundError: No module named 'services.dashboard_service'"

**Step 3: Write minimal implementation**

Create `services/dashboard_service.py`:

```python
"""
Dashboard aggregation service for EVE Co-Pilot 2.0

Aggregates opportunities from:
- Market Hunter (manufacturing)
- Arbitrage Finder (trading)
- War Analyzer (combat demand)

Sorts by user priorities: Industrie → Handel → War Room
"""

from typing import List, Dict, Any
from datetime import datetime, timedelta


class DashboardService:
    """Aggregates and prioritizes opportunities for dashboard"""

    CATEGORY_PRIORITY = {
        'production': 1,
        'trade': 2,
        'war_demand': 3
    }

    def __init__(self):
        self.cache = {}
        self.cache_ttl = timedelta(minutes=5)

    def get_opportunities(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get top opportunities across all categories

        Args:
            limit: Maximum number of opportunities to return (default 10)

        Returns:
            List of opportunity dicts sorted by priority and profitability
        """
        # Check cache
        cache_key = f"opportunities_{limit}"
        if cache_key in self.cache:
            cached_time, cached_data = self.cache[cache_key]
            if datetime.now() - cached_time < self.cache_ttl:
                return cached_data

        opportunities = []

        # Aggregate from all sources
        opportunities.extend(self._get_production_opportunities())
        opportunities.extend(self._get_trade_opportunities())
        opportunities.extend(self._get_war_demand_opportunities())

        # Sort by priority and profit
        sorted_ops = self._sort_opportunities(opportunities)

        # Limit results
        result = sorted_ops[:limit]

        # Cache result
        self.cache[cache_key] = (datetime.now(), result)

        return result

    def _get_production_opportunities(self) -> List[Dict[str, Any]]:
        """Get manufacturing opportunities from Market Hunter"""
        # TODO: Integrate with existing market_hunter.py
        # For now, return empty list to make tests pass
        return []

    def _get_trade_opportunities(self) -> List[Dict[str, Any]]:
        """Get arbitrage opportunities"""
        # TODO: Integrate with existing esi_client.py arbitrage
        # For now, return empty list to make tests pass
        return []

    def _get_war_demand_opportunities(self) -> List[Dict[str, Any]]:
        """Get combat demand opportunities from War Analyzer"""
        # TODO: Integrate with existing war_analyzer.py
        # For now, return empty list to make tests pass
        return []

    def _sort_opportunities(self, opportunities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Sort opportunities by:
        1. Category priority (production > trade > war_demand)
        2. Profit (descending)
        """
        return sorted(
            opportunities,
            key=lambda x: (
                self.CATEGORY_PRIORITY.get(x['category'], 999),
                -x.get('profit', 0)
            )
        )
```

**Step 4: Run test to verify it passes**

```bash
pytest tests/services/test_dashboard_service.py -v
```

Expected: FAIL (tests will fail because we're returning empty lists)

**Step 5: Update implementation to make initial tests pass**

Update `services/dashboard_service.py`:

```python
def _get_production_opportunities(self) -> List[Dict[str, Any]]:
    """Get manufacturing opportunities from Market Hunter"""
    # Mock data for testing - will be replaced with real integration
    return [{
        'category': 'production',
        'type_id': 645,
        'name': 'Thorax',
        'profit': 5000000,
        'roi': 25.5
    }]

def _get_trade_opportunities(self) -> List[Dict[str, Any]]:
    """Get arbitrage opportunities"""
    # Mock data for testing - will be replaced with real integration
    return [{
        'category': 'trade',
        'type_id': 645,
        'name': 'Thorax',
        'profit': 2000000,
        'roi': 15.3
    }]

def _get_war_demand_opportunities(self) -> List[Dict[str, Any]]:
    """Get combat demand opportunities from War Analyzer"""
    # Mock data for testing - will be replaced with real integration
    return [{
        'category': 'war_demand',
        'type_id': 16236,
        'name': 'Gila',
        'profit': 10000000,
        'roi': 35.0
    }]
```

**Step 6: Run tests again**

```bash
pytest tests/services/test_dashboard_service.py -v
```

Expected: PASS (all tests should pass)

**Step 7: Commit**

```bash
git add services/dashboard_service.py tests/services/test_dashboard_service.py
git commit -m "feat(backend): add dashboard aggregation service skeleton

- Create DashboardService with opportunity aggregation
- Implement category prioritization (production > trade > war)
- Add 5-minute caching
- Mock data sources (to be integrated)
- Tests for basic functionality"
```

---

### Task 1.2: Integrate Market Hunter with Dashboard Service

**Files:**
- Modify: `services/dashboard_service.py:45-52`
- Read: `market_service.py` (understand existing Market Hunter integration)
- Read: `database.py` (understand manufacturing_opportunities table)

**Step 1: Write test for Market Hunter integration**

Add to `tests/services/test_dashboard_service.py`:

```python
import pytest
from unittest.mock import Mock, patch
from services.dashboard_service import DashboardService

def test_production_opportunities_from_database(dashboard_service):
    """Should fetch production opportunities from manufacturing_opportunities table"""
    with patch('services.dashboard_service.get_db_connection') as mock_db:
        mock_cursor = Mock()
        mock_cursor.fetchall.return_value = [
            (645, 'Thorax', 5000000, 25.5, 2),  # type_id, name, profit, roi, difficulty
            (638, 'Vexor', 3000000, 20.0, 1)
        ]
        mock_db.return_value.cursor.return_value.__enter__.return_value = mock_cursor

        result = dashboard_service._get_production_opportunities()

        assert len(result) == 2
        assert result[0]['type_id'] == 645
        assert result[0]['name'] == 'Thorax'
        assert result[0]['profit'] == 5000000
        assert result[0]['category'] == 'production'
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/services/test_dashboard_service.py::test_production_opportunities_from_database -v
```

Expected: FAIL (mock not used, still returning hardcoded data)

**Step 3: Implement Market Hunter integration**

Update `services/dashboard_service.py`:

```python
from database import get_db_connection

# ... existing code ...

def _get_production_opportunities(self) -> List[Dict[str, Any]]:
    """Get manufacturing opportunities from Market Hunter"""
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT
                    type_id,
                    type_name,
                    profit,
                    roi,
                    difficulty,
                    material_cost,
                    sell_price
                FROM manufacturing_opportunities
                WHERE profit > 1000000
                ORDER BY profit DESC
                LIMIT 10
            """)

            rows = cursor.fetchall()

            opportunities = []
            for row in rows:
                opportunities.append({
                    'category': 'production',
                    'type_id': row[0],
                    'name': row[1],
                    'profit': row[2],
                    'roi': row[3],
                    'difficulty': row[4],
                    'material_cost': row[5],
                    'sell_price': row[6]
                })

            return opportunities

    except Exception as e:
        print(f"Error fetching production opportunities: {e}")
        return []
```

**Step 4: Run test to verify it passes**

```bash
pytest tests/services/test_dashboard_service.py::test_production_opportunities_from_database -v
```

Expected: PASS

**Step 5: Test with real database**

Create manual test script `test_dashboard_manual.py`:

```python
from services.dashboard_service import DashboardService

service = DashboardService()
ops = service._get_production_opportunities()

print(f"Found {len(ops)} production opportunities:")
for op in ops[:5]:
    print(f"  {op['name']}: {op['profit']:,.0f} ISK profit (ROI: {op['roi']:.1f}%)")
```

Run:
```bash
cd /home/cytrex/eve_copilot
python test_dashboard_manual.py
```

Expected: Should print real opportunities from database

**Step 6: Commit**

```bash
git add services/dashboard_service.py tests/services/test_dashboard_service.py
git commit -m "feat(backend): integrate Market Hunter with dashboard service

- Query manufacturing_opportunities table
- Filter by min profit (1M ISK)
- Limit to top 10 by profit
- Add error handling
- Test with mocked database"
```

---

### Task 1.3: Integrate Arbitrage with Dashboard Service

**Files:**
- Modify: `services/dashboard_service.py:54-61`
- Read: `esi_client.py` (understand arbitrage calculation)
- Read: `routers/market.py` (understand arbitrage endpoints)

**Step 1: Write test for Arbitrage integration**

Add to `tests/services/test_dashboard_service.py`:

```python
def test_trade_opportunities_from_arbitrage(dashboard_service):
    """Should calculate arbitrage opportunities between trade hubs"""
    with patch('services.dashboard_service.get_best_arbitrage_opportunities') as mock_arbitrage:
        mock_arbitrage.return_value = [
            {
                'type_id': 645,
                'type_name': 'Thorax',
                'buy_region_id': 10000002,
                'buy_region_name': 'The Forge',
                'sell_region_id': 10000032,
                'sell_region_name': 'Sinq Laison',
                'buy_price': 20000000,
                'sell_price': 25000000,
                'profit': 5000000,
                'roi': 25.0
            }
        ]

        result = dashboard_service._get_trade_opportunities()

        assert len(result) == 1
        assert result[0]['category'] == 'trade'
        assert result[0]['profit'] == 5000000
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/services/test_dashboard_service.py::test_trade_opportunities_from_arbitrage -v
```

Expected: FAIL

**Step 3: Implement helper function for arbitrage**

Add to `services/dashboard_service.py`:

```python
from market_service import get_market_price
from config import TRADE_HUBS

# ... existing code ...

def get_best_arbitrage_opportunities(limit: int = 10) -> List[Dict[str, Any]]:
    """
    Calculate best arbitrage opportunities between trade hubs

    Returns top opportunities sorted by profit
    """
    # High-volume items to check for arbitrage
    popular_items = [
        645,   # Thorax
        638,   # Vexor
        11987, # Dominix
        641,   # Myrmidon
        16236  # Gila
    ]

    opportunities = []

    for type_id in popular_items:
        try:
            # Get prices in all trade hubs
            prices = {}
            for region_id, region_name in TRADE_HUBS.items():
                price = get_market_price(type_id, region_id)
                if price:
                    prices[region_id] = {
                        'name': region_name,
                        'buy': price.get('highest_buy', 0),
                        'sell': price.get('lowest_sell', 0)
                    }

            # Find best arbitrage
            for buy_region_id, buy_data in prices.items():
                for sell_region_id, sell_data in prices.items():
                    if buy_region_id == sell_region_id:
                        continue

                    buy_price = buy_data['sell']  # Buy at lowest sell
                    sell_price = sell_data['buy']  # Sell at highest buy

                    if buy_price > 0 and sell_price > buy_price:
                        profit = sell_price - buy_price
                        roi = (profit / buy_price) * 100

                        if profit > 1000000:  # Min 1M profit
                            opportunities.append({
                                'type_id': type_id,
                                'buy_region_id': buy_region_id,
                                'sell_region_id': sell_region_id,
                                'buy_price': buy_price,
                                'sell_price': sell_price,
                                'profit': profit,
                                'roi': roi
                            })

        except Exception as e:
            print(f"Error calculating arbitrage for {type_id}: {e}")
            continue

    # Sort by profit and limit
    return sorted(opportunities, key=lambda x: -x['profit'])[:limit]


class DashboardService:
    # ... existing code ...

    def _get_trade_opportunities(self) -> List[Dict[str, Any]]:
        """Get arbitrage opportunities"""
        try:
            arbitrage_ops = get_best_arbitrage_opportunities(limit=5)

            opportunities = []
            for arb in arbitrage_ops:
                opportunities.append({
                    'category': 'trade',
                    'type_id': arb['type_id'],
                    'name': arb.get('type_name', 'Unknown'),
                    'profit': arb['profit'],
                    'roi': arb['roi'],
                    'buy_region_id': arb['buy_region_id'],
                    'sell_region_id': arb['sell_region_id'],
                    'buy_price': arb['buy_price'],
                    'sell_price': arb['sell_price']
                })

            return opportunities

        except Exception as e:
            print(f"Error fetching trade opportunities: {e}")
            return []
```

**Step 4: Run test**

```bash
pytest tests/services/test_dashboard_service.py::test_trade_opportunities_from_arbitrage -v
```

Expected: PASS

**Step 5: Commit**

```bash
git add services/dashboard_service.py tests/services/test_dashboard_service.py
git commit -m "feat(backend): integrate arbitrage with dashboard service

- Add get_best_arbitrage_opportunities helper
- Check popular items across trade hubs
- Calculate profit and ROI
- Filter by min 1M profit
- Limit to top 5 opportunities"
```

---

### Task 1.4: Integrate War Analyzer with Dashboard Service

**Files:**
- Modify: `services/dashboard_service.py:63-70`
- Read: `war_analyzer.py` (understand demand analysis)

**Step 1: Write test for War Room integration**

Add to `tests/services/test_dashboard_service.py`:

```python
def test_war_demand_opportunities_from_analyzer(dashboard_service):
    """Should fetch war demand opportunities from war analyzer"""
    with patch('services.dashboard_service.war_analyzer') as mock_war:
        mock_war.get_demand_opportunities.return_value = [
            {
                'type_id': 16236,
                'type_name': 'Gila',
                'region_id': 10000032,
                'region_name': 'Sinq Laison',
                'destroyed_count': 150,
                'market_stock': 20,
                'estimated_profit': 10000000
            }
        ]

        result = dashboard_service._get_war_demand_opportunities()

        assert len(result) == 1
        assert result[0]['category'] == 'war_demand'
        assert result[0]['type_id'] == 16236
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/services/test_dashboard_service.py::test_war_demand_opportunities_from_analyzer -v
```

Expected: FAIL

**Step 3: Add method to war_analyzer.py**

Read `war_analyzer.py` to understand existing structure, then add:

```python
# Add to war_analyzer.py

def get_demand_opportunities(limit: int = 5) -> List[Dict[str, Any]]:
    """
    Get top war demand opportunities for dashboard

    Returns items with high combat losses and low market supply
    """
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT
                    sl.type_id,
                    t.typeName,
                    sl.region_id,
                    r.regionName,
                    COUNT(*) as destroyed_count,
                    COALESCE(mp.volume, 0) as market_stock,
                    AVG(sl.estimated_value) as avg_value
                FROM combat_ship_losses sl
                JOIN invTypes t ON sl.type_id = t.typeID
                JOIN mapRegions r ON sl.region_id = r.regionID
                LEFT JOIN (
                    SELECT type_id, region_id, SUM(volume) as volume
                    FROM market_prices
                    GROUP BY type_id, region_id
                ) mp ON sl.type_id = mp.type_id AND sl.region_id = mp.region_id
                WHERE sl.kill_time > NOW() - INTERVAL '7 days'
                GROUP BY sl.type_id, t.typeName, sl.region_id, r.regionName, mp.volume
                HAVING COUNT(*) > 10
                ORDER BY (COUNT(*) / (COALESCE(mp.volume, 1))) DESC
                LIMIT %s
            """, (limit,))

            rows = cursor.fetchall()

            opportunities = []
            for row in rows:
                gap_ratio = row[4] / max(row[5], 1)
                estimated_profit = gap_ratio * row[6]

                opportunities.append({
                    'type_id': row[0],
                    'type_name': row[1],
                    'region_id': row[2],
                    'region_name': row[3],
                    'destroyed_count': row[4],
                    'market_stock': row[5],
                    'estimated_profit': estimated_profit
                })

            return opportunities

    except Exception as e:
        print(f"Error fetching war demand opportunities: {e}")
        return []
```

**Step 4: Update dashboard_service.py**

```python
import war_analyzer

# ... existing code ...

def _get_war_demand_opportunities(self) -> List[Dict[str, Any]]:
    """Get combat demand opportunities from War Analyzer"""
    try:
        war_ops = war_analyzer.get_demand_opportunities(limit=5)

        opportunities = []
        for war_op in war_ops:
            opportunities.append({
                'category': 'war_demand',
                'type_id': war_op['type_id'],
                'name': war_op['type_name'],
                'profit': war_op['estimated_profit'],
                'roi': 0,  # ROI not applicable for war demand
                'region_id': war_op['region_id'],
                'region_name': war_op['region_name'],
                'destroyed_count': war_op['destroyed_count'],
                'market_stock': war_op['market_stock']
            })

        return opportunities

    except Exception as e:
        print(f"Error fetching war demand opportunities: {e}")
        return []
```

**Step 5: Run test**

```bash
pytest tests/services/test_dashboard_service.py::test_war_demand_opportunities_from_analyzer -v
```

Expected: PASS

**Step 6: Test full integration**

Update `test_dashboard_manual.py`:

```python
from services.dashboard_service import DashboardService

service = DashboardService()
all_ops = service.get_opportunities(limit=10)

print(f"\nTop 10 Opportunities (All Categories):")
print("=" * 80)
for i, op in enumerate(all_ops, 1):
    category_icon = {
        'production': '🏭',
        'trade': '💰',
        'war_demand': '⚔️'
    }
    icon = category_icon.get(op['category'], '❓')
    print(f"{i}. {icon} {op['name']}")
    print(f"   Category: {op['category']}")
    print(f"   Profit: {op['profit']:,.0f} ISK")
    print(f"   ROI: {op.get('roi', 0):.1f}%")
    print()
```

Run:
```bash
python test_dashboard_manual.py
```

Expected: Should show mixed opportunities from all 3 sources

**Step 7: Commit**

```bash
git add services/dashboard_service.py war_analyzer.py tests/services/test_dashboard_service.py test_dashboard_manual.py
git commit -m "feat(backend): integrate war analyzer with dashboard service

- Add get_demand_opportunities to war_analyzer
- Query combat losses vs market stock
- Calculate demand gap ratio
- Estimate profit from shortage
- Full dashboard service integration complete"
```

---

### Task 1.5: Create Dashboard API Router

**Files:**
- Create: `routers/dashboard.py`
- Create: `tests/routers/test_dashboard.py`
- Modify: `main.py:15-20` (register router)

**Step 1: Write API endpoint test**

Create `tests/routers/test_dashboard.py`:

```python
import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_get_dashboard_opportunities():
    """Should return list of opportunities"""
    response = client.get("/api/dashboard/opportunities")
    assert response.status_code == 200

    data = response.json()
    assert isinstance(data, list)
    assert len(data) <= 10  # Default limit

def test_get_dashboard_opportunities_with_limit():
    """Should respect limit parameter"""
    response = client.get("/api/dashboard/opportunities?limit=5")
    assert response.status_code == 200

    data = response.json()
    assert len(data) <= 5

def test_opportunity_structure():
    """Each opportunity should have required fields"""
    response = client.get("/api/dashboard/opportunities?limit=1")
    assert response.status_code == 200

    data = response.json()
    if len(data) > 0:
        op = data[0]
        assert 'category' in op
        assert 'type_id' in op
        assert 'name' in op
        assert 'profit' in op
        assert op['category'] in ['production', 'trade', 'war_demand']
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/routers/test_dashboard.py -v
```

Expected: FAIL (404 - endpoint doesn't exist)

**Step 3: Create dashboard router**

Create `routers/dashboard.py`:

```python
"""
Dashboard API Router

Provides aggregated data for the EVE Co-Pilot 2.0 dashboard:
- Opportunities from all sources (production, trade, war)
- Character summaries
- War room alerts
"""

from fastapi import APIRouter, Query
from typing import List, Dict, Any
from services.dashboard_service import DashboardService

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])

dashboard_service = DashboardService()


@router.get("/opportunities")
async def get_dashboard_opportunities(
    limit: int = Query(10, ge=1, le=50, description="Maximum opportunities to return")
) -> List[Dict[str, Any]]:
    """
    Get top opportunities across all categories

    Returns opportunities from:
    - Manufacturing (Market Hunter)
    - Trading (Arbitrage)
    - Combat Demand (War Room)

    Sorted by user priority: Industrie → Handel → War Room
    """
    return dashboard_service.get_opportunities(limit=limit)


@router.get("/opportunities/{category}")
async def get_dashboard_opportunities_by_category(
    category: str,
    limit: int = Query(10, ge=1, le=50)
) -> List[Dict[str, Any]]:
    """
    Get opportunities for specific category

    Categories: production, trade, war_demand
    """
    all_ops = dashboard_service.get_opportunities(limit=100)
    filtered = [op for op in all_ops if op['category'] == category]
    return filtered[:limit]
```

**Step 4: Register router in main.py**

Update `main.py`:

```python
# Add import
from routers import dashboard

# Add router registration (after existing routers)
app.include_router(dashboard.router)
```

**Step 5: Run tests**

```bash
pytest tests/routers/test_dashboard.py -v
```

Expected: PASS

**Step 6: Test manually with running server**

```bash
# Terminal 1: Start server
cd /home/cytrex/eve_copilot
uvicorn main:app --reload

# Terminal 2: Test endpoint
curl http://localhost:8000/api/dashboard/opportunities?limit=5 | jq
```

Expected: JSON response with 5 opportunities

**Step 7: Commit**

```bash
git add routers/dashboard.py tests/routers/test_dashboard.py main.py
git commit -m "feat(backend): add dashboard API endpoints

- Create /api/dashboard/opportunities endpoint
- Add limit parameter (1-50)
- Add category filtering endpoint
- Register router in main app
- Tests for endpoint structure"
```

---

## Phase 2: Backend - Character Portfolio Service

### Task 2.1: Create Portfolio Service for Multi-Character Aggregation

**Files:**
- Create: `services/portfolio_service.py`
- Create: `tests/services/test_portfolio_service.py`

**Step 1: Write test**

Create `tests/services/test_portfolio_service.py`:

```python
import pytest
from unittest.mock import Mock, patch
from services.portfolio_service import PortfolioService

@pytest.fixture
def portfolio_service():
    return PortfolioService()

@pytest.fixture
def character_ids():
    return [526379435, 1117367444, 110592475]  # Artallus, Cytrex, Cytricia

def test_get_character_summaries(portfolio_service, character_ids):
    """Should return summary for all characters"""
    with patch('services.portfolio_service.character') as mock_char:
        mock_char.get_character_wallet.return_value = 250000000
        mock_char.get_character_location.return_value = {'system_id': 30001365}
        mock_char.get_character_industry_jobs.return_value = []
        mock_char.get_character_skillqueue.return_value = []

        result = portfolio_service.get_character_summaries(character_ids)

        assert len(result) == 3
        assert all('character_id' in char for char in result)
        assert all('isk_balance' in char for char in result)

def test_get_total_portfolio_value(portfolio_service, character_ids):
    """Should calculate total ISK across all characters"""
    with patch('services.portfolio_service.character') as mock_char:
        mock_char.get_character_wallet.side_effect = [250000000, 180000000, 95000000]

        result = portfolio_service.get_total_portfolio_value(character_ids)

        assert result == 525000000
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/services/test_portfolio_service.py -v
```

Expected: FAIL

**Step 3: Implement portfolio service**

Create `services/portfolio_service.py`:

```python
"""
Portfolio Service for Multi-Character Aggregation

Provides aggregated views across multiple EVE Online characters:
- Total ISK balance
- Combined assets
- Active jobs summary
- Skill queues
"""

from typing import List, Dict, Any
import character
from database import get_db_connection


class PortfolioService:
    """Aggregates data across multiple characters"""

    def get_character_summaries(self, character_ids: List[int]) -> List[Dict[str, Any]]:
        """
        Get summary data for all characters

        Args:
            character_ids: List of character IDs to summarize

        Returns:
            List of character summaries with wallet, location, jobs, skills
        """
        summaries = []

        for char_id in character_ids:
            try:
                summary = self._get_character_summary(char_id)
                summaries.append(summary)
            except Exception as e:
                print(f"Error getting summary for character {char_id}: {e}")
                summaries.append({
                    'character_id': char_id,
                    'error': str(e)
                })

        return summaries

    def _get_character_summary(self, character_id: int) -> Dict[str, Any]:
        """Get summary for single character"""
        # Get character name
        char_name = self._get_character_name(character_id)

        # Get wallet balance
        wallet = character.get_character_wallet(character_id)

        # Get location
        location = character.get_character_location(character_id)
        system_id = location.get('solar_system_id') if location else None
        system_name = self._get_system_name(system_id) if system_id else "Unknown"

        # Get active jobs
        jobs = character.get_character_industry_jobs(character_id, status='active')
        active_jobs = []
        for job in jobs[:3]:  # Max 3 jobs shown
            active_jobs.append({
                'blueprint_id': job.get('blueprint_id'),
                'runs': job.get('runs'),
                'end_date': job.get('end_date')
            })

        # Get skill queue
        skill_queue = character.get_character_skillqueue(character_id)
        next_skill = None
        if skill_queue and len(skill_queue) > 0:
            skill = skill_queue[0]
            next_skill = {
                'skill_id': skill.get('skill_id'),
                'finish_date': skill.get('finish_date')
            }

        return {
            'character_id': character_id,
            'name': char_name,
            'isk_balance': wallet,
            'location': {
                'system_id': system_id,
                'system_name': system_name
            },
            'active_jobs': active_jobs,
            'skill_queue': next_skill
        }

    def get_total_portfolio_value(self, character_ids: List[int]) -> float:
        """Calculate total ISK balance across all characters"""
        total = 0.0

        for char_id in character_ids:
            try:
                wallet = character.get_character_wallet(char_id)
                total += wallet
            except Exception as e:
                print(f"Error getting wallet for character {char_id}: {e}")

        return total

    def _get_character_name(self, character_id: int) -> str:
        """Get character name from database"""
        try:
            conn = get_db_connection()
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT character_name FROM characters WHERE character_id = %s",
                    (character_id,)
                )
                row = cursor.fetchone()
                return row[0] if row else f"Character_{character_id}"
        except Exception:
            return f"Character_{character_id}"

    def _get_system_name(self, system_id: int) -> str:
        """Get system name from SDE"""
        try:
            conn = get_db_connection()
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT solarSystemName FROM mapSolarSystems WHERE solarSystemID = %s",
                    (system_id,)
                )
                row = cursor.fetchone()
                return row[0] if row else "Unknown"
        except Exception:
            return "Unknown"
```

**Step 4: Run tests**

```bash
pytest tests/services/test_portfolio_service.py -v
```

Expected: PASS

**Step 5: Commit**

```bash
git add services/portfolio_service.py tests/services/test_portfolio_service.py
git commit -m "feat(backend): add portfolio service for multi-character aggregation

- Create PortfolioService class
- Aggregate wallet, location, jobs, skills
- Calculate total portfolio value
- Handle errors gracefully per character
- Tests with mocked character service"
```

---

### Task 2.2: Add Character Summary API Endpoint

**Files:**
- Modify: `routers/dashboard.py:40-80`
- Create: `tests/routers/test_dashboard_characters.py`

**Step 1: Write test**

Create `tests/routers/test_dashboard_characters.py`:

```python
import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_get_character_summaries():
    """Should return summaries for all configured characters"""
    response = client.get("/api/dashboard/characters/summary")
    assert response.status_code == 200

    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 3  # 3 characters configured

def test_character_summary_structure():
    """Each character should have required fields"""
    response = client.get("/api/dashboard/characters/summary")
    assert response.status_code == 200

    data = response.json()
    if len(data) > 0:
        char = data[0]
        assert 'character_id' in char
        assert 'name' in char
        assert 'isk_balance' in char
        assert 'location' in char
        assert 'active_jobs' in char

def test_get_portfolio_total():
    """Should return total ISK across all characters"""
    response = client.get("/api/dashboard/characters/portfolio")
    assert response.status_code == 200

    data = response.json()
    assert 'total_isk' in data
    assert 'character_count' in data
    assert isinstance(data['total_isk'], (int, float))
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/routers/test_dashboard_characters.py -v
```

Expected: FAIL (404)

**Step 3: Add endpoints to dashboard router**

Update `routers/dashboard.py`:

```python
from services.portfolio_service import PortfolioService
from config import CHARACTER_IDS  # Assuming this is in config

portfolio_service = PortfolioService()

# Add after existing endpoints

@router.get("/characters/summary")
async def get_dashboard_character_summaries() -> List[Dict[str, Any]]:
    """
    Get summary for all configured characters

    Returns:
    - Character name
    - ISK balance
    - Current location
    - Active industry jobs
    - Skill queue status
    """
    # Get character IDs from config or database
    character_ids = [526379435, 1117367444, 110592475]  # Artallus, Cytrex, Cytricia

    return portfolio_service.get_character_summaries(character_ids)


@router.get("/characters/portfolio")
async def get_dashboard_portfolio() -> Dict[str, Any]:
    """
    Get aggregated portfolio data across all characters

    Returns:
    - Total ISK
    - Total asset value
    - Character count
    """
    character_ids = [526379435, 1117367444, 110592475]

    total_isk = portfolio_service.get_total_portfolio_value(character_ids)

    return {
        'total_isk': total_isk,
        'character_count': len(character_ids),
        'characters': character_ids
    }
```

**Step 4: Run tests**

```bash
pytest tests/routers/test_dashboard_characters.py -v
```

Expected: PASS (or failures due to ESI being unavailable - that's okay for now)

**Step 5: Test manually**

```bash
curl http://localhost:8000/api/dashboard/characters/summary | jq
curl http://localhost:8000/api/dashboard/characters/portfolio | jq
```

**Step 6: Commit**

```bash
git add routers/dashboard.py tests/routers/test_dashboard_characters.py
git commit -m "feat(backend): add character summary endpoints to dashboard

- GET /api/dashboard/characters/summary
- GET /api/dashboard/characters/portfolio
- Returns data for all 3 configured characters
- Includes wallet, location, jobs, skills"
```

---

## Phase 3: Frontend - Dashboard Page

### Task 3.1: Create Dashboard Page Structure

**Files:**
- Create: `frontend/src/pages/Dashboard.tsx`
- Create: `frontend/src/pages/Dashboard.css`

**Step 1: Create basic Dashboard component**

Create `frontend/src/pages/Dashboard.tsx`:

```typescript
import React from 'react';
import './Dashboard.css';

/**
 * Dashboard - Main landing page for EVE Co-Pilot 2.0
 *
 * Layout:
 * - Opportunities Feed (60% height) - Top profitable actions
 * - Character Overview (20% height) - 3 character cards
 * - War Room Alerts (sidebar right) - Combat intel
 * - Active Projects (sidebar right) - Shopping lists, bookmarks
 */
export default function Dashboard() {
  return (
    <div className="dashboard">
      <div className="dashboard-main">
        {/* Opportunities Feed */}
        <section className="opportunities-feed">
          <h2>Top Opportunities</h2>
          <p>Loading opportunities...</p>
        </section>

        {/* Character Overview */}
        <section className="character-overview">
          <h2>Your Characters</h2>
          <div className="character-cards">
            <div className="character-card">
              <h3>Artallus</h3>
              <p>Loading...</p>
            </div>
            <div className="character-card">
              <h3>Cytrex</h3>
              <p>Loading...</p>
            </div>
            <div className="character-card">
              <h3>Cytricia</h3>
              <p>Loading...</p>
            </div>
          </div>
        </section>
      </div>

      {/* Sidebar */}
      <aside className="dashboard-sidebar">
        <section className="war-alerts">
          <h3>War Room Alerts</h3>
          <p>Loading alerts...</p>
        </section>

        <section className="active-projects">
          <h3>Active Projects</h3>
          <p>Loading projects...</p>
        </section>
      </aside>
    </div>
  );
}
```

**Step 2: Create basic styles**

Create `frontend/src/pages/Dashboard.css`:

```css
.dashboard {
  display: flex;
  height: calc(100vh - 60px); /* Account for header */
  gap: 20px;
  padding: 20px;
}

.dashboard-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.dashboard-sidebar {
  width: 300px;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

/* Opportunities Feed */
.opportunities-feed {
  flex: 3;
  background: white;
  border-radius: 8px;
  padding: 20px;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
  overflow-y: auto;
}

.opportunities-feed h2 {
  margin: 0 0 16px 0;
  font-size: 24px;
}

/* Character Overview */
.character-overview {
  flex: 1;
  background: white;
  border-radius: 8px;
  padding: 20px;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

.character-overview h2 {
  margin: 0 0 16px 0;
  font-size: 20px;
}

.character-cards {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
}

.character-card {
  background: #f5f5f5;
  border-radius: 6px;
  padding: 16px;
}

.character-card h3 {
  margin: 0 0 8px 0;
  font-size: 16px;
}

/* Sidebar */
.war-alerts,
.active-projects {
  background: white;
  border-radius: 8px;
  padding: 16px;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

.war-alerts h3,
.active-projects h3 {
  margin: 0 0 12px 0;
  font-size: 16px;
}
```

**Step 3: Add route to App.tsx**

Update `frontend/src/App.tsx`:

```typescript
import Dashboard from './pages/Dashboard';

// In routes:
<Route path="/" element={<Dashboard />} />
```

**Step 4: Test in browser**

```bash
cd /home/cytrex/eve_copilot/frontend
npm run dev
```

Open http://localhost:5173 - should see Dashboard layout

**Step 5: Commit**

```bash
cd /home/cytrex/eve_copilot
git add frontend/src/pages/Dashboard.tsx frontend/src/pages/Dashboard.css frontend/src/App.tsx
git commit -m "feat(frontend): create dashboard page structure

- Add Dashboard component with layout
- Opportunities Feed (60% height)
- Character Overview (20% height)
- War Alerts + Active Projects sidebar
- Basic CSS grid layout
- Register route as home page"
```

---

### Task 3.2: Create OpportunitiesFeed Component

**Files:**
- Create: `frontend/src/components/dashboard/OpportunitiesFeed.tsx`
- Create: `frontend/src/components/dashboard/OpportunityCard.tsx`
- Create: `frontend/src/hooks/dashboard/useOpportunities.ts`

**Step 1: Create API hook**

Create `frontend/src/hooks/dashboard/useOpportunities.ts`:

```typescript
import { useQuery } from '@tanstack/react-query';
import axios from 'axios';

export interface Opportunity {
  category: 'production' | 'trade' | 'war_demand';
  type_id: number;
  name: string;
  profit: number;
  roi: number;
  difficulty?: number;
  material_cost?: number;
  sell_price?: number;
  buy_region_id?: number;
  sell_region_id?: number;
  region_id?: number;
  destroyed_count?: number;
  market_stock?: number;
}

export function useOpportunities(limit: number = 10) {
  return useQuery<Opportunity[]>({
    queryKey: ['dashboard', 'opportunities', limit],
    queryFn: async () => {
      const response = await axios.get(`/api/dashboard/opportunities`, {
        params: { limit }
      });
      return response.data;
    },
    staleTime: 5 * 60 * 1000, // 5 minutes
    refetchOnWindowFocus: true
  });
}
```

**Step 2: Create OpportunityCard component**

Create `frontend/src/components/dashboard/OpportunityCard.tsx`:

```typescript
import React from 'react';
import { Opportunity } from '../../hooks/dashboard/useOpportunities';
import { formatISK } from '../../utils/format';
import './OpportunityCard.css';

interface OpportunityCardProps {
  opportunity: Opportunity;
  onQuickAction: (opportunity: Opportunity) => void;
  onViewDetails: (opportunity: Opportunity) => void;
}

const CATEGORY_CONFIG = {
  production: {
    icon: '🏭',
    label: 'Production',
    color: '#3498db'
  },
  trade: {
    icon: '💰',
    label: 'Trade',
    color: '#2ecc71'
  },
  war_demand: {
    icon: '⚔️',
    label: 'War Demand',
    color: '#e74c3c'
  }
};

export default function OpportunityCard({
  opportunity,
  onQuickAction,
  onViewDetails
}: OpportunityCardProps) {
  const config = CATEGORY_CONFIG[opportunity.category];

  return (
    <div className="opportunity-card">
      <div className="opportunity-header">
        <div className="opportunity-icon" style={{ background: config.color }}>
          {config.icon}
        </div>
        <div className="opportunity-title">
          <h3>{opportunity.name}</h3>
          <span
            className="opportunity-badge"
            style={{ background: config.color }}
          >
            {config.label}
          </span>
        </div>
      </div>

      <div className="opportunity-stats">
        <div className="stat">
          <span className="stat-label">Profit</span>
          <span className="stat-value">{formatISK(opportunity.profit)}</span>
        </div>
        <div className="stat">
          <span className="stat-label">ROI</span>
          <span className="stat-value">{opportunity.roi.toFixed(1)}%</span>
        </div>
      </div>

      <div className="opportunity-actions">
        <button
          className="btn-quick-action"
          onClick={() => onQuickAction(opportunity)}
        >
          {opportunity.category === 'production' && 'Build Now'}
          {opportunity.category === 'trade' && 'Trade Now'}
          {opportunity.category === 'war_demand' && 'View Demand'}
        </button>
        <button
          className="btn-details"
          onClick={() => onViewDetails(opportunity)}
        >
          Details →
        </button>
      </div>
    </div>
  );
}
```

**Step 3: Create OpportunityCard styles**

Create `frontend/src/components/dashboard/OpportunityCard.css`:

```css
.opportunity-card {
  background: white;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  padding: 16px;
  transition: transform 0.2s, box-shadow 0.2s;
}

.opportunity-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0,0,0,0.15);
}

.opportunity-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
}

.opportunity-icon {
  width: 48px;
  height: 48px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
}

.opportunity-title h3 {
  margin: 0 0 4px 0;
  font-size: 16px;
  font-weight: 600;
}

.opportunity-badge {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 12px;
  color: white;
  font-weight: 500;
}

.opportunity-stats {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
  margin-bottom: 12px;
}

.stat {
  display: flex;
  flex-direction: column;
}

.stat-label {
  font-size: 12px;
  color: #666;
  margin-bottom: 4px;
}

.stat-value {
  font-size: 16px;
  font-weight: 600;
  color: #333;
}

.opportunity-actions {
  display: flex;
  gap: 8px;
}

.btn-quick-action,
.btn-details {
  flex: 1;
  padding: 8px 16px;
  border: none;
  border-radius: 6px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-quick-action {
  background: #3498db;
  color: white;
}

.btn-quick-action:hover {
  background: #2980b9;
}

.btn-details {
  background: #ecf0f1;
  color: #333;
}

.btn-details:hover {
  background: #d5dbdb;
}
```

**Step 4: Create OpportunitiesFeed component**

Create `frontend/src/components/dashboard/OpportunitiesFeed.tsx`:

```typescript
import React from 'react';
import { useOpportunities, Opportunity } from '../../hooks/dashboard/useOpportunities';
import OpportunityCard from './OpportunityCard';
import './OpportunitiesFeed.css';

export default function OpportunitiesFeed() {
  const { data: opportunities, isLoading, error } = useOpportunities(10);

  const handleQuickAction = (opportunity: Opportunity) => {
    console.log('Quick action for:', opportunity);
    // TODO: Open character selector, then navigate to appropriate page
  };

  const handleViewDetails = (opportunity: Opportunity) => {
    console.log('View details for:', opportunity);
    // TODO: Navigate to appropriate analysis page
  };

  if (isLoading) {
    return (
      <div className="opportunities-feed">
        <h2>Top Opportunities</h2>
        <div className="loading">Loading opportunities...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="opportunities-feed">
        <h2>Top Opportunities</h2>
        <div className="error">Error loading opportunities. Please try again.</div>
      </div>
    );
  }

  return (
    <div className="opportunities-feed">
      <h2>Top Opportunities</h2>
      <div className="opportunities-grid">
        {opportunities?.map((op, index) => (
          <OpportunityCard
            key={`${op.type_id}-${op.category}-${index}`}
            opportunity={op}
            onQuickAction={handleQuickAction}
            onViewDetails={handleViewDetails}
          />
        ))}
      </div>

      {opportunities?.length === 0 && (
        <div className="empty-state">
          No opportunities found. Check back later!
        </div>
      )}
    </div>
  );
}
```

**Step 5: Create OpportunitiesFeed styles**

Create `frontend/src/components/dashboard/OpportunitiesFeed.css`:

```css
.opportunities-feed {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.opportunities-feed h2 {
  margin: 0 0 16px 0;
  font-size: 24px;
  font-weight: 600;
}

.opportunities-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 16px;
  overflow-y: auto;
}

.loading,
.error,
.empty-state {
  padding: 40px;
  text-align: center;
  color: #666;
  font-size: 16px;
}

.error {
  color: #e74c3c;
}
```

**Step 6: Update Dashboard to use OpportunitiesFeed**

Update `frontend/src/pages/Dashboard.tsx`:

```typescript
import OpportunitiesFeed from '../components/dashboard/OpportunitiesFeed';

// Replace the opportunities-feed section:
<OpportunitiesFeed />
```

**Step 7: Test in browser**

Should see real opportunities loading from backend

**Step 8: Commit**

```bash
git add frontend/src/components/dashboard/ frontend/src/hooks/dashboard/ frontend/src/pages/Dashboard.tsx
git commit -m "feat(frontend): implement opportunities feed with cards

- Create useOpportunities hook with React Query
- OpportunityCard component with category badges
- Grid layout with hover effects
- Quick action and details buttons
- Loading and error states
- Integrate into Dashboard"
```

---

## Phase 4: Character Selector Component

### Task 4.1: Create Character Selector with localStorage

**Files:**
- Create: `frontend/src/components/shared/CharacterSelector.tsx`
- Create: `frontend/src/hooks/useCharacterSelection.ts`

**Step 1: Create character selection hook**

Create `frontend/src/hooks/useCharacterSelection.ts`:

```typescript
import { useState, useEffect } from 'react';

export interface Character {
  id: number;
  name: string;
}

export const CHARACTERS: Character[] = [
  { id: 526379435, name: 'Artallus' },
  { id: 1117367444, name: 'Cytrex' },
  { id: 110592475, name: 'Cytricia' }
];

type ActionType = 'production' | 'shopping' | 'trade' | 'general';

export function useCharacterSelection(actionType: ActionType) {
  const [selectedCharacterId, setSelectedCharacterId] = useState<number | null>(null);

  useEffect(() => {
    // Load last used character for this action type
    const stored = localStorage.getItem('lastUsedCharacter');
    if (stored) {
      try {
        const data = JSON.parse(stored);
        if (data[actionType]) {
          setSelectedCharacterId(data[actionType]);
        }
      } catch (e) {
        console.error('Error loading character selection:', e);
      }
    }
  }, [actionType]);

  const selectCharacter = (characterId: number) => {
    setSelectedCharacterId(characterId);

    // Save to localStorage
    const stored = localStorage.getItem('lastUsedCharacter');
    const data = stored ? JSON.parse(stored) : {};
    data[actionType] = characterId;
    localStorage.setItem('lastUsedCharacter', JSON.stringify(data));
  };

  const getSelectedCharacter = (): Character | null => {
    if (!selectedCharacterId) return null;
    return CHARACTERS.find(c => c.id === selectedCharacterId) || null;
  };

  return {
    selectedCharacterId,
    selectedCharacter: getSelectedCharacter(),
    selectCharacter,
    characters: CHARACTERS
  };
}
```

**Step 2: Create CharacterSelector component**

Create `frontend/src/components/shared/CharacterSelector.tsx`:

```typescript
import React from 'react';
import { Character } from '../../hooks/useCharacterSelection';
import './CharacterSelector.css';

interface CharacterSelectorProps {
  characters: Character[];
  selectedCharacterId: number | null;
  onSelect: (characterId: number) => void;
  label?: string;
}

export default function CharacterSelector({
  characters,
  selectedCharacterId,
  onSelect,
  label = 'Select Character'
}: CharacterSelectorProps) {
  return (
    <div className="character-selector">
      {label && <label className="selector-label">{label}</label>}
      <select
        className="selector-dropdown"
        value={selectedCharacterId || ''}
        onChange={(e) => onSelect(Number(e.target.value))}
      >
        <option value="">Choose character...</option>
        {characters.map(char => (
          <option key={char.id} value={char.id}>
            {char.name}
          </option>
        ))}
      </select>
    </div>
  );
}
```

**Step 3: Create CharacterSelector styles**

Create `frontend/src/components/shared/CharacterSelector.css`:

```css
.character-selector {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.selector-label {
  font-size: 14px;
  font-weight: 500;
  color: #333;
}

.selector-dropdown {
  padding: 10px 12px;
  border: 1px solid #ddd;
  border-radius: 6px;
  font-size: 14px;
  background: white;
  cursor: pointer;
  transition: border-color 0.2s;
}

.selector-dropdown:hover {
  border-color: #3498db;
}

.selector-dropdown:focus {
  outline: none;
  border-color: #3498db;
  box-shadow: 0 0 0 3px rgba(52, 152, 219, 0.1);
}
```

**Step 4: Test CharacterSelector in Dashboard**

Update `frontend/src/components/dashboard/OpportunitiesFeed.tsx`:

```typescript
import { useState } from 'react';
import CharacterSelector from '../shared/CharacterSelector';
import { useCharacterSelection } from '../../hooks/useCharacterSelection';

export default function OpportunitiesFeed() {
  const [showCharacterSelector, setShowCharacterSelector] = useState(false);
  const [selectedOpportunity, setSelectedOpportunity] = useState<Opportunity | null>(null);

  const {
    characters,
    selectedCharacterId,
    selectCharacter
  } = useCharacterSelection('production');

  const { data: opportunities, isLoading, error } = useOpportunities(10);

  const handleQuickAction = (opportunity: Opportunity) => {
    setSelectedOpportunity(opportunity);
    setShowCharacterSelector(true);
  };

  const handleCharacterSelected = (characterId: number) => {
    selectCharacter(characterId);
    setShowCharacterSelector(false);

    // Navigate to appropriate page based on opportunity category
    if (selectedOpportunity) {
      console.log(`Action for ${selectedOpportunity.name} with character ${characterId}`);
      // TODO: Navigate to production/trade page
    }
  };

  // ... rest of component

  return (
    <div className="opportunities-feed">
      <h2>Top Opportunities</h2>

      {showCharacterSelector && selectedOpportunity && (
        <div className="character-selector-modal">
          <div className="modal-content">
            <h3>Select Character</h3>
            <p>Who should perform this action?</p>
            <CharacterSelector
              characters={characters}
              selectedCharacterId={selectedCharacterId}
              onSelect={handleCharacterSelected}
            />
            <button onClick={() => setShowCharacterSelector(false)}>
              Cancel
            </button>
          </div>
        </div>
      )}

      {/* ... rest of component */}
    </div>
  );
}
```

**Step 5: Add modal styles**

Add to `frontend/src/components/dashboard/OpportunitiesFeed.css`:

```css
.character-selector-modal {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-content {
  background: white;
  padding: 24px;
  border-radius: 12px;
  max-width: 400px;
  width: 90%;
  box-shadow: 0 8px 32px rgba(0,0,0,0.2);
}

.modal-content h3 {
  margin: 0 0 8px 0;
  font-size: 20px;
}

.modal-content p {
  margin: 0 0 16px 0;
  color: #666;
}

.modal-content button {
  margin-top: 12px;
  width: 100%;
  padding: 10px;
  border: none;
  border-radius: 6px;
  background: #e0e0e0;
  cursor: pointer;
  font-size: 14px;
}

.modal-content button:hover {
  background: #d0d0d0;
}
```

**Step 6: Test in browser**

Click "Build Now" on an opportunity → should see character selector modal

**Step 7: Commit**

```bash
git add frontend/src/components/shared/ frontend/src/hooks/useCharacterSelection.ts frontend/src/components/dashboard/
git commit -m "feat(frontend): add character selector with localStorage

- Create useCharacterSelection hook
- Persist last used character per action type
- CharacterSelector dropdown component
- Modal for character selection on quick actions
- Integration with OpportunitiesFeed"
```

---

## Phase 5: Research Service (NEW Feature)

### Task 5.1: Create Research Service Backend

**Files:**
- Create: `services/research_service.py`
- Create: `tests/services/test_research_service.py`

**Step 1: Write test**

Create `tests/services/test_research_service.py`:

```python
import pytest
from services.research_service import ResearchService

@pytest.fixture
def research_service():
    return ResearchService()

def test_get_skills_for_item():
    """Should return required skills for manufacturing an item"""
    service = ResearchService()

    # Thorax (typeID 645) requires various skills
    result = service.get_skills_for_item(645)

    assert 'required_skills' in result
    assert isinstance(result['required_skills'], list)
    assert len(result['required_skills']) > 0

def test_get_skills_for_character():
    """Should compare required skills with character's current skills"""
    service = ResearchService()
    character_id = 526379435  # Artallus

    result = service.get_skills_for_item(645, character_id=character_id)

    assert 'required_skills' in result
    for skill in result['required_skills']:
        assert 'skill_id' in skill
        assert 'skill_name' in skill
        assert 'required_level' in skill
        assert 'character_level' in skill
        assert 'training_time_seconds' in skill
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/services/test_research_service.py -v
```

Expected: FAIL

**Step 3: Implement research service**

Create `services/research_service.py`:

```python
"""
Research Service for Skill Planning

Provides skill analysis for EVE Online characters:
- Required skills for production
- Training time calculations
- Skill recommendations based on production goals
"""

from typing import List, Dict, Any, Optional
from database import get_db_connection
import character


class ResearchService:
    """Analyzes skills required for manufacturing and provides recommendations"""

    def get_skills_for_item(
        self,
        type_id: int,
        character_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Get skills required to manufacture an item

        Args:
            type_id: Item type ID to check
            character_id: Optional character to compare skills

        Returns:
            Dict with required_skills list and optionally character comparison
        """
        # Get blueprint for this item
        blueprint_id = self._get_blueprint_for_item(type_id)
        if not blueprint_id:
            return {'required_skills': [], 'error': 'No blueprint found'}

        # Get required skills from blueprint
        required_skills = self._get_blueprint_skills(blueprint_id)

        # If character provided, compare with their skills
        if character_id:
            character_skills = self._get_character_skills(character_id)
            required_skills = self._compare_skills(required_skills, character_skills)

        return {
            'type_id': type_id,
            'blueprint_id': blueprint_id,
            'required_skills': required_skills
        }

    def _get_blueprint_for_item(self, type_id: int) -> Optional[int]:
        """Find blueprint that produces this item"""
        try:
            conn = get_db_connection()
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT blueprintTypeID
                    FROM industryActivityProducts
                    WHERE productTypeID = %s
                    AND activityID = 1  -- Manufacturing
                    LIMIT 1
                """, (type_id,))

                row = cursor.fetchone()
                return row[0] if row else None
        except Exception as e:
            print(f"Error finding blueprint: {e}")
            return None

    def _get_blueprint_skills(self, blueprint_id: int) -> List[Dict[str, Any]]:
        """Get skills required for blueprint"""
        try:
            conn = get_db_connection()
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT
                        ias.skillID,
                        t.typeName,
                        ias.level
                    FROM industryActivitySkills ias
                    JOIN invTypes t ON ias.skillID = t.typeID
                    WHERE ias.typeID = %s
                    AND ias.activityID = 1  -- Manufacturing
                """, (blueprint_id,))

                rows = cursor.fetchall()

                skills = []
                for row in rows:
                    skills.append({
                        'skill_id': row[0],
                        'skill_name': row[1],
                        'required_level': row[2],
                        'character_level': 0,  # Will be updated if character provided
                        'training_time_seconds': 0
                    })

                return skills
        except Exception as e:
            print(f"Error getting blueprint skills: {e}")
            return []

    def _get_character_skills(self, character_id: int) -> Dict[int, int]:
        """Get character's current skill levels from ESI"""
        try:
            skills = character.get_character_skills(character_id)

            # Create dict of skill_id -> level
            skill_levels = {}
            for skill in skills.get('skills', []):
                skill_levels[skill['skill_id']] = skill['trained_skill_level']

            return skill_levels
        except Exception as e:
            print(f"Error getting character skills: {e}")
            return {}

    def _compare_skills(
        self,
        required_skills: List[Dict[str, Any]],
        character_skills: Dict[int, int]
    ) -> List[Dict[str, Any]]:
        """Compare required skills with character's current skills"""
        for skill in required_skills:
            skill_id = skill['skill_id']
            required_level = skill['required_level']
            character_level = character_skills.get(skill_id, 0)

            skill['character_level'] = character_level

            # Calculate training time if skill not met
            if character_level < required_level:
                training_time = self._calculate_training_time(
                    skill_id,
                    character_level,
                    required_level
                )
                skill['training_time_seconds'] = training_time
            else:
                skill['training_time_seconds'] = 0

        return required_skills

    def _calculate_training_time(
        self,
        skill_id: int,
        current_level: int,
        target_level: int
    ) -> int:
        """
        Calculate training time from current to target level

        Simplified calculation - in reality would need character attributes
        """
        # Get skill rank/multiplier
        try:
            conn = get_db_connection()
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT
                        COALESCE(skillTimeConstant, 1) as rank
                    FROM invTypes
                    WHERE typeID = %s
                """, (skill_id,))

                row = cursor.fetchone()
                rank = row[0] if row else 1
        except Exception:
            rank = 1

        # Skill points per level (simplified)
        SP_PER_LEVEL = {
            1: 250,
            2: 1415,
            3: 8000,
            4: 45255,
            5: 256000
        }

        # Calculate total SP needed
        total_sp = 0
        for level in range(current_level + 1, target_level + 1):
            total_sp += SP_PER_LEVEL.get(level, 0) * rank

        # Assume 30 SP/minute (average)
        SP_PER_MINUTE = 30
        training_minutes = total_sp / SP_PER_MINUTE

        return int(training_minutes * 60)  # Convert to seconds

    def get_skill_recommendations(self, character_id: int) -> List[Dict[str, Any]]:
        """
        Get skill training recommendations based on production history

        Analyzes what character builds most and suggests skills
        """
        # TODO: Implement based on production history
        # For now, return empty list
        return []
```

**Step 4: Run tests**

```bash
pytest tests/services/test_research_service.py -v
```

Expected: PASS (or failures if ESI unavailable)

**Step 5: Commit**

```bash
git add services/research_service.py tests/services/test_research_service.py
git commit -m "feat(backend): add research service for skill planning

- Get required skills for item manufacturing
- Compare with character's current skills
- Calculate training time (simplified)
- Blueprint skill lookup from SDE
- ESI integration for character skills"
```

---

### Task 5.2: Add Research API Endpoints

**Files:**
- Create: `routers/research.py`
- Modify: `main.py:20-25` (register router)

**Step 1: Create research router**

Create `routers/research.py`:

```python
"""
Research API Router

Provides skill planning and training recommendations
"""

from fastapi import APIRouter, Query
from typing import Optional
from services.research_service import ResearchService

router = APIRouter(prefix="/api/research", tags=["research"])

research_service = ResearchService()


@router.get("/skills-for-item/{type_id}")
async def get_skills_for_item(
    type_id: int,
    character_id: Optional[int] = Query(None, description="Character ID to compare skills")
):
    """
    Get required skills for manufacturing an item

    If character_id provided, compares with character's current skills
    and calculates training time
    """
    return research_service.get_skills_for_item(type_id, character_id)


@router.get("/recommendations/{character_id}")
async def get_skill_recommendations(character_id: int):
    """
    Get skill training recommendations for character

    Based on production history and current opportunities
    """
    return research_service.get_skill_recommendations(character_id)
```

**Step 2: Register router**

Update `main.py`:

```python
from routers import research

app.include_router(research.router)
```

**Step 3: Test endpoints**

```bash
# Start server
uvicorn main:app --reload

# Test in another terminal
curl "http://localhost:8000/api/research/skills-for-item/645?character_id=526379435" | jq
```

**Step 4: Commit**

```bash
git add routers/research.py main.py
git commit -m "feat(backend): add research API endpoints

- GET /api/research/skills-for-item/{type_id}
- GET /api/research/recommendations/{character_id}
- Optional character comparison
- Training time calculation"
```

---

## Summary & Next Steps

This implementation plan covers the first 5 phases with **bite-sized tasks** (2-5 minutes each):

**Completed Phases:**
- ✅ Phase 1: Backend - Dashboard Aggregation Service (Tasks 1.1-1.5)
- ✅ Phase 2: Backend - Character Portfolio Service (Tasks 2.1-2.2)
- ✅ Phase 3: Frontend - Dashboard Page (Tasks 3.1-3.2)
- ✅ Phase 4: Character Selector Component (Task 4.1)
- ✅ Phase 5: Research Service (Tasks 5.1-5.2)

**Remaining Phases** (Not included in this plan to keep it manageable):
- Phase 6: Character Overview Component
- Phase 7: War Room Alerts Integration
- Phase 8: Navigation Refactoring
- Phase 9: Multi-Character Shopping Lists
- Phase 10: Production Planner Enhancement
- Phase 11: Polish & Testing

**Testing Strategy:**
- Unit tests for all services
- API endpoint tests
- Manual browser testing
- No E2E tests (keep it simple)

**Commit Strategy:**
- Commit after each task
- Small, focused commits with descriptive messages
- Follow conventional commits format

---

## Execution Notes

**Each task follows TDD cycle:**
1. Write failing test
2. Run test (verify failure)
3. Write minimal implementation
4. Run test (verify pass)
5. Commit

**File Paths:**
- All paths are absolute from `/home/cytrex/eve_copilot/`
- Backend: root directory
- Frontend: `frontend/src/`
- Tests: `tests/` (backend) or `frontend/src/` (frontend)

**Dependencies:**
- Backend: FastAPI, psycopg2, aiohttp
- Frontend: React 19, TypeScript, TanStack Query, Vite
- Database: PostgreSQL 16 with EVE SDE

**Character IDs for Testing:**
- Artallus: 526379435
- Cytrex: 1117367444
- Cytricia: 110592475

---

**Plan saved to:** `docs/plans/2025-12-11-multi-account-redesign-implementation.md`
