# Production System API Documentation

**Version:** 1.0.0
**Date:** 2025-12-17

## Overview

Complete production system with chain analysis, economics calculations, and workflow management.

## API Endpoints

### Production Chains

**Base Path:** `/api/production`

#### GET /chains/{type_id}

Get complete production chain for an item.

**Query Parameters:**
- `format` (string): Output format - `tree` or `flat` (default: `tree`)

**Example:**
```bash
curl "http://localhost:8000/api/production/chains/24698?format=flat"
```

**Response:**
```json
{
  "item_type_id": 24698,
  "item_name": "Drake",
  "materials": [
    {
      "material_type_id": 34,
      "material_name": "Tritanium",
      "base_quantity": 5600000.0
    }
  ]
}
```

#### GET /chains/{type_id}/materials

Get flattened material list with ME adjustments.

**Query Parameters:**
- `me` (int): Material Efficiency 0-10 (default: 0)
- `runs` (int): Number of production runs (default: 1)

**Example:**
```bash
curl "http://localhost:8000/api/production/chains/24698/materials?me=10&runs=1"
```

**Response:**
```json
{
  "item_type_id": 24698,
  "item_name": "Drake",
  "runs": 1,
  "me_level": 10,
  "materials": [
    {
      "type_id": 34,
      "name": "Tritanium",
      "base_quantity": 5600000,
      "adjusted_quantity": 5040000,
      "me_savings": 560000
    }
  ]
}
```

#### GET /chains/{type_id}/direct

Get only direct material dependencies (1 level).

**Example:**
```bash
curl "http://localhost:8000/api/production/chains/648/direct"
```

### Production Economics

**Base Path:** `/api/production/economics`

#### GET /economics/{type_id}

Get complete production economics analysis.

**Query Parameters:**
- `region_id` (int): Region ID (default: 10000002 - The Forge)
- `me` (int): Material Efficiency 0-10 (default: 0)
- `te` (int): Time Efficiency 0-20 (default: 0)

**Example:**
```bash
curl "http://localhost:8000/api/production/economics/178?region_id=10000002&me=10"
```

**Response:**
```json
{
  "type_id": 178,
  "item_name": "Carbonized Lead S",
  "region_id": 10000002,
  "region_name": "The Forge",
  "costs": {
    "material_cost": 708.07,
    "job_cost": 15.73,
    "total_cost": 723.80
  },
  "market": {
    "sell_price": 3.0,
    "buy_price": 0.64
  },
  "profitability": {
    "profit_sell": -720.80,
    "profit_buy": -723.16,
    "roi_sell_percent": -99.59,
    "roi_buy_percent": -99.91
  },
  "production_time": 300
}
```

#### GET /economics/opportunities

Find profitable manufacturing opportunities.

**Query Parameters:**
- `region_id` (int): Region ID (default: 10000002)
- `min_roi` (float): Minimum ROI percentage (default: 0)
- `min_profit` (float): Minimum profit in ISK (default: 0)
- `limit` (int): Max results 1-500 (default: 50)

**Example:**
```bash
curl "http://localhost:8000/api/production/economics/opportunities?min_roi=15&min_profit=1000000&limit=20"
```

**Response:**
```json
{
  "region_id": 10000002,
  "region_name": "The Forge",
  "filters": {
    "min_roi": 15.0,
    "min_profit": 1000000.0
  },
  "opportunities": [
    {
      "type_id": 648,
      "name": "Badger",
      "roi_percent": 18.5,
      "profit": 2500000
    }
  ],
  "total_count": 15
}
```

#### GET /economics/{type_id}/regions

Compare production profitability across multiple regions.

**Example:**
```bash
curl "http://localhost:8000/api/production/economics/648/regions"
```

**Response:**
```json
{
  "type_id": 648,
  "item_name": "Badger",
  "regions": [
    {
      "region_id": 10000043,
      "region_name": "Domain",
      "roi_percent": 18.2,
      "profit": 3200000
    },
    {
      "region_id": 10000002,
      "region_name": "The Forge",
      "roi_percent": 14.5,
      "profit": 2800000
    }
  ],
  "best_region": {
    "region_id": 10000043,
    "region_name": "Domain"
  }
}
```

### Production Workflow

**Base Path:** `/api/production/workflow`

#### POST /jobs

Create a new production job.

**Request Body:**
```json
{
  "character_id": 526379435,
  "item_type_id": 648,
  "blueprint_type_id": 11535,
  "me_level": 10,
  "te_level": 20,
  "runs": 5,
  "materials": [
    {
      "material_type_id": 34,
      "quantity_needed": 400000,
      "decision": "buy",
      "cost_per_unit": 5.5,
      "total_cost": 2200000
    }
  ],
  "system_id": 30000144
}
```

**Response:**
```json
{
  "job_id": 123,
  "status": "planned",
  "total_cost": 2200000
}
```

#### GET /jobs

Get production jobs for a character.

**Query Parameters:**
- `character_id` (int): Character ID (required)
- `status` (string): Status filter (optional)

**Example:**
```bash
curl "http://localhost:8000/api/production/workflow/jobs?character_id=526379435&status=active"
```

#### PATCH /jobs/{job_id}

Update production job status.

**Request Body:**
```json
{
  "status": "completed",
  "actual_revenue": 3500000
}
```

## Data Updates

### Economics Updater

Update production economics data:

```bash
# Update 100 items in The Forge
python3 -m jobs.production_economics_updater --region=10000002 --limit=100

# Update all items
python3 -m jobs.production_economics_updater --all

# Update single item
python3 -m jobs.production_economics_updater --item=648 --region=10000002
```

### Cron Job

Economics data updates automatically every 30 minutes:

```bash
*/30 * * * * /home/cytrex/eve_copilot/jobs/cron_production_economics.sh
```

## Database

### Tables

- `production_dependencies` - Direct material requirements
- `production_chains` - Complete chains to raw materials
- `production_economics` - Cost and profitability data
- `production_jobs` - Production job tracking
- `production_job_materials` - Job materials with make-or-buy decisions

### Statistics

- **Items with chains:** 4,156
- **Total chain entries:** 32,131
- **Total dependencies:** 24,353

## Error Handling

All endpoints return standard HTTP status codes:

- `200 OK` - Success
- `404 Not Found` - Item or data not found
- `422 Unprocessable Entity` - Invalid parameters
- `500 Internal Server Error` - Server error

Error response format:
```json
{
  "detail": "Error message"
}
```

## Rate Limits

No rate limits currently enforced.

## Examples

### Find Profitable Ships

```bash
curl "http://localhost:8000/api/production/economics/opportunities?region_id=10000002&min_roi=10&limit=50"
```

### Calculate Drake Production Cost

```bash
curl "http://localhost:8000/api/production/chains/24698/materials?me=10&runs=1"
curl "http://localhost:8000/api/production/economics/24698?region_id=10000002&me=10"
```

### Compare Regions for Badger

```bash
curl "http://localhost:8000/api/production/economics/648/regions"
```

## Support

For issues or questions, see:
- API Documentation: http://localhost:8000/docs
- GitHub: https://github.com/CytrexSGR/Eve-Online-Copilot
