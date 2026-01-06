import { useState, useEffect } from 'react';
import { reportsApi } from '../services/api';
import { RefreshIndicator } from '../components/RefreshIndicator';
import { useAutoRefresh } from '../hooks/useAutoRefresh';
import type { TradeRoutes as TradeRoutesType } from '../types/reports';

export function TradeRoutes() {
  const [report, setReport] = useState<TradeRoutesType | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState(new Date());

  const fetchReport = async () => {
    try {
      setError(null);
      const data = await reportsApi.getTradeRoutes();
      setReport(data);
      setLastUpdated(new Date());
      setLoading(false);
    } catch (err) {
      setError('Failed to load trade routes report');
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

  const getDangerColor = (score: number) => {
    if (score >= 8) return 'var(--danger)';
    if (score >= 5) return 'var(--warning)';
    return 'var(--success)';
  };

  const getDangerLabel = (score: number) => {
    if (score >= 8) return 'EXTREME';
    if (score >= 5) return 'HIGH';
    if (score >= 3) return 'MODERATE';
    return 'LOW';
  };

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2rem' }}>
        <div>
          <h1>🚚 Trade Route Safety Analysis</h1>
          <p style={{ color: 'var(--text-secondary)' }}>Combat danger assessment for major trade routes</p>
        </div>
        <RefreshIndicator lastUpdated={lastUpdated} autoRefreshSeconds={60} />
      </div>

      {/* Global Summary */}
      <div className="card card-elevated">
        <h2>Global Summary</h2>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', gap: '2rem', marginTop: '1.5rem' }}>
          <div>
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.875rem' }}>Total Routes Analyzed</p>
            <p style={{ fontSize: '2.5rem', fontWeight: 700, color: 'var(--accent-blue)' }}>
              {report.global.total_routes}
            </p>
          </div>
          <div>
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.875rem' }}>Dangerous Routes</p>
            <p style={{ fontSize: '2.5rem', fontWeight: 700, color: 'var(--danger)' }}>
              {report.global.dangerous_routes}
            </p>
          </div>
          <div>
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.875rem' }}>Average Danger Score</p>
            <p style={{ fontSize: '2.5rem', fontWeight: 700, color: getDangerColor(report.global.avg_danger_score) }}>
              {report.global.avg_danger_score.toFixed(1)}/10
            </p>
          </div>
          <div>
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.875rem' }}>Gate Camps Detected</p>
            <p style={{ fontSize: '2.5rem', fontWeight: 700, color: 'var(--warning)' }}>
              {report.global.gate_camps_detected}
            </p>
          </div>
        </div>
      </div>

      {/* Trade Routes - Full List */}
      {report.routes.map((route) => (
        <div
          key={`${route.origin_system}-${route.destination_system}`}
          className="card"
          style={{ marginTop: '1.5rem' }}
        >
          {/* Route Header */}
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
            <div>
              <h2 style={{ marginBottom: '0.5rem' }}>
                {route.origin_system} → {route.destination_system}
              </h2>
              <div style={{ display: 'flex', gap: '1rem', fontSize: '0.875rem', color: 'var(--text-secondary)' }}>
                <span>{route.jumps} jumps</span>
                <span>•</span>
                <span>{route.total_kills.toLocaleString()} kills (24h)</span>
                <span>•</span>
                <span>{(route.total_isk_destroyed / 1_000_000_000).toFixed(2)}B ISK destroyed</span>
              </div>
            </div>
            <div style={{ textAlign: 'right' }}>
              <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginBottom: '0.25rem' }}>
                Overall Danger
              </p>
              <div style={{
                padding: '0.5rem 1rem',
                borderRadius: '8px',
                background: getDangerColor(route.danger_score),
                color: 'white',
                fontWeight: 700,
                fontSize: '1.25rem'
              }}>
                {getDangerLabel(route.danger_score)} ({route.danger_score.toFixed(1)}/10)
              </div>
            </div>
          </div>

          {/* System-by-System Breakdown */}
          <div>
            <h3 style={{ fontSize: '1rem', marginBottom: '1rem', color: 'var(--text-secondary)' }}>
              System-by-System Analysis
            </h3>
            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                <thead>
                  <tr style={{ borderBottom: '2px solid var(--border-color)', textAlign: 'left' }}>
                    <th style={{ padding: '0.75rem', color: 'var(--text-secondary)', fontSize: '0.875rem' }}>System</th>
                    <th style={{ padding: '0.75rem', color: 'var(--text-secondary)', fontSize: '0.875rem', textAlign: 'center' }}>Security</th>
                    <th style={{ padding: '0.75rem', color: 'var(--text-secondary)', fontSize: '0.875rem', textAlign: 'center' }}>Danger</th>
                    <th style={{ padding: '0.75rem', color: 'var(--text-secondary)', fontSize: '0.875rem', textAlign: 'right' }}>Kills (24h)</th>
                    <th style={{ padding: '0.75rem', color: 'var(--text-secondary)', fontSize: '0.875rem', textAlign: 'right' }}>ISK Destroyed</th>
                    <th style={{ padding: '0.75rem', color: 'var(--text-secondary)', fontSize: '0.875rem', textAlign: 'center' }}>Gate Camp</th>
                  </tr>
                </thead>
                <tbody>
                  {route.systems.map((system, sysIdx) => (
                    <tr
                      key={system.system_id}
                      style={{
                        borderBottom: '1px solid var(--border-color)',
                        background: sysIdx % 2 === 0 ? 'var(--bg-elevated)' : 'transparent'
                      }}
                    >
                      <td style={{ padding: '0.75rem', fontWeight: 500 }}>
                        {system.system_name}
                      </td>
                      <td style={{ padding: '0.75rem', textAlign: 'center' }}>
                        <span style={{
                          padding: '0.25rem 0.5rem',
                          borderRadius: '4px',
                          fontSize: '0.75rem',
                          fontWeight: 600,
                          background: system.security_status >= 0.5 ? 'var(--success)' : system.security_status >= 0 ? 'var(--warning)' : 'var(--danger)',
                          color: 'white'
                        }}>
                          {system.security_status.toFixed(1)}
                        </span>
                      </td>
                      <td style={{ padding: '0.75rem', textAlign: 'center' }}>
                        <span style={{
                          padding: '0.25rem 0.5rem',
                          borderRadius: '4px',
                          fontSize: '0.75rem',
                          fontWeight: 600,
                          background: getDangerColor(system.danger_score),
                          color: 'white'
                        }}>
                          {system.danger_score.toFixed(1)}/10
                        </span>
                      </td>
                      <td style={{ padding: '0.75rem', textAlign: 'right', color: 'var(--accent-blue)', fontWeight: 600 }}>
                        {system.kills_24h.toLocaleString()}
                      </td>
                      <td style={{ padding: '0.75rem', textAlign: 'right', fontFamily: 'monospace' }}>
                        {(system.isk_destroyed_24h / 1_000_000_000).toFixed(2)}B
                      </td>
                      <td style={{ padding: '0.75rem', textAlign: 'center' }}>
                        {system.is_gate_camp ? (
                          <span style={{
                            padding: '0.25rem 0.5rem',
                            borderRadius: '4px',
                            fontSize: '0.75rem',
                            fontWeight: 700,
                            background: 'var(--danger)',
                            color: 'white'
                          }}>
                            ⚠️ CAMP
                          </span>
                        ) : (
                          <span style={{ color: 'var(--text-secondary)' }}>—</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Route Recommendations */}
          <div style={{ marginTop: '1.5rem', padding: '1rem', background: 'var(--bg-elevated)', borderRadius: '8px' }}>
            <h4 style={{ fontSize: '0.875rem', fontWeight: 600, marginBottom: '0.5rem', color: 'var(--text-secondary)' }}>
              Recommendations
            </h4>
            {route.danger_score >= 7 ? (
              <div style={{ color: 'var(--danger)' }}>
                <p style={{ marginBottom: '0.5rem' }}>
                  ⚠️ <strong>EXTREME DANGER:</strong> This route is extremely hazardous. Consider:
                </p>
                <ul style={{ marginLeft: '1.5rem', lineHeight: 1.6 }}>
                  <li>Using a tanked hauler (Deep Space Transport)</li>
                  <li>Traveling with an escort fleet</li>
                  <li>Avoiding peak activity times</li>
                  <li>Using a scout to check ahead</li>
                </ul>
              </div>
            ) : route.danger_score >= 4 ? (
              <div style={{ color: 'var(--warning)' }}>
                <p style={{ marginBottom: '0.5rem' }}>
                  ⚠️ <strong>HIGH RISK:</strong> Exercise caution on this route:
                </p>
                <ul style={{ marginLeft: '1.5rem', lineHeight: 1.6 }}>
                  <li>Avoid carrying high-value cargo in fragile ships</li>
                  <li>Monitor local chat and intel channels</li>
                  <li>Consider a more expensive but safer ship</li>
                </ul>
              </div>
            ) : (
              <div style={{ color: 'var(--success)' }}>
                <p>
                  ✓ <strong>RELATIVELY SAFE:</strong> This route shows low combat activity. Standard precautions apply.
                </p>
              </div>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}
