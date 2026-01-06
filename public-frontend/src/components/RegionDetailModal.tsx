interface RegionDetailModalProps {
  region: {
    region_id: number;
    region_name: string;
    kills: number;
    total_isk_destroyed: number;
    top_systems: Array<{ system_id: number; system_name: string; kills: number }>;
    top_ships: Array<{ ship_type_id: number; ship_name: string; losses: number }>;
    top_destroyed_items: Array<{ item_type_id: number; item_name: string; quantity_destroyed: number }>;
  };
  onClose: () => void;
}

export function RegionDetailModal({ region, onClose }: RegionDetailModalProps) {
  return (
    <div
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        background: 'rgba(0, 0, 0, 0.9)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 1000,
        padding: '2rem'
      }}
      onClick={onClose}
    >
      <div
        className="card"
        style={{
          maxWidth: '1200px',
          maxHeight: '90vh',
          overflow: 'auto',
          width: '100%'
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2rem', position: 'sticky', top: 0, background: 'var(--bg-secondary)', paddingBottom: '1rem', zIndex: 10 }}>
          <div>
            <h2 style={{ fontSize: '1.75rem', marginBottom: '0.5rem' }}>
              {region.region_name} - Detailed Analysis
            </h2>
            <div style={{ display: 'flex', gap: '2rem', fontSize: '0.875rem', color: 'var(--text-secondary)' }}>
              <span>{region.kills.toLocaleString()} kills</span>
              <span>•</span>
              <span>{(region.total_isk_destroyed / 1_000_000_000).toFixed(2)}B ISK destroyed</span>
            </div>
          </div>
          <button
            onClick={onClose}
            style={{
              background: 'var(--danger)',
              border: 'none',
              color: 'white',
              padding: '0.75rem 1.5rem',
              borderRadius: '4px',
              cursor: 'pointer',
              fontSize: '1rem',
              fontWeight: 600
            }}
          >
            ✕ Close
          </button>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(350px, 1fr))', gap: '2rem' }}>
          {/* All Systems */}
          <div>
            <h3 style={{ fontSize: '1.25rem', marginBottom: '1rem', color: 'var(--accent-blue)' }}>
              🌍 All Systems ({region.top_systems.length})
            </h3>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
              {region.top_systems.map((system, idx) => (
                <div
                  key={system.system_id}
                  style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    padding: '0.75rem',
                    background: idx % 2 === 0 ? 'var(--bg-elevated)' : 'transparent',
                    borderRadius: '4px'
                  }}
                >
                  <span style={{ fontWeight: 500 }}>{system.system_name}</span>
                  <span style={{ color: 'var(--accent-blue)', fontWeight: 700 }}>
                    {system.kills} kills
                  </span>
                </div>
              ))}
            </div>
          </div>

          {/* All Ships Destroyed */}
          <div>
            <h3 style={{ fontSize: '1.25rem', marginBottom: '1rem', color: 'var(--danger)' }}>
              🚀 All Ships Destroyed ({region.top_ships.length})
            </h3>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
              {region.top_ships.map((ship, idx) => (
                <div
                  key={ship.ship_type_id}
                  style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    padding: '0.75rem',
                    background: idx % 2 === 0 ? 'var(--bg-elevated)' : 'transparent',
                    borderRadius: '4px'
                  }}
                >
                  <span style={{ fontWeight: 500 }}>{ship.ship_name}</span>
                  <span style={{ color: 'var(--danger)', fontWeight: 700 }}>
                    {ship.losses}x
                  </span>
                </div>
              ))}
            </div>
          </div>

          {/* All Destroyed Items */}
          <div>
            <h3 style={{ fontSize: '1.25rem', marginBottom: '1rem', color: 'var(--warning)' }}>
              💎 All Destroyed Items ({region.top_destroyed_items.length})
            </h3>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
              {region.top_destroyed_items.map((item, idx) => (
                <div
                  key={item.item_type_id}
                  style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    padding: '0.75rem',
                    background: idx % 2 === 0 ? 'var(--bg-elevated)' : 'transparent',
                    borderRadius: '4px'
                  }}
                >
                  <span style={{ fontSize: '0.9rem', fontWeight: 500 }}>{item.item_name}</span>
                  <span style={{ color: 'var(--warning)', fontWeight: 700 }}>
                    {item.quantity_destroyed.toLocaleString()}x
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
