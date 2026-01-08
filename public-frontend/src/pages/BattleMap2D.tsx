import { useState, useEffect, useRef, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { battleApi } from '../services/api';

interface MapSystem {
  system_id: number;
  system_name: string;
  region_id: number;
  region_name: string;
  x: number;
  z: number;
  security: number;
}

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
  x: number;
  z: number;
}

interface Tooltip {
  visible: boolean;
  x: number;
  y: number;
  battle: ActiveBattle | null;
}

interface ViewPort {
  offsetX: number;
  offsetY: number;
  scale: number;
}

export function BattleMap2D() {
  const navigate = useNavigate();
  const canvasRef = useRef<HTMLCanvasElement>(null);

  // Map view toggle state
  const [mapView, setMapView] = useState<'battles' | 'ectmap'>('ectmap');

  const [systems, setSystems] = useState<MapSystem[]>([]);
  const [battles, setBattles] = useState<ActiveBattle[]>([]);
  const [loading, setLoading] = useState(true);
  const [tooltip, setTooltip] = useState<Tooltip>({ visible: false, x: 0, y: 0, battle: null });
  const [viewport, setViewport] = useState<ViewPort>({ offsetX: 0, offsetY: 0, scale: 1 });
  const [isDragging, setIsDragging] = useState(false);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });

  // Load map data
  useEffect(() => {
    const loadData = async () => {
      try {
        setLoading(true);
        // Load battles with embedded coordinates (fast!)
        const battlesData = await battleApi.getActiveBattles(1000);

        setBattles(battlesData.battles);
        setSystems([]); // No longer need to load all systems
        console.log(`[BattleMap2D] Loaded ${battlesData.battles.length} battles`);
      } catch (err) {
        console.error('[BattleMap2D] Failed to load map data:', err);
      } finally {
        setLoading(false);
      }
    };

    loadData();

    // Refresh battles every 10 seconds
    const interval = setInterval(async () => {
      try {
        const battlesData = await battleApi.getActiveBattles(1000);
        setBattles(battlesData.battles);
      } catch (err) {
        console.error('[BattleMap2D] Failed to refresh battles:', err);
      }
    }, 10000);

    return () => clearInterval(interval);
  }, []);

  // Calculate bounds for map centering based on battles
  const calculateBounds = useCallback(() => {
    if (battles.length === 0) return { minX: 0, maxX: 0, minZ: 0, maxZ: 0 };

    const minX = Math.min(...battles.map(b => b.x));
    const maxX = Math.max(...battles.map(b => b.x));
    const minZ = Math.min(...battles.map(b => b.z));
    const maxZ = Math.max(...battles.map(b => b.z));

    return { minX, maxX, minZ, maxZ };
  }, [battles]);

  // World to screen coordinate conversion
  const worldToScreen = useCallback((worldX: number, worldZ: number, canvas: HTMLCanvasElement) => {
    const bounds = calculateBounds();
    const worldWidth = bounds.maxX - bounds.minX;
    const worldHeight = bounds.maxZ - bounds.minZ;

    // Normalize to 0-1
    const normX = (worldX - bounds.minX) / worldWidth;
    const normZ = (worldZ - bounds.minZ) / worldHeight;

    // Apply viewport transformations
    const centerX = canvas.width / 2;
    const centerY = canvas.height / 2;

    const x = centerX + (normX - 0.5) * canvas.width * viewport.scale + viewport.offsetX;
    const y = centerY + (normZ - 0.5) * canvas.height * viewport.scale + viewport.offsetY;

    return { x, y };
  }, [calculateBounds, viewport]);

  // Screen to world coordinate conversion (for future features like distance measurement)
  // const screenToWorld = useCallback((screenX: number, screenY: number, canvas: HTMLCanvasElement) => {
  //   const bounds = calculateBounds();
  //   const worldWidth = bounds.maxX - bounds.minX;
  //   const worldHeight = bounds.maxZ - bounds.minZ;

  //   const centerX = canvas.width / 2;
  //   const centerY = canvas.height / 2;

  //   const normX = ((screenX - centerX - viewport.offsetX) / (canvas.width * viewport.scale)) + 0.5;
  //   const normZ = ((screenY - centerY - viewport.offsetY) / (canvas.height * viewport.scale)) + 0.5;

  //   const worldX = bounds.minX + normX * worldWidth;
  //   const worldZ = bounds.minZ + normZ * worldHeight;

  //   return { worldX, worldZ };
  // }, [calculateBounds, viewport]);

  // Draw the map
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || battles.length === 0) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // Set canvas size
    canvas.width = canvas.offsetWidth * window.devicePixelRatio;
    canvas.height = canvas.offsetHeight * window.devicePixelRatio;
    ctx.scale(window.devicePixelRatio, window.devicePixelRatio);

    // Clear canvas
    ctx.fillStyle = '#0d1117';
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    // Only draw battles (no background systems for performance)
    battles.forEach(battle => {
      const { x, y } = worldToScreen(battle.x, battle.z, canvas);

      // Size based on kills (min 5, max 25)
      const size = Math.min(Math.max(battle.total_kills / 20, 5), 25);

      // Color based on intensity
      let color = '#3fb950'; // low
      if (battle.intensity === 'moderate') color = '#58a6ff';
      else if (battle.intensity === 'high') color = '#d29922';
      else if (battle.intensity === 'extreme') color = '#f85149';

      // Draw glow
      const gradient = ctx.createRadialGradient(x, y, 0, x, y, size + 5);
      gradient.addColorStop(0, color);
      gradient.addColorStop(1, 'rgba(0,0,0,0)');
      ctx.fillStyle = gradient;
      ctx.beginPath();
      ctx.arc(x, y, size + 5, 0, Math.PI * 2);
      ctx.fill();

      // Draw main circle
      ctx.fillStyle = color;
      ctx.beginPath();
      ctx.arc(x, y, size, 0, Math.PI * 2);
      ctx.fill();

      // Draw border
      ctx.strokeStyle = '#fff';
      ctx.lineWidth = 1;
      ctx.stroke();
    });
  }, [systems, battles, viewport, worldToScreen]);

  // Mouse move handler for tooltips
  const handleMouseMove = useCallback((e: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const rect = canvas.getBoundingClientRect();
    const mouseX = e.clientX - rect.left;
    const mouseY = e.clientY - rect.top;

    // Check if hovering over any battle
    let hoveredBattle: ActiveBattle | null = null;

    for (const battle of battles) {
      const { x, y } = worldToScreen(battle.x, battle.z, canvas);
      const size = Math.min(Math.max(battle.total_kills / 20, 5), 25);

      const distance = Math.sqrt((mouseX - x) ** 2 + (mouseY - y) ** 2);
      if (distance <= size) {
        hoveredBattle = battle;
        break;
      }
    }

    if (hoveredBattle) {
      setTooltip({
        visible: true,
        x: e.clientX,
        y: e.clientY,
        battle: hoveredBattle
      });
      canvas.style.cursor = 'pointer';
    } else {
      setTooltip({ visible: false, x: 0, y: 0, battle: null });
      canvas.style.cursor = isDragging ? 'grabbing' : 'grab';
    }
  }, [battles, worldToScreen, isDragging]);

  // Mouse click handler
  const handleClick = useCallback((_e: React.MouseEvent<HTMLCanvasElement>) => {
    if (tooltip.visible && tooltip.battle) {
      navigate(`/battle/${tooltip.battle.battle_id}`);
    }
  }, [tooltip, navigate]);

  // Mouse wheel handler for zoom
  const handleWheel = useCallback((e: React.WheelEvent<HTMLCanvasElement>) => {
    e.preventDefault();
    const zoomFactor = e.deltaY > 0 ? 0.9 : 1.1;
    setViewport(prev => ({
      ...prev,
      scale: Math.min(Math.max(prev.scale * zoomFactor, 0.5), 5)
    }));
  }, []);

  // Pan handlers
  const handleMouseDown = useCallback((e: React.MouseEvent<HTMLCanvasElement>) => {
    if (tooltip.visible) return; // Don't pan when clicking on a battle
    setIsDragging(true);
    setDragStart({ x: e.clientX - viewport.offsetX, y: e.clientY - viewport.offsetY });
    if (canvasRef.current) {
      canvasRef.current.style.cursor = 'grabbing';
    }
  }, [viewport, tooltip]);

  const handleMouseUp = useCallback(() => {
    setIsDragging(false);
    if (canvasRef.current && !tooltip.visible) {
      canvasRef.current.style.cursor = 'grab';
    }
  }, [tooltip]);

  const handleMouseMoveGlobal = useCallback((e: React.MouseEvent<HTMLCanvasElement>) => {
    if (isDragging) {
      setViewport(prev => ({
        ...prev,
        offsetX: e.clientX - dragStart.x,
        offsetY: e.clientY - dragStart.y
      }));
    }
    handleMouseMove(e);
  }, [isDragging, dragStart, handleMouseMove]);

  // Reset view button
  const resetView = () => {
    setViewport({ offsetX: 0, offsetY: 0, scale: 1 });
  };

  if (loading) {
    return (
      <div style={{ height: 'calc(100vh - 120px)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <div>
          <div className="skeleton" style={{ height: '40px', width: '300px', marginBottom: '1rem' }} />
          <div className="skeleton" style={{ height: '600px', width: '100%' }} />
        </div>
      </div>
    );
  }

  return (
    <div>
      {/* Header Card */}
      <div className="card" style={{ marginBottom: '1.5rem' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '1rem' }}>
          <div>
            <h1>🗺️ EVE Battle Map</h1>
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.875rem', marginTop: '0.5rem' }}>
              {mapView === 'ectmap'
                ? 'Complete EVE Online universe map with all systems, regions, and routes'
                : `Fast 2D Canvas visualization of ${battles.length} active battles across New Eden`}
            </p>
          </div>

          {/* View Toggle */}
          <div style={{ display: 'flex', gap: '0.5rem', background: 'var(--bg-primary)', padding: '0.25rem', borderRadius: '6px', border: '1px solid var(--border-color)' }}>
            <button
              onClick={() => setMapView('ectmap')}
              style={{
                padding: '0.5rem 1rem',
                background: mapView === 'ectmap' ? 'var(--accent-blue)' : 'transparent',
                color: mapView === 'ectmap' ? 'white' : 'var(--text-primary)',
                border: 'none',
                borderRadius: '4px',
                cursor: 'pointer',
                fontWeight: mapView === 'ectmap' ? 600 : 400,
                fontSize: '0.875rem',
                transition: 'all 0.2s',
              }}
            >
              🗺️ Full Map
            </button>
            <button
              onClick={() => setMapView('battles')}
              style={{
                padding: '0.5rem 1rem',
                background: mapView === 'battles' ? 'var(--accent-blue)' : 'transparent',
                color: mapView === 'battles' ? 'white' : 'var(--text-primary)',
                border: 'none',
                borderRadius: '4px',
                cursor: 'pointer',
                fontWeight: mapView === 'battles' ? 600 : 400,
                fontSize: '0.875rem',
                transition: 'all 0.2s',
              }}
            >
              ⚔️ Battles Only
            </button>
          </div>
        </div>

        {mapView === 'battles' && (
          <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap', alignItems: 'center' }}>
            <button
              onClick={resetView}
              style={{
                padding: '0.5rem 1rem',
                background: 'var(--bg-elevated)',
                border: '1px solid var(--border-color)',
                borderRadius: '6px',
                color: 'var(--text-primary)',
                cursor: 'pointer',
                fontSize: '0.875rem'
              }}
            >
              🎯 Reset View
            </button>
            <div style={{ fontSize: '0.875rem', color: 'var(--text-secondary)' }}>
              Zoom: {(viewport.scale * 100).toFixed(0)}%
            </div>
            <div style={{ fontSize: '0.875rem', color: 'var(--text-secondary)' }}>
              💡 Scroll to zoom • Drag to pan • Click battles for details
            </div>
          </div>
        )}
      </div>

      {/* Map Display - Conditional */}
      <div className="card" style={{ padding: 0, position: 'relative', overflow: 'hidden' }}>
        {mapView === 'ectmap' ? (
          <iframe
            src="http://localhost:3001"
            style={{
              width: '100%',
              height: '700px',
              border: 'none',
              display: 'block'
            }}
            title="EVE Online Universe Map (ectmap)"
          />
        ) : (
          <canvas
            ref={canvasRef}
            onMouseMove={handleMouseMoveGlobal}
            onClick={handleClick}
            onWheel={handleWheel}
            onMouseDown={handleMouseDown}
            onMouseUp={handleMouseUp}
            onMouseLeave={handleMouseUp}
            style={{
              width: '100%',
              height: '700px',
              cursor: 'grab',
              display: 'block'
            }}
          />
        )}
      </div>

      {/* Tooltip */}
      {tooltip.visible && tooltip.battle && (
        <div
          style={{
            position: 'fixed',
            left: `${tooltip.x + 15}px`,
            top: `${tooltip.y + 15}px`,
            background: 'var(--bg-elevated)',
            border: '1px solid var(--border-color)',
            borderRadius: '8px',
            padding: '1rem',
            boxShadow: '0 4px 12px rgba(0,0,0,0.3)',
            pointerEvents: 'none',
            zIndex: 1000,
            minWidth: '250px'
          }}
        >
          <div style={{ fontSize: '1rem', fontWeight: 600, marginBottom: '0.5rem', color: 'var(--text-primary)' }}>
            ⚔️ {tooltip.battle.system_name}
          </div>
          <div style={{ fontSize: '0.875rem', color: 'var(--text-secondary)', marginBottom: '0.75rem' }}>
            {tooltip.battle.region_name} • {tooltip.battle.security.toFixed(1)} sec
          </div>

          <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '0.75rem' }}>
            <div
              style={{
                padding: '0.25rem 0.5rem',
                borderRadius: '4px',
                fontSize: '0.75rem',
                fontWeight: 600,
                background: tooltip.battle.intensity === 'extreme' ? 'var(--danger)' :
                            tooltip.battle.intensity === 'high' ? 'var(--warning)' :
                            tooltip.battle.intensity === 'moderate' ? 'var(--accent-blue)' :
                            'var(--success)',
                color: '#fff'
              }}
            >
              {tooltip.battle.intensity.toUpperCase()} INTENSITY
            </div>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.5rem', fontSize: '0.875rem' }}>
            <div>
              <div style={{ color: 'var(--text-secondary)' }}>Kills</div>
              <div style={{ color: 'var(--text-primary)', fontWeight: 600 }}>
                {tooltip.battle.total_kills}
              </div>
            </div>
            <div>
              <div style={{ color: 'var(--text-secondary)' }}>ISK Lost</div>
              <div style={{ color: 'var(--text-primary)', fontWeight: 600 }}>
                {(tooltip.battle.total_isk_destroyed / 1_000_000_000).toFixed(1)}B
              </div>
            </div>
            <div>
              <div style={{ color: 'var(--text-secondary)' }}>Duration</div>
              <div style={{ color: 'var(--text-primary)', fontWeight: 600 }}>
                {Math.floor(tooltip.battle.duration_minutes / 60)}h {tooltip.battle.duration_minutes % 60}m
              </div>
            </div>
          </div>

          <div style={{ marginTop: '0.75rem', fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
            Click for details →
          </div>
        </div>
      )}

      {/* Legend */}
      <div className="card" style={{ marginTop: '1.5rem' }}>
        <h3 style={{ fontSize: '1rem', marginBottom: '1rem' }}>📖 Legend</h3>
        <div>
          <div style={{ fontSize: '0.875rem', fontWeight: 600, marginBottom: '0.5rem' }}>Battle Intensity & Size</div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem', fontSize: '0.75rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <div style={{ width: '12px', height: '12px', borderRadius: '50%', background: '#f85149' }} />
                <span>Extreme (100+ kills)</span>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <div style={{ width: '12px', height: '12px', borderRadius: '50%', background: '#d29922' }} />
                <span>High (50+ kills)</span>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <div style={{ width: '12px', height: '12px', borderRadius: '50%', background: '#58a6ff' }} />
                <span>Moderate (10+ kills)</span>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <div style={{ width: '12px', height: '12px', borderRadius: '50%', background: '#3fb950' }} />
                <span>Low (&lt;10 kills)</span>
              </div>
              <div style={{ marginTop: '0.5rem', color: 'var(--text-secondary)', fontSize: '0.75rem' }}>
                💡 Circle size = kill count • Larger = more kills
              </div>
            </div>
        </div>
      </div>
    </div>
  );
}
