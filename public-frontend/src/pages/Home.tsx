import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { RefreshIndicator } from '../components/RefreshIndicator';
import { useAutoRefresh } from '../hooks/useAutoRefresh';
import { useAllReports } from '../hooks/useReports';
import { reportsApi } from '../services/api';
import type { StrategicBriefing } from '../types/reports';
import BattleStatsCards from '../components/BattleStatsCards';
import LiveBattles from '../components/LiveBattles';
import TelegramMirror from '../components/TelegramMirror';

export function Home() {
  const [lastUpdated, setLastUpdated] = useState(new Date());
  const [briefing, setBriefing] = useState<StrategicBriefing | null>(null);
  const [briefingLoading, setBriefingLoading] = useState(true);

  const {
    battleReport,
    profiteering,
    allianceWars,
    tradeRoutes,
    isLoading,
    isError,
    error,
    refetch
  } = useAllReports();

  // Fetch strategic briefing
  const fetchBriefing = async () => {
    try {
      setBriefingLoading(true);
      const data = await reportsApi.getStrategicBriefing();
      setBriefing(data);
    } catch (err) {
      console.error('Failed to load strategic briefing:', err);
    } finally {
      setBriefingLoading(false);
    }
  };

  useEffect(() => {
    fetchBriefing();
  }, []);

  // Auto-refresh every 60 seconds
  useAutoRefresh(() => {
    refetch();
    setLastUpdated(new Date());
  }, 60);

  if (isLoading) {
    return (
      <div>
        <div className="skeleton" style={{ height: '200px', marginBottom: '1rem' }} />
        <div className="skeleton" style={{ height: '200px', marginBottom: '1rem' }} />
        <div className="skeleton" style={{ height: '200px', marginBottom: '1rem' }} />
      </div>
    );
  }

  if (isError) {
    return (
      <div className="card" style={{
        background: 'var(--danger)',
        color: 'white',
        textAlign: 'center',
        padding: '2rem'
      }}>
        <h2>❌ {error instanceof Error ? error.message : 'Failed to load reports. Please try again.'}</h2>
        <button
          onClick={() => {
            refetch();
            setLastUpdated(new Date());
          }}
          style={{
            marginTop: '1rem',
            padding: '0.5rem 1rem',
            background: 'white',
            color: 'var(--danger)',
            border: 'none',
            borderRadius: '4px',
            cursor: 'pointer',
            fontWeight: 600
          }}
        >
          Retry
        </button>
      </div>
    );
  }

  return (
    <div>
      {/* Alpha Warning Banner */}
      <div style={{
        background: 'linear-gradient(135deg, #ff6b00 0%, #ff9500 100%)',
        color: 'white',
        padding: '1rem 1.5rem',
        borderRadius: '8px',
        marginBottom: '1.5rem',
        border: '2px solid rgba(255, 255, 255, 0.2)',
        display: 'flex',
        alignItems: 'center',
        gap: '1rem'
      }}>
        <span style={{ fontSize: '2rem' }}>⚠️</span>
        <div style={{ flex: 1 }}>
          <div style={{ fontWeight: 700, fontSize: '1.125rem', marginBottom: '0.25rem' }}>
            Alpha Software
          </div>
          <div style={{ fontSize: '0.875rem', opacity: 0.95 }}>
            This dashboard is in active development. Data may be incomplete or inaccurate. Features are subject to change.
          </div>
        </div>
      </div>

      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: '2rem'
      }}>
        <div>
          <h1 style={{ fontSize: '2rem', marginBottom: '0.5rem' }}>
            Combat Intelligence Dashboard
          </h1>
          <p style={{ color: 'var(--text-secondary)' }}>
            Real-time intelligence from across New Eden
          </p>
        </div>
        <RefreshIndicator lastUpdated={lastUpdated} autoRefreshSeconds={60} />
      </div>

      {/* Strategic Intelligence Briefing */}
      <div className="card" style={{
        marginBottom: '1.5rem',
        background: 'linear-gradient(135deg, var(--bg-surface) 0%, var(--bg-elevated) 100%)',
        border: '1px solid var(--accent-purple)',
        borderLeft: '4px solid var(--accent-purple)'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '1rem' }}>
          <span style={{ fontSize: '1.75rem' }}>🎖️</span>
          <div>
            <h2 style={{ margin: 0, fontSize: '1.25rem' }}>Strategic Intelligence Briefing</h2>
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.75rem', margin: 0 }}>
              AI-powered strategic analysis for alliance leadership
              {briefing?.generated_at && (
                <span> • Last update: {new Date(briefing.generated_at).toLocaleTimeString()}</span>
              )}
            </p>
          </div>
        </div>

        {briefingLoading ? (
          <div style={{ padding: '2rem', textAlign: 'center' }}>
            <div className="skeleton" style={{ height: '100px', marginBottom: '1rem' }} />
            <p style={{ color: 'var(--text-secondary)' }}>Generating strategic briefing...</p>
          </div>
        ) : briefing?.error ? (
          <div style={{ padding: '1rem', background: 'rgba(248, 81, 73, 0.1)', borderRadius: '8px', color: 'var(--danger)' }}>
            Briefing temporarily unavailable: {briefing.error}
          </div>
        ) : briefing ? (
          <div>
            {/* Alerts (if any) */}
            {briefing.alerts && briefing.alerts.length > 0 && (
              <div style={{ marginBottom: '1.25rem' }}>
                {briefing.alerts.map((alert, idx) => (
                  <div
                    key={idx}
                    style={{
                      padding: '0.75rem 1rem',
                      background: 'rgba(248, 81, 73, 0.15)',
                      border: '1px solid var(--danger)',
                      borderRadius: '6px',
                      marginBottom: '0.5rem',
                      fontSize: '0.875rem',
                      color: 'var(--danger)',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '0.5rem'
                    }}
                  >
                    <span>⚠️</span> {alert}
                  </div>
                ))}
              </div>
            )}

            {/* Executive Briefing */}
            <div style={{
              padding: '1.25rem',
              background: 'var(--bg-surface)',
              borderRadius: '8px',
              marginBottom: '1.25rem',
              lineHeight: '1.7',
              color: 'var(--text-primary)'
            }}>
              {briefing.briefing.split('\n').map((paragraph, idx) => (
                <p key={idx} style={{ marginBottom: idx < briefing.briefing.split('\n').length - 1 ? '1rem' : 0 }}>
                  {paragraph}
                </p>
              ))}
            </div>

            {/* Power Assessment */}
            {briefing.power_assessment && (
              <div style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
                gap: '1rem',
                marginBottom: '1.25rem'
              }}>
                {briefing.power_assessment.gaining_power.length > 0 && (
                  <div style={{
                    padding: '1rem',
                    background: 'rgba(63, 185, 80, 0.1)',
                    borderRadius: '8px',
                    border: '1px solid var(--success)'
                  }}>
                    <h4 style={{ fontSize: '0.75rem', color: 'var(--success)', marginBottom: '0.5rem' }}>
                      📈 GAINING POWER
                    </h4>
                    {briefing.power_assessment.gaining_power.map((name, idx) => (
                      <div key={idx} style={{ fontSize: '0.875rem', padding: '0.25rem 0' }}>{name}</div>
                    ))}
                  </div>
                )}
                {briefing.power_assessment.losing_power.length > 0 && (
                  <div style={{
                    padding: '1rem',
                    background: 'rgba(248, 81, 73, 0.1)',
                    borderRadius: '8px',
                    border: '1px solid var(--danger)'
                  }}>
                    <h4 style={{ fontSize: '0.75rem', color: 'var(--danger)', marginBottom: '0.5rem' }}>
                      📉 LOSING POWER
                    </h4>
                    {briefing.power_assessment.losing_power.map((name, idx) => (
                      <div key={idx} style={{ fontSize: '0.875rem', padding: '0.25rem 0' }}>{name}</div>
                    ))}
                  </div>
                )}
                {briefing.power_assessment.contested.length > 0 && (
                  <div style={{
                    padding: '1rem',
                    background: 'rgba(210, 153, 34, 0.1)',
                    borderRadius: '8px',
                    border: '1px solid var(--warning)'
                  }}>
                    <h4 style={{ fontSize: '0.75rem', color: 'var(--warning)', marginBottom: '0.5rem' }}>
                      ⚔️ CONTESTED ZONES
                    </h4>
                    {briefing.power_assessment.contested.map((name, idx) => (
                      <div key={idx} style={{ fontSize: '0.875rem', padding: '0.25rem 0' }}>{name}</div>
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* Key Highlights */}
            {briefing.highlights && briefing.highlights.length > 0 && (
              <div>
                <h3 style={{ fontSize: '0.875rem', marginBottom: '0.75rem', color: 'var(--accent-blue)' }}>
                  🎯 Key Strategic Highlights
                </h3>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                  {briefing.highlights.map((highlight, idx) => (
                    <div
                      key={idx}
                      style={{
                        padding: '0.75rem 1rem',
                        background: 'var(--bg-elevated)',
                        borderRadius: '6px',
                        borderLeft: '3px solid var(--accent-blue)',
                        fontSize: '0.875rem',
                        color: 'var(--text-primary)'
                      }}
                    >
                      {highlight}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        ) : null}
      </div>

      {/* Live Battle Intelligence */}
      <BattleStatsCards />

      <div style={{
        display: 'grid',
        gridTemplateColumns: '2fr 1fr',
        gap: '1.5rem',
        marginBottom: '2rem'
      }}>
        <LiveBattles />
        <TelegramMirror />
      </div>

      {/* Battle Report Summary */}
      <div className="card card-elevated">
        <h2>⚔️ 24-Hour Battle Report</h2>
        {battleReport && (
          <>
            <div style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
              gap: '1.5rem',
              margin: '1.5rem 0'
            }}>
              <div>
                <p style={{ color: 'var(--text-secondary)', fontSize: '0.875rem' }}>
                  Total Kills
                </p>
                <p style={{ fontSize: '2rem', fontWeight: 700, color: 'var(--accent-blue)' }}>
                  {battleReport.global.total_kills.toLocaleString()}
                </p>
              </div>
              <div>
                <p style={{ color: 'var(--text-secondary)', fontSize: '0.875rem' }}>
                  ISK Destroyed
                </p>
                <p style={{ fontSize: '2rem', fontWeight: 700, color: 'var(--danger)' }}>
                  {(battleReport.global.total_isk_destroyed / 1_000_000_000).toFixed(1)}B
                </p>
              </div>
              <div>
                <p style={{ color: 'var(--text-secondary)', fontSize: '0.875rem' }}>
                  Peak Hour (UTC)
                </p>
                <p style={{ fontSize: '1.25rem', fontWeight: 600, color: 'var(--warning)' }}>
                  {battleReport.global.peak_hour_utc}:00
                </p>
              </div>
            </div>
            <Link
              to="/battle-report"
              style={{
                color: 'var(--accent-blue)',
                fontWeight: 600
              }}
            >
              View Full Report →
            </Link>
          </>
        )}
      </div>

      {/* War Profiteering Summary */}
      <div className="card">
        <h2>💰 War Profiteering Opportunities</h2>
        {profiteering && profiteering.items.length > 0 && (
          <>
            <p style={{ color: 'var(--text-secondary)', marginBottom: '1rem' }}>
              Top {profiteering.items.slice(0, 5).length} destroyed items by market value
            </p>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
              {profiteering.items.slice(0, 5).map((item, idx) => (
                <div
                  key={item.item_type_id}
                  style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    padding: '0.75rem',
                    background: 'var(--bg-elevated)',
                    borderRadius: '4px'
                  }}
                >
                  <span style={{ fontWeight: 600 }}>
                    {idx + 1}. {item.item_name}
                  </span>
                  <span style={{ color: 'var(--success)' }}>
                    {(item.opportunity_value / 1_000_000_000).toFixed(2)}B ISK
                  </span>
                </div>
              ))}
            </div>
            <Link
              to="/war-profiteering"
              style={{
                color: 'var(--accent-blue)',
                fontWeight: 600,
                display: 'block',
                marginTop: '1rem'
              }}
            >
              View All Opportunities →
            </Link>
          </>
        )}
      </div>

      {/* Alliance Wars Summary */}
      <div className="card">
        <h2>🛡️ Alliance Wars</h2>
        {allianceWars && allianceWars.conflicts.length > 0 && (
          <>
            <p style={{ color: 'var(--text-secondary)', marginBottom: '1rem' }}>
              Top {allianceWars.conflicts.slice(0, 3).length} active conflicts
            </p>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              {allianceWars.conflicts.slice(0, 3).map((conflict) => (
                <div
                  key={`${conflict.alliance_1_id}-${conflict.alliance_2_id}`}
                  style={{
                    padding: '1rem',
                    background: 'var(--bg-elevated)',
                    borderRadius: '4px',
                    borderLeft: `4px solid ${
                      conflict.winner === conflict.alliance_1_name ? 'var(--success)' :
                      conflict.winner === conflict.alliance_2_name ? 'var(--danger)' :
                      'var(--warning)'
                    }`
                  }}
                >
                  <div style={{ fontWeight: 600, marginBottom: '0.5rem' }}>
                    {conflict.alliance_1_name} vs {conflict.alliance_2_name}
                  </div>
                  <div style={{
                    display: 'flex',
                    gap: '1.5rem',
                    fontSize: '0.875rem',
                    color: 'var(--text-secondary)'
                  }}>
                    <span>Kills: {conflict.alliance_1_kills + conflict.alliance_2_kills}</span>
                    <span>A1 Eff: {conflict.alliance_1_efficiency.toFixed(1)}%</span>
                    <span>A2 Eff: {conflict.alliance_2_efficiency.toFixed(1)}%</span>
                  </div>
                </div>
              ))}
            </div>
            <Link
              to="/alliance-wars"
              style={{
                color: 'var(--accent-blue)',
                fontWeight: 600,
                display: 'block',
                marginTop: '1rem'
              }}
            >
              View All Wars →
            </Link>
          </>
        )}
      </div>

      {/* Trade Routes Summary */}
      <div className="card">
        <h2>🛣️ Trade Route Safety</h2>
        {tradeRoutes && tradeRoutes.routes.length > 0 && (
          <>
            <p style={{ color: 'var(--text-secondary)', marginBottom: '1rem' }}>
              Route danger levels (last 24h)
            </p>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
              {tradeRoutes.routes.slice(0, 5).map((route) => {
                const dangerLevel = route.danger_score >= 7 ? 'HIGH' :
                                  route.danger_score >= 4 ? 'MODERATE' :
                                  route.danger_score >= 2 ? 'LOW' : 'SAFE';
                return (
                  <div
                    key={`${route.origin_system}-${route.destination_system}`}
                    style={{
                      display: 'flex',
                      justifyContent: 'space-between',
                      padding: '0.75rem',
                      background: 'var(--bg-elevated)',
                      borderRadius: '4px'
                    }}
                  >
                    <span>
                      {route.origin_system} → {route.destination_system}
                    </span>
                    <span style={{
                      fontWeight: 600,
                      color:
                        dangerLevel === 'SAFE' ? 'var(--success)' :
                        dangerLevel === 'LOW' ? 'var(--accent-blue)' :
                        dangerLevel === 'MODERATE' ? 'var(--warning)' :
                        'var(--danger)'
                    }}>
                      {dangerLevel} ({route.danger_score.toFixed(1)})
                    </span>
                  </div>
                );
              })}
            </div>
            <Link
              to="/trade-routes"
              style={{
                color: 'var(--accent-blue)',
                fontWeight: 600,
                display: 'block',
                marginTop: '1rem'
              }}
            >
              View Route Details →
            </Link>
          </>
        )}
      </div>
    </div>
  );
}
