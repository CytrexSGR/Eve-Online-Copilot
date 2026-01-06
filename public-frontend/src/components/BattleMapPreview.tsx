import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { EveMap3D, useMapControl } from 'eve-map-3d';
import type { SolarSystem, Stargate, Region } from 'eve-map-3d';
import type { HotZone, BattleReport } from '../types/reports';

interface BattleMapPreviewProps {
  hotZones?: HotZone[];
  battleReport?: BattleReport;  // Full battle report for all 4 layers
  showAllLayers?: boolean;  // If true, show all 4 combat layers
}

/**
 * BattleMapPreview Component
 *
 * Displays a 3D galaxy map preview with highlighted hot zones (systems with high kill activity).
 * Clicking the preview navigates to the full Battle Map page.
 *
 * Features:
 * - Loads EVE SDE data from /data/*.jsonl files
 * - Highlights hot zone systems in red/orange glow
 * - Fixed 500px height for preview display
 * - Click-to-navigate functionality
 * - Loading states and error handling
 */
export function BattleMapPreview({ hotZones = [], battleReport, showAllLayers = false }: BattleMapPreviewProps) {
  const [systems, setSystems] = useState<SolarSystem[]>([]);
  const [stargates, setStargates] = useState<Stargate[]>([]);
  const [regions, setRegions] = useState<Region[]>([]);
  const [loading, setLoading] = useState(true); // Start as true - load automatically
  const [error, setError] = useState<string | null>(null);
  const [liveHotspots, setLiveHotspots] = useState<any[]>([]);
  const navigate = useNavigate();

  // Initialize map control with hot zones highlighted
  const mapControl = useMapControl({
    language: 'en',
    filterNewEdenOnly: true,
    style: {
      backgroundColor: '#000000',
      connectionLineColor: '#30363d',
      connectionLineOpacity: 0.3,
    },
  });

  // Poll live hotspots every 10 seconds
  useEffect(() => {
    const fetchLiveHotspots = async () => {
      try {
        // Use relative URL so it works with Vite proxy in dev and production URL
        const response = await fetch('/api/war/live-hotspots');
        if (response.ok) {
          const data = await response.json();
          setLiveHotspots(data.hotspots || []);
          console.log(`[BattleMapPreview] Loaded ${data.hotspots?.length || 0} live hotspots`);
        }
      } catch (err) {
        console.error('[BattleMapPreview] Failed to fetch live hotspots:', err);
      }
    };

    // Initial fetch
    fetchLiveHotspots();

    // Poll every 10 seconds
    const interval = setInterval(fetchLiveHotspots, 10000);

    return () => clearInterval(interval);
  }, []);

  // Load JSONL data files automatically on mount
  useEffect(() => {
    const loadJSONL = async (path: string): Promise<any[]> => {
      const response = await fetch(path);
      if (!response.ok) {
        throw new Error(`Failed to load ${path}: ${response.statusText}`);
      }
      const text = await response.text();
      // Parse JSONL format (each line is a JSON object)
      return text
        .trim()
        .split('\n')
        .filter(line => line.trim())
        .map(line => JSON.parse(line));
    };

    const loadMapData = async () => {
      try {
        setError(null);
        setLoading(true);

        console.log('[BattleMapPreview] Loading 7.7 MB of map data automatically...');

        // Load all three data files in parallel
        const [systemsData, stargatesData, regionsData] = await Promise.all([
          loadJSONL('/data/mapSolarSystems.jsonl'),
          loadJSONL('/data/mapStargates.jsonl'),
          loadJSONL('/data/mapRegions.jsonl'),
        ]);

        console.log('[BattleMapPreview] Map data loaded successfully');

        setSystems(systemsData);
        setStargates(stargatesData);
        setRegions(regionsData);
        setLoading(false);
      } catch (err) {
        console.error('Failed to load map data:', err);
        setError(err instanceof Error ? err.message : 'Failed to load map data');
        setLoading(false);
      }
    };

    loadMapData();
  }, []);

  // Highlight combat events when data is loaded
  useEffect(() => {
    if (systems.length === 0) return;

    try {
      const systemRenderConfigs: Array<{
        systemId: number;
        color: string;
        size: number;
        highlighted: boolean;
        opacity: number;
      }> = [];

      // Track which systems already rendered (for priority management)
      const renderedSystems = new Set<number>();

      // Priority 0: LIVE HOTSPOTS (highest priority - pulsing white/yellow)
      // Age-based coloring: <1min = white pulsing, 1-3min = bright yellow, 3-5min = orange
      if (liveHotspots.length > 0) {
        console.log(`[BattleMapPreview] Rendering ${liveHotspots.length} LIVE hotspots`);
        liveHotspots.forEach(hotspot => {
          const age = hotspot.age_seconds || 0;
          let color = '#ffffff';
          let size = 7.0;

          if (age < 60) {
            // Very fresh (<1 min) - Pulsing white
            color = '#ffffff';
            size = 7.0;
          } else if (age < 180) {
            // Fresh (1-3 min) - Bright yellow
            color = '#ffff00';
            size = 6.0;
          } else {
            // Older (3-5 min) - Fading orange
            color = '#ff9900';
            size = 5.0;
          }

          systemRenderConfigs.push({
            systemId: hotspot.system_id,
            color,
            size,
            highlighted: true,
            opacity: 1.0,
          });

          // Mark as rendered so other layers don't override
          renderedSystems.add(hotspot.system_id);
        });
      }

      if (showAllLayers && battleReport) {
        // Show ALL 4 combat layers with priority-based coloring
        console.log('[BattleMapPreview] Showing all 4 combat layers');

        const allSystemIds = new Set<number>();

        // Extract capital kills from nested structure (it's a dict, not array)
        const capitalKillsList: any[] = [];
        const capitalKills = battleReport.capital_kills as any;
        if (capitalKills && typeof capitalKills === 'object') {
          ['titans', 'supercarriers', 'carriers', 'dreadnoughts', 'force_auxiliaries'].forEach(category => {
            if (capitalKills[category]?.kills) {
              capitalKillsList.push(...capitalKills[category].kills);
            }
          });
        }

        // Collect all unique system IDs
        battleReport.hot_zones?.forEach(z => allSystemIds.add(z.system_id));
        capitalKillsList.forEach((k: any) => allSystemIds.add(k.system_id));
        battleReport.danger_zones?.forEach((d: any) => allSystemIds.add(d.system_id));
        battleReport.high_value_kills?.forEach((h: any) => allSystemIds.add(h.system_id));

        console.log(`[BattleMapPreview] Found systems - Hot: ${battleReport.hot_zones?.length || 0}, Capital: ${capitalKillsList.length}, Danger: ${(battleReport.danger_zones as any[])?.length || 0}, High-Value: ${(battleReport.high_value_kills as any[])?.length || 0}`);

        // Create lookups for priority determination
        const capitalKillsMap = new Map(capitalKillsList.map((k: any) => [k.system_id, k]));
        const hotZoneMap = new Map(battleReport.hot_zones?.map(z => [z.system_id, z]) || []);
        const highValueMap = new Map(battleReport.high_value_kills?.map((h: any) => [h.system_id, h]) || []);
        const dangerZoneMap = new Map(battleReport.danger_zones?.map((d: any) => [d.system_id, d]) || []);

        // Assign colors based on priority (skip if already rendered as live hotspot)
        allSystemIds.forEach(systemId => {
          // Skip if already rendered as live hotspot (highest priority)
          if (renderedSystems.has(systemId)) {
            return;
          }

          let color = '#ffffff';
          let size = 3.0;

          // Priority 1: Capital Kills (bright purple)
          if (capitalKillsMap.has(systemId)) {
            color = '#d946ef';
            size = 5.0;
          }
          // Priority 2: Hot Zones (bright red/orange)
          else if (hotZoneMap.has(systemId)) {
            const index = battleReport.hot_zones.findIndex(z => z.system_id === systemId);
            const isTopThree = index < 3;
            color = isTopThree ? '#ff0000' : '#ff6600';
            size = isTopThree ? 4.5 : 3.5;
          }
          // Priority 3: High-Value Kills (bright cyan)
          else if (highValueMap.has(systemId)) {
            color = '#00ffff';
            size = 4.0;
          }
          // Priority 4: Danger Zones (bright yellow)
          else if (dangerZoneMap.has(systemId)) {
            color = '#ffaa00';
            size = 3.5;
          }

          systemRenderConfigs.push({
            systemId,
            color,
            size,
            highlighted: true,
            opacity: 1.0,
          });

          renderedSystems.add(systemId);
        });

        console.log(`[BattleMapPreview] Configured ${systemRenderConfigs.length} combat systems across all layers`);
      }
      else if (hotZones.length > 0) {
        // Show only hot zones (legacy mode)
        console.log('[BattleMapPreview] Highlighting hot zones:', hotZones.length);

        hotZones.forEach((zone, index) => {
          // Skip if already rendered as live hotspot
          if (renderedSystems.has(zone.system_id)) {
            return;
          }

          const isTopThree = index < 3;
          const color = isTopThree ? '#ff0000' : '#ff6600';
          const size = isTopThree ? 4.5 : 3.5;

          systemRenderConfigs.push({
            systemId: zone.system_id,
            color,
            size,
            highlighted: true,
            opacity: 1.0,
          });

          renderedSystems.add(zone.system_id);
        });
      }

      // Update map control configuration
      if (systemRenderConfigs.length > 0) {
        mapControl.setConfig({
          systemRenderConfigs,
        });
        console.log('[BattleMapPreview] Combat systems configured successfully');
      }
    } catch (err) {
      console.error('[BattleMapPreview] Error highlighting combat systems:', err);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [systems.length, hotZones.length, battleReport, showAllLayers, liveHotspots.length]);

  // Handle container click to navigate to full map
  const handleClick = () => {
    navigate('/battle-map');
  };

  if (loading) {
    return (
      <div className="card" style={{ height: '500px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <div style={{ textAlign: 'center' }}>
          <div className="skeleton" style={{ height: '40px', width: '200px', margin: '0 auto 1rem' }} />
          <p style={{ color: 'var(--text-secondary)' }}>Loading galaxy map data...</p>
          <p style={{ color: 'var(--text-tertiary)', fontSize: '0.75rem', marginTop: '0.5rem' }}>
            Downloading 7.7 MB (8,437 systems)
          </p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="card" style={{ height: '500px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <div style={{ textAlign: 'center', color: 'var(--danger)' }}>
          <p style={{ fontSize: '1.5rem', marginBottom: '0.5rem' }}>⚠️</p>
          <p>{error}</p>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.875rem', marginTop: '0.5rem' }}>
            Unable to load map data
          </p>
          <button
            onClick={() => window.location.reload()}
            style={{
              marginTop: '1rem',
              background: 'var(--accent-blue)',
              color: 'white',
              border: 'none',
              padding: '0.5rem 1rem',
              borderRadius: '4px',
              cursor: 'pointer',
            }}
          >
            Reload Page
          </button>
        </div>
      </div>
    );
  }

  if (systems.length === 0) {
    return (
      <div className="card" style={{ height: '500px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <p style={{ color: 'var(--text-secondary)' }}>No map data available</p>
      </div>
    );
  }

  return (
    <div className="card" style={{ padding: 0, overflow: 'hidden', position: 'relative' }}>
      <div
        style={{
          position: 'relative',
          height: '500px',
        }}
      >
        {/* 3D Map */}
        <EveMap3D
          systems={systems}
          stargates={stargates}
          regions={regions}
          mapControl={mapControl}
        />

        {/* Info badge - top left (vertical layout) */}
        <div
          style={{
            position: 'absolute',
            top: '1rem',
            left: '1rem',
            background: 'rgba(0, 0, 0, 0.85)',
            padding: '0.75rem',
            borderRadius: '6px',
            border: '1px solid rgba(255, 255, 255, 0.1)',
            pointerEvents: 'none',
            minWidth: '140px',
          }}
        >
          {showAllLayers && battleReport ? (
            <div style={{ fontSize: '0.75rem', lineHeight: '1.6' }}>
              <div style={{ fontWeight: 600, marginBottom: '0.5rem', color: 'var(--text-primary)', fontSize: '0.875rem' }}>
                🌌 Combat Activity
              </div>
              <div style={{ color: 'var(--text-secondary)' }}>
                {liveHotspots.length > 0 && (
                  <div style={{ color: '#ffffff', fontWeight: 700, animation: 'pulse 2s ease-in-out infinite' }}>
                    ⚡ {liveHotspots.length} LIVE hotspots
                  </div>
                )}
                <div style={{ color: '#ff4444' }}>🔴 {battleReport.hot_zones?.length || 0} hot zones</div>
                {(() => {
                  const capitalKills = battleReport.capital_kills as any;
                  let count = 0;
                  if (capitalKills) {
                    ['titans', 'supercarriers', 'carriers', 'dreadnoughts', 'force_auxiliaries'].forEach(category => {
                      count += capitalKills[category]?.kills?.length || 0;
                    });
                  }
                  return count > 0 ? <div style={{ color: '#d946ef' }}>🟣 {count} capitals</div> : null;
                })()}
                {(battleReport.high_value_kills as any[])?.length > 0 && (
                  <div style={{ color: '#00ffff' }}>🔵 {(battleReport.high_value_kills as any[]).length} high-value</div>
                )}
                {(battleReport.danger_zones as any[])?.length > 0 && (
                  <div style={{ color: '#ffaa00' }}>🟡 {(battleReport.danger_zones as any[]).length} danger zones</div>
                )}
              </div>
            </div>
          ) : (
            <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
              <div style={{ fontWeight: 600, marginBottom: '0.25rem', color: 'var(--text-primary)', fontSize: '0.875rem' }}>
                🌌 Combat Activity
              </div>
              {liveHotspots.length > 0 && (
                <div style={{ color: '#ffffff', fontWeight: 700 }}>⚡ {liveHotspots.length} LIVE hotspots</div>
              )}
              <div style={{ color: '#ff4444' }}>🔴 {hotZones.length} hot zones</div>
            </div>
          )}
        </div>

        {/* "View Full Map" button - bottom right */}
        <button
          onClick={handleClick}
          style={{
            position: 'absolute',
            bottom: '1rem',
            right: '1rem',
            background: 'var(--accent-blue)',
            color: 'white',
            border: 'none',
            padding: '0.75rem 1.5rem',
            borderRadius: '6px',
            fontSize: '0.875rem',
            fontWeight: 600,
            cursor: 'pointer',
            boxShadow: '0 4px 12px rgba(88, 166, 255, 0.3)',
            transition: 'all 0.2s ease',
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.background = '#6eb8ff';
            e.currentTarget.style.transform = 'translateY(-2px)';
            e.currentTarget.style.boxShadow = '0 6px 16px rgba(88, 166, 255, 0.4)';
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.background = 'var(--accent-blue)';
            e.currentTarget.style.transform = 'translateY(0)';
            e.currentTarget.style.boxShadow = '0 4px 12px rgba(88, 166, 255, 0.3)';
          }}
        >
          🗺️ View Full Battle Map
        </button>
      </div>
    </div>
  );
}
