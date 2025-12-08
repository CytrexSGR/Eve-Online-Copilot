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
