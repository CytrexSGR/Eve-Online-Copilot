/**
 * Battle Map Page
 * Shows the ectmap with live battle overlay
 */
export function BattleMap2D() {
  return (
    <div>
      {/* Header Card */}
      <div className="card" style={{ marginBottom: '1.5rem' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '1rem' }}>
          <div>
            <h1>🗺️ EVE Battle Map</h1>
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.875rem', marginTop: '0.5rem' }}>
              Complete EVE Online universe map with live battle tracking
            </p>
          </div>
        </div>

        <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap', alignItems: 'center' }}>
          <div style={{ fontSize: '0.875rem', color: 'var(--text-secondary)' }}>
            💡 Battle layer controls are in the bottom-right corner of the map
          </div>
        </div>
      </div>

      {/* ectmap iframe */}
      <div className="card" style={{ padding: 0, position: 'relative', overflow: 'hidden' }}>
        <iframe
          src="/ectmap"
          style={{
            width: '100%',
            height: '700px',
            border: 'none',
            display: 'block'
          }}
          title="EVE Online Universe Map (ectmap)"
        />
      </div>

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
