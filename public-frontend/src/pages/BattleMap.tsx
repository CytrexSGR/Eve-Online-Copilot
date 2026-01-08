import { useState, useEffect, useMemo } from 'react';
import { EveMap3D, useMapControl } from 'eve-map-3d';
import type { SolarSystem, Stargate, Region } from 'eve-map-3d';
import { battleApi, reportsApi } from '../services/api';
import type { BattleReport, HotZone, HighValueKill, DangerZone } from '../types/reports';
import { useNavigate } from 'react-router-dom';

interface ActiveBattle {
  battle_id: number;
  system_id: number;
  system_name: string;
  region_name: string;
  security: number;
  total_kills: number;
  total_isk_destroyed: number;
  last_milestone: number;
  started_at: string;
  last_kill_at: string;
  duration_minutes: number;
  telegram_sent: boolean;
  intensity: 'extreme' | 'high' | 'moderate' | 'low';
}

export function BattleMap() {
  const navigate = useNavigate();

  // Map data state
  const [systems, setSystems] = useState<SolarSystem[]>([]);
  const [stargates, setStargates] = useState<Stargate[]>([]);
  const [regions, setRegions] = useState<Region[]>([]);
  const [mapLoading, setMapLoading] = useState(true);

  // Battle report data state
  const [battleReport, setBattleReport] = useState<BattleReport | null>(null);

  // Active battles state
  const [activeBattles, setActiveBattles] = useState<ActiveBattle[]>([]);

  // Live hotspots state
  const [liveHotspots, setLiveHotspots] = useState<any[]>([]);

  // Filter state - ALL 6 filters
  const [filters, setFilters] = useState({
    activeBattles: true,
    liveHotspots: true,
    hotZones: true,
    capitalKills: false,
    dangerZones: false,
    highValueKills: false,
  });

  // Tooltip state
  const [tooltip, setTooltip] = useState<{
    visible: boolean;
    x: number;
    y: number;
    battle: ActiveBattle | null;
  }>({ visible: false, x: 0, y: 0, battle: null });

  // Initialize map control
  const mapControl = useMapControl({
    language: 'en',
    filterNewEdenOnly: true,
    containerStyle: {
      height: '500px',
      width: '100%',
    },
    style: {
      backgroundColor: '#000000',
    },
    events: {
      onSystemClick: (system: SolarSystem) => {
        console.log('System clicked:', system._key);
      },
    },
  });

  // Load JSONL map data
  useEffect(() => {
    const loadJSONL = async (path: string): Promise<any[]> => {
      try {
        const response = await fetch(path);
        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
        const text = await response.text();
        return text.trim().split('\n').map(line => JSON.parse(line));
      } catch (error) {
        console.error(`Failed to load ${path}:`, error);
        throw error;
      }
    };

    const loadMapData = async () => {
      try {
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
        setMapLoading(false);
      }
    };

    loadMapData();
  }, []);

  // Load battle report data
  useEffect(() => {
    const loadBattleReport = async () => {
      try {
        const data = await reportsApi.getBattleReport();
        setBattleReport(data);
      } catch (err) {
        console.error('Failed to load battle report:', err);
      }
    };

    loadBattleReport();
  }, []);

  // Load active battles
  useEffect(() => {
    const fetchActiveBattles = async () => {
      try {
        const data = await battleApi.getActiveBattles(50);
        console.log('[BattleMap] Fetched active battles:', data);
        if (data.battles && data.battles.length > 0) {
          console.log('[BattleMap] Setting activeBattles:', data.battles.length);
          setActiveBattles(data.battles);
        } else {
          console.warn('[BattleMap] No battles in response or empty array');
        }
      } catch (err) {
        console.error('Failed to fetch active battles:', err);
      }
    };

    fetchActiveBattles();
    const interval = setInterval(fetchActiveBattles, 10000);
    return () => clearInterval(interval);
  }, []);

  // Poll live hotspots every 10 seconds
  useEffect(() => {
    const fetchLiveHotspots = async () => {
      try {
        const response = await fetch('/api/war/live-hotspots');
        if (response.ok) {
          const data = await response.json();
          setLiveHotspots(data.hotspots || []);
        }
      } catch (err) {
        console.error('Failed to fetch live hotspots:', err);
      }
    };

    fetchLiveHotspots();
    const interval = setInterval(fetchLiveHotspots, 10000);
    return () => clearInterval(interval);
  }, []);

  // Build system lookup maps for quick access
  const systemLookups = useMemo(() => {
    if (!battleReport) return null;

    const hotZoneMap = new Map<number, HotZone>();
    const capitalKillsMap = new Map<number, number>();
    const dangerZoneMap = new Map<number, DangerZone>();
    const highValueKillsMap = new Map<number, HighValueKill[]>();

    // Hot zones
    battleReport.hot_zones.forEach(zone => {
      hotZoneMap.set(zone.system_id, zone);
    });

    // Capital kills
    Object.values(battleReport.capital_kills).forEach(category => {
      category.kills.forEach((kill: any) => {
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

    // Danger zones
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
    const configs: Array<{
      systemId: number;
      color: string;
      size: number;
      highlighted: boolean;
      opacity: number;
    }> = [];

    const hotZoneMap = systemLookups?.hotZoneMap;
    const capitalKillsMap = systemLookups?.capitalKillsMap;
    const dangerZoneMap = systemLookups?.dangerZoneMap;
    const highValueKillsMap = systemLookups?.highValueKillsMap;

    const renderedSystems = new Set<number>();

    // Priority 0: ACTIVE BATTLES
    if (filters.activeBattles && activeBattles.length > 0) {
      activeBattles.forEach(battle => {
        let color = '#00ff00';
        let size = 6.0;

        switch (battle.intensity) {
          case 'extreme':
            color = '#ff0066';
            size = 8.0;
            break;
          case 'high':
            color = '#ff6600';
            size = 7.0;
            break;
          case 'moderate':
            color = '#ffcc00';
            size = 6.0;
            break;
          case 'low':
            color = '#00ff00';
            size = 5.0;
            break;
        }

        configs.push({
          systemId: battle.system_id,
          color,
          size,
          highlighted: true,
          opacity: 1.0,
        });

        renderedSystems.add(battle.system_id);
      });
    }

    // Priority 1: LIVE HOTSPOTS
    if (filters.liveHotspots && liveHotspots.length > 0) {
      liveHotspots.forEach(hotspot => {
        if (renderedSystems.has(hotspot.system_id)) return;

        const age = hotspot.age_seconds || 0;
        let color = '#ffffff';
        let size = 7.0;

        if (age < 60) {
          color = '#ffffff';
          size = 7.0;
        } else if (age < 180) {
          color = '#ffff00';
          size = 6.0;
        } else {
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

    if (filters.hotZones && hotZoneMap) {
      hotZoneMap.forEach((_, systemId) => allSystemIds.add(systemId));
    }
    if (filters.capitalKills && capitalKillsMap) {
      capitalKillsMap.forEach((_, systemId) => allSystemIds.add(systemId));
    }
    if (filters.dangerZones && dangerZoneMap) {
      dangerZoneMap.forEach((_, systemId) => allSystemIds.add(systemId));
    }
    if (filters.highValueKills && highValueKillsMap) {
      highValueKillsMap.forEach((_, systemId) => allSystemIds.add(systemId));
    }

    // For each system, determine color and size based on priority
    allSystemIds.forEach(systemId => {
      if (renderedSystems.has(systemId)) return;

      let color = '#ffffff';
      let size = 3.0;

      // Priority 2: Capital Kills
      if (filters.capitalKills && capitalKillsMap && capitalKillsMap.has(systemId)) {
        color = '#d946ef';
        size = 5.0;
      }
      // Priority 3: Hot Zones
      else if (filters.hotZones && hotZoneMap && battleReport && hotZoneMap.has(systemId)) {
        const index = battleReport.hot_zones.findIndex(z => z.system_id === systemId);
        const isTopThree = index < 3;
        color = isTopThree ? '#ff0000' : '#ff6600';
        size = isTopThree ? 4.5 : 3.5;
      }
      // Priority 4: High-Value Kills
      else if (filters.highValueKills && highValueKillsMap && highValueKillsMap.has(systemId)) {
        color = '#00ffff';
        size = 4.0;
      }
      // Priority 5: Danger Zones
      else if (filters.dangerZones && dangerZoneMap && dangerZoneMap.has(systemId)) {
        color = '#ffaa00';
        size = 3.5;
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
  }, [battleReport, systemLookups, filters, liveHotspots, activeBattles]);

  // Update map with new render configs when filters change
  useEffect(() => {
    if (systems.length > 0) {
      console.log(`[BattleMap] Updating map with ${systemRenderConfigs.length} system configs`);
      mapControl.setConfig({
        systemRenderConfigs,
      });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [systems.length, systemRenderConfigs]);

  // Toggle filter
  const toggleFilter = (key: keyof typeof filters) => {
    setFilters(prev => ({ ...prev, [key]: !prev[key] }));
  };

  // Count systems for each filter
  const filterCounts = useMemo(() => {
    if (!battleReport || !systemLookups) {
      return {
        activeBattles: activeBattles.length,
        liveHotspots: liveHotspots.length,
        hotZones: 0,
        capitalKills: 0,
        dangerZones: 0,
        highValueKills: 0,
      };
    }

    return {
      activeBattles: activeBattles.length,
      liveHotspots: liveHotspots.length,
      hotZones: battleReport.hot_zones.length,
      capitalKills: systemLookups.capitalKillsMap.size,
      dangerZones: systemLookups.dangerZoneMap.size,
      highValueKills: systemLookups.highValueKillsMap.size,
    };
  }, [battleReport, systemLookups, liveHotspots.length, activeBattles.length]);

  if (mapLoading) {
    return (
      <div style={{ height: 'calc(100vh - 120px)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <div className="skeleton" style={{ height: '40px', width: '300px' }} />
      </div>
    );
  }

  return (
    <div>
      {/* Combat Layers Filter Card */}
      <div className="card" style={{ marginBottom: '1.5rem' }}>
        <h2>🗺️ Combat Map Layers</h2>
        <p style={{ color: 'var(--text-secondary)', fontSize: '0.875rem', marginBottom: '1rem' }}>
          Toggle combat data overlays on the map
        </p>
        <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap' }}>
          {/* Active Battles */}
          <div
            onClick={() => toggleFilter('activeBattles')}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem',
              cursor: 'pointer',
              padding: '0.5rem 1rem',
              background: filters.activeBattles ? 'var(--bg-elevated)' : 'transparent',
              borderRadius: '6px',
              border: '1px solid var(--border-color)',
              transition: 'all 0.2s',
            }}
          >
            <div style={{
              width: '12px',
              height: '12px',
              borderRadius: '50%',
              background: '#ff0066',
              boxShadow: filters.activeBattles ? '0 0 8px #ff0066' : 'none',
            }} />
            <span style={{ fontSize: '0.875rem', fontWeight: filters.activeBattles ? 600 : 400 }}>
              Active Battles ({filterCounts.activeBattles})
            </span>
          </div>

          {/* LIVE Hotspots */}
          <div
            onClick={() => toggleFilter('liveHotspots')}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem',
              cursor: 'pointer',
              padding: '0.5rem 1rem',
              background: filters.liveHotspots ? 'var(--bg-elevated)' : 'transparent',
              borderRadius: '6px',
              border: '1px solid var(--border-color)',
              transition: 'all 0.2s',
            }}
          >
            <div style={{
              width: '12px',
              height: '12px',
              borderRadius: '50%',
              background: '#ffffff',
              boxShadow: filters.liveHotspots ? '0 0 8px #ffffff' : 'none',
            }} />
            <span style={{ fontSize: '0.875rem', fontWeight: filters.liveHotspots ? 600 : 400 }}>
              LIVE Hotspots ⚡ ({filterCounts.liveHotspots})
            </span>
          </div>

          {/* Hot Zones */}
          <div
            onClick={() => toggleFilter('hotZones')}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem',
              cursor: 'pointer',
              padding: '0.5rem 1rem',
              background: filters.hotZones ? 'var(--bg-elevated)' : 'transparent',
              borderRadius: '6px',
              border: '1px solid var(--border-color)',
              transition: 'all 0.2s',
            }}
          >
            <div style={{
              width: '12px',
              height: '12px',
              borderRadius: '50%',
              background: '#ff0000',
              boxShadow: filters.hotZones ? '0 0 8px #ff0000' : 'none',
            }} />
            <span style={{ fontSize: '0.875rem', fontWeight: filters.hotZones ? 600 : 400 }}>
              Hot Zones ({filterCounts.hotZones})
            </span>
          </div>

          {/* Capital Kills */}
          <div
            onClick={() => toggleFilter('capitalKills')}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem',
              cursor: 'pointer',
              padding: '0.5rem 1rem',
              background: filters.capitalKills ? 'var(--bg-elevated)' : 'transparent',
              borderRadius: '6px',
              border: '1px solid var(--border-color)',
              transition: 'all 0.2s',
            }}
          >
            <div style={{
              width: '12px',
              height: '12px',
              borderRadius: '50%',
              background: '#bc8cff',
              boxShadow: filters.capitalKills ? '0 0 8px #bc8cff' : 'none',
            }} />
            <span style={{ fontSize: '0.875rem', fontWeight: filters.capitalKills ? 600 : 400 }}>
              Capital Kills ({filterCounts.capitalKills})
            </span>
          </div>

          {/* Danger Zones */}
          <div
            onClick={() => toggleFilter('dangerZones')}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem',
              cursor: 'pointer',
              padding: '0.5rem 1rem',
              background: filters.dangerZones ? 'var(--bg-elevated)' : 'transparent',
              borderRadius: '6px',
              border: '1px solid var(--border-color)',
              transition: 'all 0.2s',
            }}
          >
            <div style={{
              width: '12px',
              height: '12px',
              borderRadius: '50%',
              background: '#d29922',
              boxShadow: filters.dangerZones ? '0 0 8px #d29922' : 'none',
            }} />
            <span style={{ fontSize: '0.875rem', fontWeight: filters.dangerZones ? 600 : 400 }}>
              Danger Zones ({filterCounts.dangerZones})
            </span>
          </div>

          {/* High-Value Kills */}
          <div
            onClick={() => toggleFilter('highValueKills')}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem',
              cursor: 'pointer',
              padding: '0.5rem 1rem',
              background: filters.highValueKills ? 'var(--bg-elevated)' : 'transparent',
              borderRadius: '6px',
              border: '1px solid var(--border-color)',
              transition: 'all 0.2s',
            }}
          >
            <div style={{
              width: '12px',
              height: '12px',
              borderRadius: '50%',
              background: '#00d9ff',
              boxShadow: filters.highValueKills ? '0 0 8px #00d9ff' : 'none',
            }} />
            <span style={{ fontSize: '0.875rem', fontWeight: filters.highValueKills ? 600 : 400 }}>
              High-Value Kills ({filterCounts.highValueKills})
            </span>
          </div>
        </div>
      </div>

      {/* 3D Galaxy Map */}
      <div className="card" style={{ padding: 0, marginBottom: '1.5rem' }}>
        <div style={{ padding: '1.5rem 1.5rem 0.5rem' }}>
          <h2>🌌 Galaxy Combat Map - Real-Time</h2>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.875rem' }}>
            Interactive 3D visualization of active battles across New Eden
          </p>
        </div>
        <div style={{ height: '500px' }}>
          <EveMap3D
            systems={systems}
            stargates={stargates}
            regions={regions}
            mapControl={mapControl}
          />
        </div>
      </div>

      {/* Active Battles Section */}
      <div className="card">
        <h2>⚔️ Active Battles</h2>
        <p style={{ color: 'var(--text-secondary)', fontSize: '0.875rem', marginBottom: '1.5rem' }}>
          Ongoing combat operations • Updates every 10 seconds • {activeBattles.length} battles loaded
        </p>
        {activeBattles.length === 0 ? (
          <div style={{ padding: '3rem', textAlign: 'center', color: 'var(--text-secondary)' }}>
            <div style={{ fontSize: '3rem', marginBottom: '1rem' }}>⚔️</div>
            <p>No active battles at the moment</p>
          </div>
        ) : (
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))',
            gap: '1rem',
          }}>
            {activeBattles.slice(0, 20).map((battle) => (
            <div
              key={battle.battle_id}
              style={{
                padding: '1rem',
                background: 'var(--bg-primary)',
                borderRadius: '8px',
                border: '2px solid',
                borderColor: battle.intensity === 'extreme' ? 'var(--danger)' :
                            battle.intensity === 'high' ? 'var(--warning)' :
                            battle.intensity === 'moderate' ? 'var(--accent-blue)' :
                            'var(--success)',
                cursor: 'pointer',
                transition: 'all 0.2s',
              }}
              onMouseEnter={(e) => {
                setTooltip({
                  visible: true,
                  x: e.clientX,
                  y: e.clientY,
                  battle
                });
              }}
              onMouseMove={(e) => {
                if (tooltip.visible && tooltip.battle?.battle_id === battle.battle_id) {
                  setTooltip(prev => ({
                    ...prev,
                    x: e.clientX,
                    y: e.clientY,
                  }));
                }
              }}
              onMouseLeave={() => {
                setTooltip({ visible: false, x: 0, y: 0, battle: null });
              }}
              onClick={() => {
                navigate(`/battle/${battle.battle_id}`);
              }}
              onMouseOver={(e) => {
                (e.currentTarget as HTMLElement).style.transform = 'translateY(-2px)';
                (e.currentTarget as HTMLElement).style.boxShadow = '0 4px 12px rgba(0, 0, 0, 0.3)';
              }}
              onMouseOut={(e) => {
                (e.currentTarget as HTMLElement).style.transform = 'translateY(0)';
                (e.currentTarget as HTMLElement).style.boxShadow = 'none';
              }}
            >
              <div style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                marginBottom: '0.5rem'
              }}>
                <div style={{ fontSize: '1rem', fontWeight: 700 }}>
                  {battle.system_name}
                </div>
                <div style={{
                  fontSize: '0.65rem',
                  fontWeight: 600,
                  padding: '0.25rem 0.5rem',
                  borderRadius: '4px',
                  background: battle.intensity === 'extreme' ? 'var(--danger)' :
                              battle.intensity === 'high' ? 'var(--warning)' :
                              battle.intensity === 'moderate' ? 'var(--accent-blue)' :
                              'var(--success)',
                  color: 'white'
                }}>
                  {battle.intensity.toUpperCase()}
                </div>
              </div>

              <div style={{
                fontSize: '0.75rem',
                color: 'var(--text-secondary)',
                marginBottom: '0.75rem'
              }}>
                {battle.region_name} • {battle.security.toFixed(1)} sec
              </div>

              <div style={{
                display: 'grid',
                gridTemplateColumns: '1fr 1fr',
                gap: '0.5rem',
                fontSize: '0.875rem'
              }}>
                <div>
                  <div style={{ color: 'var(--text-secondary)', fontSize: '0.75rem' }}>Kills</div>
                  <div style={{ color: 'var(--accent-blue)', fontWeight: 600 }}>{battle.total_kills}</div>
                </div>
                <div>
                  <div style={{ color: 'var(--text-secondary)', fontSize: '0.75rem' }}>ISK</div>
                  <div style={{ color: 'var(--danger)', fontWeight: 600 }}>
                    {(battle.total_isk_destroyed / 1_000_000_000).toFixed(1)}B
                  </div>
                </div>
              </div>

              <div style={{
                marginTop: '0.5rem',
                fontSize: '0.7rem',
                color: 'var(--text-tertiary)',
                fontStyle: 'italic',
                textAlign: 'center'
              }}>
                Click for full details →
              </div>
            </div>
          ))}
        </div>
        )}
      </div>

      {/* Tooltip */}
      {tooltip.visible && tooltip.battle && (
        <div style={{
          position: 'fixed',
          left: `${tooltip.x + 15}px`,
          top: `${tooltip.y + 15}px`,
          background: 'var(--bg-elevated)',
          border: '2px solid var(--accent-blue)',
          borderRadius: '8px',
          padding: '0.75rem',
          minWidth: '250px',
          boxShadow: '0 4px 12px rgba(0, 0, 0, 0.5)',
          pointerEvents: 'none',
          zIndex: 10000,
        }}>
          <div style={{ marginBottom: '0.5rem' }}>
            <div style={{
              fontSize: '1rem',
              fontWeight: 700,
              color: 'var(--text-primary)',
              marginBottom: '0.25rem'
            }}>
              {tooltip.battle.system_name}
            </div>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
              {tooltip.battle.region_name} • {tooltip.battle.security.toFixed(1)} sec
            </div>
          </div>

          <div style={{
            display: 'inline-block',
            padding: '0.25rem 0.5rem',
            borderRadius: '4px',
            fontSize: '0.75rem',
            fontWeight: 600,
            marginBottom: '0.5rem',
            background: tooltip.battle.intensity === 'extreme' ? 'var(--danger)' :
                        tooltip.battle.intensity === 'high' ? 'var(--warning)' :
                        tooltip.battle.intensity === 'moderate' ? 'var(--accent-blue)' :
                        'var(--success)',
            color: 'white'
          }}>
            {tooltip.battle.intensity.toUpperCase()} INTENSITY
          </div>

          <div style={{
            display: 'grid',
            gridTemplateColumns: '1fr 1fr',
            gap: '0.5rem',
            fontSize: '0.875rem'
          }}>
            <div>
              <div style={{ color: 'var(--text-secondary)', fontSize: '0.75rem' }}>Kills</div>
              <div style={{ color: 'var(--accent-blue)', fontWeight: 600 }}>
                {tooltip.battle.total_kills}
              </div>
            </div>
            <div>
              <div style={{ color: 'var(--text-secondary)', fontSize: '0.75rem' }}>ISK Destroyed</div>
              <div style={{ color: 'var(--danger)', fontWeight: 600 }}>
                {(tooltip.battle.total_isk_destroyed / 1_000_000_000).toFixed(1)}B
              </div>
            </div>
            <div>
              <div style={{ color: 'var(--text-secondary)', fontSize: '0.75rem' }}>Duration</div>
              <div style={{ color: 'var(--text-primary)', fontWeight: 600 }}>
                {Math.floor(tooltip.battle.duration_minutes / 60)}h {tooltip.battle.duration_minutes % 60}m
              </div>
            </div>
            <div>
              <div style={{ color: 'var(--text-secondary)', fontSize: '0.75rem' }}>Status</div>
              <div style={{ color: 'var(--success)', fontWeight: 600 }}>
                ACTIVE
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
