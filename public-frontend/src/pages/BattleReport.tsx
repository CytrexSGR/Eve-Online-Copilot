import { useState, useEffect } from 'react';
import { reportsApi } from '../services/api';
import { RefreshIndicator } from '../components/RefreshIndicator';
import { useAutoRefresh } from '../hooks/useAutoRefresh';
import type { BattleReport as BattleReportType } from '../types/reports';

export function BattleReport() {
  const [report, setReport] = useState<BattleReportType | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState(new Date());
  const [expandedRegions, setExpandedRegions] = useState<Set<number>>(new Set());

  const toggleRegion = (regionId: number) => {
    setExpandedRegions(prev => {
      const next = new Set(prev);
      if (next.has(regionId)) {
        next.delete(regionId);
      } else {
        next.add(regionId);
      }
      return next;
    });
  };

  const fetchReport = async () => {
    try {
      setError(null);
      const data = await reportsApi.getBattleReport();
      setReport(data);
      setLastUpdated(new Date());
      setLoading(false);
    } catch (err) {
      setError('Failed to load battle report');
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchReport();
  }, []);

  useAutoRefresh(fetchReport, 60);

  if (loading) return <div className="skeleton" style={{ height: '500px' }} />;
  if (error) return <div className="card" style={{ background: 'var(--danger)', color: 'white' }}>{error}</div>;
  if (!report) return null;

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2rem' }}>
        <div>
          <h1>⚔️ 24-Hour Battle Report</h1>
          <p style={{ color: 'var(--text-secondary)' }}>Complete combat statistics for the last 24 hours</p>
        </div>
        <RefreshIndicator lastUpdated={lastUpdated} autoRefreshSeconds={60} />
      </div>

      {/* Global Summary */}
      <div className="card card-elevated">
        <h2>Global Summary</h2>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', gap: '2rem', marginTop: '1.5rem' }}>
          <div>
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.875rem' }}>Total Kills</p>
            <p style={{ fontSize: '2.5rem', fontWeight: 700, color: 'var(--accent-blue)' }}>
              {report.global.total_kills.toLocaleString()}
            </p>
          </div>
          <div>
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.875rem' }}>Total ISK Destroyed</p>
            <p style={{ fontSize: '2.5rem', fontWeight: 700, color: 'var(--danger)' }}>
              {(report.global.total_isk_destroyed / 1_000_000_000).toFixed(2)}B ISK
            </p>
          </div>
          <div>
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.875rem' }}>Most Active Region</p>
            <p style={{ fontSize: '1.5rem', fontWeight: 600, color: 'var(--warning)' }}>
              {report.global.most_active_region}
            </p>
          </div>
          <div>
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.875rem' }}>Most Expensive Region</p>
            <p style={{ fontSize: '1.5rem', fontWeight: 600, color: 'var(--success)' }}>
              {report.global.most_expensive_region}
            </p>
          </div>
        </div>
      </div>

      {/* Regional Breakdown */}
      {report.regions.map((region) => {
        const isExpanded = expandedRegions.has(region.region_id);

        return (
          <div
            key={region.region_id}
            className="card"
            style={{
              marginTop: '1.5rem',
              border: isExpanded ? '2px solid var(--accent-blue)' : '1px solid var(--border-color)'
            }}
          >
            {/* Region Header - Always Visible */}
            <div
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                padding: '1rem',
                cursor: 'pointer',
                background: isExpanded ? 'var(--bg-elevated)' : 'transparent',
                borderRadius: '4px'
              }}
              onClick={() => toggleRegion(region.region_id)}
            >
              <div style={{ flex: 1 }}>
                <h2 style={{ marginBottom: '0.5rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  <span style={{ fontSize: '1.5rem' }}>{isExpanded ? '▼' : '▶'}</span>
                  {region.region_name}
                </h2>
                <div style={{ display: 'flex', gap: '2rem', fontSize: '0.875rem', color: 'var(--text-secondary)' }}>
                  <span>{region.kills.toLocaleString()} kills</span>
                  <span>•</span>
                  <span>{(region.total_isk_destroyed / 1_000_000_000).toFixed(2)}B ISK destroyed</span>
                  <span>•</span>
                  <span>{region.top_systems.length} systems</span>
                  <span>•</span>
                  <span>{region.top_ships.length} ship types</span>
                </div>
              </div>
              <div style={{ textAlign: 'right', paddingRight: '1rem' }}>
                <div style={{
                  padding: '0.5rem 1rem',
                  background: 'var(--accent-blue)',
                  borderRadius: '4px',
                  fontSize: '0.875rem',
                  fontWeight: 600,
                  color: 'white'
                }}>
                  {isExpanded ? 'Click to collapse' : 'Click for details'}
                </div>
              </div>
            </div>

            {/* Expanded Details */}
            {isExpanded && (
              <div style={{ padding: '2rem 1rem 1rem 1rem', borderTop: '1px solid var(--border-color)' }}>
                {/* Statistics Grid */}
                <div style={{
                  display: 'grid',
                  gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
                  gap: '1.5rem',
                  marginBottom: '2rem',
                  padding: '1.5rem',
                  background: 'var(--bg-elevated)',
                  borderRadius: '8px'
                }}>
                  <div>
                    <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginBottom: '0.25rem' }}>Total Kills</p>
                    <p style={{ fontSize: '1.75rem', fontWeight: 700, color: 'var(--accent-blue)' }}>
                      {region.kills.toLocaleString()}
                    </p>
                  </div>
                  <div>
                    <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginBottom: '0.25rem' }}>ISK Destroyed</p>
                    <p style={{ fontSize: '1.75rem', fontWeight: 700, color: 'var(--danger)' }}>
                      {(region.total_isk_destroyed / 1_000_000_000).toFixed(2)}B
                    </p>
                  </div>
                  <div>
                    <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginBottom: '0.25rem' }}>Avg Kill Value</p>
                    <p style={{ fontSize: '1.75rem', fontWeight: 700, color: 'var(--success)' }}>
                      {(region.avg_kill_value / 1_000_000).toFixed(1)}M
                    </p>
                  </div>
                  <div>
                    <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginBottom: '0.25rem' }}>Active Systems</p>
                    <p style={{ fontSize: '1.75rem', fontWeight: 700, color: 'var(--warning)' }}>
                      {region.top_systems.length}
                    </p>
                  </div>
                </div>

                {/* Detailed Tables */}
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(350px, 1fr))', gap: '2rem' }}>
                  {/* All Systems - Complete List */}
                  <div>
                    <h3 style={{ fontSize: '1.25rem', marginBottom: '1rem', color: 'var(--accent-blue)', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                      🌍 All Combat Systems ({region.top_systems.length})
                    </h3>
                    <div style={{
                      maxHeight: '400px',
                      overflowY: 'auto',
                      border: '1px solid var(--border-color)',
                      borderRadius: '4px'
                    }}>
                      {region.top_systems.map((system, idx) => (
                        <div
                          key={system.system_id}
                          style={{
                            display: 'flex',
                            justifyContent: 'space-between',
                            padding: '0.75rem',
                            background: idx % 2 === 0 ? 'var(--bg-elevated)' : 'transparent',
                            borderBottom: idx < region.top_systems.length - 1 ? '1px solid var(--border-color)' : 'none'
                          }}
                        >
                          <span style={{ fontWeight: 500 }}>
                            <span style={{ color: 'var(--text-secondary)', fontSize: '0.875rem', marginRight: '0.5rem' }}>
                              #{idx + 1}
                            </span>
                            {system.system_name}
                          </span>
                          <span style={{ color: 'var(--accent-blue)', fontWeight: 700 }}>
                            {system.kills} kills
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* All Ships - Complete List */}
                  <div>
                    <h3 style={{ fontSize: '1.25rem', marginBottom: '1rem', color: 'var(--danger)', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                      🚀 All Ships Destroyed ({region.top_ships.length})
                    </h3>
                    <div style={{
                      maxHeight: '400px',
                      overflowY: 'auto',
                      border: '1px solid var(--border-color)',
                      borderRadius: '4px'
                    }}>
                      {region.top_ships.map((ship, idx) => (
                        <div
                          key={ship.ship_type_id}
                          style={{
                            display: 'flex',
                            justifyContent: 'space-between',
                            padding: '0.75rem',
                            background: idx % 2 === 0 ? 'var(--bg-elevated)' : 'transparent',
                            borderBottom: idx < region.top_ships.length - 1 ? '1px solid var(--border-color)' : 'none'
                          }}
                        >
                          <span style={{ fontWeight: 500 }}>
                            <span style={{ color: 'var(--text-secondary)', fontSize: '0.875rem', marginRight: '0.5rem' }}>
                              #{idx + 1}
                            </span>
                            {ship.ship_name}
                          </span>
                          <span style={{ color: 'var(--danger)', fontWeight: 700 }}>
                            {ship.losses}x destroyed
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* All Destroyed Items - Complete List */}
                  <div>
                    <h3 style={{ fontSize: '1.25rem', marginBottom: '1rem', color: 'var(--warning)', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                      💎 All Destroyed Items ({region.top_destroyed_items.length})
                    </h3>
                    <div style={{
                      maxHeight: '400px',
                      overflowY: 'auto',
                      border: '1px solid var(--border-color)',
                      borderRadius: '4px'
                    }}>
                      {region.top_destroyed_items.map((item, idx) => (
                        <div
                          key={item.item_type_id}
                          style={{
                            display: 'flex',
                            justifyContent: 'space-between',
                            padding: '0.75rem',
                            background: idx % 2 === 0 ? 'var(--bg-elevated)' : 'transparent',
                            borderBottom: idx < region.top_destroyed_items.length - 1 ? '1px solid var(--border-color)' : 'none'
                          }}
                        >
                          <span style={{ fontSize: '0.9rem', fontWeight: 500 }}>
                            <span style={{ color: 'var(--text-secondary)', fontSize: '0.875rem', marginRight: '0.5rem' }}>
                              #{idx + 1}
                            </span>
                            {item.item_name}
                          </span>
                          <span style={{ color: 'var(--warning)', fontWeight: 700 }}>
                            {item.quantity_destroyed.toLocaleString()}x
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
