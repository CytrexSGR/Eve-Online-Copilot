import { useState, useEffect, useRef } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Map } from 'lucide-react';
import { api } from '../../../api';
import { formatISK, formatQuantity } from '../../../utils/format';
import type { ComparisonItem, ShoppingRoute } from '../../../types/shopping';
import { REGION_NAMES, START_SYSTEMS } from '../../../types/shopping';

interface ShoppingRouteDisplayProps {
  items: ComparisonItem[];
  homeSystem: string;
}

/**
 * Component to display shopping route with optimized travel path
 */
export function ShoppingRouteDisplay({ items, homeSystem: initialHomeSystem }: ShoppingRouteDisplayProps) {
  const [expandedLegs, setExpandedLegs] = useState<Set<number>>(new Set());
  const [homeSystem, setHomeSystem] = useState(initialHomeSystem);
  const [includeReturn, setIncludeReturn] = useState(true);
  const isInitialMount = useRef(true);

  // Only sync with prop on initial mount, not on subsequent updates
  // This prevents the selection from reverting when React Query refetches
  useEffect(() => {
    if (isInitialMount.current) {
      isInitialMount.current = false;
      setHomeSystem(initialHomeSystem);
    }
  }, [initialHomeSystem]);

  // Group items by their currently selected region
  const selectedRouteByRegion: Record<string, { item_name: string; quantity: number; total: number }[]> = {};
  let selectedTotal = 0;

  for (const item of items) {
    if (item.current_region && item.current_price) {
      if (!selectedRouteByRegion[item.current_region]) {
        selectedRouteByRegion[item.current_region] = [];
      }
      const total = item.current_price * item.quantity;
      selectedRouteByRegion[item.current_region].push({
        item_name: item.item_name,
        quantity: item.quantity,
        total,
      });
      selectedTotal += total;
    }
  }

  const selectedRegions = Object.keys(selectedRouteByRegion);

  // Fetch optimal route through selected hubs
  const { data: routeData } = useQuery<ShoppingRoute>({
    queryKey: ['shopping-route', selectedRegions.sort().join(','), homeSystem, includeReturn],
    queryFn: async () => {
      if (selectedRegions.length === 0) return { total_jumps: 0, route: [], order: [] };
      const response = await api.get('/api/shopping/route', {
        params: {
          regions: selectedRegions.join(','),
          home_system: homeSystem,
          return_home: includeReturn,
        },
      });
      return response.data;
    },
    enabled: selectedRegions.length > 0,
  });

  const toggleLeg = (idx: number) => {
    setExpandedLegs((prev) => {
      const next = new Set(prev);
      if (next.has(idx)) {
        next.delete(idx);
      } else {
        next.add(idx);
      }
      return next;
    });
  };

  const getSecurityColor = (sec: number) => {
    if (sec >= 0.5) return 'var(--accent-green)';
    if (sec > 0) return 'var(--accent-yellow)';
    return 'var(--accent-red)';
  };

  if (selectedRegions.length === 0) return null;

  // Order regions by optimal route (filter out home system at start and end)
  const orderedRegions =
    routeData?.order?.filter((r, idx, arr) => {
      // Remove first element (home system)
      if (idx === 0) return false;
      // Remove last element if it's the return trip (same as first)
      if (idx === arr.length - 1 && r.toLowerCase() === arr[0].toLowerCase()) return false;
      return true;
    }) || selectedRegions;

  return (
    <div className="card" style={{ marginTop: 16 }}>
      <div className="card-header">
        <span className="card-title">
          <Map size={18} style={{ marginRight: 8 }} />
          Shopping Route
        </span>
        <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
          {routeData && routeData.total_jumps > 0 && (
            <span className="badge badge-blue">{routeData.total_jumps} jumps total</span>
          )}
          <span className="isk" style={{ fontWeight: 600 }}>
            Total: {formatISK(selectedTotal)}
          </span>
        </div>
      </div>

      {/* Route options */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 16,
          padding: '8px 0',
          borderBottom: '1px solid var(--border)',
          flexWrap: 'wrap',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <label className="neutral" style={{ fontSize: 12 }}>
            Start:
          </label>
          <select
            value={homeSystem}
            onChange={(e) => setHomeSystem(e.target.value)}
            style={{
              padding: '4px 8px',
              background: 'var(--bg-dark)',
              border: '1px solid var(--border)',
              borderRadius: 4,
              color: 'var(--text-primary)',
              fontSize: 12,
            }}
          >
            {START_SYSTEMS.map((sys) => (
              <option key={sys.value} value={sys.value}>
                {sys.name}
              </option>
            ))}
          </select>
        </div>
        <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 12, cursor: 'pointer' }}>
          <input
            type="checkbox"
            checked={includeReturn}
            onChange={(e) => setIncludeReturn(e.target.checked)}
            style={{ accentColor: 'var(--accent-blue)' }}
          />
          <span>Include return trip</span>
        </label>
      </div>

      {/* Route visualization with expandable system list */}
      {routeData?.route && routeData.route.length > 0 && (
        <div style={{ padding: '12px 0', marginBottom: 12, borderBottom: '1px solid var(--border)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
            <span style={{ fontWeight: 500 }}>{homeSystem}</span>
            {routeData.route.map((leg, idx) => (
              <span key={idx} style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <span className="neutral">→</span>
                <button
                  onClick={() => toggleLeg(idx)}
                  className="badge badge-blue"
                  style={{
                    fontSize: 10,
                    cursor: 'pointer',
                    border: 'none',
                    background: expandedLegs.has(idx) ? 'var(--accent-blue)' : undefined,
                  }}
                  title="Click to show systems"
                >
                  {leg.jumps}j {expandedLegs.has(idx) ? '▼' : '▶'}
                </button>
                <span className="neutral">→</span>
                <span style={{ fontWeight: 500 }}>{leg.to}</span>
              </span>
            ))}
          </div>

          {/* Expanded system lists */}
          {routeData.route.map(
            (leg, idx) =>
              expandedLegs.has(idx) &&
              leg.systems && (
                <div
                  key={`systems-${idx}`}
                  style={{
                    marginTop: 8,
                    marginLeft: 16,
                    padding: 8,
                    background: 'var(--bg-dark)',
                    borderRadius: 6,
                    fontSize: 12,
                  }}
                >
                  <div style={{ fontWeight: 500, marginBottom: 4 }}>
                    {leg.from} → {leg.to} ({leg.jumps} jumps)
                  </div>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                    {leg.systems.map((sys, sIdx) => (
                      <span
                        key={sIdx}
                        style={{
                          padding: '2px 6px',
                          background: 'var(--bg-card)',
                          borderRadius: 4,
                          borderLeft: `3px solid ${getSecurityColor(sys.security)}`,
                        }}
                      >
                        {sys.name}
                        <span className="neutral" style={{ marginLeft: 4, fontSize: 10 }}>
                          {sys.security.toFixed(1)}
                        </span>
                      </span>
                    ))}
                  </div>
                </div>
              )
          )}
        </div>
      )}

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 16 }}>
        {orderedRegions.map((regionOrHub) => {
          // Handle both region keys and hub names from route
          const region =
            regionOrHub.toLowerCase() === 'jita'
              ? 'the_forge'
              : regionOrHub.toLowerCase() === 'amarr'
              ? 'domain'
              : regionOrHub.toLowerCase() === 'rens'
              ? 'heimatar'
              : regionOrHub.toLowerCase() === 'dodixie'
              ? 'sinq_laison'
              : regionOrHub.toLowerCase() === 'hek'
              ? 'metropolis'
              : regionOrHub;
          const items = selectedRouteByRegion[region];
          if (!items) return null;

          const routeLeg = routeData?.route?.find((r) => r.to.toLowerCase() === regionOrHub.toLowerCase());

          return (
            <div
              key={region}
              style={{
                padding: 12,
                background: 'var(--bg-dark)',
                borderRadius: 8,
              }}
            >
              <div style={{ fontWeight: 600, marginBottom: 8 }}>
                {REGION_NAMES[region] || region}
                <span className="neutral" style={{ fontWeight: 400, marginLeft: 8 }}>
                  ({items.length} items)
                </span>
                {routeLeg && (
                  <span className="badge badge-blue" style={{ marginLeft: 8 }}>
                    {routeLeg.jumps} jumps
                  </span>
                )}
              </div>
              {items.map((item, idx) => (
                <div
                  key={idx}
                  style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    fontSize: 12,
                    padding: '4px 0',
                    borderTop: idx > 0 ? '1px solid var(--border)' : undefined,
                  }}
                >
                  <span>
                    {item.item_name} x{formatQuantity(item.quantity)}
                  </span>
                  <span className="isk">{formatISK(item.total)}</span>
                </div>
              ))}
              <div
                style={{
                  marginTop: 8,
                  paddingTop: 8,
                  borderTop: '1px solid var(--border)',
                  fontWeight: 500,
                }}
              >
                Subtotal: {formatISK(items.reduce((sum, i) => sum + i.total, 0))}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
