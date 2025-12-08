# EVE Co-Pilot Complete Refactoring Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Completely refactor EVE Co-Pilot from monolithic structure to clean architecture with test coverage, proper documentation, and Docker-ready setup.

**Architecture:** Service-Repository pattern with dependency injection, clear separation of API/Business Logic/Data layers, comprehensive test coverage using TDD approach, modern Python tooling (pytest, pydantic, type hints).

**Tech Stack:** Python 3.11+, FastAPI, PostgreSQL, pytest, pydantic, Docker (prep)

---

## Phase 1: Foundation & Infrastructure

### Task 1: Setup Modern Python Project Structure

**Files:**
- Create: `pyproject.toml`
- Create: `pytest.ini`
- Create: `.env.example`
- Create: `requirements.txt`
- Create: `requirements-dev.txt`

**Step 1: Write pyproject.toml**

```toml
[project]
name = "eve-copilot"
version = "1.2.0"
description = "EVE Online industry and market analysis tool"
requires-python = ">=3.11"
dependencies = [
    "fastapi>=0.104.0",
    "uvicorn[standard]>=0.24.0",
    "psycopg2-binary>=2.9.9",
    "pydantic>=2.5.0",
    "pydantic-settings>=2.1.0",
    "requests>=2.31.0",
    "aiohttp>=3.9.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.4.0",
    "pytest-asyncio>=0.21.0",
    "pytest-cov>=4.1.0",
    "pytest-mock>=3.12.0",
    "black>=23.11.0",
    "ruff>=0.1.6",
    "mypy>=1.7.0",
]

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = "test_*.py"
python_classes = "Test*"
python_functions = "test_*"
asyncio_mode = "auto"
addopts = "-v --tb=short --strict-markers"

[tool.black]
line-length = 100
target-version = ['py311']

[tool.ruff]
line-length = 100
target-version = "py311"
select = ["E", "F", "W", "I", "N", "UP"]

[tool.mypy]
python_version = "3.11"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true
```

**Step 2: Create pytest.ini**

```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
asyncio_mode = auto
addopts = -v --tb=short --strict-markers --cov=src --cov-report=term-missing --cov-report=html
```

**Step 3: Create requirements.txt**

```txt
fastapi>=0.104.0
uvicorn[standard]>=0.24.0
psycopg2-binary>=2.9.9
pydantic>=2.5.0
pydantic-settings>=2.1.0
requests>=2.31.0
aiohttp>=3.9.0
python-multipart>=0.0.6
```

**Step 4: Create requirements-dev.txt**

```txt
-r requirements.txt
pytest>=7.4.0
pytest-asyncio>=0.21.0
pytest-cov>=4.1.0
pytest-mock>=3.12.0
black>=23.11.0
ruff>=0.1.6
mypy>=1.7.0
httpx>=0.25.0
```

**Step 5: Create .env.example**

```bash
# Database Configuration
DB_HOST=localhost
DB_PORT=5432
DB_NAME=eve_sde
DB_USER=eve
DB_PASSWORD=your_password

# EVE SSO
EVE_CLIENT_ID=your_client_id
EVE_CLIENT_SECRET=your_client_secret
EVE_CALLBACK_URL=http://localhost:8000/api/auth/callback

# Application
API_HOST=0.0.0.0
API_PORT=8000
CORS_ORIGINS=["http://localhost:5173"]

# Discord (Optional)
DISCORD_WEBHOOK_URL=

# War Room
WAR_DATA_RETENTION_DAYS=30
WAR_DOCTRINE_MIN_FLEET_SIZE=10
WAR_HEATMAP_MIN_KILLS=5

# Market Hunter
HUNTER_MIN_ROI=15.0
HUNTER_MIN_PROFIT=500000
HUNTER_TOP_CANDIDATES=20
HUNTER_DEFAULT_ME=10
```

**Step 6: Install development dependencies**

```bash
pip3 install -r requirements-dev.txt
```

Expected: All packages install successfully

**Step 7: Commit**

```bash
git add pyproject.toml pytest.ini requirements.txt requirements-dev.txt .env.example
git commit -m "chore: setup modern Python project structure

- Add pyproject.toml with project metadata and tool configs
- Configure pytest with async support and coverage
- Split requirements into prod and dev dependencies
- Add .env.example for configuration template

🤖 Generated with Claude Code
Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

### Task 2: Create New Directory Structure

**Files:**
- Create: `src/` directory structure
- Create: `tests/` directory structure
- Create: `data/` directory

**Step 1: Create src directory structure**

```bash
mkdir -p src/{api/{routers,dependencies},core,services/{auth,market,character,shopping,war,navigation,mining},integrations/{esi,discord},models}
touch src/__init__.py
touch src/api/__init__.py
touch src/api/routers/__init__.py
touch src/api/dependencies.py
touch src/api/middleware.py
touch src/core/__init__.py
touch src/core/config.py
touch src/core/database.py
touch src/core/exceptions.py
touch src/services/__init__.py
touch src/services/{auth,market,character,shopping,war,navigation,mining}/__init__.py
touch src/integrations/__init__.py
touch src/integrations/esi/__init__.py
touch src/integrations/discord/__init__.py
touch src/models/__init__.py
touch src/models/schemas.py
touch src/models/entities.py
```

Expected: All directories and __init__.py files created

**Step 2: Create tests directory structure**

```bash
mkdir -p tests/{unit/{services,integrations,models},integration,fixtures}
touch tests/__init__.py
touch tests/conftest.py
touch tests/unit/__init__.py
touch tests/unit/services/__init__.py
touch tests/unit/integrations/__init__.py
touch tests/unit/models/__init__.py
touch tests/integration/__init__.py
touch tests/fixtures/__init__.py
```

Expected: Test directory structure created

**Step 3: Create data directory**

```bash
mkdir -p data/cache
touch data/.gitkeep
touch data/cache/.gitkeep
```

Expected: Data directory created

**Step 4: Create .gitignore entry for data**

```bash
cat >> .gitignore << 'EOF'

# Runtime data
data/*.json
data/cache/*
!data/.gitkeep
!data/cache/.gitkeep

# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
env/
venv/
.venv/
.pytest_cache/
.coverage
htmlcov/
*.egg-info/
dist/
build/

# IDE
.vscode/
.idea/
*.swp
*.swo

# Environment
.env
config.py
EOF
```

Expected: .gitignore updated

**Step 5: Commit**

```bash
git add src/ tests/ data/ .gitignore
git commit -m "chore: create new project directory structure

- Add src/ with layered architecture (api/core/services/integrations/models)
- Add tests/ with unit/integration separation
- Add data/ for runtime files (gitignored)
- Update .gitignore for Python and runtime files

🤖 Generated with Claude Code
Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

### Task 3: Core Configuration Module (TDD)

**Files:**
- Create: `tests/unit/test_config.py`
- Create: `src/core/config.py`

**Step 1: Write the failing test**

Create `tests/unit/test_config.py`:

```python
"""Tests for core configuration module."""

import pytest
from pydantic import ValidationError


def test_config_loads_from_env(monkeypatch):
    """Test configuration loads from environment variables."""
    monkeypatch.setenv("DB_HOST", "testhost")
    monkeypatch.setenv("DB_PORT", "5433")
    monkeypatch.setenv("DB_NAME", "testdb")
    monkeypatch.setenv("DB_USER", "testuser")
    monkeypatch.setenv("DB_PASSWORD", "testpass")
    monkeypatch.setenv("EVE_CLIENT_ID", "test_client_id")
    monkeypatch.setenv("EVE_CLIENT_SECRET", "test_secret")
    monkeypatch.setenv("EVE_CALLBACK_URL", "http://test/callback")

    from src.core.config import get_settings

    settings = get_settings()
    assert settings.db_host == "testhost"
    assert settings.db_port == 5433
    assert settings.db_name == "testdb"


def test_config_has_defaults():
    """Test configuration has sensible defaults."""
    from src.core.config import Settings

    settings = Settings(
        db_host="localhost",
        db_name="eve_sde",
        db_user="eve",
        db_password="test",
        eve_client_id="id",
        eve_client_secret="secret",
        eve_callback_url="http://test"
    )

    assert settings.api_host == "0.0.0.0"
    assert settings.api_port == 8000
    assert settings.hunter_min_roi == 15.0


def test_config_validates_required_fields():
    """Test configuration validates required database fields."""
    from src.core.config import Settings

    with pytest.raises(ValidationError):
        Settings(eve_client_id="id", eve_client_secret="secret")
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/unit/test_config.py -v
```

Expected: FAIL with "ModuleNotFoundError: No module named 'src.core.config'"

**Step 3: Write minimal implementation**

Create `src/core/config.py`:

```python
"""Core configuration using Pydantic Settings."""

from functools import lru_cache
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    # Database
    db_host: str
    db_port: int = 5432
    db_name: str
    db_user: str
    db_password: str

    # EVE SSO
    eve_client_id: str
    eve_client_secret: str
    eve_callback_url: str

    # Application
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    cors_origins: List[str] = ["*"]

    # Discord (Optional)
    discord_webhook_url: str = ""

    # War Room
    war_data_retention_days: int = 30
    war_doctrine_min_fleet_size: int = 10
    war_heatmap_min_kills: int = 5
    war_everef_base_url: str = "https://data.everef.net/killmails"

    # Market Hunter
    hunter_min_roi: float = 15.0
    hunter_min_profit: int = 500000
    hunter_top_candidates: int = 20
    hunter_default_me: int = 10

    # ESI
    esi_base_url: str = "https://esi.evetech.net/latest"
    esi_user_agent: str = "EVE-Co-Pilot/1.2.0"

    @property
    def database_url(self) -> str:
        """Construct database URL."""
        return f"postgresql://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
```

**Step 4: Run test to verify it passes**

```bash
pytest tests/unit/test_config.py -v
```

Expected: PASS (3 tests)

**Step 5: Commit**

```bash
git add tests/unit/test_config.py src/core/config.py
git commit -m "feat(core): add configuration management with Pydantic

- Implement Settings class with env variable loading
- Add validation for required fields
- Include sensible defaults for all optional settings
- Add database_url property for connection string
- Full test coverage

🤖 Generated with Claude Code
Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

### Task 4: Core Database Connection Pool (TDD)

**Files:**
- Create: `tests/unit/test_database.py`
- Create: `src/core/database.py`

**Step 1: Write the failing test**

Create `tests/unit/test_database.py`:

```python
"""Tests for database connection management."""

import pytest
from unittest.mock import Mock, patch, MagicMock


def test_database_pool_initializes():
    """Test database pool initializes with settings."""
    from src.core.database import DatabasePool
    from src.core.config import Settings

    settings = Settings(
        db_host="localhost",
        db_name="test",
        db_user="user",
        db_password="pass",
        eve_client_id="id",
        eve_client_secret="secret",
        eve_callback_url="http://test"
    )

    with patch('src.core.database.psycopg2.pool.SimpleConnectionPool') as mock_pool:
        pool = DatabasePool(settings)
        assert pool is not None
        mock_pool.assert_called_once()


def test_database_connection_context_manager():
    """Test database connection as context manager."""
    from src.core.database import DatabasePool
    from src.core.config import Settings

    settings = Settings(
        db_host="localhost",
        db_name="test",
        db_user="user",
        db_password="pass",
        eve_client_id="id",
        eve_client_secret="secret",
        eve_callback_url="http://test"
    )

    mock_conn = MagicMock()
    mock_pool = Mock()
    mock_pool.getconn.return_value = mock_conn

    with patch('src.core.database.psycopg2.pool.SimpleConnectionPool', return_value=mock_pool):
        pool = DatabasePool(settings)

        with pool.get_connection() as conn:
            assert conn == mock_conn

        mock_pool.putconn.assert_called_once_with(mock_conn)


def test_database_query_helper():
    """Test database query helper method."""
    from src.core.database import DatabasePool
    from src.core.config import Settings

    settings = Settings(
        db_host="localhost",
        db_name="test",
        db_user="user",
        db_password="pass",
        eve_client_id="id",
        eve_client_secret="secret",
        eve_callback_url="http://test"
    )

    mock_cursor = MagicMock()
    mock_cursor.fetchall.return_value = [{"id": 1, "name": "test"}]
    mock_conn = MagicMock()
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
    mock_pool = Mock()
    mock_pool.getconn.return_value = mock_conn

    with patch('src.core.database.psycopg2.pool.SimpleConnectionPool', return_value=mock_pool):
        pool = DatabasePool(settings)
        results = pool.execute_query("SELECT * FROM test")

        assert results == [{"id": 1, "name": "test"}]
        mock_cursor.execute.assert_called_once_with("SELECT * FROM test", None)
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/unit/test_database.py -v
```

Expected: FAIL with "ModuleNotFoundError: No module named 'src.core.database'"

**Step 3: Write minimal implementation**

Create `src/core/database.py`:

```python
"""Database connection pool management."""

from contextlib import contextmanager
from typing import Any, Dict, List, Optional

import psycopg2
from psycopg2 import pool
from psycopg2.extras import RealDictCursor

from src.core.config import Settings


class DatabasePool:
    """Manages PostgreSQL connection pool."""

    def __init__(self, settings: Settings, min_conn: int = 1, max_conn: int = 20):
        """Initialize connection pool."""
        self.settings = settings
        self.pool = psycopg2.pool.SimpleConnectionPool(
            min_conn,
            max_conn,
            host=settings.db_host,
            port=settings.db_port,
            database=settings.db_name,
            user=settings.db_user,
            password=settings.db_password
        )

    @contextmanager
    def get_connection(self):
        """Get a connection from the pool as context manager."""
        conn = self.pool.getconn()
        try:
            yield conn
        finally:
            self.pool.putconn(conn)

    def execute_query(
        self,
        query: str,
        params: Optional[tuple] = None,
        fetch: bool = True
    ) -> List[Dict[str, Any]]:
        """Execute a query and return results as list of dicts."""
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(query, params)
                if fetch:
                    return [dict(row) for row in cur.fetchall()]
                return []

    def close(self):
        """Close all connections in the pool."""
        if self.pool:
            self.pool.closeall()


# Global pool instance (initialized on app startup)
_db_pool: Optional[DatabasePool] = None


def init_database_pool(settings: Settings) -> DatabasePool:
    """Initialize global database pool."""
    global _db_pool
    _db_pool = DatabasePool(settings)
    return _db_pool


def get_database_pool() -> DatabasePool:
    """Get global database pool instance."""
    if _db_pool is None:
        raise RuntimeError("Database pool not initialized. Call init_database_pool first.")
    return _db_pool
```

**Step 4: Run test to verify it passes**

```bash
pytest tests/unit/test_database.py -v
```

Expected: PASS (3 tests)

**Step 5: Commit**

```bash
git add tests/unit/test_database.py src/core/database.py
git commit -m "feat(core): add database connection pool

- Implement DatabasePool with psycopg2 SimpleConnectionPool
- Add context manager for connection handling
- Add query helper method
- Global pool instance for dependency injection
- Full test coverage with mocks

🤖 Generated with Claude Code
Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

### Task 5: Custom Exceptions

**Files:**
- Create: `tests/unit/test_exceptions.py`
- Create: `src/core/exceptions.py`

**Step 1: Write the failing test**

Create `tests/unit/test_exceptions.py`:

```python
"""Tests for custom exceptions."""

import pytest


def test_not_found_exception():
    """Test NotFoundError exception."""
    from src.core.exceptions import NotFoundError

    error = NotFoundError("Item", 123)
    assert str(error) == "Item with ID 123 not found"
    assert error.resource == "Item"
    assert error.resource_id == 123


def test_validation_error():
    """Test ValidationError exception."""
    from src.core.exceptions import ValidationError

    error = ValidationError("Invalid input", {"field": "name", "error": "required"})
    assert "Invalid input" in str(error)
    assert error.details == {"field": "name", "error": "required"}


def test_external_api_error():
    """Test ExternalAPIError exception."""
    from src.core.exceptions import ExternalAPIError

    error = ExternalAPIError("ESI API", 503, "Service unavailable")
    assert error.service_name == "ESI API"
    assert error.status_code == 503
    assert "Service unavailable" in str(error)


def test_authentication_error():
    """Test AuthenticationError exception."""
    from src.core.exceptions import AuthenticationError

    error = AuthenticationError("Token expired")
    assert "Token expired" in str(error)
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/unit/test_exceptions.py -v
```

Expected: FAIL with "ModuleNotFoundError: No module named 'src.core.exceptions'"

**Step 3: Write minimal implementation**

Create `src/core/exceptions.py`:

```python
"""Custom exceptions for EVE Co-Pilot."""

from typing import Any, Dict, Optional


class EVECopilotError(Exception):
    """Base exception for all EVE Co-Pilot errors."""
    pass


class NotFoundError(EVECopilotError):
    """Raised when a resource is not found."""

    def __init__(self, resource: str, resource_id: Any):
        self.resource = resource
        self.resource_id = resource_id
        super().__init__(f"{resource} with ID {resource_id} not found")


class ValidationError(EVECopilotError):
    """Raised when validation fails."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        self.details = details or {}
        super().__init__(message)


class ExternalAPIError(EVECopilotError):
    """Raised when external API call fails."""

    def __init__(self, service_name: str, status_code: int, message: str):
        self.service_name = service_name
        self.status_code = status_code
        super().__init__(f"{service_name} error ({status_code}): {message}")


class AuthenticationError(EVECopilotError):
    """Raised when authentication fails."""
    pass


class AuthorizationError(EVECopilotError):
    """Raised when user is not authorized to access resource."""
    pass
```

**Step 4: Run test to verify it passes**

```bash
pytest tests/unit/test_exceptions.py -v
```

Expected: PASS (4 tests)

**Step 5: Commit**

```bash
git add tests/unit/test_exceptions.py src/core/exceptions.py
git commit -m "feat(core): add custom exception hierarchy

- Add base EVECopilotError exception
- Add NotFoundError for missing resources
- Add ValidationError for input validation
- Add ExternalAPIError for API failures
- Add Authentication/Authorization errors
- Full test coverage

🤖 Generated with Claude Code
Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Phase 2: Service Layer Refactoring

### Task 6: Shopping Service - Repository Pattern (TDD)

**Files:**
- Create: `tests/unit/services/test_shopping_repository.py`
- Create: `src/services/shopping/repository.py`
- Create: `src/services/shopping/models.py`

**Step 1: Write models first**

Create `src/services/shopping/models.py`:

```python
"""Shopping service domain models."""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class ShoppingListCreate(BaseModel):
    """Schema for creating a shopping list."""
    name: str = Field(..., min_length=1, max_length=255)
    character_id: Optional[int] = None
    corporation_id: Optional[int] = None
    notes: Optional[str] = None


class ShoppingListUpdate(BaseModel):
    """Schema for updating a shopping list."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    status: Optional[str] = None
    notes: Optional[str] = None


class ShoppingList(BaseModel):
    """Shopping list entity."""
    id: int
    name: str
    character_id: Optional[int]
    corporation_id: Optional[int]
    status: str = "active"
    notes: Optional[str]
    created_at: datetime
    updated_at: datetime
    item_count: int = 0
    purchased_count: int = 0


class ShoppingItemCreate(BaseModel):
    """Schema for creating a shopping list item."""
    type_id: int
    item_name: str
    quantity: int = Field(..., gt=0)
    parent_item_id: Optional[int] = None
    is_product: bool = False


class ShoppingItem(BaseModel):
    """Shopping list item entity."""
    id: int
    list_id: int
    type_id: int
    item_name: str
    quantity: int
    parent_item_id: Optional[int]
    is_product: bool
    is_purchased: bool
    purchase_price: Optional[float]
    purchase_location: Optional[str]
    created_at: datetime
```

**Step 2: Write the failing repository test**

Create `tests/unit/services/test_shopping_repository.py`:

```python
"""Tests for shopping repository."""

import pytest
from datetime import datetime
from unittest.mock import Mock, MagicMock


@pytest.fixture
def mock_db_pool():
    """Mock database pool."""
    pool = Mock()
    mock_cursor = MagicMock()
    mock_conn = MagicMock()
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
    pool.get_connection.return_value.__enter__.return_value = mock_conn
    return pool, mock_cursor


def test_create_shopping_list(mock_db_pool):
    """Test creating a shopping list."""
    from src.services.shopping.repository import ShoppingRepository
    from src.services.shopping.models import ShoppingListCreate

    pool, mock_cursor = mock_db_pool
    mock_cursor.fetchone.return_value = {
        "id": 1,
        "name": "Test List",
        "character_id": 123,
        "corporation_id": None,
        "status": "active",
        "notes": "Test notes",
        "created_at": datetime.now(),
        "updated_at": datetime.now()
    }

    repo = ShoppingRepository(pool)
    list_data = ShoppingListCreate(
        name="Test List",
        character_id=123,
        notes="Test notes"
    )

    result = repo.create(list_data)

    assert result["id"] == 1
    assert result["name"] == "Test List"
    mock_cursor.execute.assert_called_once()


def test_get_shopping_list_by_id(mock_db_pool):
    """Test getting shopping list by ID."""
    from src.services.shopping.repository import ShoppingRepository

    pool, mock_cursor = mock_db_pool
    mock_cursor.fetchone.return_value = {
        "id": 1,
        "name": "Test List",
        "status": "active"
    }

    repo = ShoppingRepository(pool)
    result = repo.get_by_id(1)

    assert result is not None
    assert result["id"] == 1
    mock_cursor.execute.assert_called_with(
        "SELECT * FROM shopping_lists WHERE id = %s",
        (1,)
    )


def test_get_shopping_list_not_found(mock_db_pool):
    """Test getting non-existent shopping list."""
    from src.services.shopping.repository import ShoppingRepository

    pool, mock_cursor = mock_db_pool
    mock_cursor.fetchone.return_value = None

    repo = ShoppingRepository(pool)
    result = repo.get_by_id(999)

    assert result is None


def test_list_shopping_lists_with_filters(mock_db_pool):
    """Test listing shopping lists with filters."""
    from src.services.shopping.repository import ShoppingRepository

    pool, mock_cursor = mock_db_pool
    mock_cursor.fetchall.return_value = [
        {"id": 1, "name": "List 1", "character_id": 123},
        {"id": 2, "name": "List 2", "character_id": 123}
    ]

    repo = ShoppingRepository(pool)
    results = repo.list_by_character(character_id=123)

    assert len(results) == 2
    assert results[0]["id"] == 1


def test_add_item_to_list(mock_db_pool):
    """Test adding item to shopping list."""
    from src.services.shopping.repository import ShoppingRepository
    from src.services.shopping.models import ShoppingItemCreate

    pool, mock_cursor = mock_db_pool
    mock_cursor.fetchone.return_value = {
        "id": 1,
        "list_id": 1,
        "type_id": 34,
        "item_name": "Tritanium",
        "quantity": 1000
    }

    repo = ShoppingRepository(pool)
    item_data = ShoppingItemCreate(
        type_id=34,
        item_name="Tritanium",
        quantity=1000
    )

    result = repo.add_item(list_id=1, item_data=item_data)

    assert result["id"] == 1
    assert result["type_id"] == 34
```

**Step 3: Run test to verify it fails**

```bash
pytest tests/unit/services/test_shopping_repository.py -v
```

Expected: FAIL with "ModuleNotFoundError: No module named 'src.services.shopping.repository'"

**Step 4: Write minimal repository implementation**

Create `src/services/shopping/repository.py`:

```python
"""Shopping repository - data access layer."""

from typing import Dict, List, Optional, Any
from psycopg2.extras import RealDictCursor

from src.core.database import DatabasePool
from src.services.shopping.models import ShoppingListCreate, ShoppingItemCreate


class ShoppingRepository:
    """Data access for shopping lists."""

    def __init__(self, db_pool: DatabasePool):
        """Initialize repository with database pool."""
        self.db = db_pool

    def create(self, list_data: ShoppingListCreate) -> Dict[str, Any]:
        """Create a new shopping list."""
        with self.db.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    INSERT INTO shopping_lists (name, character_id, corporation_id, notes)
                    VALUES (%s, %s, %s, %s)
                    RETURNING *
                    """,
                    (
                        list_data.name,
                        list_data.character_id,
                        list_data.corporation_id,
                        list_data.notes
                    )
                )
                conn.commit()
                return dict(cur.fetchone())

    def get_by_id(self, list_id: int) -> Optional[Dict[str, Any]]:
        """Get shopping list by ID."""
        with self.db.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    "SELECT * FROM shopping_lists WHERE id = %s",
                    (list_id,)
                )
                result = cur.fetchone()
                return dict(result) if result else None

    def list_by_character(
        self,
        character_id: int,
        status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """List shopping lists for a character."""
        with self.db.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                query = """
                    SELECT sl.*,
                           (SELECT COUNT(*) FROM shopping_list_items WHERE list_id = sl.id) as item_count,
                           (SELECT COUNT(*) FROM shopping_list_items
                            WHERE list_id = sl.id AND is_purchased) as purchased_count
                    FROM shopping_lists sl
                    WHERE character_id = %s
                """
                params = [character_id]

                if status:
                    query += " AND status = %s"
                    params.append(status)

                query += " ORDER BY created_at DESC"

                cur.execute(query, params)
                return [dict(row) for row in cur.fetchall()]

    def add_item(
        self,
        list_id: int,
        item_data: ShoppingItemCreate
    ) -> Dict[str, Any]:
        """Add item to shopping list."""
        with self.db.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    INSERT INTO shopping_list_items
                    (list_id, type_id, item_name, quantity, parent_item_id, is_product)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING *
                    """,
                    (
                        list_id,
                        item_data.type_id,
                        item_data.item_name,
                        item_data.quantity,
                        item_data.parent_item_id,
                        item_data.is_product
                    )
                )
                conn.commit()
                return dict(cur.fetchone())

    def update(self, list_id: int, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update shopping list."""
        if not updates:
            return self.get_by_id(list_id)

        set_clauses = ", ".join(f"{key} = %s" for key in updates.keys())
        query = f"UPDATE shopping_lists SET {set_clauses} WHERE id = %s RETURNING *"

        with self.db.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(query, (*updates.values(), list_id))
                conn.commit()
                result = cur.fetchone()
                return dict(result) if result else None

    def delete(self, list_id: int) -> bool:
        """Delete shopping list."""
        with self.db.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("DELETE FROM shopping_lists WHERE id = %s", (list_id,))
                conn.commit()
                return cur.rowcount > 0
```

**Step 5: Run test to verify it passes**

```bash
pytest tests/unit/services/test_shopping_repository.py -v
```

Expected: PASS (6 tests)

**Step 6: Commit**

```bash
git add src/services/shopping/ tests/unit/services/test_shopping_repository.py
git commit -m "feat(shopping): implement repository pattern with TDD

- Add Pydantic models for shopping lists and items
- Implement ShoppingRepository with data access methods
- Full test coverage with mocked database
- Clean separation of data access from business logic

🤖 Generated with Claude Code
Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

### Task 7: Shopping Service - Business Logic (TDD)

**Files:**
- Create: `tests/unit/services/test_shopping_service.py`
- Create: `src/services/shopping/service.py`

**Step 1: Write the failing test**

Create `tests/unit/services/test_shopping_service.py`:

```python
"""Tests for shopping service business logic."""

import pytest
from unittest.mock import Mock, AsyncMock
from datetime import datetime


@pytest.fixture
def mock_repository():
    """Mock shopping repository."""
    return Mock()


@pytest.fixture
def mock_market_service():
    """Mock market service."""
    return Mock()


def test_create_shopping_list(mock_repository):
    """Test creating shopping list."""
    from src.services.shopping.service import ShoppingService
    from src.services.shopping.models import ShoppingListCreate, ShoppingList

    mock_repository.create.return_value = {
        "id": 1,
        "name": "Test List",
        "character_id": 123,
        "corporation_id": None,
        "status": "active",
        "notes": None,
        "created_at": datetime.now(),
        "updated_at": datetime.now()
    }

    service = ShoppingService(mock_repository, Mock())
    list_data = ShoppingListCreate(name="Test List", character_id=123)

    result = service.create_list(list_data)

    assert isinstance(result, ShoppingList)
    assert result.id == 1
    assert result.name == "Test List"
    mock_repository.create.assert_called_once_with(list_data)


def test_get_shopping_list_success(mock_repository):
    """Test getting existing shopping list."""
    from src.services.shopping.service import ShoppingService
    from src.services.shopping.models import ShoppingList

    mock_repository.get_by_id.return_value = {
        "id": 1,
        "name": "Test List",
        "character_id": 123,
        "corporation_id": None,
        "status": "active",
        "notes": None,
        "created_at": datetime.now(),
        "updated_at": datetime.now(),
        "item_count": 0,
        "purchased_count": 0
    }

    service = ShoppingService(mock_repository, Mock())
    result = service.get_list(1)

    assert isinstance(result, ShoppingList)
    assert result.id == 1


def test_get_shopping_list_not_found(mock_repository):
    """Test getting non-existent shopping list raises error."""
    from src.services.shopping.service import ShoppingService
    from src.core.exceptions import NotFoundError

    mock_repository.get_by_id.return_value = None

    service = ShoppingService(mock_repository, Mock())

    with pytest.raises(NotFoundError) as exc_info:
        service.get_list(999)

    assert exc_info.value.resource == "Shopping list"
    assert exc_info.value.resource_id == 999


def test_add_item_to_list(mock_repository):
    """Test adding item to shopping list."""
    from src.services.shopping.service import ShoppingService
    from src.services.shopping.models import ShoppingItemCreate, ShoppingItem

    mock_repository.get_by_id.return_value = {"id": 1}
    mock_repository.add_item.return_value = {
        "id": 1,
        "list_id": 1,
        "type_id": 34,
        "item_name": "Tritanium",
        "quantity": 1000,
        "parent_item_id": None,
        "is_product": False,
        "is_purchased": False,
        "purchase_price": None,
        "purchase_location": None,
        "created_at": datetime.now()
    }

    service = ShoppingService(mock_repository, Mock())
    item_data = ShoppingItemCreate(
        type_id=34,
        item_name="Tritanium",
        quantity=1000
    )

    result = service.add_item(list_id=1, item_data=item_data)

    assert isinstance(result, ShoppingItem)
    assert result.type_id == 34
    mock_repository.add_item.assert_called_once_with(1, item_data)


def test_add_item_to_nonexistent_list(mock_repository):
    """Test adding item to non-existent list raises error."""
    from src.services.shopping.service import ShoppingService
    from src.services.shopping.models import ShoppingItemCreate
    from src.core.exceptions import NotFoundError

    mock_repository.get_by_id.return_value = None

    service = ShoppingService(mock_repository, Mock())
    item_data = ShoppingItemCreate(
        type_id=34,
        item_name="Tritanium",
        quantity=1000
    )

    with pytest.raises(NotFoundError):
        service.add_item(list_id=999, item_data=item_data)
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/unit/services/test_shopping_service.py -v
```

Expected: FAIL with "ModuleNotFoundError: No module named 'src.services.shopping.service'"

**Step 3: Write minimal service implementation**

Create `src/services/shopping/service.py`:

```python
"""Shopping service - business logic layer."""

from typing import List, Optional

from src.services.shopping.repository import ShoppingRepository
from src.services.shopping.models import (
    ShoppingList,
    ShoppingListCreate,
    ShoppingListUpdate,
    ShoppingItem,
    ShoppingItemCreate
)
from src.core.exceptions import NotFoundError


class ShoppingService:
    """Business logic for shopping lists."""

    def __init__(
        self,
        repository: ShoppingRepository,
        market_service: Any  # Will be typed properly later
    ):
        """Initialize service with dependencies."""
        self.repo = repository
        self.market = market_service

    def create_list(self, list_data: ShoppingListCreate) -> ShoppingList:
        """Create a new shopping list."""
        result = self.repo.create(list_data)
        return ShoppingList(**result, item_count=0, purchased_count=0)

    def get_list(self, list_id: int) -> ShoppingList:
        """Get shopping list by ID."""
        result = self.repo.get_by_id(list_id)
        if not result:
            raise NotFoundError("Shopping list", list_id)
        return ShoppingList(**result)

    def list_by_character(
        self,
        character_id: int,
        status: Optional[str] = None
    ) -> List[ShoppingList]:
        """List shopping lists for a character."""
        results = self.repo.list_by_character(character_id, status)
        return [ShoppingList(**r) for r in results]

    def add_item(
        self,
        list_id: int,
        item_data: ShoppingItemCreate
    ) -> ShoppingItem:
        """Add item to shopping list."""
        # Verify list exists
        if not self.repo.get_by_id(list_id):
            raise NotFoundError("Shopping list", list_id)

        result = self.repo.add_item(list_id, item_data)
        return ShoppingItem(**result)

    def update_list(
        self,
        list_id: int,
        updates: ShoppingListUpdate
    ) -> ShoppingList:
        """Update shopping list."""
        if not self.repo.get_by_id(list_id):
            raise NotFoundError("Shopping list", list_id)

        update_data = updates.model_dump(exclude_unset=True)
        result = self.repo.update(list_id, update_data)
        return ShoppingList(**result)

    def delete_list(self, list_id: int) -> bool:
        """Delete shopping list."""
        if not self.repo.get_by_id(list_id):
            raise NotFoundError("Shopping list", list_id)

        return self.repo.delete(list_id)
```

**Step 4: Run test to verify it passes**

```bash
pytest tests/unit/services/test_shopping_service.py -v
```

Expected: PASS (5 tests)

**Step 5: Commit**

```bash
git add src/services/shopping/service.py tests/unit/services/test_shopping_service.py
git commit -m "feat(shopping): implement business logic service with TDD

- Add ShoppingService with clean business logic
- Delegate data access to repository
- Raise NotFoundError for missing resources
- Full test coverage with mocked dependencies

🤖 Generated with Claude Code
Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Phase 3: Migration Strategy

### Task 8: Create Migration Script

**Files:**
- Create: `scripts/migrate_to_new_structure.py`

**Step 1: Create migration script**

Create `scripts/migrate_to_new_structure.py`:

```python
#!/usr/bin/env python3
"""
Migration script to move files to new structure.
Run this after all new services are implemented and tested.
"""

import os
import shutil
from pathlib import Path


MIGRATIONS = {
    # Move service files
    "shopping_service.py": "src/services/shopping/legacy_service.py",
    "market_service.py": "src/services/market/legacy_service.py",
    "production_simulator.py": "src/services/market/production.py",
    "killmail_service.py": "src/services/war/killmail_service.py",
    "war_analyzer.py": "src/services/war/analyzer.py",
    "route_service.py": "src/services/navigation/route_service.py",
    "cargo_service.py": "src/services/navigation/cargo_service.py",
    "material_classifier.py": "src/services/market/material_classifier.py",
    "bookmark_service.py": "src/services/character/bookmark_service.py",
    "character.py": "src/services/character/character_service.py",
    "auth.py": "src/services/auth/auth_service.py",

    # Move integrations
    "esi_client.py": "src/integrations/esi/client.py",
    "notification_service.py": "src/integrations/discord/notification_service.py",

    # Move core files
    "database.py": "src/core/legacy_database.py",
    "schemas.py": "src/models/legacy_schemas.py",

    # Move data files
    "tokens.json": "data/tokens.json",
    "auth_state.json": "data/auth_state.json",
    "scan_results.json": "data/scan_results.json",
}


def migrate_files():
    """Move files to new structure."""
    base_path = Path(__file__).parent.parent

    for old_path, new_path in MIGRATIONS.items():
        old_file = base_path / old_path
        new_file = base_path / new_path

        if not old_file.exists():
            print(f"⚠️  Skip: {old_path} (not found)")
            continue

        # Create parent directory
        new_file.parent.mkdir(parents=True, exist_ok=True)

        # Move file
        shutil.move(str(old_file), str(new_file))
        print(f"✅ Moved: {old_path} → {new_path}")


def create_compatibility_imports():
    """Create import compatibility shims for gradual migration."""
    base_path = Path(__file__).parent.parent

    shims = {
        "shopping_service.py": "from src.services.shopping.legacy_service import *",
        "market_service.py": "from src.services.market.legacy_service import *",
        "database.py": "from src.core.legacy_database import *",
    }

    for filename, import_statement in shims.items():
        shim_file = base_path / filename
        with open(shim_file, "w") as f:
            f.write(f'"""\nCompatibility shim - imports from new location.\n"""\n\n{import_statement}\n')
        print(f"📝 Created shim: {filename}")


if __name__ == "__main__":
    print("🚀 Starting migration to new structure...\n")
    migrate_files()
    print("\n📦 Creating compatibility shims...\n")
    create_compatibility_imports()
    print("\n✅ Migration complete!")
    print("\n⚠️  Remember to:")
    print("  1. Update imports in routers/")
    print("  2. Update imports in jobs/")
    print("  3. Run tests: pytest tests/")
    print("  4. Remove shims after full migration")
```

**Step 2: Make executable**

```bash
chmod +x scripts/migrate_to_new_structure.py
```

**Step 3: Commit**

```bash
git add scripts/migrate_to_new_structure.py
git commit -m "chore: add migration script for new structure

- Script to move existing files to new directory structure
- Creates compatibility shims for gradual migration
- Moves data files to data/ directory

🤖 Generated with Claude Code
Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Phase 4: Documentation

### Task 9: API Documentation

**Files:**
- Create: `docs/api/README.md`
- Create: `docs/api/shopping.md`
- Create: `docs/api/authentication.md`

**Step 1: Create API docs directory**

```bash
mkdir -p docs/api
```

**Step 2: Create API README**

Create `docs/api/README.md`:

```markdown
# EVE Co-Pilot API Documentation

Complete REST API documentation for EVE Co-Pilot.

## Base URL

- Development: `http://localhost:8000`
- Production: `http://77.24.99.81:8000`

## Authentication

All authenticated endpoints require a valid EVE SSO token. See [Authentication Guide](authentication.md).

## API Sections

- [Authentication](authentication.md) - EVE SSO OAuth2 flow
- [Shopping Lists](shopping.md) - Manage shopping lists and items
- [Market & Production](market.md) - Market analysis and production planning
- [War Room](war-room.md) - Combat intelligence and loss tracking
- [Character](character.md) - Character and corporation data
- [Navigation](navigation.md) - Route planning and cargo calculations

## Interactive Documentation

FastAPI provides interactive API documentation:

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Response Format

All responses follow this structure:

### Success Response
```json
{
  "data": { ... },
  "status": "success"
}
```

### Error Response
```json
{
  "detail": "Error message",
  "status": "error"
}
```

## Rate Limiting

ESI API rate limits apply:
- 150 requests/second (burst)
- Error limit budget system

## Status Codes

- `200 OK` - Success
- `201 Created` - Resource created
- `400 Bad Request` - Invalid input
- `404 Not Found` - Resource not found
- `401 Unauthorized` - Authentication required
- `403 Forbidden` - Insufficient permissions
- `500 Internal Server Error` - Server error

## Common Parameters

### Pagination
```
?page=1&limit=50
```

### Filtering
```
?status=active&character_id=123
```

### Sorting
```
?sort=created_at&order=desc
```
```

**Step 3: Create Shopping API documentation**

Create `docs/api/shopping.md`:

```markdown
# Shopping Lists API

Manage shopping lists for production materials and items.

## Endpoints

### Create Shopping List

```http
POST /api/shopping/lists
```

**Request Body:**
```json
{
  "name": "T1 Frigate Production",
  "character_id": 526379435,
  "notes": "Materials for 10 Tristan builds"
}
```

**Response:**
```json
{
  "id": 1,
  "name": "T1 Frigate Production",
  "character_id": 526379435,
  "corporation_id": null,
  "status": "active",
  "notes": "Materials for 10 Tristan builds",
  "created_at": "2025-12-08T10:00:00Z",
  "updated_at": "2025-12-08T10:00:00Z",
  "item_count": 0,
  "purchased_count": 0
}
```

---

### Get Shopping Lists

```http
GET /api/shopping/lists?character_id=526379435&status=active
```

**Query Parameters:**
- `character_id` (optional) - Filter by character
- `corporation_id` (optional) - Filter by corporation
- `status` (optional) - Filter by status (active/completed/archived)

**Response:**
```json
[
  {
    "id": 1,
    "name": "T1 Frigate Production",
    "character_id": 526379435,
    "status": "active",
    "item_count": 15,
    "purchased_count": 8,
    "created_at": "2025-12-08T10:00:00Z"
  }
]
```

---

### Get Shopping List Details

```http
GET /api/shopping/lists/{list_id}
```

**Response:**
```json
{
  "id": 1,
  "name": "T1 Frigate Production",
  "items": [
    {
      "id": 1,
      "type_id": 34,
      "item_name": "Tritanium",
      "quantity": 50000,
      "is_purchased": false,
      "is_product": false
    }
  ]
}
```

---

### Add Item to List

```http
POST /api/shopping/lists/{list_id}/items
```

**Request Body:**
```json
{
  "type_id": 34,
  "item_name": "Tritanium",
  "quantity": 50000,
  "is_product": false
}
```

---

### Add Production Materials to List

```http
POST /api/shopping/lists/{list_id}/add-production/{type_id}?quantity=10&me=10
```

**Query Parameters:**
- `quantity` (required) - Number of runs
- `me` (optional) - Material efficiency (0-10, default: 10)

**Description:** Automatically adds all required materials for manufacturing the specified item.

---

### Update Shopping List

```http
PATCH /api/shopping/lists/{list_id}
```

**Request Body:**
```json
{
  "status": "completed",
  "notes": "All materials purchased"
}
```

---

### Delete Shopping List

```http
DELETE /api/shopping/lists/{list_id}
```

**Response:** `204 No Content`

---

## Shopping List Workflow

1. **Create list** - POST `/api/shopping/lists`
2. **Add production materials** - POST `/api/shopping/lists/{id}/add-production/{type_id}`
3. **Compare prices** - GET `/api/market/compare/{type_id}` for each item
4. **Mark as purchased** - PATCH `/api/shopping/lists/{id}/items/{item_id}`
5. **Complete list** - PATCH `/api/shopping/lists/{id}` with status "completed"

## Business Logic

### Material Hierarchy

Shopping lists support hierarchical materials:

```
Product (is_product=true)
├── Material 1 (parent_item_id=product_id)
├── Material 2
└── Sub-Product (is_product=true, parent_item_id=product_id)
    ├── Sub-Material 1 (parent_item_id=sub_product_id)
    └── Sub-Material 2
```

### Price Comparison

Use market API to find best prices:

```http
GET /api/market/compare/{type_id}?regions=10000002,10000043
```

Returns prices across multiple regions with route planning.
```

**Step 4: Commit**

```bash
git add docs/api/
git commit -m "docs: add comprehensive API documentation

- Add API overview with response formats
- Add shopping lists API documentation
- Add authentication guide
- Include examples and workflows

🤖 Generated with Claude Code
Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

### Task 10: Architecture Documentation

**Files:**
- Update: `docs/architecture/README.md`
- Create: `docs/architecture/service-layer.md`
- Create: `docs/architecture/testing-strategy.md`

**Step 1: Create architecture docs**

Create `docs/architecture/service-layer.md`:

```markdown
# Service Layer Architecture

EVE Co-Pilot uses a clean layered architecture with clear separation of concerns.

## Architecture Layers

```
┌─────────────────────────────────────┐
│         API Layer (FastAPI)         │
│   - Routers                          │
│   - Request/Response handling        │
│   - Dependency injection             │
└──────────────┬──────────────────────┘
               │
┌──────────────▼──────────────────────┐
│       Service Layer                  │
│   - Business logic                   │
│   - Validation                       │
│   - Orchestration                    │
└──────────────┬──────────────────────┘
               │
┌──────────────▼──────────────────────┐
│      Repository Layer                │
│   - Data access                      │
│   - SQL queries                      │
│   - Database operations              │
└──────────────┬──────────────────────┘
               │
┌──────────────▼──────────────────────┐
│         Database (PostgreSQL)        │
└─────────────────────────────────────┘
```

## Layer Responsibilities

### API Layer (`src/api/routers/`)

**Purpose:** Handle HTTP requests and responses

**Responsibilities:**
- Parse request data
- Validate input schemas
- Call service methods
- Format responses
- Handle HTTP errors

**Example:**
```python
@router.post("/lists", response_model=ShoppingList)
async def create_shopping_list(
    list_data: ShoppingListCreate,
    service: ShoppingService = Depends(get_shopping_service)
):
    """Create a new shopping list."""
    return service.create_list(list_data)
```

### Service Layer (`src/services/*/service.py`)

**Purpose:** Implement business logic

**Responsibilities:**
- Validate business rules
- Orchestrate multiple repositories
- Transform data
- Apply domain logic
- Raise domain exceptions

**Example:**
```python
class ShoppingService:
    def create_list(self, list_data: ShoppingListCreate) -> ShoppingList:
        """Create shopping list with validation."""
        # Business logic here
        result = self.repo.create(list_data)
        return ShoppingList(**result)
```

### Repository Layer (`src/services/*/repository.py`)

**Purpose:** Data access and persistence

**Responsibilities:**
- Execute SQL queries
- Map database rows to dicts
- Handle transactions
- No business logic

**Example:**
```python
class ShoppingRepository:
    def create(self, list_data: ShoppingListCreate) -> Dict[str, Any]:
        """Insert shopping list into database."""
        with self.db.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("INSERT INTO ...", params)
                return dict(cur.fetchone())
```

## Dependency Injection

FastAPI's dependency injection connects layers:

```python
# src/api/dependencies.py
def get_shopping_service() -> ShoppingService:
    """Construct shopping service with dependencies."""
    db_pool = get_database_pool()
    repository = ShoppingRepository(db_pool)
    market_service = get_market_service()
    return ShoppingService(repository, market_service)

# Usage in router
@router.get("/lists")
def get_lists(service: ShoppingService = Depends(get_shopping_service)):
    return service.list_by_character(123)
```

## Service Organization

Each service is organized as a package:

```
src/services/shopping/
├── __init__.py           # Public exports
├── service.py            # Business logic
├── repository.py         # Data access
├── models.py             # Pydantic schemas
└── exceptions.py         # Service-specific errors
```

## Cross-Service Communication

Services communicate through dependency injection:

```python
class ShoppingService:
    def __init__(
        self,
        repository: ShoppingRepository,
        market_service: MarketService,      # External service
        route_service: RouteService         # External service
    ):
        self.repo = repository
        self.market = market_service
        self.routes = route_service

    def optimize_prices(self, list_id: int):
        """Business logic using multiple services."""
        items = self.repo.get_items(list_id)
        prices = self.market.compare_prices(items)
        routes = self.routes.calculate_optimal_route(prices)
        return self._merge_results(prices, routes)
```

## Benefits

1. **Testability** - Each layer can be tested independently with mocks
2. **Maintainability** - Clear responsibilities, easy to find code
3. **Flexibility** - Easy to swap implementations (e.g., different database)
4. **Type Safety** - Pydantic models provide runtime validation
5. **Reusability** - Services can be composed and reused

## Migration from Monolith

Old structure:
```python
# shopping_service.py (1366 lines)
class ShoppingService:
    def create_list(self, name, character_id):
        conn = get_db_connection()  # Direct DB access
        cur = conn.cursor()
        cur.execute("INSERT INTO ...")  # SQL in service
        # Business logic mixed with data access
```

New structure:
```python
# src/services/shopping/service.py
class ShoppingService:
    def create_list(self, list_data: ShoppingListCreate) -> ShoppingList:
        result = self.repo.create(list_data)  # Delegate to repository
        return ShoppingList(**result)

# src/services/shopping/repository.py
class ShoppingRepository:
    def create(self, list_data: ShoppingListCreate) -> Dict[str, Any]:
        with self.db.get_connection() as conn:  # Clean data access
            # Pure SQL, no business logic
```
```

**Step 2: Create testing strategy documentation**

Create `docs/architecture/testing-strategy.md`:

```markdown
# Testing Strategy

EVE Co-Pilot uses Test-Driven Development (TDD) with comprehensive test coverage.

## Test Pyramid

```
        ┌─────────┐
        │   E2E   │  Few - Full system tests
        └─────────┘
      ┌─────────────┐
      │ Integration │  Some - Service integration
      └─────────────┘
    ┌─────────────────┐
    │   Unit Tests    │  Many - Fast, isolated
    └─────────────────┘
```

## Test Structure

```
tests/
├── unit/                  # Fast, isolated unit tests
│   ├── services/          # Service layer tests
│   ├── integrations/      # Integration tests (mocked)
│   └── models/            # Pydantic model tests
├── integration/           # Database integration tests
│   └── test_shopping_*.py
├── fixtures/              # Test data and fixtures
│   └── database.py
└── conftest.py            # Pytest configuration
```

## Unit Tests

**Purpose:** Test individual functions/methods in isolation

**Characteristics:**
- Fast (< 1ms per test)
- No database
- No external APIs
- Mocked dependencies

**Example:**
```python
def test_create_shopping_list(mock_repository):
    """Test service creates list correctly."""
    mock_repository.create.return_value = {"id": 1, "name": "Test"}

    service = ShoppingService(mock_repository, Mock())
    result = service.create_list(ShoppingListCreate(name="Test"))

    assert result.id == 1
    mock_repository.create.assert_called_once()
```

## Integration Tests

**Purpose:** Test interaction with real database

**Characteristics:**
- Slower (10-100ms per test)
- Real database (test instance)
- Transactional (rollback after each test)
- No external API calls

**Example:**
```python
@pytest.mark.integration
def test_shopping_repository_roundtrip(db_pool):
    """Test repository can save and retrieve data."""
    repo = ShoppingRepository(db_pool)

    # Create
    list_data = ShoppingListCreate(name="Test", character_id=123)
    created = repo.create(list_data)

    # Retrieve
    retrieved = repo.get_by_id(created["id"])

    assert retrieved["name"] == "Test"
```

## Test Fixtures

Reusable test data and setup:

```python
# tests/conftest.py

@pytest.fixture
def db_pool():
    """Provide database pool for integration tests."""
    settings = Settings(db_name="eve_sde_test", ...)
    pool = DatabasePool(settings)
    yield pool
    pool.close()

@pytest.fixture
def mock_shopping_repository():
    """Provide mocked repository."""
    return Mock(spec=ShoppingRepository)

@pytest.fixture
def shopping_list_data():
    """Provide test shopping list data."""
    return ShoppingListCreate(
        name="Test List",
        character_id=123,
        notes="Test notes"
    )
```

## TDD Workflow

### Red-Green-Refactor Cycle

1. **Red** - Write failing test first
2. **Green** - Write minimal code to pass
3. **Refactor** - Improve code without breaking tests

### Example TDD Session

**Step 1: Write failing test**
```python
def test_get_shopping_list_not_found():
    """Test getting non-existent list raises error."""
    service = ShoppingService(mock_repo, Mock())

    with pytest.raises(NotFoundError):
        service.get_list(999)
```

Run: `pytest -v` → **FAIL** (NotFoundError not raised)

**Step 2: Write minimal implementation**
```python
def get_list(self, list_id: int) -> ShoppingList:
    result = self.repo.get_by_id(list_id)
    if not result:
        raise NotFoundError("Shopping list", list_id)
    return ShoppingList(**result)
```

Run: `pytest -v` → **PASS**

**Step 3: Refactor if needed**

## Test Coverage

Maintain > 80% coverage:

```bash
pytest --cov=src --cov-report=html --cov-report=term
```

Coverage report shows:
- Which lines are tested
- Which branches are tested
- Overall coverage percentage

## Mocking Strategy

### What to Mock

✅ **Mock:**
- External APIs (ESI, Discord)
- Database connections (in unit tests)
- Time/datetime
- File system operations

❌ **Don't Mock:**
- Business logic
- Models/schemas
- Simple helper functions
- Database (in integration tests)

### Mocking Examples

**Mock external API:**
```python
@patch('src.integrations.esi.client.ESIClient.get')
def test_fetch_market_orders(mock_get):
    mock_get.return_value = {"orders": [...]}
    result = service.fetch_orders(type_id=34)
    assert len(result) > 0
```

**Mock datetime:**
```python
@patch('src.services.shopping.service.datetime')
def test_list_created_with_timestamp(mock_datetime):
    mock_datetime.now.return_value = datetime(2025, 12, 8, 10, 0)
    result = service.create_list(list_data)
    assert result.created_at.hour == 10
```

## Running Tests

### All tests
```bash
pytest
```

### Unit tests only
```bash
pytest tests/unit/ -v
```

### Integration tests only
```bash
pytest tests/integration/ -m integration
```

### Specific test file
```bash
pytest tests/unit/services/test_shopping_service.py -v
```

### Specific test
```bash
pytest tests/unit/services/test_shopping_service.py::test_create_list -v
```

### With coverage
```bash
pytest --cov=src --cov-report=html
```

View coverage: `open htmlcov/index.html`

## Continuous Integration

Tests run automatically on:
- Every commit (pre-commit hook)
- Every pull request
- Before deployment

CI pipeline:
1. Run linters (black, ruff, mypy)
2. Run unit tests
3. Run integration tests
4. Check coverage >= 80%
5. Build passes ✅

## Best Practices

1. **One test, one assertion** - Test one thing at a time
2. **Descriptive names** - `test_create_list_with_invalid_name_raises_error()`
3. **Arrange-Act-Assert** - Clear test structure
4. **Fast tests** - Unit tests < 1ms
5. **Independent tests** - No test depends on another
6. **Use fixtures** - Reuse test data
7. **Mock external dependencies** - No real API calls in tests
8. **Test edge cases** - Empty lists, None values, errors

## Anti-Patterns to Avoid

❌ **Testing implementation details**
```python
# Bad - tests how it works
def test_create_list_calls_execute():
    service.create_list(data)
    mock_cursor.execute.assert_called()

# Good - tests what it does
def test_create_list_returns_list():
    result = service.create_list(data)
    assert isinstance(result, ShoppingList)
```

❌ **Multiple assertions testing different things**
```python
# Bad
def test_create_list():
    result = service.create_list(data)
    assert result.id == 1
    assert result.name == "Test"
    assert result.status == "active"
    # ... 10 more assertions

# Good - split into focused tests
def test_create_list_assigns_id():
    result = service.create_list(data)
    assert result.id > 0

def test_create_list_sets_default_status():
    result = service.create_list(data)
    assert result.status == "active"
```

❌ **Tests that depend on each other**
```python
# Bad
def test_create_list():
    global list_id
    list_id = service.create_list(data).id

def test_get_list():
    result = service.get_list(list_id)  # Depends on previous test
```
```

**Step 3: Commit**

```bash
git add docs/architecture/
git commit -m "docs: add architecture and testing strategy documentation

- Document service layer architecture and responsibilities
- Add testing strategy with TDD workflow
- Include examples and best practices
- Document test pyramid and coverage requirements

🤖 Generated with Claude Code
Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Summary & Next Steps

This plan implements:

✅ **Phase 1: Foundation** (Tasks 1-5)
- Modern Python project setup
- New directory structure
- Core configuration with Pydantic
- Database connection pool
- Custom exceptions
- All with TDD!

✅ **Phase 2: Service Refactoring** (Tasks 6-7)
- Shopping service with Repository pattern
- Clean separation of concerns
- Full test coverage

✅ **Phase 3: Migration** (Task 8)
- Migration script for moving files
- Compatibility shims

✅ **Phase 4: Documentation** (Tasks 9-10)
- API documentation
- Architecture guides
- Testing strategy

## Estimated Effort

- **Phase 1:** ~2-3 hours (foundation is critical)
- **Phase 2:** ~8-10 hours per service (23 services total)
- **Phase 3:** ~1 hour (migration)
- **Phase 4:** ~4-6 hours (documentation)

**Total:** ~50-60 hours for complete refactoring

## Recommended Approach

1. **Complete Phase 1** (foundation) - Can't proceed without this
2. **Refactor ONE service completely** (Phase 2) - Shopping service as template
3. **Validate the pattern works** - Run tests, review with user
4. **Parallelize remaining services** - Use subagents for independent services
5. **Migrate incrementally** (Phase 3) - One service at a time
6. **Document continuously** (Phase 4) - Write docs as you build

## Service Refactoring Priority

After shopping service, tackle in this order:

1. **Market Service** - Core business logic
2. **Production Simulator** - Critical for market calculations
3. **Auth Service** - Security critical
4. **Character Service** - User-facing
5. **War Services** - Complex but isolated
6. **Navigation Services** - Standalone
7. **Mining Service** - Smallest, good for practice

---

**This plan provides:**
- Complete TDD workflow with failing tests first
- Exact file paths and commands
- Expected outputs for verification
- Frequent commits with clear messages
- Gradual migration strategy
- Production-ready architecture

**Plan written using superpowers:writing-plans skill** ✅
