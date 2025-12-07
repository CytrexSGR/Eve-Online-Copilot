# Backend Development Guide

> **Back to:** [CLAUDE.md](CLAUDE.md)

---

## Docker

### Container Management

```bash
# Check database container
echo 'Aug2012#' | sudo -S docker ps | grep eve_db

# Start if not running
echo 'Aug2012#' | sudo -S docker start eve_db

# Connect to database
echo 'Aug2012#' | sudo -S docker exec eve_db psql -U eve -d eve_sde

# View container logs
echo 'Aug2012#' | sudo -S docker logs eve_db --tail 50
```

### Future Docker Setup (Planned)

The application will be containerized. Planned structure:

```yaml
# docker-compose.yml (planned)
services:
  backend:
    build: .
    ports:
      - "8000:8000"
    depends_on:
      - db
    volumes:
      - ./:/app
      - ./tokens.json:/app/tokens.json

  frontend:
    build: ./frontend
    ports:
      - "5173:5173"

  db:
    image: postgres:16
    environment:
      POSTGRES_DB: eve_sde
      POSTGRES_USER: eve
      POSTGRES_PASSWORD: EvE_Pr0ject_2024
    volumes:
      - postgres_data:/var/lib/postgresql/data
```

---

## Database

### Connection

```python
from database import get_db_connection

with get_db_connection() as conn:
    with conn.cursor() as cur:
        cur.execute("SELECT * FROM market_prices WHERE type_id = %s", (648,))
        rows = cur.fetchall()
```

### Common Queries

```sql
-- Get item info
SELECT "typeID", "typeName", "groupID" FROM "invTypes" WHERE "typeID" = 648;

-- Get blueprint materials
SELECT m."materialTypeID", t."typeName", m.quantity
FROM "invTypeMaterials" m
JOIN "invTypes" t ON m."materialTypeID" = t."typeID"
WHERE m."typeID" = 648;

-- Get regional prices
SELECT type_id, region_id, lowest_sell, highest_buy, sell_volume
FROM market_prices
WHERE type_id = 648;

-- Get combat losses
SELECT type_id, SUM(quantity) as total
FROM combat_ship_losses
WHERE kill_date > NOW() - INTERVAL '7 days'
GROUP BY type_id
ORDER BY total DESC
LIMIT 20;
```

### Migrations

Migrations are in `/home/cytrex/eve_copilot/migrations/`

```bash
# Run migration
echo 'Aug2012#' | sudo -S docker exec eve_db psql -U eve -d eve_sde -f /path/to/migration.sql

# Or via cat
cat migrations/003_war_room.sql | sudo -S docker exec -i eve_db psql -U eve -d eve_sde
```

---

## ESI Client

### Rate Limiting

The `esi_client.py` handles rate limiting automatically:

```python
from esi_client import esi_client

# Get market stats
stats = esi_client.get_market_stats(region_id=10000002, type_id=648)

# Get all region prices
prices = esi_client.get_all_region_prices(type_id=648)

# Find arbitrage
opportunities = esi_client.find_arbitrage_opportunities(type_id=648, min_profit=5.0)
```

### Error Handling

```python
result = esi_client.get_market_stats(region_id, type_id)
if not result.get("total_orders"):
    # No market data
    pass
```

### Cache

```python
# Clear cache if needed
esi_client.clear_cache()
```

---

## Authentication

### OAuth2 Flow

1. User visits `/api/auth/login`
2. Redirected to EVE SSO
3. Callback to `/api/auth/callback`
4. Token stored in `tokens.json`

### Token Usage

```python
from auth import eve_auth

# Get authenticated characters
characters = eve_auth.get_authenticated_characters()

# Refresh token
result = eve_auth.refresh_token(character_id)

# Get valid token for API call
token = eve_auth.get_valid_token(character_id)
```

### Character Data

```python
from character import character_api

# Wallet
balance = character_api.get_wallet_balance(character_id)

# Assets
assets = character_api.get_assets(character_id, location_id=None)

# Skills
skills = character_api.get_skills(character_id)

# Market orders
orders = character_api.get_market_orders(character_id)

# Industry jobs
jobs = character_api.get_industry_jobs(character_id, include_completed=False)
```

---

## API Patterns

### Router Structure

```python
# routers/example.py
from fastapi import APIRouter, HTTPException, Query
from typing import Optional

router = APIRouter(prefix="/api/example", tags=["example"])

@router.get("/items")
async def get_items(
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0)
):
    """Get paginated items"""
    return {"items": [], "total": 0}

@router.get("/items/{item_id}")
async def get_item(item_id: int):
    """Get single item"""
    item = fetch_item(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return item
```

### Register Router

```python
# main.py
from routers.example import router as example_router

app.include_router(example_router)
```

### Request Models

```python
from pydantic import BaseModel
from typing import Optional, List

class CreateItemRequest(BaseModel):
    name: str
    type_id: int
    quantity: int = 1
    notes: Optional[str] = None
    tags: Optional[List[str]] = None

@router.post("/items")
async def create_item(request: CreateItemRequest):
    return {"id": 1, **request.dict()}
```

---

## Critical Patterns

### 1. Always Use Parameterized Queries

```python
# CORRECT
cur.execute("SELECT * FROM items WHERE type_id = %s", (type_id,))

# WRONG - SQL Injection risk!
cur.execute(f"SELECT * FROM items WHERE type_id = {type_id}")
```

### 2. Handle ESI Errors Gracefully

```python
result = esi_client.get_market_stats(region_id, type_id)
if isinstance(result, dict) and "error" in result:
    raise HTTPException(status_code=400, detail=result["error"])
```

### 3. Use Context Managers for Database

```python
# CORRECT - Connection automatically closed
with get_db_connection() as conn:
    with conn.cursor() as cur:
        cur.execute(query)

# WRONG - Connection might leak
conn = get_db_connection()
cur = conn.cursor()
cur.execute(query)
# forgot to close!
```

### 4. Batch Database Operations

```python
# CORRECT - Single query
cur.execute("""
    SELECT type_id, lowest_sell FROM market_prices
    WHERE type_id = ANY(%s)
""", (type_ids,))

# WRONG - N+1 queries
for type_id in type_ids:
    cur.execute("SELECT lowest_sell FROM market_prices WHERE type_id = %s", (type_id,))
```

### 5. Material Efficiency Calculation

```python
# ME reduces material requirements
me_factor = 1 - (me_level / 100)  # ME 10 = 0.9 multiplier
adjusted_quantity = max(1, int(base_quantity * me_factor))
```

---

## Services

### Adding a New Service

```python
# my_service.py
from database import get_db_connection
from config import SOME_CONFIG

class MyService:
    def __init__(self):
        self.cache = {}

    def get_data(self, item_id: int) -> dict:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT * FROM my_table WHERE id = %s
                """, (item_id,))
                row = cur.fetchone()
                if not row:
                    return {"error": "Not found"}
                return {"id": row[0], "name": row[1]}

my_service = MyService()
```

### Using in Router

```python
from my_service import my_service

@router.get("/data/{item_id}")
async def get_data(item_id: int):
    result = my_service.get_data(item_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result
```

---

## Cron Jobs

### Job Structure

```python
#!/usr/bin/env python3
"""
Job description here
"""
import sys
import logging
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    logger.info("Starting job...")
    try:
        # Job logic here
        pass
    except Exception as e:
        logger.error(f"Job failed: {e}")
        sys.exit(1)
    logger.info("Job completed successfully")

if __name__ == "__main__":
    main()
```

### Cron Shell Wrapper

```bash
#!/bin/bash
# jobs/cron_my_job.sh
cd /home/cytrex/eve_copilot
/usr/bin/python3 -m jobs.my_job >> logs/my_job.log 2>&1
```

### Add to Crontab

```bash
# Edit crontab
crontab -e

# Add line
*/5 * * * * /home/cytrex/eve_copilot/jobs/cron_my_job.sh
```

---

## Testing

### Manual API Testing

```bash
# Health check
curl http://localhost:8000/

# Get item
curl http://localhost:8000/api/items/648

# POST with JSON
curl -X POST http://localhost:8000/api/shopping/lists \
  -H "Content-Type: application/json" \
  -d '{"name": "Test List"}'

# Pretty print
curl http://localhost:8000/api/production/optimize/648 | python3 -m json.tool
```

### Database Testing

```bash
# Connect and run query
echo 'Aug2012#' | sudo -S docker exec eve_db psql -U eve -d eve_sde -c "SELECT COUNT(*) FROM market_prices;"
```

---

## Troubleshooting

### Backend won't start

```bash
# Check if port is in use
lsof -i :8000

# Kill existing process
pkill -f uvicorn

# Start with verbose logging
uvicorn main:app --host 0.0.0.0 --port 8000 --reload --log-level debug
```

### Database connection failed

```bash
# Check container
echo 'Aug2012#' | sudo -S docker ps | grep eve_db

# Start container
echo 'Aug2012#' | sudo -S docker start eve_db

# Test connection
echo 'Aug2012#' | sudo -S docker exec eve_db psql -U eve -d eve_sde -c "SELECT 1;"
```

### ESI rate limited

- Check response headers for rate limit info
- Wait 60 seconds for reset
- Reduce parallel requests in batch jobs

### Token expired

```bash
# Check token status
curl http://localhost:8000/api/auth/characters

# Refresh specific character
curl -X POST http://localhost:8000/api/auth/refresh/1117367444
```

---

## Configuration Reference

### config.py

```python
# Database
DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "database": "eve_sde",
    "user": "eve",
    "password": "EvE_Pr0ject_2024"
}

# ESI
ESI_BASE_URL = "https://esi.evetech.net/latest"

# Regions
REGIONS = {
    "the_forge": 10000002,      # Jita
    "domain": 10000043,          # Amarr
    "heimatar": 10000030,        # Rens
    "sinq_laison": 10000032,     # Dodixie
    "metropolis": 10000042,      # Hek
}

# Market Hunter
HUNTER_MIN_ROI = 15.0
HUNTER_MIN_PROFIT = 500000
HUNTER_TOP_CANDIDATES = 20
HUNTER_DEFAULT_ME = 10

# War Room
WAR_DATA_RETENTION_DAYS = 30
WAR_DOCTRINE_MIN_FLEET_SIZE = 10
WAR_HEATMAP_MIN_KILLS = 5
```

---

**Last Updated:** 2025-12-07
