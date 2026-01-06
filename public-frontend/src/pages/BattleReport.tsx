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
      {report.regions.map((region) => (
        <div key={region.region_id} className="card" style={{ marginTop: '1.5rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
            <h2>{region.region_name}</h2>
            <div style={{ textAlign: 'right' }}>
              <p style={{ fontSize: '1.25rem', fontWeight: 600, color: 'var(--accent-blue)' }}>
                {region.kills} kills
              </p>
              <p style={{ fontSize: '0.875rem', color: 'var(--text-secondary)' }}>
                {(region.total_isk_destroyed / 1_000_000_000).toFixed(2)}B ISK destroyed
              </p>
            </div>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '2rem' }}>
            {/* Top Systems */}
            <div>
              <h3 style={{ fontSize: '1rem', marginBottom: '1rem', color: 'var(--text-secondary)' }}>
                🌍 Top Systems
              </h3>
              {region.top_systems.map((system, idx) => (
                <div
                  key={system.system_id}
                  style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    padding: '0.5rem',
                    background: idx % 2 === 0 ? 'var(--bg-elevated)' : 'transparent',
                    borderRadius: '4px',
                    marginBottom: '0.25rem'
                  }}
                >
                  <span>{system.system_name}</span>
                  <span style={{ color: 'var(--accent-blue)', fontWeight: 600 }}>
                    {system.kills} kills
                  </span>
                </div>
              ))}
            </div>

            {/* Top Ships */}
            <div>
              <h3 style={{ fontSize: '1rem', marginBottom: '1rem', color: 'var(--text-secondary)' }}>
                🚀 Top Ships Destroyed
              </h3>
              {region.top_ships.map((ship, idx) => (
                <div
                  key={ship.ship_type_id}
                  style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    padding: '0.5rem',
                    background: idx % 2 === 0 ? 'var(--bg-elevated)' : 'transparent',
                    borderRadius: '4px',
                    marginBottom: '0.25rem'
                  }}
                >
                  <span>{ship.ship_name}</span>
                  <span style={{ color: 'var(--danger)', fontWeight: 600 }}>
                    {ship.losses}
                  </span>
                </div>
              ))}
            </div>

            {/* Top Destroyed Items */}
            <div>
              <h3 style={{ fontSize: '1rem', marginBottom: '1rem', color: 'var(--text-secondary)' }}>
                💎 Top Destroyed Items
              </h3>
              {region.top_destroyed_items.map((item, idx) => (
                <div
                  key={item.item_type_id}
                  style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    padding: '0.5rem',
                    background: idx % 2 === 0 ? 'var(--bg-elevated)' : 'transparent',
                    borderRadius: '4px',
                    marginBottom: '0.25rem'
                  }}
                >
                  <span style={{ fontSize: '0.875rem' }}>{item.item_name}</span>
                  <span style={{ color: 'var(--warning)', fontWeight: 600, fontSize: '0.875rem' }}>
                    {item.quantity_destroyed}x
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
