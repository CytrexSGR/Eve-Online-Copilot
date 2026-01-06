import { useState, useEffect, useMemo } from 'react';
import { EveMap3D, useMapControl } from 'eve-map-3d';
import type { SolarSystem, Stargate, Region } from 'eve-map-3d';
import { reportsApi } from '../services/api';
import type { BattleReport, HotZone, HighValueKill, DangerZone } from '../types/reports';

/**
 * BattleMap Page - Full-screen 3D Galaxy Map with Combat Data Overlays
 *
 * Features:
 * - Real-time battle report data from /api/reports/battle-24h
 * - Live hotspots from Telegram combat alerts (real-time, 10s polling)
 * - Multi-layer filtering: Live Hotspots, Hot Zones, Capital Kills, Danger Zones, High-Value Kills
 * - Interactive system selection with detailed info panel
 * - Left sidebar for filter controls
 * - Right sidebar for system information
 * - Color-coded system highlights based on combat activity
 *
 * Filter Priority (when multiple attributes apply):
 * 0. LIVE Hotspots (white pulsing) - HIGHEST PRIORITY, real-time combat
 * 1. Capital Kills (purple) - capital ship losses
 * 2. Hot Zones (red/orange) - high kill activity
 * 3. High-Value Kills (cyan) - expensive kills
 * 4. Danger Zones (yellow) - industrial ship losses
 */
export function BattleMap() {
  // Map data state
  const [systems, setSystems] = useState<SolarSystem[]>([]);
  const [stargates, setStargates] = useState<Stargate[]>([]);
  const [regions, setRegions] = useState<Region[]>([]);
  const [mapLoading, setMapLoading] = useState(true);
  const [mapError, setMapError] = useState<string | null>(null);

  // Battle report data state
  const [battleReport, setBattleReport] = useState<BattleReport | null>(null);
  const [reportLoading, setReportLoading] = useState(true);
  const [reportError, setReportError] = useState<string | null>(null);

  // Filter state (default: only Hot Zones enabled)
  const [filters, setFilters] = useState({
    liveHotspots: true,
    hotZones: true,
    capitalKills: false,
    dangerZones: false,
    highValueKills: false,
  });

  // Live hotspots state
  const [liveHotspots, setLiveHotspots] = useState<any[]>([]);

  // Selected system state for info panel
  const [selectedSystem, setSelectedSystem] = useState<{
    systemId: number;
    systemName: string;
    regionName: string;
    securityStatus: number;
    data: {
      hotZone?: HotZone;
      capitalKills?: number;
      dangerZone?: DangerZone;
      highValueKills?: HighValueKill[];
    };
  } | null>(null);

  // Initialize map control
  const mapControl = useMapControl({
    language: 'en',
    filterNewEdenOnly: true,
    containerStyle: {
      height: 'calc(100vh - 120px)',
      width: '100%',
    },
    style: {
      backgroundColor: '#000000',
    },
    events: {
      onSystemClick: (system: SolarSystem) => {
        handleSystemClick(system._key);
      },
    },
  });

  // Load JSONL map data
  useEffect(() => {
    const loadJSONL = async (path: string): Promise<any[]> => {
      const response = await fetch(path);
      if (!response.ok) {
        throw new Error(`Failed to load ${path}: ${response.statusText}`);
      }
      const text = await response.text();
      return text
        .trim()
        .split('\n')
        .filter(line => line.trim())
        .map(line => JSON.parse(line));
    };

    const loadMapData = async () => {
      try {
        setMapError(null);
        setMapLoading(true);

        const [systemsData, stargatesData, regionsData] = await Promise.all([
          loadJSONL('/data/mapSolarSystems.jsonl'),
          loadJSONL('/data/mapStargates.jsonl'),
          loadJSONL('/data/mapRegions.jsonl'),
        ]);

        setSystems(systemsData);
        setStargates(stargatesData);
        setRegions(regionsData);
        setMapLoading(false);
      } catch (err) {
        console.error('Failed to load map data:', err);
        setMapError(err instanceof Error ? err.message : 'Failed to load map data');
        setMapLoading(false);
      }
    };

    loadMapData();
  }, []);

  // Load battle report data
  useEffect(() => {
    const loadBattleReport = async () => {
      try {
        setReportError(null);
        setReportLoading(true);
        const data = await reportsApi.getBattleReport();
        setBattleReport(data);
        setReportLoading(false);
      } catch (err) {
        console.error('Failed to load battle report:', err);
        setReportError(err instanceof Error ? err.message : 'Failed to load battle report');
        setReportLoading(false);
      }
    };

    loadBattleReport();
  }, []);

  // Poll live hotspots every 10 seconds
  useEffect(() => {
    const fetchLiveHotspots = async () => {
      try {
        const response = await fetch('http://localhost:8000/api/war/live-hotspots');
        if (response.ok) {
          const data = await response.json();
          setLiveHotspots(data.hotspots || []);
          console.log(`[BattleMap] Loaded ${data.hotspots?.length || 0} live hotspots`);
        }
      } catch (err) {
        console.error('[BattleMap] Failed to fetch live hotspots:', err);
      }
    };

    // Initial fetch
    fetchLiveHotspots();

    // Poll every 10 seconds
    const interval = setInterval(fetchLiveHotspots, 10000);

    return () => clearInterval(interval);
  }, []);

  // Build system lookup maps for quick access
  const systemLookups = useMemo(() => {
    if (!battleReport) return null;

    // Create maps for O(1) lookup by system_id
    const hotZoneMap = new Map<number, HotZone>();
    const capitalKillsMap = new Map<number, number>();
    const dangerZoneMap = new Map<number, DangerZone>();
    const highValueKillsMap = new Map<number, HighValueKill[]>();

    // Hot zones
    battleReport.hot_zones.forEach(zone => {
      hotZoneMap.set(zone.system_id, zone);
    });

    // Capital kills - count by system (grouped by system_name, need to map to system_id)
    Object.values(battleReport.capital_kills).forEach(category => {
      category.kills.forEach((kill: any) => {
        // Find system by name to get system_id
        const system = systems.find(s => {
          const systemName = typeof s.name === 'string' ? s.name : s.name['en'] || s.name['zh'];
          return systemName === kill.system_name;
        });
        if (system) {
          const currentCount = capitalKillsMap.get(system._key) || 0;
          capitalKillsMap.set(system._key, currentCount + 1);
        }
      });
    });

    // Danger zones - map system_name to system_id
    battleReport.danger_zones.forEach(zone => {
      const system = systems.find(s => {
        const systemName = typeof s.name === 'string' ? s.name : s.name['en'] || s.name['zh'];
        return systemName === zone.system_name;
      });
      if (system) {
        dangerZoneMap.set(system._key, zone);
      }
    });

    // High-value kills
    battleReport.high_value_kills.forEach(kill => {
      const existing = highValueKillsMap.get(kill.system_id) || [];
      existing.push(kill);
      highValueKillsMap.set(kill.system_id, existing);
    });

    return {
      hotZoneMap,
      capitalKillsMap,
      dangerZoneMap,
      highValueKillsMap,
    };
  }, [battleReport, systems]);

  // Build systemRenderConfigs based on active filters
  const systemRenderConfigs = useMemo(() => {
    if (!battleReport || !systemLookups) return [];

    const configs: Array<{
      systemId: number;
      color: string;
      size: number;
      highlighted: boolean;
      opacity: number;
    }> = [];

    const { hotZoneMap, capitalKillsMap, dangerZoneMap, highValueKillsMap } = systemLookups;

    // Track which systems already rendered (for priority management)
    const renderedSystems = new Set<number>();

    // Priority 0: LIVE HOTSPOTS (highest priority - pulsing white/yellow)
    if (filters.liveHotspots && liveHotspots.length > 0) {
      console.log(`[BattleMap] Rendering ${liveHotspots.length} LIVE hotspots`);
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

        configs.push({
          systemId: hotspot.system_id,
          color,
          size,
          highlighted: true,
          opacity: 1.0,
        });

        renderedSystems.add(hotspot.system_id);
      });
    }

    // Collect all unique system IDs across all enabled filters
    const allSystemIds = new Set<number>();

    if (filters.hotZones) {
      hotZoneMap.forEach((_, systemId) => allSystemIds.add(systemId));
    }
    if (filters.capitalKills) {
      capitalKillsMap.forEach((_, systemId) => allSystemIds.add(systemId));
    }
    if (filters.dangerZones) {
      dangerZoneMap.forEach((_, systemId) => allSystemIds.add(systemId));
    }
    if (filters.highValueKills) {
      highValueKillsMap.forEach((_, systemId) => allSystemIds.add(systemId));
    }

    // For each system, determine color and size based on priority
    // Skip if already rendered as live hotspot
    // MUCH LARGER and BRIGHTER for better visibility
    allSystemIds.forEach(systemId => {
      // Skip if already rendered as live hotspot
      if (renderedSystems.has(systemId)) {
        return;
      }

      let color = '#ffffff';
      let size = 3.0;

      // Priority 1: Capital Kills (bright purple - highest priority)
      if (filters.capitalKills && capitalKillsMap.has(systemId)) {
        color = '#d946ef'; // bright purple/magenta
        size = 5.0; // Very large for capital kills
      }
      // Priority 2: Hot Zones (bright red/orange)
      else if (filters.hotZones && hotZoneMap.has(systemId)) {
        const index = battleReport.hot_zones.findIndex(z => z.system_id === systemId);
        const isTopThree = index < 3;
        color = isTopThree ? '#ff0000' : '#ff6600'; // Bright red/orange
        size = isTopThree ? 4.5 : 3.5; // Much larger
      }
      // Priority 3: High-Value Kills (bright cyan)
      else if (filters.highValueKills && highValueKillsMap.has(systemId)) {
        color = '#00ffff'; // bright cyan
        size = 4.0; // Larger
      }
      // Priority 4: Danger Zones (bright yellow)
      else if (filters.dangerZones && dangerZoneMap.has(systemId)) {
        color = '#ffaa00'; // bright yellow/orange
        size = 3.5; // Larger
      }

      configs.push({
        systemId,
        color,
        size,
        highlighted: true,
        opacity: 1.0,
      });
    });

    return configs;
  }, [battleReport, systemLookups, filters, liveHotspots.length]);

  // Update map with new render configs when filters change
  useEffect(() => {
    if (systems.length > 0 && systemRenderConfigs.length > 0) {
      mapControl.setConfig({
        systemRenderConfigs,
      });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [systems.length, systemRenderConfigs]);

  // Handle system click - show info panel
  const handleSystemClick = (systemId: number) => {
    if (!battleReport || !systemLookups || !systems.length) return;

    const system = systems.find(s => s._key === systemId);
    if (!system) return;

    const { hotZoneMap, capitalKillsMap, dangerZoneMap, highValueKillsMap } = systemLookups;

    // Get system name (handle both string and object formats)
    const systemName = typeof system.name === 'string' ? system.name : system.name['en'] || system.name['zh'] || 'Unknown';

    // Find region name from regions array
    const region = regions.find(r => r._key === system.regionID);
    const regionName = region
      ? (typeof region.name === 'string' ? region.name : region.name['en'] || region.name['zh'] || 'Unknown')
      : 'Unknown';

    setSelectedSystem({
      systemId,
      systemName,
      regionName,
      securityStatus: system.securityStatus || 0,
      data: {
        hotZone: hotZoneMap.get(systemId),
        capitalKills: capitalKillsMap.get(systemId),
        dangerZone: dangerZoneMap.get(systemId),
        highValueKills: highValueKillsMap.get(systemId),
      },
    });
  };

  // Toggle filter
  const toggleFilter = (filterName: keyof typeof filters) => {
    setFilters(prev => ({
      ...prev,
      [filterName]: !prev[filterName],
    }));
  };

  // Count systems for each filter
  const filterCounts = useMemo(() => {
    if (!battleReport || !systemLookups) {
      return {
        liveHotspots: liveHotspots.length,
        hotZones: 0,
        capitalKills: 0,
        dangerZones: 0,
        highValueKills: 0,
      };
    }

    return {
      liveHotspots: liveHotspots.length,
      hotZones: battleReport.hot_zones.length,
      capitalKills: systemLookups.capitalKillsMap.size,
      dangerZones: systemLookups.dangerZoneMap.size,
      highValueKills: systemLookups.highValueKillsMap.size,
    };
  }, [battleReport, systemLookups, liveHotspots.length]);

  // Loading state
  if (mapLoading || reportLoading) {
    return (
      <div style={{ height: 'calc(100vh - 120px)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <div style={{ textAlign: 'center' }}>
          <div className="skeleton" style={{ height: '40px', width: '300px', margin: '0 auto 1rem' }} />
          <p style={{ color: 'var(--text-secondary)' }}>
            {mapLoading ? 'Loading galaxy map...' : 'Loading battle data...'}
          </p>
        </div>
      </div>
    );
  }

  // Error state
  if (mapError || reportError) {
    return (
      <div className="card" style={{ background: 'var(--danger)', color: 'white' }}>
        <h2>Error Loading Battle Map</h2>
        <p>{mapError || reportError}</p>
      </div>
    );
  }

  return (
    <div style={{
      display: 'flex',
      gap: '0',
      height: 'calc(100vh - 120px)',
      background: 'var(--bg-primary)',
    }}>
      {/* Left Sidebar - Filters */}
      <div style={{
        width: '280px',
        background: 'var(--bg-secondary)',
        borderRight: '1px solid var(--border-color)',
        padding: '1.5rem',
        overflowY: 'auto',
      }}>
        <h2 style={{ fontSize: '1.25rem', marginBottom: '1rem' }}>Combat Layers</h2>
        <p style={{
          color: 'var(--text-secondary)',
          fontSize: '0.875rem',
          marginBottom: '1.5rem'
        }}>
          Toggle combat data overlays on the map
        </p>

        {/* Filter Checkboxes */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          {/* LIVE Hotspots */}
          <label style={{
            display: 'flex',
            alignItems: 'center',
            cursor: 'pointer',
            padding: '0.75rem',
            background: filters.liveHotspots ? 'var(--bg-elevated)' : 'transparent',
            borderRadius: '6px',
            border: '1px solid',
            borderColor: filters.liveHotspots ? '#ffffff' : 'var(--border-color)',
            transition: 'all 0.2s',
          }}>
            <input
              type="checkbox"
              checked={filters.liveHotspots}
              onChange={() => toggleFilter('liveHotspots')}
              style={{
                marginRight: '0.75rem',
                width: '18px',
                height: '18px',
                cursor: 'pointer',
                accentColor: '#ffffff',
              }}
            />
            <div style={{ flex: 1 }}>
              <div style={{
                display: 'flex',
                alignItems: 'center',
                gap: '0.5rem',
                marginBottom: '0.25rem',
              }}>
                <div style={{
                  width: '12px',
                  height: '12px',
                  borderRadius: '50%',
                  background: '#ffffff',
                  boxShadow: '0 0 12px #ffffff',
                  animation: 'pulse 2s ease-in-out infinite',
                }} />
                <span style={{ fontWeight: 700, color: '#ffffff' }}>LIVE Hotspots ⚡</span>
              </div>
              <div style={{
                fontSize: '0.75rem',
                color: 'var(--text-secondary)',
              }}>
                {filterCounts.liveHotspots} active
              </div>
            </div>
          </label>

          {/* Hot Zones */}
          <label style={{
            display: 'flex',
            alignItems: 'center',
            cursor: 'pointer',
            padding: '0.75rem',
            background: filters.hotZones ? 'var(--bg-elevated)' : 'transparent',
            borderRadius: '6px',
            border: '1px solid',
            borderColor: filters.hotZones ? '#ff4444' : 'var(--border-color)',
            transition: 'all 0.2s',
          }}>
            <input
              type="checkbox"
              checked={filters.hotZones}
              onChange={() => toggleFilter('hotZones')}
              style={{
                marginRight: '0.75rem',
                width: '18px',
                height: '18px',
                cursor: 'pointer',
                accentColor: '#ff4444',
              }}
            />
            <div style={{ flex: 1 }}>
              <div style={{
                display: 'flex',
                alignItems: 'center',
                gap: '0.5rem',
                marginBottom: '0.25rem',
              }}>
                <div style={{
                  width: '12px',
                  height: '12px',
                  borderRadius: '50%',
                  background: '#ff4444',
                  boxShadow: '0 0 8px #ff4444',
                }} />
                <span style={{ fontWeight: 600 }}>Hot Zones</span>
              </div>
              <div style={{
                fontSize: '0.75rem',
                color: 'var(--text-secondary)',
              }}>
                {filterCounts.hotZones} systems
              </div>
            </div>
          </label>

          {/* Capital Kills */}
          <label style={{
            display: 'flex',
            alignItems: 'center',
            cursor: 'pointer',
            padding: '0.75rem',
            background: filters.capitalKills ? 'var(--bg-elevated)' : 'transparent',
            borderRadius: '6px',
            border: '1px solid',
            borderColor: filters.capitalKills ? '#bc8cff' : 'var(--border-color)',
            transition: 'all 0.2s',
          }}>
            <input
              type="checkbox"
              checked={filters.capitalKills}
              onChange={() => toggleFilter('capitalKills')}
              style={{
                marginRight: '0.75rem',
                width: '18px',
                height: '18px',
                cursor: 'pointer',
                accentColor: '#bc8cff',
              }}
            />
            <div style={{ flex: 1 }}>
              <div style={{
                display: 'flex',
                alignItems: 'center',
                gap: '0.5rem',
                marginBottom: '0.25rem',
              }}>
                <div style={{
                  width: '12px',
                  height: '12px',
                  borderRadius: '50%',
                  background: '#bc8cff',
                  boxShadow: '0 0 8px #bc8cff',
                }} />
                <span style={{ fontWeight: 600 }}>Capital Kills</span>
              </div>
              <div style={{
                fontSize: '0.75rem',
                color: 'var(--text-secondary)',
              }}>
                {filterCounts.capitalKills} systems
              </div>
            </div>
          </label>

          {/* Danger Zones */}
          <label style={{
            display: 'flex',
            alignItems: 'center',
            cursor: 'pointer',
            padding: '0.75rem',
            background: filters.dangerZones ? 'var(--bg-elevated)' : 'transparent',
            borderRadius: '6px',
            border: '1px solid',
            borderColor: filters.dangerZones ? '#d29922' : 'var(--border-color)',
            transition: 'all 0.2s',
          }}>
            <input
              type="checkbox"
              checked={filters.dangerZones}
              onChange={() => toggleFilter('dangerZones')}
              style={{
                marginRight: '0.75rem',
                width: '18px',
                height: '18px',
                cursor: 'pointer',
                accentColor: '#d29922',
              }}
            />
            <div style={{ flex: 1 }}>
              <div style={{
                display: 'flex',
                alignItems: 'center',
                gap: '0.5rem',
                marginBottom: '0.25rem',
              }}>
                <div style={{
                  width: '12px',
                  height: '12px',
                  borderRadius: '50%',
                  background: '#d29922',
                  boxShadow: '0 0 8px #d29922',
                }} />
                <span style={{ fontWeight: 600 }}>Danger Zones</span>
              </div>
              <div style={{
                fontSize: '0.75rem',
                color: 'var(--text-secondary)',
              }}>
                {filterCounts.dangerZones} systems
              </div>
            </div>
          </label>

          {/* High-Value Kills */}
          <label style={{
            display: 'flex',
            alignItems: 'center',
            cursor: 'pointer',
            padding: '0.75rem',
            background: filters.highValueKills ? 'var(--bg-elevated)' : 'transparent',
            borderRadius: '6px',
            border: '1px solid',
            borderColor: filters.highValueKills ? '#00d9ff' : 'var(--border-color)',
            transition: 'all 0.2s',
          }}>
            <input
              type="checkbox"
              checked={filters.highValueKills}
              onChange={() => toggleFilter('highValueKills')}
              style={{
                marginRight: '0.75rem',
                width: '18px',
                height: '18px',
                cursor: 'pointer',
                accentColor: '#00d9ff',
              }}
            />
            <div style={{ flex: 1 }}>
              <div style={{
                display: 'flex',
                alignItems: 'center',
                gap: '0.5rem',
                marginBottom: '0.25rem',
              }}>
                <div style={{
                  width: '12px',
                  height: '12px',
                  borderRadius: '50%',
                  background: '#00d9ff',
                  boxShadow: '0 0 8px #00d9ff',
                }} />
                <span style={{ fontWeight: 600 }}>High-Value Kills</span>
              </div>
              <div style={{
                fontSize: '0.75rem',
                color: 'var(--text-secondary)',
              }}>
                {filterCounts.highValueKills} systems
              </div>
            </div>
          </label>
        </div>

        {/* Global Stats */}
        {battleReport && (
          <div style={{
            marginTop: '2rem',
            paddingTop: '1.5rem',
            borderTop: '1px solid var(--border-color)',
          }}>
            <h3 style={{ fontSize: '1rem', marginBottom: '1rem' }}>24h Summary</h3>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
              <div>
                <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                  Total Kills
                </div>
                <div style={{ fontSize: '1.25rem', fontWeight: 700, color: 'var(--text-primary)' }}>
                  {battleReport.global.total_kills.toLocaleString()}
                </div>
              </div>
              <div>
                <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                  ISK Destroyed
                </div>
                <div style={{ fontSize: '1.25rem', fontWeight: 700, color: 'var(--danger)' }}>
                  {(battleReport.global.total_isk_destroyed / 1_000_000_000).toFixed(1)}B ISK
                </div>
              </div>
              <div>
                <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                  Peak Hour (UTC)
                </div>
                <div style={{ fontSize: '1.25rem', fontWeight: 700, color: 'var(--accent-blue)' }}>
                  {String(battleReport.global.peak_hour_utc).padStart(2, '0')}:00
                </div>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Main Map Area */}
      <div style={{ flex: 1, position: 'relative' }}>
        <EveMap3D
          systems={systems}
          stargates={stargates}
          regions={regions}
          mapControl={mapControl}
        />

        {/* Instructions overlay */}
        <div style={{
          position: 'absolute',
          top: '1rem',
          left: '1rem',
          background: 'rgba(13, 17, 23, 0.95)',
          padding: '1rem',
          borderRadius: '8px',
          border: '1px solid var(--border-color)',
          maxWidth: '300px',
        }}>
          <h3 style={{ fontSize: '0.875rem', marginBottom: '0.5rem' }}>Controls</h3>
          <ul style={{
            fontSize: '0.75rem',
            color: 'var(--text-secondary)',
            listStyle: 'none',
            padding: 0,
          }}>
            <li style={{ marginBottom: '0.25rem' }}>🖱️ Click & drag to rotate</li>
            <li style={{ marginBottom: '0.25rem' }}>🔍 Scroll to zoom</li>
            <li>📍 Click system for details</li>
          </ul>
        </div>
      </div>

      {/* Right Sidebar - System Info Panel */}
      {selectedSystem && (
        <div style={{
          width: '320px',
          background: 'var(--bg-secondary)',
          borderLeft: '1px solid var(--border-color)',
          padding: '1.5rem',
          overflowY: 'auto',
          animation: 'slideInRight 0.3s ease',
        }}>
          {/* Close button */}
          <button
            onClick={() => setSelectedSystem(null)}
            style={{
              position: 'absolute',
              top: '1rem',
              right: '1rem',
              background: 'transparent',
              border: 'none',
              color: 'var(--text-secondary)',
              fontSize: '1.5rem',
              cursor: 'pointer',
              padding: '0.25rem',
              lineHeight: 1,
            }}
          >
            ×
          </button>

          {/* System header */}
          <div style={{ marginBottom: '1.5rem' }}>
            <h2 style={{ fontSize: '1.5rem', marginBottom: '0.5rem' }}>
              {selectedSystem.systemName}
            </h2>
            <div style={{
              display: 'flex',
              flexDirection: 'column',
              gap: '0.25rem',
              fontSize: '0.875rem',
              color: 'var(--text-secondary)',
            }}>
              <div>Region: {selectedSystem.regionName}</div>
              <div style={{
                color: selectedSystem.securityStatus >= 0.5
                  ? 'var(--success)'
                  : selectedSystem.securityStatus > 0
                    ? 'var(--warning)'
                    : 'var(--danger)',
              }}>
                Security: {selectedSystem.securityStatus.toFixed(1)}
              </div>
            </div>
          </div>

          {/* Combat data sections */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
            {/* Hot Zone data */}
            {selectedSystem.data.hotZone && (
              <div style={{
                padding: '1rem',
                background: 'rgba(255, 68, 68, 0.1)',
                border: '1px solid #ff4444',
                borderRadius: '6px',
              }}>
                <h3 style={{
                  fontSize: '1rem',
                  marginBottom: '0.75rem',
                  color: '#ff4444',
                }}>
                  🔥 Hot Zone
                </h3>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                  <div>
                    <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                      Kills (24h)
                    </div>
                    <div style={{ fontSize: '1.25rem', fontWeight: 700 }}>
                      {selectedSystem.data.hotZone.kills}
                    </div>
                  </div>
                  <div>
                    <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                      ISK Destroyed
                    </div>
                    <div style={{ fontSize: '1.25rem', fontWeight: 700, color: 'var(--danger)' }}>
                      {(selectedSystem.data.hotZone.total_isk_destroyed / 1_000_000_000).toFixed(1)}B
                    </div>
                  </div>
                  {selectedSystem.data.hotZone.dominant_ship_type && (
                    <div>
                      <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                        Dominant Ship
                      </div>
                      <div style={{ fontSize: '0.875rem', fontWeight: 600 }}>
                        {selectedSystem.data.hotZone.dominant_ship_type}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Capital Kills data */}
            {selectedSystem.data.capitalKills && selectedSystem.data.capitalKills > 0 && (
              <div style={{
                padding: '1rem',
                background: 'rgba(188, 140, 255, 0.1)',
                border: '1px solid #bc8cff',
                borderRadius: '6px',
              }}>
                <h3 style={{
                  fontSize: '1rem',
                  marginBottom: '0.75rem',
                  color: '#bc8cff',
                }}>
                  ⚔️ Capital Kills
                </h3>
                <div>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                    Capital Ships Destroyed
                  </div>
                  <div style={{ fontSize: '1.25rem', fontWeight: 700 }}>
                    {selectedSystem.data.capitalKills}
                  </div>
                </div>
              </div>
            )}

            {/* Danger Zone data */}
            {selectedSystem.data.dangerZone && (
              <div style={{
                padding: '1rem',
                background: 'rgba(210, 153, 34, 0.1)',
                border: '1px solid #d29922',
                borderRadius: '6px',
              }}>
                <h3 style={{
                  fontSize: '1rem',
                  marginBottom: '0.75rem',
                  color: '#d29922',
                }}>
                  ⚠️ Danger Zone
                </h3>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                  <div>
                    <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                      Industrials Killed
                    </div>
                    <div style={{ fontSize: '1.25rem', fontWeight: 700 }}>
                      {selectedSystem.data.dangerZone.industrials_killed}
                    </div>
                  </div>
                  {selectedSystem.data.dangerZone.freighters_killed > 0 && (
                    <div>
                      <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                        Freighters Killed
                      </div>
                      <div style={{ fontSize: '1.25rem', fontWeight: 700, color: 'var(--danger)' }}>
                        {selectedSystem.data.dangerZone.freighters_killed}
                      </div>
                    </div>
                  )}
                  <div>
                    <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                      Warning Level
                    </div>
                    <div style={{
                      fontSize: '0.875rem',
                      fontWeight: 700,
                      color: selectedSystem.data.dangerZone.warning_level === 'EXTREME'
                        ? 'var(--danger)'
                        : selectedSystem.data.dangerZone.warning_level === 'HIGH'
                          ? 'var(--warning)'
                          : 'var(--text-primary)',
                    }}>
                      {selectedSystem.data.dangerZone.warning_level}
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* High-Value Kills data */}
            {selectedSystem.data.highValueKills && selectedSystem.data.highValueKills.length > 0 && (
              <div style={{
                padding: '1rem',
                background: 'rgba(0, 217, 255, 0.1)',
                border: '1px solid #00d9ff',
                borderRadius: '6px',
              }}>
                <h3 style={{
                  fontSize: '1rem',
                  marginBottom: '0.75rem',
                  color: '#00d9ff',
                }}>
                  💎 High-Value Kills
                </h3>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                  <div>
                    <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                      Total High-Value Kills
                    </div>
                    <div style={{ fontSize: '1.25rem', fontWeight: 700 }}>
                      {selectedSystem.data.highValueKills.length}
                    </div>
                  </div>
                  <div>
                    <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                      Highest Value Kill
                    </div>
                    <div style={{ fontSize: '1rem', fontWeight: 700, color: 'var(--danger)' }}>
                      {(Math.max(...selectedSystem.data.highValueKills.map(k => k.isk_destroyed)) / 1_000_000_000).toFixed(1)}B ISK
                    </div>
                    <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: '0.25rem' }}>
                      {selectedSystem.data.highValueKills[0]?.ship_name || 'Unknown'}
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* No data message */}
            {!selectedSystem.data.hotZone &&
             !selectedSystem.data.capitalKills &&
             !selectedSystem.data.dangerZone &&
             (!selectedSystem.data.highValueKills || selectedSystem.data.highValueKills.length === 0) && (
              <div style={{
                padding: '1.5rem',
                textAlign: 'center',
                color: 'var(--text-secondary)',
              }}>
                <p>No combat activity detected in this system during the last 24 hours.</p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* CSS animations */}
      <style>{`
        @keyframes slideInRight {
          from {
            transform: translateX(100%);
            opacity: 0;
          }
          to {
            transform: translateX(0);
            opacity: 1;
          }
        }
      `}</style>
    </div>
  );
}
