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
