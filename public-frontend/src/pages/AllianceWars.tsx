import { useState, useEffect } from 'react';
import { reportsApi } from '../services/api';
import { RefreshIndicator } from '../components/RefreshIndicator';
import { useAutoRefresh } from '../hooks/useAutoRefresh';
import type { AllianceWars as AllianceWarsType } from '../types/reports';

export function AllianceWars() {
  const [report, setReport] = useState<AllianceWarsType | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState(new Date());

  const fetchReport = async () => {
    try {
      setError(null);
      const data = await reportsApi.getAllianceWars();
      setReport(data);
      setLastUpdated(new Date());
      setLoading(false);
    } catch (err) {
      setError('Failed to load alliance wars report');
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
          <h1>⚔️ Alliance Wars & Conflicts</h1>
          <p style={{ color: 'var(--text-secondary)' }}>Active alliance conflicts and combat statistics</p>
        </div>
        <RefreshIndicator lastUpdated={lastUpdated} autoRefreshSeconds={60} />
      </div>

      {/* Global Summary */}
      <div className="card card-elevated">
        <h2>Global Summary</h2>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', gap: '2rem', marginTop: '1.5rem' }}>
          <div>
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.875rem' }}>Active Conflicts</p>
            <p style={{ fontSize: '2.5rem', fontWeight: 700, color: 'var(--danger)' }}>
              {report.global.active_conflicts}
            </p>
          </div>
          <div>
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.875rem' }}>Total Combatants</p>
            <p style={{ fontSize: '2.5rem', fontWeight: 700, color: 'var(--accent-blue)' }}>
              {report.global.total_alliances_involved}
            </p>
          </div>
          <div>
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.875rem' }}>Total Kills</p>
            <p style={{ fontSize: '2.5rem', fontWeight: 700, color: 'var(--warning)' }}>
              {report.global.total_kills.toLocaleString()}
            </p>
          </div>
          <div>
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.875rem' }}>Total ISK Destroyed</p>
            <p style={{ fontSize: '2.5rem', fontWeight: 700, color: 'var(--success)' }}>
              {(report.global.total_isk_destroyed / 1_000_000_000).toFixed(2)}B
            </p>
          </div>
        </div>
      </div>

      {/* Active Conflicts - Full List */}
      <div className="card" style={{ marginTop: '1.5rem' }}>
        <h2>Active Conflicts</h2>
        <p style={{ color: 'var(--text-secondary)', marginBottom: '1.5rem' }}>
          Ongoing alliance wars ranked by intensity and strategic significance
        </p>

        {report.conflicts.map((conflict) => (
          <div
            key={`${conflict.alliance_1_id}-${conflict.alliance_2_id}`}
            className="card"
            style={{
              marginBottom: '1.5rem',
              background: 'var(--bg-elevated)',
              border: '1px solid var(--border-color)'
            }}
          >
            {/* Conflict Header */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
              <div>
                <h3 style={{ fontSize: '1.25rem', marginBottom: '0.5rem' }}>
                  <span style={{ color: 'var(--accent-blue)' }}>{conflict.alliance_1_name}</span>
                  {' vs '}
                  <span style={{ color: 'var(--danger)' }}>{conflict.alliance_2_name}</span>
                </h3>
                <div style={{ display: 'flex', gap: '1rem', fontSize: '0.875rem', color: 'var(--text-secondary)' }}>
                  <span>
                    {conflict.primary_regions.join(', ')}
                  </span>
                  <span>•</span>
                  <span>
                    {conflict.duration_days} days
                  </span>
                </div>
              </div>
              {conflict.winner && (
                <div style={{ textAlign: 'right' }}>
                  <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>Winner</p>
                  <p style={{ fontSize: '1.125rem', fontWeight: 600, color: 'var(--success)' }}>
                    {conflict.winner}
                  </p>
                </div>
              )}
            </div>

            {/* Combat Statistics */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1.5rem', marginTop: '1rem' }}>
              <div>
                <h4 style={{ fontSize: '0.875rem', color: 'var(--text-secondary)', marginBottom: '0.5rem' }}>
                  {conflict.alliance_1_name} Stats
                </h4>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span style={{ fontSize: '0.875rem', color: 'var(--text-secondary)' }}>Kills:</span>
                    <span style={{ fontSize: '0.875rem', fontWeight: 600, color: 'var(--success)' }}>
                      {conflict.alliance_1_kills.toLocaleString()}
                    </span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span style={{ fontSize: '0.875rem', color: 'var(--text-secondary)' }}>Losses:</span>
                    <span style={{ fontSize: '0.875rem', fontWeight: 600, color: 'var(--danger)' }}>
                      {conflict.alliance_1_losses.toLocaleString()}
                    </span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span style={{ fontSize: '0.875rem', color: 'var(--text-secondary)' }}>ISK Destroyed:</span>
                    <span style={{ fontSize: '0.875rem', fontWeight: 600, fontFamily: 'monospace' }}>
                      {(conflict.alliance_1_isk_destroyed / 1_000_000_000).toFixed(2)}B
                    </span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span style={{ fontSize: '0.875rem', color: 'var(--text-secondary)' }}>ISK Lost:</span>
                    <span style={{ fontSize: '0.875rem', fontWeight: 600, fontFamily: 'monospace' }}>
                      {(conflict.alliance_1_isk_lost / 1_000_000_000).toFixed(2)}B
                    </span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '0.5rem', paddingTop: '0.5rem', borderTop: '1px solid var(--border-color)' }}>
                    <span style={{ fontSize: '0.875rem', fontWeight: 600 }}>ISK Efficiency:</span>
                    <span style={{ fontSize: '0.875rem', fontWeight: 700, color: conflict.alliance_1_efficiency >= 50 ? 'var(--success)' : 'var(--danger)' }}>
                      {conflict.alliance_1_efficiency.toFixed(1)}%
                    </span>
                  </div>
                </div>
              </div>

              <div>
                <h4 style={{ fontSize: '0.875rem', color: 'var(--text-secondary)', marginBottom: '0.5rem' }}>
                  {conflict.alliance_2_name} Stats
                </h4>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span style={{ fontSize: '0.875rem', color: 'var(--text-secondary)' }}>Kills:</span>
                    <span style={{ fontSize: '0.875rem', fontWeight: 600, color: 'var(--success)' }}>
                      {conflict.alliance_2_kills.toLocaleString()}
                    </span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span style={{ fontSize: '0.875rem', color: 'var(--text-secondary)' }}>Losses:</span>
                    <span style={{ fontSize: '0.875rem', fontWeight: 600, color: 'var(--danger)' }}>
                      {conflict.alliance_2_losses.toLocaleString()}
                    </span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span style={{ fontSize: '0.875rem', color: 'var(--text-secondary)' }}>ISK Destroyed:</span>
                    <span style={{ fontSize: '0.875rem', fontWeight: 600, fontFamily: 'monospace' }}>
                      {(conflict.alliance_2_isk_destroyed / 1_000_000_000).toFixed(2)}B
                    </span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span style={{ fontSize: '0.875rem', color: 'var(--text-secondary)' }}>ISK Lost:</span>
                    <span style={{ fontSize: '0.875rem', fontWeight: 600, fontFamily: 'monospace' }}>
                      {(conflict.alliance_2_isk_lost / 1_000_000_000).toFixed(2)}B
                    </span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '0.5rem', paddingTop: '0.5rem', borderTop: '1px solid var(--border-color)' }}>
                    <span style={{ fontSize: '0.875rem', fontWeight: 600 }}>ISK Efficiency:</span>
                    <span style={{ fontSize: '0.875rem', fontWeight: 700, color: conflict.alliance_2_efficiency >= 50 ? 'var(--success)' : 'var(--danger)' }}>
                      {conflict.alliance_2_efficiency.toFixed(1)}%
                    </span>
                  </div>
                </div>
              </div>

              <div>
                <h4 style={{ fontSize: '0.875rem', color: 'var(--text-secondary)', marginBottom: '0.5rem' }}>
                  Most Active Systems
                </h4>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
                  {conflict.active_systems.slice(0, 5).map((system) => (
                    <div key={system.system_id} style={{ display: 'flex', justifyContent: 'space-between' }}>
                      <span style={{ fontSize: '0.875rem' }}>{system.system_name}</span>
                      <span style={{ fontSize: '0.875rem', fontWeight: 600, color: 'var(--accent-blue)' }}>
                        {system.kills}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Strategic Analysis */}
      {report.strategic_hotspots && report.strategic_hotspots.length > 0 && (
        <div className="card" style={{ marginTop: '1.5rem' }}>
          <h2>Strategic Hotspots</h2>
          <p style={{ color: 'var(--text-secondary)', marginBottom: '1rem' }}>
            Systems with high strategic value and ongoing contest
          </p>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '1rem' }}>
            {report.strategic_hotspots.map((hotspot) => (
              <div
                key={hotspot.system_id}
                style={{
                  padding: '1rem',
                  background: 'var(--bg-elevated)',
                  borderRadius: '8px',
                  border: '1px solid var(--border-color)'
                }}
              >
                <h3 style={{ fontSize: '1.125rem', marginBottom: '0.5rem', color: 'var(--warning)' }}>
                  {hotspot.system_name}
                </h3>
                <div style={{ fontSize: '0.875rem', color: 'var(--text-secondary)' }}>
                  {hotspot.region_name}
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '1rem' }}>
                  <div>
                    <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>Kills (24h)</p>
                    <p style={{ fontSize: '1.25rem', fontWeight: 600, color: 'var(--accent-blue)' }}>
                      {hotspot.kills_24h}
                    </p>
                  </div>
                  <div style={{ textAlign: 'right' }}>
                    <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>Strategic Value</p>
                    <p style={{ fontSize: '1.25rem', fontWeight: 600, color: 'var(--success)' }}>
                      {hotspot.strategic_value.toFixed(1)}
                    </p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
