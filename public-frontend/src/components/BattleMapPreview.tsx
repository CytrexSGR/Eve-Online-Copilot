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
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();

  // Initialize map control with hot zones highlighted
  const mapControl = useMapControl({
    language: 'en',
    filterNewEdenOnly: true,
    containerStyle: {
      height: '500px',
      width: '100%',
      cursor: 'pointer',
      position: 'relative',
    },
    style: {
      backgroundColor: '#000000',
    },
    events: {
      onSystemClick: () => {
        // Navigate to full battle map on any system click
        navigate('/battle-map');
      },
    },
  });

  // Load JSONL data files
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

        // Load all three data files in parallel
        const [systemsData, stargatesData, regionsData] = await Promise.all([
          loadJSONL('/data/mapSolarSystems.jsonl'),
          loadJSONL('/data/mapStargates.jsonl'),
          loadJSONL('/data/mapRegions.jsonl'),
        ]);

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

  // Highlight hot zones when data is loaded
  useEffect(() => {
    if (systems.length > 0 && hotZones.length > 0) {
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

      // Focus on the hottest system (first in list)
      if (hotZones.length > 0) {
        // Small delay to ensure systems are rendered
        setTimeout(() => {
          mapControl.focusSystem(hotZones[0].system_id, 1500);
        }, 100);
      }
    }
  }, [systems, hotZones, mapControl]);

  // Handle container click to navigate to full map
  const handleClick = () => {
    navigate('/battle-map');
  };

  if (loading) {
    return (
      <div className="card" style={{ height: '500px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <div style={{ textAlign: 'center' }}>
          <div className="skeleton" style={{ height: '40px', width: '200px', margin: '0 auto 1rem' }} />
          <p style={{ color: 'var(--text-secondary)' }}>Loading galaxy map...</p>
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
        onClick={handleClick}
        style={{
          position: 'relative',
          height: '500px',
          cursor: 'pointer',
        }}
      >
        {/* 3D Map */}
        <EveMap3D
          systems={systems}
          stargates={stargates}
          regions={regions}
          mapControl={mapControl}
        />

        {/* Overlay with "Click to view full map" message */}
        <div
          style={{
            position: 'absolute',
            bottom: 0,
            left: 0,
            right: 0,
            background: 'linear-gradient(to top, rgba(13, 17, 23, 0.95), transparent)',
            padding: '2rem 1rem 1rem',
            pointerEvents: 'none',
          }}
        >
          <div style={{ textAlign: 'center' }}>
            <p style={{
              fontSize: '1.125rem',
              fontWeight: 600,
              color: 'var(--accent-blue)',
              margin: 0,
              textShadow: '0 2px 8px rgba(0, 0, 0, 0.8)',
            }}>
              🗺️ Click to view full Battle Map
            </p>
            <p style={{
              fontSize: '0.875rem',
              color: 'var(--text-secondary)',
              margin: '0.5rem 0 0',
              textShadow: '0 2px 8px rgba(0, 0, 0, 0.8)',
            }}>
              {hotZones.length} hot zones highlighted in red/orange
            </p>
          </div>
        </div>

        {/* Hover effect overlay */}
        <div
          style={{
            position: 'absolute',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            background: 'rgba(88, 166, 255, 0.05)',
            opacity: 0,
            transition: 'opacity 0.3s ease',
            pointerEvents: 'none',
          }}
          className="hover-overlay"
        />
      </div>

      <style>{`
        .card:hover .hover-overlay {
          opacity: 1;
        }
      `}</style>
    </div>
  );
}
