import { Truck } from 'lucide-react';
import type { TransportOptions } from '../../../types/shopping';

interface TransportViewProps {
  transportOptions: TransportOptions | undefined;
  isLoading: boolean;
  safeRoutesOnly: boolean;
  setSafeRoutesOnly: (value: boolean) => void;
  transportFilter: string;
  setTransportFilter: (value: string) => void;
}

/**
 * Transport planning view with cargo capacity and ship options
 */
export function TransportView({
  transportOptions,
  isLoading,
  safeRoutesOnly,
  setSafeRoutesOnly,
  transportFilter,
  setTransportFilter,
}: TransportViewProps) {
  return (
    <div className="card">
      <div className="card-header">
        <span className="card-title">
          <Truck size={18} style={{ marginRight: 8 }} />
          Transport Options
        </span>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 13 }}>
            <input type="checkbox" checked={safeRoutesOnly} onChange={(e) => setSafeRoutesOnly(e.target.checked)} />
            Safe routes only
          </label>
        </div>
      </div>

      {isLoading ? (
        <div className="loading">
          <div className="spinner"></div>
          Calculating transport options...
        </div>
      ) : transportOptions?.options.length === 0 ? (
        <div style={{ padding: 20, textAlign: 'center' }}>
          <p className="neutral">{transportOptions?.message || 'No transport options available'}</p>
          <p style={{ fontSize: 12, marginTop: 8 }}>Run the capability sync to update available ships.</p>
        </div>
      ) : (
        <>
          {/* Summary Header */}
          <div
            style={{
              padding: '12px 16px',
              background: 'var(--bg-dark)',
              borderBottom: '1px solid var(--border-color)',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
            }}
          >
            <div>
              <strong>{transportOptions?.volume_formatted}</strong>
              <span className="neutral" style={{ marginLeft: 8 }}>
                {transportOptions?.route_summary}
              </span>
            </div>
            <div style={{ display: 'flex', gap: 4 }}>
              {['fewest_trips', 'fastest', 'lowest_risk'].map((filter) => (
                <button
                  key={filter}
                  className={`btn btn-small ${transportFilter === filter ? 'btn-primary' : 'btn-secondary'}`}
                  onClick={() => setTransportFilter(transportFilter === filter ? '' : filter)}
                  style={{ padding: '4px 8px', fontSize: 11 }}
                >
                  {filter === 'fewest_trips' ? 'Fewest Trips' : filter === 'fastest' ? 'Fastest' : 'Lowest Risk'}
                </button>
              ))}
            </div>
          </div>

          {/* Options List */}
          <div style={{ padding: 16, display: 'flex', flexDirection: 'column', gap: 12 }}>
            {transportOptions?.options.map((option, idx) => (
              <div
                key={option.id}
                style={{
                  padding: 16,
                  background: 'var(--bg-dark)',
                  borderRadius: 8,
                  border: idx === 0 ? '2px solid var(--accent-blue)' : '1px solid var(--border-color)',
                }}
              >
                {idx === 0 && (
                  <span className="badge badge-blue" style={{ marginBottom: 8, display: 'inline-block' }}>
                    RECOMMENDED
                  </span>
                )}

                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                  <div>
                    <div style={{ fontWeight: 600, marginBottom: 4 }}>
                      {option.characters[0]?.name} → {option.characters[0]?.ship_name}
                    </div>
                    <div className="neutral" style={{ fontSize: 12 }}>
                      {option.characters[0]?.ship_group} • {option.characters[0]?.ship_location}
                    </div>
                  </div>

                  <div style={{ textAlign: 'right' }}>
                    <span
                      className={
                        option.risk_score === 0 ? 'positive' : option.risk_score <= 2 ? 'neutral' : 'negative'
                      }
                    >
                      {option.risk_score === 0 ? '✅' : '⚠️'} {option.risk_label}
                    </span>
                  </div>
                </div>

                <div
                  style={{
                    display: 'grid',
                    gridTemplateColumns: 'repeat(4, 1fr)',
                    gap: 16,
                    marginTop: 12,
                    paddingTop: 12,
                    borderTop: '1px solid var(--border-color)',
                  }}
                >
                  <div>
                    <div className="neutral" style={{ fontSize: 11 }}>
                      Trips
                    </div>
                    <div style={{ fontWeight: 600 }}>{option.trips}</div>
                  </div>
                  <div>
                    <div className="neutral" style={{ fontSize: 11 }}>
                      Time
                    </div>
                    <div style={{ fontWeight: 600 }}>{option.flight_time_formatted}</div>
                  </div>
                  <div>
                    <div className="neutral" style={{ fontSize: 11 }}>
                      Capacity Used
                    </div>
                    <div style={{ fontWeight: 600 }}>{option.capacity_used_pct}%</div>
                  </div>
                  <div>
                    <div className="neutral" style={{ fontSize: 11 }}>
                      Ship Capacity
                    </div>
                    <div style={{ fontWeight: 600 }}>{(option.capacity_m3 / 1000).toFixed(0)}K m³</div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
