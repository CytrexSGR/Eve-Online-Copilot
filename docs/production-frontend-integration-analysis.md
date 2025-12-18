# Production System Frontend Integration Analysis

**Date:** 2025-12-18
**Status:** Analysis Complete - Ready for Implementation

---

## Executive Summary

Das neue Produktionssystem (Production Chains, Economics, Workflow) muss in verschiedene Frontend-Bereiche integriert werden. Diese Analyse zeigt konkrete Integrationspunkte, erforderliche Code-Änderungen und Prioritäten.

**Betroffene Frontend-Bereiche:**
1. **War Room** (Market Gaps) - Produktionsmöglichkeiten bei Engpässen zeigen
2. **Shopping Planner** - Materialberechnung mit neuem Chain-API verbessern
3. **Materials Overview** - Migration auf neue Chain-API
4. **Production Planner** - Komplette Migration auf neue APIs

---

## 1. War Room Integration

### Betroffene Seite
**File:** `frontend/src/pages/WarRoomMarketGaps.tsx` (406 lines)

### Aktuelle Implementierung
```typescript
// Current API usage
const demandQuery = useQuery({
  queryKey: ['warDemand', regionId, days],
  queryFn: () => getWarDemand(regionId, days),
});

// Shows: Lost quantity, Market stock, Gap
// Data from: /api/war/demand/{region_id}
```

### Integration des neuen Systems

#### **Feature: Production Opportunity Indicators**

**Ziel:** Zeige bei Market Gaps, welche Items profitabel hergestellt werden können.

**Neue API Calls:**
```typescript
// For each item in market gaps, check if manufacturable and profitable
GET /api/production/economics/{type_id}?region_id={region_id}&me=10
```

**UI Enhancements:**

1. **Neue Spalte: "Production Profit"**
   - Zeigt ROI% und absoluten Profit
   - Farbcodierung: Grün (>15% ROI), Gelb (5-15%), Grau (<5%)
   - Nur angezeigt für herstellbare Items

2. **Action Button: "Quick Plan"**
   - Fügt Item direkt zum Production Planner oder Shopping List hinzu
   - Pre-fills ME=10 und estimated runs basierend auf Gap-Größe

3. **Filter: "Show Profitable Only"**
   - Zeigt nur Gaps, die durch profitable Produktion gedeckt werden können
   - Threshold: Min ROI 10%

**Code Changes:**

```typescript
// 1. Add new state for economics data
const [economicsData, setEconomicsData] = useState<Record<number, EconomicsData>>({});

// 2. Fetch economics for visible items
const { data: economicsMap } = useQuery({
  queryKey: ['war-market-gap-economics', filteredAndSorted.map(g => g.type_id).slice(0, 20)],
  queryFn: async () => {
    const results: Record<number, EconomicsData> = {};
    const topItems = filteredAndSorted.slice(0, 20); // Top 20 gaps only

    await Promise.all(
      topItems.map(async (gap) => {
        try {
          const response = await api.get(`/api/production/economics/${gap.type_id}`, {
            params: { region_id: regionId, me: 10 }
          });
          results[gap.type_id] = response.data;
        } catch {
          // Not manufacturable
        }
      })
    );
    return results;
  },
  enabled: gaps.length > 0,
});

// 3. Update table with new columns
<th>Gap</th>
<th>Production ROI</th> {/* NEW */}
<th>Actions</th>        {/* NEW */}

// 4. In table body
<td>
  {economicsMap?.[item.type_id] ? (
    <span className={getRoiClass(economicsMap[item.type_id].profitability.roi_sell_percent)}>
      {economicsMap[item.type_id].profitability.roi_sell_percent.toFixed(1)}%
      <span className="neutral"> / {formatISK(economicsMap[item.type_id].profitability.profit_sell)}</span>
    </span>
  ) : (
    <span className="neutral">-</span>
  )}
</td>
<td>
  {economicsMap?.[item.type_id] && economicsMap[item.type_id].profitability.roi_sell_percent > 10 && (
    <button
      className="btn btn-primary btn-sm"
      onClick={() => addToProductionQueue(item.type_id, item.name, Math.ceil(Math.abs(item.gap)))}
      title="Add to production planner"
    >
      <Plus size={14} /> Plan
    </button>
  )}
</td>
```

**Benefits:**
- War Room Analysten sehen sofort, welche Gaps durch profitable Produktion gelöst werden können
- Direkte Weiterleitung zu Production Planner mit vorausgefüllten Daten
- Verbindet Nachfrage-Analyse mit Produktionsplanung

**Priority:** ⭐⭐⭐ HIGH (hoher Mehrwert für War Room Analytics)

---

## 2. Shopping Planner Integration

### Betroffene Seite
**File:** `frontend/src/pages/ShoppingPlanner.tsx` (1,229 lines)

### Aktuelle Implementierung

```typescript
// Current material calculation
const calculateMaterials = useMutation({
  mutationFn: async (itemId: number) => {
    const response = await api.post<CalculateMaterialsResponse>(
      `/api/shopping/items/${itemId}/calculate-materials`
    );
    return response.data;
  },
});

// Manual handling of sub-product decisions
// Shows modal for buy/build choices
// Applies materials via POST /api/shopping/items/{itemId}/apply-materials
```

### Integration des neuen Systems

#### **Feature: Accurate Production Chain Calculation**

**Problem:** Aktuell verwendet Shopping Planner eine separate, potentiell veraltete Material-Berechnung.

**Lösung:** Nutze das neue Production Chains API als Single Source of Truth.

**Neue API Integration:**

```typescript
// Replace /api/shopping/items/{itemId}/calculate-materials with:
GET /api/production/chains/{type_id}/materials?me={me}&runs={runs}

// Response provides:
{
  "item_type_id": 648,
  "item_name": "Badger",
  "runs": 1,
  "me_level": 10,
  "materials": [
    {
      "type_id": 34,
      "name": "Tritanium",
      "base_quantity": 400000,
      "adjusted_quantity": 360000,
      "me_savings": 40000
    }
  ]
}
```

**Code Changes:**

```typescript
// 1. Update calculateMaterials to use production chains API
const calculateMaterials = useMutation({
  mutationFn: async (itemId: number) => {
    // Get item details from shopping list
    const item = selectedListData?.products.find(p => p.id === itemId);
    if (!item) throw new Error('Item not found');

    // Use new production chains API
    const response = await api.get(`/api/production/chains/${item.type_id}/materials`, {
      params: {
        me: item.me_level || 10,
        runs: item.runs || 1
      }
    });

    // Transform to match existing interface
    return {
      product: { id: itemId, ...response.data },
      materials: response.data.materials,
      sub_products: [] // Fetch separately if needed
    };
  },
});

// 2. Add economics check for sub-product decisions
const checkSubProductProfitability = async (typeId: number, regionId: number) => {
  try {
    const response = await api.get(`/api/production/economics/${typeId}`, {
      params: { region_id: regionId, me: 10 }
    });
    return response.data.profitability.roi_sell_percent;
  } catch {
    return null;
  }
};

// 3. Enhance sub-product modal with profitability data
{pendingMaterials.sub_products.map(sp => (
  <div key={sp.type_id}>
    <div>{sp.item_name}</div>
    <div className="neutral">
      x{formatQuantity(sp.quantity)}
      {/* NEW: Show ROI indicator */}
      {sp.roi && (
        <span className={sp.roi > 15 ? 'positive' : sp.roi > 5 ? 'neutral' : 'negative'}>
          {sp.roi > 0 && '+'}{sp.roi.toFixed(1)}% ROI
        </span>
      )}
    </div>
    <select
      value={subProductDecisions[sp.type_id] || 'buy'}
      onChange={e => setSubProductDecisions({
        ...subProductDecisions,
        [sp.type_id]: e.target.value as 'buy' | 'build'
      })}
    >
      <option value="buy">Buy</option>
      <option value="build">Build {/* Recommended if ROI > 15% */}</option>
    </select>
  </div>
))}
```

**Benefits:**
- Konsistente Materialberechnung über alle Features hinweg
- Einheitliche ME-Berechnung (keine Diskrepanzen mehr)
- Sub-Product Entscheidungen basierend auf tatsächlicher Profitabilität
- Einfachere Wartung (eine API für alle)

**Priority:** ⭐⭐⭐⭐ CRITICAL (Kernfunktionalität, hohe Nutzerfrequenz)

---

## 3. Materials Overview Integration

### Betroffene Seite
**File:** `frontend/src/pages/MaterialsOverview.tsx` (320 lines)

### Aktuelle Implementierung

```typescript
// Current API usage - OLD PRODUCTION API
const { data: productionDataMap } = useQuery({
  queryKey: ['bookmarks-production', bookmarks?.map(b => b.type_id).join(',')],
  queryFn: async () => {
    const result: Record<number, ProductionData> = {};
    await Promise.all(
      bookmarks.map(async (bookmark) => {
        const response = await api.get(`/api/production/optimize/${bookmark.type_id}`, {
          params: { me: 10 }
        });
        result[bookmark.type_id] = response.data;
      })
    );
    return result;
  },
});
```

### Integration des neuen Systems

#### **Feature: Migrate to New Production Chains API**

**Ziel:** Replace old `/api/production/optimize/{type_id}` with new chains API.

**Neue API:**
```typescript
GET /api/production/chains/{type_id}/materials?me=10&runs=1
```

**Code Changes:**

```typescript
// 1. Replace API call with new chains endpoint
const { data: productionDataMap, isLoading: productionLoading, refetch: refetchProduction } = useQuery<Record<number, ProductionData>>({
  queryKey: ['bookmarks-production-v2', bookmarks?.map(b => b.type_id).join(',')],
  queryFn: async () => {
    if (!bookmarks || bookmarks.length === 0) return {};
    const result: Record<number, ProductionData> = {};

    await Promise.all(
      bookmarks.map(async (bookmark) => {
        try {
          // NEW: Use production chains API
          const response = await api.get(`/api/production/chains/${bookmark.type_id}/materials`, {
            params: { me: 10, runs: 1 }
          });

          // Transform to match existing interface
          result[bookmark.type_id] = {
            materials: response.data.materials.map((mat: any) => ({
              type_id: mat.type_id,
              name: mat.name,
              base_quantity: mat.base_quantity,
              adjusted_quantity: mat.adjusted_quantity,
              prices_by_region: mat.prices_by_region || {} // May need separate pricing call
            }))
          };
        } catch {
          // Ignore items without blueprints
        }
      })
    );

    return result;
  },
  enabled: !!bookmarks && bookmarks.length > 0,
  staleTime: 60000,
});

// 2. OPTIONAL: Add economics summary
const { data: economicsSummary } = useQuery({
  queryKey: ['bookmarks-economics', bookmarks?.map(b => b.type_id).join(',')],
  queryFn: async () => {
    // Fetch economics for all bookmarked items to show total production cost vs market value
    const results: Record<number, EconomicsData> = {};
    await Promise.all(
      bookmarks!.map(async (bookmark) => {
        try {
          const response = await api.get(`/api/production/economics/${bookmark.type_id}`, {
            params: { region_id: 10000002, me: 10 }
          });
          results[bookmark.type_id] = response.data;
        } catch {}
      })
    );
    return results;
  },
  enabled: !!bookmarks && bookmarks.length > 0,
});
```

**Enhanced Features:**

1. **Production Cost Summary Card** (NEW)
   - Total material cost across all bookmarked items
   - Total production cost (materials + job fees)
   - Potential profit if all items were manufactured and sold

```typescript
// Add new stat card
<div className="stat-card">
  <div className="stat-label">Total Production Cost</div>
  <div className="stat-value isk">
    {formatISK(
      Object.values(economicsSummary || {}).reduce(
        (sum, econ) => sum + econ.costs.total_cost,
        0
      )
    )}
  </div>
  <div className="neutral" style={{ fontSize: 12, marginTop: 4 }}>
    {Object.keys(economicsSummary || {}).length} manufacturable items
  </div>
</div>
```

2. **Profitability Column** (NEW)
   - Show potential ROI for each bookmarked item
   - Color-coded: Green (profitable), Red (loss), Grey (N/A)

**Benefits:**
- Konsistente Daten mit Production Planner
- Schnellere Berechnungen (optimiertes Chain-API)
- Basis für zukünftige Erweiterungen (Batch-Produktion planen)

**Priority:** ⭐⭐⭐ HIGH (direkte Migration, keine neuen Features nötig)

---

## 4. Production Planner Integration

### Betroffene Seite
**File:** `frontend/src/pages/ProductionPlanner.tsx` (349 lines)

### Aktuelle Implementierung

```typescript
// Current API - OLD SYSTEM
const { data: productionData } = useQuery<ProductionData>({
  queryKey: ['production', selectedItem?.typeID, meLevel],
  queryFn: async () => {
    const response = await api.get(`/api/production/optimize/${selectedItem!.typeID}`, {
      params: { me: meLevel },
    });
    return response.data;
  },
});

// Current features:
// - Material costs by region
// - Best production region
// - Best sell region
// - ROI calculation
```

### Integration des neuen Systems

#### **Feature: Complete Migration to New Production System**

**Ziel:** Vollständige Umstellung auf die neuen APIs mit erweiterten Features.

**Neue API Integration:**

```typescript
// 1. Materials and costs
GET /api/production/chains/{type_id}/materials?me={me}&runs={runs}

// 2. Economics and profitability
GET /api/production/economics/{type_id}?region_id={region_id}&me={me}&te={te}

// 3. Multi-region comparison
GET /api/production/economics/{type_id}/regions

// 4. Find similar opportunities
GET /api/production/economics/opportunities?region_id={region_id}&min_roi=10&limit=20
```

**Complete Rewrite:**

```typescript
export default function ProductionPlanner() {
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedItem, setSelectedItem] = useState<SearchResult | null>(null);
  const [meLevel, setMeLevel] = useState(10);
  const [teLevel, setTeLevel] = useState(20);
  const [runs, setRuns] = useState(1);
  const [selectedRegion, setSelectedRegion] = useState(10000002); // The Forge

  // Search items (unchanged)
  const { data: searchResults } = useQuery<SearchResult[]>({
    queryKey: ['itemSearch', searchQuery],
    queryFn: () => searchItems(searchQuery),
    enabled: searchQuery.length >= 2,
  });

  // NEW: Get production chain materials
  const { data: materialsData, isLoading: materialsLoading } = useQuery({
    queryKey: ['production-materials', selectedItem?.typeID, meLevel, runs],
    queryFn: async () => {
      const response = await api.get(`/api/production/chains/${selectedItem!.typeID}/materials`, {
        params: { me: meLevel, runs }
      });
      return response.data;
    },
    enabled: !!selectedItem,
  });

  // NEW: Get economics for selected region
  const { data: economicsData, isLoading: economicsLoading } = useQuery({
    queryKey: ['production-economics', selectedItem?.typeID, selectedRegion, meLevel, teLevel],
    queryFn: async () => {
      const response = await api.get(`/api/production/economics/${selectedItem!.typeID}`, {
        params: { region_id: selectedRegion, me: meLevel, te: teLevel }
      });
      return response.data;
    },
    enabled: !!selectedItem,
  });

  // NEW: Get multi-region comparison
  const { data: regionsData } = useQuery({
    queryKey: ['production-regions', selectedItem?.typeID],
    queryFn: async () => {
      const response = await api.get(`/api/production/economics/${selectedItem!.typeID}/regions`);
      return response.data;
    },
    enabled: !!selectedItem,
  });

  // NEW: Get similar profitable opportunities
  const { data: opportunities } = useQuery({
    queryKey: ['production-opportunities', selectedRegion],
    queryFn: async () => {
      const response = await api.get('/api/production/economics/opportunities', {
        params: {
          region_id: selectedRegion,
          min_roi: 10,
          min_profit: 1000000,
          limit: 10
        }
      });
      return response.data;
    },
  });

  const isLoading = materialsLoading || economicsLoading;

  return (
    <div>
      {/* Header with filters (unchanged) */}
      <div className="page-header">
        <h1>Production Planner</h1>
        <p>Plan production with accurate costs, profitability, and workflow integration</p>
      </div>

      {/* Search and Filters */}
      <div className="card">
        <div className="filters">
          {/* Item search (unchanged) */}
          <div className="filter-group" style={{ flex: 1 }}>
            <label>Search Item</label>
            <div className="search-box">
              <Search size={18} />
              <input type="text" placeholder="Search for an item..." />
            </div>
          </div>

          {/* ME Level */}
          <div className="filter-group">
            <label>ME Level</label>
            <select value={meLevel} onChange={(e) => setMeLevel(Number(e.target.value))}>
              {[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10].map((level) => (
                <option key={level} value={level}>ME {level}</option>
              ))}
            </select>
          </div>

          {/* NEW: TE Level */}
          <div className="filter-group">
            <label>TE Level</label>
            <select value={teLevel} onChange={(e) => setTeLevel(Number(e.target.value))}>
              {[0, 2, 4, 6, 8, 10, 12, 14, 16, 18, 20].map((level) => (
                <option key={level} value={level}>TE {level}</option>
              ))}
            </select>
          </div>

          {/* NEW: Region Selector */}
          <div className="filter-group">
            <label>Region</label>
            <select value={selectedRegion} onChange={(e) => setSelectedRegion(Number(e.target.value))}>
              <option value={10000002}>The Forge (Jita)</option>
              <option value={10000043}>Domain (Amarr)</option>
              <option value={10000030}>Heimatar (Rens)</option>
              <option value={10000032}>Sinq Laison (Dodixie)</option>
              <option value={10000042}>Metropolis (Hek)</option>
            </select>
          </div>

          {/* Runs */}
          <div className="filter-group">
            <label>Runs</label>
            <input type="number" value={runs} onChange={(e) => setRuns(Math.max(1, Number(e.target.value)))} />
          </div>
        </div>
      </div>

      {economicsData && (
        <>
          {/* NEW: Summary Stats with economics data */}
          <div className="stats-grid">
            <div className="stat-card">
              <div className="stat-label">Material Cost</div>
              <div className="stat-value isk">{formatISK(economicsData.costs.material_cost * runs)}</div>
            </div>
            <div className="stat-card">
              <div className="stat-label">Job Cost</div>
              <div className="stat-value isk">{formatISK(economicsData.costs.job_cost * runs)}</div>
            </div>
            <div className="stat-card">
              <div className="stat-label">Total Cost</div>
              <div className="stat-value isk">{formatISK(economicsData.costs.total_cost * runs)}</div>
            </div>
            <div className="stat-card">
              <div className="stat-label">Sell Price</div>
              <div className="stat-value isk positive">{formatISK(economicsData.market.sell_price * runs)}</div>
            </div>
            <div className="stat-card">
              <div className="stat-label">Profit (Sell)</div>
              <div className={`stat-value ${economicsData.profitability.profit_sell > 0 ? 'positive' : 'negative'}`}>
                {economicsData.profitability.profit_sell > 0 ? '+' : ''}
                {formatISK(economicsData.profitability.profit_sell * runs)}
              </div>
            </div>
            <div className="stat-card">
              <div className="stat-label">ROI</div>
              <div className={`stat-value ${economicsData.profitability.roi_sell_percent > 0 ? 'positive' : 'negative'}`}>
                {economicsData.profitability.roi_sell_percent.toFixed(1)}%
              </div>
            </div>
            {/* NEW: Production Time */}
            <div className="stat-card">
              <div className="stat-label">Production Time</div>
              <div className="stat-value">{Math.floor(economicsData.production_time / 60)}h {economicsData.production_time % 60}m</div>
              <div className="neutral" style={{ fontSize: 12 }}>per run</div>
            </div>
            {/* NEW: TE Savings */}
            <div className="stat-card">
              <div className="stat-label">Time Saved (TE{teLevel})</div>
              <div className="stat-value positive">
                {Math.floor((economicsData.production_time * (teLevel / 100)) / 60)}h
              </div>
            </div>
          </div>

          {/* NEW: Multi-Region Comparison */}
          <div className="card">
            <h3 style={{ marginBottom: 16 }}>
              <TrendingUp size={18} style={{ marginRight: 8 }} />
              Regional Comparison
            </h3>
            <div className="region-grid">
              {regionsData?.regions.map((region: any) => (
                <div
                  key={region.region_id}
                  className={`region-card ${region.region_id === regionsData.best_region.region_id ? 'best' : ''}`}
                >
                  <div className="region-name">
                    {region.region_name}
                    {region.region_id === regionsData.best_region.region_id && (
                      <span className="badge badge-green">Best</span>
                    )}
                  </div>
                  <div className="region-stats">
                    <div>
                      <span className="neutral">Profit:</span>
                      <span className={`isk ${region.profit > 0 ? 'positive' : 'negative'}`}>
                        {formatISK(region.profit)}
                      </span>
                    </div>
                    <div>
                      <span className="neutral">ROI:</span>
                      <span className={region.roi_percent > 0 ? 'positive' : 'negative'}>
                        {region.roi_percent.toFixed(1)}%
                      </span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Materials Table (updated with new data structure) */}
          <div className="card">
            <h3 style={{ marginBottom: 16 }}>
              <Package size={18} style={{ marginRight: 8 }} />
              Required Materials
            </h3>
            <div className="table-container">
              <table>
                <thead>
                  <tr>
                    <th>Material</th>
                    <th>Base Qty</th>
                    <th>With ME{meLevel}</th>
                    <th>Total (×{runs})</th>
                    <th>ME Savings</th>
                    <th>Unit Price</th>
                    <th>Total Cost</th>
                  </tr>
                </thead>
                <tbody>
                  {materialsData?.materials.map((mat: any) => (
                    <tr key={mat.type_id}>
                      <td><strong>{mat.name}</strong></td>
                      <td className="neutral">{formatQuantity(mat.base_quantity)}</td>
                      <td>{formatQuantity(mat.adjusted_quantity)}</td>
                      <td className="positive">{formatQuantity(mat.adjusted_quantity * runs)}</td>
                      <td className="positive">-{formatQuantity(mat.me_savings * runs)}</td>
                      <td className="isk">{formatISK(mat.unit_price || 0, false)}</td>
                      <td className="isk">{formatISK((mat.unit_price || 0) * mat.adjusted_quantity * runs)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* NEW: Similar Opportunities Section */}
          {opportunities && opportunities.opportunities.length > 0 && (
            <div className="card">
              <h3 style={{ marginBottom: 16 }}>
                <Factory size={18} style={{ marginRight: 8 }} />
                Similar Profitable Items in {economicsData.region_name}
              </h3>
              <div className="table-container">
                <table>
                  <thead>
                    <tr>
                      <th>Item</th>
                      <th>ROI</th>
                      <th>Profit</th>
                      <th>Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    {opportunities.opportunities.slice(0, 5).map((opp: any) => (
                      <tr key={opp.type_id}>
                        <td>{opp.name}</td>
                        <td className="positive">{opp.roi_percent.toFixed(1)}%</td>
                        <td className="isk positive">{formatISK(opp.profit)}</td>
                        <td>
                          <button
                            className="btn btn-primary btn-sm"
                            onClick={() => {
                              setSelectedItem({ typeID: opp.type_id, typeName: opp.name });
                              setSearchQuery(opp.name);
                            }}
                          >
                            View
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* NEW: Action Buttons */}
          <div className="card">
            <div style={{ display: 'flex', gap: 12 }}>
              <button className="btn btn-primary" onClick={() => addToShoppingList()}>
                <ShoppingCart size={16} style={{ marginRight: 8 }} />
                Add to Shopping List
              </button>
              <button className="btn btn-secondary" onClick={() => createProductionJob()}>
                <Factory size={16} style={{ marginRight: 8 }} />
                Create Production Job
              </button>
              <button className="btn btn-secondary" onClick={() => exportMultibuy()}>
                <Download size={16} style={{ marginRight: 8 }} />
                Export Multibuy
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
```

**New Functions:**

```typescript
// Add to shopping list
const addToShoppingList = async () => {
  // Create new shopping list or add to existing
  // Use materialsData to populate items
  const response = await api.post('/api/shopping/lists', {
    name: `${selectedItem?.typeName} Production`,
    corporation_id: CORP_ID
  });

  const listId = response.data.id;

  // Add product
  await api.post(`/api/shopping/lists/${listId}/items`, {
    type_id: selectedItem!.typeID,
    item_name: selectedItem!.typeName,
    quantity: runs
  });

  // Calculate materials
  await api.post(`/api/shopping/items/${response.data.id}/calculate-materials`);

  // Navigate to shopping planner
  navigate(`/shopping-lists?list=${listId}`);
};

// Create production job
const createProductionJob = async () => {
  // Use workflow API to create job
  await api.post('/api/production/workflow/jobs', {
    character_id: 526379435, // From context/selection
    item_type_id: selectedItem!.typeID,
    blueprint_type_id: getBlueprintTypeId(selectedItem!.typeID), // Lookup
    me_level: meLevel,
    te_level: teLevel,
    runs: runs,
    materials: materialsData!.materials.map(mat => ({
      material_type_id: mat.type_id,
      quantity_needed: mat.adjusted_quantity * runs,
      decision: 'buy', // Default, can be changed in workflow
      cost_per_unit: mat.unit_price,
      total_cost: mat.unit_price * mat.adjusted_quantity * runs
    })),
    system_id: 30000144 // Isikemi (home system)
  });

  alert('Production job created!');
};
```

**Benefits:**
- Vollständige Integration aller neuen APIs
- TE-Level Support (neues Feature)
- Multi-Region Vergleich übersichtlicher
- Direkte Integration mit Shopping Planner und Workflow
- Similar Items Vorschläge (upselling profitable Alternativen)
- Produktionszeit-Anzeige

**Priority:** ⭐⭐⭐⭐⭐ CRITICAL (Hauptfeature, höchste Sichtbarkeit)

---

## 5. Implementation Priority & Phasing

### Phase 1: Critical Migrations (Week 1)
**Goal:** Stabilität durch konsistente Datenquelle

1. **Materials Overview** → New Chains API
   - Einfachste Migration
   - Niedrigstes Risiko
   - Validiert neue API funktioniert korrekt

2. **Shopping Planner** → New Chains API for Material Calculation
   - Kritische Funktion
   - Hohe Nutzerfrequenz
   - Muss funktionieren für Workflow

**Deliverables:**
- MaterialsOverview.tsx migriert
- ShoppingPlanner.tsx Material-Berechnung migriert
- Beide Features getestet und deployed

### Phase 2: Enhanced Features (Week 2)
**Goal:** Mehrwert durch neue Features

3. **Production Planner** → Complete Rewrite
   - Größte Änderung
   - Showcase für neue APIs
   - TE-Support, Multi-Region, Workflow Integration

4. **War Room** → Production Opportunity Integration
   - Neues Feature (nicht Breaking Change)
   - Verbindet War Analytics mit Production
   - Hoher strategischer Wert

**Deliverables:**
- ProductionPlanner.tsx komplett neu
- WarRoomMarketGaps.tsx mit Economics-Integration
- Vollständige API-Integration demonstriert

### Phase 3: Polish & Optimization (Week 3)
**Goal:** Performance und UX

5. **Performance Optimization**
   - Caching für Economics-Calls
   - Batch-Requests wo möglich
   - Loading States optimieren

6. **UX Improvements**
   - Tooltips mit Berechnungsdetails
   - Quick-Actions (Add to Shopping, Create Job)
   - Keyboard Shortcuts
   - Dark Mode Refinements

**Deliverables:**
- Optimierte API-Calls
- Verbesserte User Experience
- Documentation Updates

---

## 6. API Mapping Summary

### Alte APIs (zu ersetzen)
```
GET /api/production/optimize/{type_id}?me={me}
├─ Used in: ProductionPlanner, MaterialsOverview
└─ Replace with: /api/production/chains/{type_id}/materials + /api/production/economics/{type_id}

POST /api/shopping/items/{itemId}/calculate-materials
├─ Used in: ShoppingPlanner
└─ Replace with: /api/production/chains/{type_id}/materials
```

### Neue APIs
```
Production Chains:
├─ GET /api/production/chains/{type_id}                      [tree format]
├─ GET /api/production/chains/{type_id}/materials           [flat with ME]
└─ GET /api/production/chains/{type_id}/direct              [direct deps only]

Production Economics:
├─ GET /api/production/economics/{type_id}                   [single region]
├─ GET /api/production/economics/{type_id}/regions           [all regions]
└─ GET /api/production/economics/opportunities               [profitable items]

Production Workflow:
├─ POST /api/production/workflow/jobs                        [create job]
├─ GET /api/production/workflow/jobs?character_id={id}      [list jobs]
└─ PATCH /api/production/workflow/jobs/{job_id}             [update job]
```

---

## 7. Testing Strategy

### Unit Tests
- API response transformation functions
- Material aggregation logic
- ROI calculation functions
- Price formatting utilities

### Integration Tests
- Complete user flows:
  1. Search → Select → View Economics → Add to Shopping List
  2. Bookmark Items → View Materials → Export Multibuy
  3. War Room Gap → Check Production ROI → Plan Production
  4. Production Planner → Create Job → Track Status

### Performance Tests
- Load testing with 50+ bookmarked items (MaterialsOverview)
- Concurrent API calls (Shopping Planner with multiple products)
- Large material lists (Capital ships, Keepstars)

### User Acceptance Tests
- Beta-Test mit Corporation Members
- Feedback zu neuen Features
- Bug Reporting via Discord

---

## 8. Rollback Plan

Falls kritische Issues auftreten:

### Rollback Strategy
1. **Feature Flags:**
   ```typescript
   const USE_NEW_PRODUCTION_API = import.meta.env.VITE_NEW_PRODUCTION_API === 'true';

   const productionApi = USE_NEW_PRODUCTION_API
     ? '/api/production/chains'
     : '/api/production/optimize';
   ```

2. **Gradual Rollout:**
   - Phase 1: 10% der User (Beta-Tester)
   - Phase 2: 50% der User
   - Phase 3: 100% der User

3. **Monitoring:**
   - API Error Rates
   - Response Times
   - User Feedback (Discord Channel)

---

## 9. Documentation Updates

### User-Facing Documentation
- [ ] Update `/docs/production-system-api.md` with frontend integration examples
- [ ] Create `/docs/production-planner-guide.md` for end-users
- [ ] Add screenshots to documentation

### Developer Documentation
- [ ] Update `CLAUDE.frontend.md` with new API patterns
- [ ] Document component-level integration
- [ ] Add troubleshooting guide

---

## 10. Success Metrics

### Technical Metrics
- ✅ 100% Migration to new APIs
- ✅ <500ms response time for economics calls
- ✅ Zero data inconsistencies between features
- ✅ All tests passing

### User Metrics
- 📊 Shopping Planner accuracy improved (fewer manual adjustments)
- 📊 Production Planner usage increased
- 📊 War Room → Production conversion rate >20%
- 📊 User feedback score >4.5/5

---

## Conclusion

Die Integration des neuen Produktionssystems in das Frontend erfordert strukturierte Phasen:

1. **Phase 1 (Critical):** Materials Overview und Shopping Planner Migration → Konsistenz
2. **Phase 2 (Enhanced):** Production Planner Rewrite und War Room Integration → Mehrwert
3. **Phase 3 (Polish):** Performance und UX Optimierung → Exzellenz

**Gesamtaufwand:** ~3 Wochen bei fokussierter Entwicklung

**Kritischer Pfad:** Shopping Planner → Production Planner → War Room

**Quick Wins:**
- Materials Overview Migration (2-3 Stunden)
- War Room Economics Column (4-6 Stunden)

**Nächster Schritt:** Phase 1 Implementation starten mit MaterialsOverview.tsx

---

**Prepared by:** Claude Sonnet 4.5
**Review Status:** Ready for Implementation
**Last Updated:** 2025-12-18
