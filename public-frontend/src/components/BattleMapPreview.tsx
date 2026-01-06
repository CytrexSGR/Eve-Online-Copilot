import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { EveMap3D, useMapControl } from 'eve-map-3d';
import type { SolarSystem, Stargate, Region } from 'eve-map-3d';
import type { HotZone } from '../types/reports';

interface BattleMapPreviewProps {
  hotZones: HotZone[];
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
export function BattleMapPreview({ hotZones }: BattleMapPreviewProps) {
  const [systems, setSystems] = useState<SolarSystem[]>([]);
  const [stargates, setStargates] = useState<Stargate[]>([]);
  const [regions, setRegions] = useState<Region[]>([]);
  const [loading, setLoading] = useState(false); // Start as false - load on demand
  const [error, setError] = useState<string | null>(null);
  const [mapLoaded, setMapLoaded] = useState(false); // Track if user wants to see map
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

  // Load JSONL data files only when user clicks "Load Map"
  const loadMapData = async () => {
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

    try {
      setError(null);
      setLoading(true);
      setMapLoaded(true);

      console.log('[BattleMapPreview] Loading 7.7 MB of map data...');

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

  // Highlight hot zones when data is loaded
  useEffect(() => {
    if (systems.length > 0 && hotZones.length > 0) {
      try {
        console.log('[BattleMapPreview] Highlighting hot zones:', hotZones.length);

        // Map hot zones to system render configs with red/orange coloring
        const systemRenderConfigs = hotZones.map((zone, index) => {
          // Top 3 are red (most dangerous), rest are orange
          const isTopThree = index < 3;
          const color = isTopThree ? '#ff4444' : '#ff9944';
          const size = isTopThree ? 2.5 : 2.0;

          return {
            systemId: zone.system_id,
            color,
            size,
            highlighted: true,
            opacity: 1.0,
          };
        });

        // Update map control configuration with hot zones
        mapControl.setConfig({
          systemRenderConfigs,
        });

        console.log('[BattleMapPreview] Hot zones configured successfully');

        // Focus on the hottest system (first in list) - optional, removed to reduce complexity
        // if (hotZones.length > 0) {
        //   setTimeout(() => {
        //     mapControl.focusSystem(hotZones[0].system_id, 1500);
        //   }, 100);
        // }
      } catch (err) {
        console.error('[BattleMapPreview] Error highlighting hot zones:', err);
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [systems.length, hotZones.length]);

  // Handle container click to navigate to full map
  const handleClick = () => {
    navigate('/battle-map');
  };

  // Show placeholder if map not loaded yet
  if (!mapLoaded) {
    return (
      <div
        className="card"
        style={{
          height: '500px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          background: 'linear-gradient(135deg, #0d1117 0%, #161b22 100%)',
          position: 'relative',
          overflow: 'hidden',
        }}
      >
        {/* Stars background effect */}
        <div style={{
          position: 'absolute',
          inset: 0,
          backgroundImage: 'radial-gradient(2px 2px at 20% 30%, white, transparent), radial-gradient(2px 2px at 60% 70%, white, transparent), radial-gradient(1px 1px at 50% 50%, white, transparent), radial-gradient(1px 1px at 80% 10%, white, transparent), radial-gradient(2px 2px at 90% 60%, white, transparent)',
          backgroundSize: '200% 200%',
          opacity: 0.3,
        }} />

        <div style={{ textAlign: 'center', position: 'relative', zIndex: 1 }}>
          <p style={{ fontSize: '3rem', marginBottom: '1rem' }}>🌌</p>
          <h3 style={{ fontSize: '1.25rem', marginBottom: '0.5rem', color: 'var(--text-primary)' }}>
            3D Galaxy Map
          </h3>
          <p style={{ color: 'var(--text-secondary)', marginBottom: '1.5rem', fontSize: '0.875rem' }}>
            Visualize {hotZones.length} combat hot zones across New Eden
          </p>
          <button
            onClick={loadMapData}
            style={{
              background: 'var(--accent-blue)',
              color: 'white',
              border: 'none',
              padding: '0.875rem 2rem',
              borderRadius: '6px',
              fontSize: '1rem',
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
            🗺️ Load 3D Map (7.7 MB)
          </button>
          <p style={{ color: 'var(--text-tertiary)', marginTop: '1rem', fontSize: '0.75rem' }}>
            High-fidelity 3D rendering of 8,437 solar systems
          </p>
        </div>
      </div>
    );
  }

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
            onClick={loadMapData}
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
            Retry
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

        {/* Info badge - top left */}
        <div
          style={{
            position: 'absolute',
            top: '1rem',
            left: '1rem',
            background: 'rgba(0, 0, 0, 0.7)',
            padding: '0.5rem 0.75rem',
            borderRadius: '4px',
            border: '1px solid rgba(255, 255, 255, 0.1)',
            pointerEvents: 'none',
          }}
        >
          <p style={{
            fontSize: '0.875rem',
            color: 'var(--text-secondary)',
            margin: 0,
          }}>
            🌌 {hotZones.length} hot zones
          </p>
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
