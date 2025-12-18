# Production System - Complete Implementation Plan

**Date:** 2025-12-17
**Status:** Ready for Execution
**Estimated Time:** 2-3 hours

## Phase 1: Database & Chain Builder ✅ COMPLETED

- [x] Database migration (004_production_system.sql)
- [x] Repository layer (chain, economics, workflow)
- [x] Batch builder script
- [x] Process all 4,197 items
- [x] Verify data integrity

## Phase 2: Chain API & Service Layer

### 2.1 Chain Service Layer
- [ ] Implement `ProductionChainService` class
- [ ] `get_chain_tree()` - Full dependency tree
- [ ] `get_materials_list()` - Flattened materials with ME
- [ ] `get_direct_dependencies()` - One level only
- [ ] ME calculation helper functions

### 2.2 Chain Router & Endpoints
- [ ] Create `routers/production_chains.py`
- [ ] `GET /api/production/chains/{type_id}` - Full tree
- [ ] `GET /api/production/chains/{type_id}/materials` - Material list
- [ ] `GET /api/production/chains/{type_id}/direct` - Direct deps
- [ ] Register router in `main.py`

### 2.3 Test Chain API
- [ ] Test with simple item (Badger)
- [ ] Test with complex item (Drake)
- [ ] Test with Titan (Erebus)
- [ ] Verify ME calculations
- [ ] Test error cases (invalid type_id)

## Phase 3: Economics System

### 3.1 Economics Updater Job
- [ ] Create `jobs/production_economics_updater.py`
- [ ] Calculate material costs from `production_chains`
- [ ] Fetch market prices from `market_prices_cache`
- [ ] Calculate base job costs per region
- [ ] Get production time from SDE
- [ ] Update `production_economics` table

### 3.2 Economics Service Layer
- [ ] Implement `ProductionEconomicsService` class
- [ ] `get_economics()` - Single item economics
- [ ] `find_opportunities()` - Profitable items
- [ ] `compare_regions()` - Multi-region comparison
- [ ] `calculate_profit()` - Profit calculations

### 3.3 Economics Router & Endpoints
- [ ] Create `routers/production_economics.py`
- [ ] `GET /api/production/economics/{type_id}` - Item economics
- [ ] `GET /api/production/economics/opportunities` - Profitable items
- [ ] `GET /api/production/economics/{type_id}/regions` - Region comparison
- [ ] Register router in `main.py`

### 3.4 Test Economics System
- [ ] Run economics updater for test items
- [ ] Verify cost calculations
- [ ] Test ROI calculations
- [ ] Test opportunity finder
- [ ] Test region comparison

### 3.5 Cron Job Setup
- [ ] Create `jobs/cron_production_economics.sh`
- [ ] Add to crontab (every 30 minutes)
- [ ] Test cron execution

## Phase 4: Workflow System

### 4.1 Workflow Service Layer
- [ ] Implement `ProductionWorkflowService` class
- [ ] `create_job()` - Create production job
- [ ] `get_jobs()` - List jobs for character
- [ ] `update_job()` - Update job status
- [ ] `get_buildable_items()` - What can character build

### 4.2 Workflow Router & Endpoints
- [ ] Create `routers/production_workflow.py`
- [ ] `POST /api/production/workflow/jobs` - Create job
- [ ] `GET /api/production/workflow/jobs` - List jobs
- [ ] `PATCH /api/production/workflow/jobs/{job_id}` - Update job
- [ ] `GET /api/production/workflow/buildable` - Buildable items
- [ ] Register router in `main.py`

### 4.3 Test Workflow System
- [ ] Create test production job
- [ ] Update job status
- [ ] Test material tracking
- [ ] Test make-or-buy logic

## Phase 5: Integration & Refactoring

### 5.1 Integrate with Existing Systems
- [ ] Update `production_simulator.py` to use new chain data
- [ ] Migrate `manufacturing_opportunities` to use `production_economics`
- [ ] Update shopping lists to use chain API
- [ ] Test backward compatibility

### 5.2 Performance Optimization
- [ ] Add missing indexes if needed
- [ ] Optimize slow queries
- [ ] Cache frequently accessed chains
- [ ] Benchmark API response times

## Phase 6: Testing & Verification

### 6.1 API Tests
- [ ] Write unit tests for repositories
- [ ] Write unit tests for services
- [ ] Write integration tests for API endpoints
- [ ] Test error handling

### 6.2 End-to-End Testing
- [ ] Test complete production planning flow
- [ ] Test economics updates
- [ ] Test job creation and tracking
- [ ] Verify all calculations

### 6.3 Data Quality Checks
- [ ] Verify all chains terminate at raw materials
- [ ] Check for circular dependencies
- [ ] Validate cost calculations
- [ ] Cross-check with known values

## Phase 7: Documentation

### 7.1 API Documentation
- [ ] Update OpenAPI schema
- [ ] Add endpoint descriptions
- [ ] Add request/response examples
- [ ] Generate API docs

### 7.2 User Documentation
- [ ] Create production system guide
- [ ] Document ME/TE calculations
- [ ] Add example queries
- [ ] Create troubleshooting guide

### 7.3 Developer Documentation
- [ ] Document database schema
- [ ] Document service layer
- [ ] Add code comments
- [ ] Create architecture diagram

## Success Criteria

### Functionality
- [ ] All API endpoints operational
- [ ] Economics updates running automatically
- [ ] Workflow system tracks jobs correctly
- [ ] ME/TE calculations accurate

### Performance
- [ ] Chain API responds in <100ms for simple items
- [ ] Chain API responds in <500ms for complex items
- [ ] Economics update processes 1000+ items in <5 minutes
- [ ] Database queries optimized with proper indexes

### Data Quality
- [ ] 100% of chains terminate at raw materials
- [ ] Cost calculations match manual calculations
- [ ] ROI calculations accurate
- [ ] No circular dependencies

### Integration
- [ ] Backward compatible with existing features
- [ ] Shopping lists work with new system
- [ ] Market hunter uses new economics
- [ ] No breaking changes

## Rollout Strategy

1. **Phase 2-4:** Implement all APIs (can run in parallel to existing system)
2. **Phase 5:** Gradual migration of features
3. **Phase 6:** Full testing before deprecating old system
4. **Phase 7:** Documentation and knowledge transfer

## Rollback Plan

- New tables independent of existing system
- Can disable new endpoints without affecting old system
- Old `production_simulator.py` remains available
- Cron jobs can be disabled without impact

## Estimated Timeline

- **Phase 2:** 30 minutes (Chain API)
- **Phase 3:** 45 minutes (Economics System)
- **Phase 4:** 30 minutes (Workflow System)
- **Phase 5:** 15 minutes (Integration)
- **Phase 6:** 30 minutes (Testing)
- **Phase 7:** 15 minutes (Documentation)

**Total:** ~2.5 hours for complete implementation
