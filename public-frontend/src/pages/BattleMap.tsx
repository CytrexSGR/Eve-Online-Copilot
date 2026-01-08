import { useState, useEffect } from 'react';
import { EveMap3D, useMapControl } from 'eve-map-3d';
import type { SolarSystem, Stargate, Region } from 'eve-map-3d';
import { battleApi } from '../services/api';
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

  // Active battles state
  const [activeBattles, setActiveBattles] = useState<ActiveBattle[]>([]);

  // Filter state
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

  // Load active battles
  useEffect(() => {
    const fetchActiveBattles = async () => {
      try {
        const data = await battleApi.getActiveBattles(50);
        if (data.battles && data.battles.length > 0) {
          setActiveBattles(data.battles);
        }
      } catch (err) {
        console.error('Failed to fetch active battles:', err);
      }
    };

    fetchActiveBattles();
    const interval = setInterval(fetchActiveBattles, 10000);
    return () => clearInterval(interval);
  }, []);

  // Toggle filter
  const toggleFilter = (key: keyof typeof filters) => {
    setFilters(prev => ({ ...prev, [key]: !prev[key] }));
  };

  if (mapLoading) {
    return (
      <div style={{ height: 'calc(100vh - 120px)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <div className="skeleton" style={{ height: '40px', width: '300px' }} />
      </div>
    );
  }

  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      height: 'calc(100vh - 120px)',
      background: 'var(--bg-primary)',
    }}>
      {/* Horizontal Filter Bar */}
      <div style={{
        display: 'flex',
        gap: '1rem',
        padding: '1rem',
        background: 'var(--bg-secondary)',
        borderBottom: '1px solid var(--border-color)',
        overflowX: 'auto',
      }}>
        <label style={{
          display: 'flex',
          alignItems: 'center',
          gap: '0.5rem',
          cursor: 'pointer',
          padding: '0.5rem 1rem',
          background: filters.activeBattles ? 'var(--bg-elevated)' : 'transparent',
          borderRadius: '6px',
          border: '1px solid',
          borderColor: filters.activeBattles ? '#ff0066' : 'var(--border-color)',
          whiteSpace: 'nowrap',
        }}>
          <input
            type="checkbox"
            checked={filters.activeBattles}
            onChange={() => toggleFilter('activeBattles')}
            style={{ accentColor: '#ff0066' }}
          />
          <span>⚔️ Active Battles</span>
          <span style={{ fontSize: '0.875rem', color: 'var(--text-secondary)' }}>
            {activeBattles.length}
          </span>
        </label>

        <label style={{
          display: 'flex',
          alignItems: 'center',
          gap: '0.5rem',
          cursor: 'pointer',
          padding: '0.5rem 1rem',
          background: filters.liveHotspots ? 'var(--bg-elevated)' : 'transparent',
          borderRadius: '6px',
          border: '1px solid',
          borderColor: filters.liveHotspots ? '#ffffff' : 'var(--border-color)',
          whiteSpace: 'nowrap',
        }}>
          <input
            type="checkbox"
            checked={filters.liveHotspots}
            onChange={() => toggleFilter('liveHotspots')}
            style={{ accentColor: '#ffffff' }}
          />
          <span>⚡ LIVE Hotspots</span>
        </label>

        <label style={{
          display: 'flex',
          alignItems: 'center',
          gap: '0.5rem',
          cursor: 'pointer',
          padding: '0.5rem 1rem',
          background: filters.hotZones ? 'var(--bg-elevated)' : 'transparent',
          borderRadius: '6px',
          border: '1px solid',
          borderColor: filters.hotZones ? '#ff0000' : 'var(--border-color)',
          whiteSpace: 'nowrap',
        }}>
          <input
            type="checkbox"
            checked={filters.hotZones}
            onChange={() => toggleFilter('hotZones')}
            style={{ accentColor: '#ff0000' }}
          />
          <span>🔥 Hot Zones</span>
        </label>
      </div>

      {/* Map Area - Full Width */}
      <div style={{ position: 'relative', height: '500px' }}>
        <EveMap3D
          systems={systems}
          stargates={stargates}
          regions={regions}
          mapControl={mapControl}
        />
      </div>

      {/* Battle Detail Grid */}
      <div style={{
        flex: 1,
        overflowY: 'auto',
        padding: '1rem',
        background: 'var(--bg-secondary)',
      }}>
        <h3 style={{ marginBottom: '1rem', fontSize: '1.125rem' }}>🔥 Active Battles</h3>
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
