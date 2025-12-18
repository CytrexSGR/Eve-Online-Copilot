# Production System Frontend Implementation Plan

**Start Date:** 2025-12-18
**Duration:** 3 Weeks
**Goal:** Complete frontend integration of new production system APIs

---

## Week 1: Critical Migrations (Foundation)

### Day 1-2: Materials Overview Migration

**Files to Change:**
- `frontend/src/pages/MaterialsOverview.tsx`
- `frontend/src/api.ts` (if needed)

**Tasks:**
1. ✅ Replace `/api/production/optimize/{type_id}` with `/api/production/chains/{type_id}/materials`
2. ✅ Update data transformation logic
3. ✅ Test with multiple bookmarked items (minerals, PI, capital components)
4. ✅ Add production cost summary card
5. ✅ Deploy and test in production

**Success Criteria:**
- All bookmarked items show correct materials
- ME calculations match old system
- No console errors
- Response time <1s for 50 items

**Estimated Time:** 4-6 hours

---

### Day 3-5: Shopping Planner Migration

**Files to Change:**
- `frontend/src/pages/ShoppingPlanner.tsx`
- `frontend/src/hooks/shopping/useMaterialCalculation.ts` (if exists)
- `frontend/src/api.ts`

**Tasks:**
1. ✅ Update `calculateMaterials` mutation to use new chains API
2. ✅ Transform API response to match existing interface
3. ✅ Fetch economics data for sub-product profitability indicators
4. ✅ Add ROI indicators in sub-product modal
5. ✅ Test complete flow: Add Product → Calculate Materials → Apply → Shopping List
6. ✅ Test with complex items (Drake, Raven, Capital components)
7. ✅ Deploy and monitor

**Success Criteria:**
- Material calculation accurate (compare with old system)
- Sub-product decisions show ROI data
- Shopping list generation works correctly
- No regression in existing functionality

**Estimated Time:** 2-3 days

---

### Week 1 Deliverables
- ✅ MaterialsOverview.tsx migrated and tested
- ✅ ShoppingPlanner.tsx material calculation migrated
- ✅ Both features deployed to production
- ✅ Documentation updated

---

## Week 2: Enhanced Features (New Capabilities)

### Day 1-3: Production Planner Complete Rewrite

**Files to Change:**
- `frontend/src/pages/ProductionPlanner.tsx` (complete rewrite)
- `frontend/src/api.ts` (add new API functions)

**New Features to Implement:**
1. ✅ Multiple API integration
   - Materials: `/api/production/chains/{type_id}/materials`
   - Economics: `/api/production/economics/{type_id}`
   - Regions: `/api/production/economics/{type_id}/regions`
   - Opportunities: `/api/production/economics/opportunities`

2. ✅ UI Enhancements
   - Add TE level selector (0-20)
   - Add region selector
   - Separate material cost and job cost display
   - Production time with TE savings
   - ME savings column in materials table

3. ✅ New Sections
   - Multi-region comparison card
   - Similar profitable opportunities section
   - Action buttons: "Add to Shopping List", "Create Production Job", "Export Multibuy"

4. ✅ Integration Functions
   - `addToShoppingList()` - creates list and navigates
   - `createProductionJob()` - uses workflow API
   - `exportMultibuy()` - copies to clipboard

**Success Criteria:**
- All 4 APIs integrated correctly
- TE level affects production time display
- Multi-region comparison accurate
- Similar opportunities relevant and profitable (>10% ROI)
- Action buttons work and navigate correctly

**Estimated Time:** 3 days

---

### Day 4-5: War Room Integration

**Files to Change:**
- `frontend/src/pages/WarRoomMarketGaps.tsx`
- `frontend/src/api.ts`

**New Features:**
1. ✅ Add economics data fetching for top 20 market gaps
2. ✅ Add "Production ROI" column
3. ✅ Add "Actions" column with "Plan" button
4. ✅ Add filter: "Show Profitable Only" (ROI >10%)
5. ✅ Implement `addToProductionQueue()` function

**Success Criteria:**
- ROI data shows for manufacturable items
- Plan button adds to production planner with pre-filled data
- Filter correctly shows only profitable items
- Performance acceptable (loads within 2s)

**Estimated Time:** 1-2 days

---

### Week 2 Deliverables
- ✅ ProductionPlanner.tsx completely rewritten with all new APIs
- ✅ WarRoomMarketGaps.tsx with production economics integration
- ✅ All features tested and deployed
- ✅ User feedback collected

---

## Week 3: Polish & Optimization

### Day 1-2: Performance Optimization

**Tasks:**
1. ✅ Implement request caching
   - Cache economics data for 5 minutes
   - Cache chains data for 10 minutes
   - Use React Query staleTime effectively

2. ✅ Batch API requests where possible
   - Materials Overview: batch material requests
   - War Room: limit concurrent requests to 5

3. ✅ Optimize loading states
   - Skeleton loaders for tables
   - Progressive rendering for large lists
   - Cancel pending requests on navigation

4. ✅ Code splitting
   - Lazy load Production Planner
   - Lazy load War Room pages
   - Reduce initial bundle size

**Success Criteria:**
- Initial page load <2s
- API response time <500ms (95th percentile)
- No more than 5 concurrent API requests
- Bundle size reduced by >20%

**Estimated Time:** 2 days

---

### Day 3-4: UX Improvements

**Tasks:**
1. ✅ Add tooltips with calculation details
   - ME savings explanation
   - ROI calculation breakdown
   - Production time formula

2. ✅ Improve loading states
   - Skeleton screens
   - Progress indicators for multi-step operations
   - Error recovery UI

3. ✅ Dark mode refinements
   - Check all colors meet WCAG AA
   - Consistent hover states
   - Better focus indicators

4. ✅ Keyboard shortcuts
   - Ctrl+K: Quick search
   - Ctrl+Enter: Calculate/Apply
   - Esc: Close modals

5. ✅ Quick actions
   - Right-click context menus
   - Drag-and-drop items to shopping list
   - Bulk operations (select multiple)

**Success Criteria:**
- All interactive elements have tooltips
- Loading states smooth and informative
- Dark mode colors pass WCAG AA
- Keyboard navigation works throughout

**Estimated Time:** 2 days

---

### Day 5: Testing & Documentation

**Tasks:**
1. ✅ Comprehensive testing
   - Unit tests for data transformations
   - Integration tests for complete flows
   - Performance tests with large datasets
   - Cross-browser testing (Chrome, Firefox, Edge)

2. ✅ User acceptance testing
   - Beta test with corporation members
   - Collect feedback via Discord
   - Create bug reports for issues

3. ✅ Documentation updates
   - Update `/docs/production-system-api.md` with frontend examples
   - Create `/docs/user-guides/production-planner-guide.md`
   - Add screenshots and GIFs
   - Update CLAUDE.frontend.md

4. ✅ Release notes
   - Document all new features
   - Migration guide for users
   - Known issues and workarounds

**Success Criteria:**
- 90%+ code coverage for new components
- All integration tests passing
- User feedback score >4/5
- Documentation complete and reviewed

**Estimated Time:** 1 day

---

### Week 3 Deliverables
- ✅ Performance optimized (<500ms API calls)
- ✅ UX polished (tooltips, keyboard shortcuts, dark mode)
- ✅ Comprehensive testing complete
- ✅ Documentation updated
- ✅ Ready for full production rollout

---

## Implementation Order

### Sequence (to minimize risk and maximize learning)

```
1. MaterialsOverview (simplest, validates API)
   ↓
2. ShoppingPlanner (critical path, high usage)
   ↓
3. ProductionPlanner (showcase, all features)
   ↓
4. WarRoom (new feature, low risk)
   ↓
5. Optimization (performance)
   ↓
6. Polish (UX)
   ↓
7. Testing & Documentation
```

---

## Risk Mitigation

### Feature Flags

All migrations use feature flags for safe rollout:

```typescript
// .env
VITE_NEW_PRODUCTION_API=true  # Enable new API
VITE_PRODUCTION_BETA=true     # Enable beta features
```

### Rollback Plan

If critical issues occur:
1. Set feature flag to false
2. Deploy previous version
3. Investigate issue
4. Fix and re-deploy

### Monitoring

Track these metrics:
- API error rates
- Response times (p50, p95, p99)
- User feedback sentiment
- Feature usage statistics

---

## Daily Checklist

### Every Day:
- [ ] Run tests before starting work
- [ ] Commit changes frequently (every feature)
- [ ] Update todo list
- [ ] Test in production-like environment
- [ ] Document decisions and learnings

### End of Day:
- [ ] Push all commits to GitHub
- [ ] Update progress in plan
- [ ] Note any blockers or questions
- [ ] Plan next day's work

---

## Success Metrics

### Technical
- ✅ 100% migration to new APIs
- ✅ <500ms p95 response time
- ✅ Zero data inconsistencies
- ✅ 90%+ test coverage
- ✅ Zero production errors

### User
- 📊 Shopping Planner accuracy +20%
- 📊 Production Planner usage +50%
- 📊 War Room → Production conversion >20%
- 📊 User feedback >4.5/5
- 📊 Support tickets -30%

---

## Timeline Overview

```
Week 1: Foundation (Critical Migrations)
├─ Day 1-2: MaterialsOverview ✓
├─ Day 3-5: ShoppingPlanner ✓
└─ Deploy & Monitor

Week 2: Enhancement (New Features)
├─ Day 1-3: ProductionPlanner Rewrite ✓
├─ Day 4-5: WarRoom Integration ✓
└─ User Feedback Collection

Week 3: Excellence (Polish & Testing)
├─ Day 1-2: Performance Optimization ✓
├─ Day 3-4: UX Improvements ✓
├─ Day 5: Testing & Documentation ✓
└─ Production Rollout 🚀
```

---

## Team Communication

### Daily Standups (if applicable)
- What did I complete yesterday?
- What am I working on today?
- Any blockers?

### Weekly Reviews
- Week 1 End: Review migrations, plan Week 2
- Week 2 End: Review features, plan Week 3
- Week 3 End: Final review, celebrate! 🎉

---

## Celebration Milestones

- 🎯 Week 1 Complete: Materials & Shopping migrated successfully
- 🎯 Week 2 Complete: All new features live
- 🎯 Week 3 Complete: Polished, tested, documented
- 🎯 Final: Production System 2.0 fully operational! 🚀

---

**Status:** Ready to Execute
**Next Step:** Start Week 1, Day 1 - Materials Overview Migration
**Prepared by:** Claude Sonnet 4.5
**Date:** 2025-12-18
