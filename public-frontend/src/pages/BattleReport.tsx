import { useState, useEffect } from 'react';
import { reportsApi } from '../services/api';
import { RefreshIndicator } from '../components/RefreshIndicator';
import { useAutoRefresh } from '../hooks/useAutoRefresh';
import { getSecurityColor, formatSecurity, formatISK } from '../utils/security';
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

  // Calculate capital totals
  const totalCapitalKills = Object.values(report.capital_kills).reduce((sum, cat) => sum + cat.count, 0);
  const totalCapitalISK = Object.values(report.capital_kills).reduce((sum, cat) => sum + cat.total_isk, 0);

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2rem' }}>
        <div>
          <h1>⚔️ Pilot Intelligence - 24h Battle Report</h1>
          <p style={{ color: 'var(--text-secondary)' }}>Actionable combat intelligence from capsuleer perspective</p>
        </div>
        <RefreshIndicator lastUpdated={lastUpdated} autoRefreshSeconds={60} />
      </div>

      {/* Hero Stats */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem', marginBottom: '2rem' }}>
        <div className="card card-elevated">
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.875rem', marginBottom: '0.5rem' }}>Total Kills</p>
          <p style={{ fontSize: '2.5rem', fontWeight: 700, color: 'var(--accent-blue)', margin: 0 }}>
            {report.global.total_kills.toLocaleString()}
          </p>
        </div>
        <div className="card card-elevated">
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.875rem', marginBottom: '0.5rem' }}>ISK Destroyed</p>
          <p style={{ fontSize: '2.5rem', fontWeight: 700, color: 'var(--danger)', margin: 0 }}>
            {formatISK(report.global.total_isk_destroyed)}
          </p>
        </div>
        <div className="card card-elevated">
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.875rem', marginBottom: '0.5rem' }}>Peak Hour (UTC)</p>
          <p style={{ fontSize: '2.5rem', fontWeight: 700, color: 'var(--warning)', margin: 0 }}>
            {report.global.peak_hour_utc}:00
          </p>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.75rem', marginTop: '0.25rem' }}>
            {report.global.peak_kills_per_hour} kills/hour
          </p>
        </div>
        {totalCapitalKills > 0 && (
          <div className="card card-elevated">
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.875rem', marginBottom: '0.5rem' }}>Capital Kills</p>
            <p style={{ fontSize: '2.5rem', fontWeight: 700, color: 'var(--success)', margin: 0 }}>
              {totalCapitalKills}
            </p>
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.75rem', marginTop: '0.25rem' }}>
              {formatISK(totalCapitalISK)}
            </p>
          </div>
        )}
      </div>

      {/* ECTMAP - LIVE BATTLE MAP */}
      <div style={{ marginBottom: '2rem' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
          <div>
            <h2 style={{ margin: 0 }}>🗺️ Live Battle Map - EVE Universe</h2>
            <p style={{ color: 'var(--text-secondary)', marginTop: '0.5rem', marginBottom: 0 }}>
              Interactive map with live battle tracking • Click battles for details • Hover for info
            </p>
          </div>
          <a
            href="http://192.168.178.108:3001"
            target="_blank"
            rel="noopener noreferrer"
            className="btn btn-primary"
            style={{
              padding: '0.5rem 1rem',
              fontSize: '0.875rem',
              textDecoration: 'none',
              whiteSpace: 'nowrap'
            }}
          >
            Open Full Map ↗
          </a>
        </div>
        <div
          className="card"
          style={{
            background: 'var(--bg-primary)',
            padding: '0',
            overflow: 'hidden',
            border: '2px solid var(--border)'
          }}
        >
          <iframe
            src="http://192.168.178.108:3001"
            style={{
              width: '100%',
              height: '700px',
              border: 'none',
              display: 'block'
            }}
            title="EVE Online Battle Map (ectmap)"
          />
        </div>
        <div style={{
          marginTop: '0.5rem',
          fontSize: '0.75rem',
          color: 'var(--text-secondary)',
          display: 'flex',
          gap: '1.5rem',
          flexWrap: 'wrap'
        }}>
          <span>🟢 Live Updates (5s)</span>
          <span>🎯 Click battles → Detail page</span>
          <span>ℹ️ Hover battles → Quick info</span>
          <span>🔴 Color by intensity</span>
          <span>📍 All systems & regions</span>
        </div>
      </div>

      {/* HOT ZONES */}
      {report.hot_zones && report.hot_zones.length > 0 && (
        <div className="card" style={{ marginBottom: '2rem' }}>
          <h2>🔥 Hot Zones - Top Combat Systems</h2>
          <p style={{ color: 'var(--text-secondary)', marginBottom: '1.5rem' }}>
            Most active systems in the last 24 hours
          </p>
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead>
                <tr style={{ borderBottom: '2px solid var(--border-color)', textAlign: 'left' }}>
                  <th style={{ padding: '0.75rem' }}>Rank</th>
                  <th style={{ padding: '0.75rem' }}>System</th>
                  <th style={{ padding: '0.75rem' }}>Region</th>
                  <th style={{ padding: '0.75rem', textAlign: 'center' }}>Sec</th>
                  <th style={{ padding: '0.75rem', textAlign: 'right' }}>Kills</th>
                  <th style={{ padding: '0.75rem', textAlign: 'right' }}>ISK Destroyed</th>
                  <th style={{ padding: '0.75rem' }}>Dominant Ship</th>
                </tr>
              </thead>
              <tbody>
                {report.hot_zones.map((zone, idx) => (
                  <tr
                    key={zone.system_id}
                    style={{
                      borderBottom: '1px solid var(--border-color)',
                      background: idx % 2 === 0 ? 'var(--bg-elevated)' : 'transparent'
                    }}
                  >
                    <td style={{ padding: '0.75rem', fontWeight: 700, color: 'var(--accent-blue)' }}>
                      #{idx + 1}
                    </td>
                    <td style={{ padding: '0.75rem', fontWeight: 600 }}>
                      {zone.system_name}
                      {zone.flags.includes('high_activity') && (
                        <span style={{ marginLeft: '0.5rem', fontSize: '0.75rem' }}>🔥</span>
                      )}
                    </td>
                    <td style={{ padding: '0.75rem', fontSize: '0.875rem', color: 'var(--text-secondary)' }}>
                      {zone.region_name}
                    </td>
                    <td style={{ padding: '0.75rem', textAlign: 'center' }}>
                      <span
                        style={{
                          padding: '0.25rem 0.5rem',
                          borderRadius: '4px',
                          fontSize: '0.875rem',
                          fontWeight: 700,
                          color: 'black',
                          background: getSecurityColor(zone.security_status)
                        }}
                      >
                        {formatSecurity(zone.security_status)}
                      </span>
                    </td>
                    <td style={{ padding: '0.75rem', textAlign: 'right', fontWeight: 600, color: 'var(--accent-blue)' }}>
                      {zone.kills.toLocaleString()}
                    </td>
                    <td style={{ padding: '0.75rem', textAlign: 'right', fontFamily: 'monospace', fontWeight: 600 }}>
                      {formatISK(zone.total_isk_destroyed)}
                    </td>
                    <td style={{ padding: '0.75rem', fontSize: '0.875rem' }}>
                      {zone.dominant_ship_type}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* CAPITAL CARNAGE */}
      {totalCapitalKills > 0 && (
        <div className="card" style={{ marginBottom: '2rem' }}>
          <h2>💀 Capital Carnage</h2>
          <p style={{ color: 'var(--text-secondary)', marginBottom: '1.5rem' }}>
            Capital ships destroyed in the last 24 hours
          </p>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', gap: '1rem' }}>
            {Object.entries(report.capital_kills).map(([type, data]) => {
              if (data.count === 0) return null;
              const typeName = type.charAt(0).toUpperCase() + type.slice(1).replace('_', ' ');
              return (
                <div key={type} style={{ padding: '1rem', background: 'var(--bg-elevated)', borderRadius: '8px', border: '1px solid var(--border-color)' }}>
                  <h3 style={{ fontSize: '1rem', marginBottom: '0.5rem', color: 'var(--accent-blue)' }}>{typeName}</h3>
                  <p style={{ fontSize: '2rem', fontWeight: 700, color: 'var(--danger)', margin: '0.5rem 0' }}>
                    {data.count}
                  </p>
                  <p style={{ fontSize: '0.875rem', color: 'var(--text-secondary)' }}>
                    {formatISK(data.total_isk)}
                  </p>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* HIGH-VALUE KILLS */}
      {report.high_value_kills && report.high_value_kills.length > 0 && (
        <div className="card" style={{ marginBottom: '2rem' }}>
          <h2>💰 High-Value Kills - Top 10</h2>
          <p style={{ color: 'var(--text-secondary)', marginBottom: '1.5rem' }}>
            Most expensive individual kills in the last 24 hours
          </p>
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead>
                <tr style={{ borderBottom: '2px solid var(--border-color)', textAlign: 'left' }}>
                  <th style={{ padding: '0.75rem' }}>Rank</th>
                  <th style={{ padding: '0.75rem', textAlign: 'right' }}>ISK Value</th>
                  <th style={{ padding: '0.75rem' }}>Ship</th>
                  <th style={{ padding: '0.75rem' }}>System</th>
                  <th style={{ padding: '0.75rem', textAlign: 'center' }}>Sec</th>
                  <th style={{ padding: '0.75rem', textAlign: 'center' }}>Type</th>
                </tr>
              </thead>
              <tbody>
                {report.high_value_kills.slice(0, 10).map((kill) => (
                  <tr
                    key={kill.killmail_id}
                    style={{
                      borderBottom: '1px solid var(--border-color)',
                      background: kill.rank % 2 === 0 ? 'transparent' : 'var(--bg-elevated)'
                    }}
                  >
                    <td style={{ padding: '0.75rem', fontWeight: 700, color: 'var(--accent-blue)' }}>
                      #{kill.rank}
                    </td>
                    <td style={{ padding: '0.75rem', textAlign: 'right', fontFamily: 'monospace', fontWeight: 700, color: 'var(--success)' }}>
                      {formatISK(kill.isk_destroyed)}
                    </td>
                    <td style={{ padding: '0.75rem', fontWeight: 600 }}>
                      {kill.ship_name}
                    </td>
                    <td style={{ padding: '0.75rem', fontSize: '0.875rem' }}>
                      {kill.system_name}
                    </td>
                    <td style={{ padding: '0.75rem', textAlign: 'center' }}>
                      <span
                        style={{
                          padding: '0.25rem 0.5rem',
                          borderRadius: '4px',
                          fontSize: '0.75rem',
                          fontWeight: 700,
                          color: 'black',
                          background: getSecurityColor(kill.security_status)
                        }}
                      >
                        {formatSecurity(kill.security_status)}
                      </span>
                    </td>
                    <td style={{ padding: '0.75rem', textAlign: 'center' }}>
                      {kill.is_gank && (
                        <span style={{
                          padding: '0.25rem 0.5rem',
                          borderRadius: '4px',
                          fontSize: '0.75rem',
                          fontWeight: 700,
                          background: 'var(--danger)',
                          color: 'white'
                        }}>
                          GANK
                        </span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* DANGER ZONES */}
      {report.danger_zones && report.danger_zones.length > 0 && (
        <div className="card" style={{ marginBottom: '2rem' }}>
          <h2>🚨 Danger Zones - Where Haulers Die</h2>
          <p style={{ color: 'var(--text-secondary)', marginBottom: '1.5rem' }}>
            Systems with high industrial/freighter losses
          </p>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '1rem' }}>
            {report.danger_zones.map((zone) => {
              const warningColor = zone.warning_level === 'EXTREME' ? 'var(--danger)' :
                                   zone.warning_level === 'HIGH' ? 'var(--warning)' : 'var(--success)';
              return (
                <div key={zone.system_name} style={{
                  padding: '1rem',
                  background: 'var(--bg-elevated)',
                  borderRadius: '8px',
                  borderLeft: `4px solid ${warningColor}`
                }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
                    <h3 style={{ fontSize: '1.125rem', fontWeight: 600 }}>{zone.system_name}</h3>
                    <span style={{
                      padding: '0.25rem 0.5rem',
                      borderRadius: '4px',
                      fontSize: '0.75rem',
                      fontWeight: 700,
                      background: warningColor,
                      color: 'white'
                    }}>
                      {zone.warning_level}
                    </span>
                  </div>
                  <p style={{ color: 'var(--text-secondary)', fontSize: '0.875rem', marginBottom: '0.75rem' }}>
                    {zone.region_name} ({formatSecurity(zone.security_status)})
                  </p>
                  <div style={{ fontSize: '0.875rem' }}>
                    <p>Freighters: <strong style={{ color: 'var(--danger)' }}>{zone.freighters_killed}</strong></p>
                    <p>Industrials: <strong style={{ color: 'var(--warning)' }}>{zone.industrials_killed}</strong></p>
                    <p>Total Value: <strong style={{ color: 'var(--success)' }}>{formatISK(zone.total_value)}</strong></p>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* SHIP BREAKDOWN */}
      {report.ship_breakdown && Object.keys(report.ship_breakdown).length > 0 && (
        <div className="card" style={{ marginBottom: '2rem' }}>
          <h2>📊 Ship Type Meta</h2>
          <p style={{ color: 'var(--text-secondary)', marginBottom: '1.5rem' }}>
            Kills and ISK destroyed by ship category
          </p>
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead>
                <tr style={{ borderBottom: '2px solid var(--border-color)', textAlign: 'left' }}>
                  <th style={{ padding: '0.75rem' }}>Ship Type</th>
                  <th style={{ padding: '0.75rem', textAlign: 'right' }}>Kills</th>
                  <th style={{ padding: '0.75rem', textAlign: 'right' }}>Total ISK</th>
                  <th style={{ padding: '0.75rem', textAlign: 'right' }}>Avg Value</th>
                </tr>
              </thead>
              <tbody>
                {Object.entries(report.ship_breakdown).slice(0, 15).map(([type, data], idx) => {
                  const typeName = type.charAt(0).toUpperCase() + type.slice(1).replace('_', ' ');
                  return (
                    <tr
                      key={type}
                      style={{
                        borderBottom: '1px solid var(--border-color)',
                        background: idx % 2 === 0 ? 'var(--bg-elevated)' : 'transparent'
                      }}
                    >
                      <td style={{ padding: '0.75rem', fontWeight: 600 }}>{typeName}</td>
                      <td style={{ padding: '0.75rem', textAlign: 'right', color: 'var(--accent-blue)', fontWeight: 600 }}>
                        {data.count.toLocaleString()}
                      </td>
                      <td style={{ padding: '0.75rem', textAlign: 'right', fontFamily: 'monospace', fontWeight: 600 }}>
                        {formatISK(data.total_isk)}
                      </td>
                      <td style={{ padding: '0.75rem', textAlign: 'right', fontFamily: 'monospace', fontSize: '0.875rem', color: 'var(--text-secondary)' }}>
                        {formatISK(data.total_isk / data.count)}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* ACTIVITY TIMELINE */}
      {report.timeline && report.timeline.length > 0 && (
        <div className="card">
          <h2>⏰ Activity Timeline (UTC)</h2>
          <p style={{ color: 'var(--text-secondary)', marginBottom: '1.5rem' }}>
            Hourly kill distribution over 24 hours
          </p>
          <div style={{ overflowX: 'auto' }}>
            <div style={{ display: 'flex', gap: '0.25rem', alignItems: 'flex-end', height: '200px', padding: '1rem 0' }}>
              {report.timeline.map((hour) => {
                const maxKills = Math.max(...report.timeline.map(h => h.kills));
                const height = (hour.kills / maxKills) * 100;
                const isPeak = hour.hour_utc === report.global.peak_hour_utc;
                return (
                  <div key={hour.hour_utc} style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '0.5rem' }}>
                    <div
                      style={{
                        width: '100%',
                        height: `${height}%`,
                        background: isPeak ? 'var(--danger)' : 'var(--accent-blue)',
                        borderRadius: '4px 4px 0 0',
                        transition: 'height 0.3s ease',
                        position: 'relative'
                      }}
                      title={`${hour.hour_utc}:00 - ${hour.kills} kills, ${formatISK(hour.isk_destroyed)}`}
                    />
                    <span style={{
                      fontSize: '0.75rem',
                      color: isPeak ? 'var(--danger)' : 'var(--text-secondary)',
                      fontWeight: isPeak ? 700 : 400
                    }}>
                      {hour.hour_utc}
                    </span>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
