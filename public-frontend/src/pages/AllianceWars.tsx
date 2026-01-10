import { useState, useEffect } from 'react';
import { reportsApi } from '../services/api';
import { RefreshIndicator } from '../components/RefreshIndicator';
import { useAutoRefresh } from '../hooks/useAutoRefresh';
import type { AllianceWars as AllianceWarsType, AllianceWarsAnalysis } from '../types/reports';

export function AllianceWars() {
  const [report, setReport] = useState<AllianceWarsType | null>(null);
  const [analysis, setAnalysis] = useState<AllianceWarsAnalysis | null>(null);
  const [analysisLoading, setAnalysisLoading] = useState(true);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState(new Date());
  const [expandedWar, setExpandedWar] = useState<string | null>(null);

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

  const fetchAnalysis = async () => {
    try {
      setAnalysisLoading(true);
      const data = await reportsApi.getAllianceWarsAnalysis();
      setAnalysis(data);
    } catch (err) {
      console.error('Failed to load analysis:', err);
    } finally {
      setAnalysisLoading(false);
    }
  };

  useEffect(() => {
    fetchReport();
    fetchAnalysis();
  }, []);

  useAutoRefresh(fetchReport, 60);

  const toggleExpand = (warKey: string) => {
    setExpandedWar(expandedWar === warKey ? null : warKey);
  };

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

      {/* AI Strategic Analysis */}
      <div className="card" style={{ marginTop: '1.5rem', background: 'linear-gradient(135deg, var(--bg-surface) 0%, var(--bg-elevated) 100%)', border: '1px solid var(--accent-purple)', borderLeft: '4px solid var(--accent-purple)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '1rem' }}>
          <span style={{ fontSize: '1.5rem' }}>🤖</span>
          <div>
            <h2 style={{ margin: 0 }}>Strategic Intelligence Analysis</h2>
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.75rem', margin: 0 }}>
              AI-powered analysis • Updated hourly
              {analysis?.generated_at && (
                <span> • Last update: {new Date(analysis.generated_at).toLocaleTimeString()}</span>
              )}
            </p>
          </div>
        </div>

        {analysisLoading ? (
          <div style={{ padding: '2rem', textAlign: 'center' }}>
            <div className="skeleton" style={{ height: '100px', marginBottom: '1rem' }} />
            <p style={{ color: 'var(--text-secondary)' }}>Generating strategic analysis...</p>
          </div>
        ) : analysis?.error ? (
          <div style={{ padding: '1rem', background: 'rgba(248, 81, 73, 0.1)', borderRadius: '8px', color: 'var(--danger)' }}>
            Analysis temporarily unavailable: {analysis.error}
          </div>
        ) : analysis ? (
          <div>
            {/* Summary Text */}
            <div style={{
              padding: '1.25rem',
              background: 'var(--bg-surface)',
              borderRadius: '8px',
              marginBottom: '1.5rem',
              lineHeight: '1.7',
              color: 'var(--text-primary)'
            }}>
              {analysis.summary.split('\n').map((paragraph, idx) => (
                <p key={idx} style={{ marginBottom: idx < analysis.summary.split('\n').length - 1 ? '1rem' : 0 }}>
                  {paragraph}
                </p>
              ))}
            </div>

            {/* Key Insights */}
            {analysis.insights && analysis.insights.length > 0 && (
              <div>
                <h3 style={{ fontSize: '1rem', marginBottom: '1rem', color: 'var(--accent-blue)' }}>
                  📊 Key Strategic Insights
                </h3>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '0.75rem' }}>
                  {analysis.insights.map((insight, idx) => (
                    <div
                      key={idx}
                      style={{
                        padding: '0.875rem 1rem',
                        background: 'var(--bg-elevated)',
                        borderRadius: '6px',
                        borderLeft: '3px solid var(--accent-blue)',
                        fontSize: '0.875rem',
                        color: 'var(--text-primary)'
                      }}
                    >
                      {insight}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Trend Analysis */}
            {analysis.trends && analysis.trends.length > 0 && (
              <div style={{ marginTop: '1.5rem' }}>
                <h3 style={{ fontSize: '1rem', marginBottom: '1rem', color: 'var(--success)' }}>
                  📈 Trend Analysis
                </h3>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                  {analysis.trends.map((trend, idx) => (
                    <div
                      key={idx}
                      style={{
                        padding: '0.875rem 1rem',
                        background: 'var(--bg-elevated)',
                        borderRadius: '6px',
                        borderLeft: '3px solid var(--success)',
                        fontSize: '0.875rem',
                        color: 'var(--text-primary)'
                      }}
                    >
                      {trend}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        ) : null}
      </div>

      {/* Coalition Summary - Auto-Detected Power Blocs */}
      {report.coalitions && report.coalitions.length > 0 && (
        <div className="card" style={{ marginTop: '1.5rem' }}>
          <h2>Power Blocs</h2>
          <p style={{ color: 'var(--text-secondary)', marginBottom: '1.5rem' }}>
            Auto-detected coalitions based on combat patterns (7 days)
          </p>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '1rem' }}>
            {report.coalitions.map((coalition) => (
              <div
                key={coalition.leader_alliance_id}
                style={{
                  padding: '1.25rem',
                  background: 'var(--bg-elevated)',
                  borderRadius: '8px',
                  border: '1px solid var(--border-color)',
                  borderLeft: `4px solid ${coalition.efficiency >= 55 ? 'var(--success)' : coalition.efficiency >= 45 ? 'var(--warning)' : 'var(--danger)'}`
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '1rem' }}>
                  <div>
                    <h3 style={{ fontSize: '1.125rem', fontWeight: 600, marginBottom: '0.25rem' }}>
                      {coalition.name}
                    </h3>
                    <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                      {coalition.member_count} alliances
                    </p>
                  </div>
                  <div style={{
                    padding: '0.25rem 0.75rem',
                    borderRadius: '999px',
                    fontSize: '0.875rem',
                    fontWeight: 600,
                    background: coalition.efficiency >= 55 ? 'rgba(63, 185, 80, 0.15)' : coalition.efficiency >= 45 ? 'rgba(210, 153, 34, 0.15)' : 'rgba(248, 81, 73, 0.15)',
                    color: coalition.efficiency >= 55 ? 'var(--success)' : coalition.efficiency >= 45 ? 'var(--warning)' : 'var(--danger)'
                  }}>
                    {coalition.efficiency.toFixed(1)}%
                  </div>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem', marginBottom: '1rem' }}>
                  <div>
                    <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>Kills</p>
                    <p style={{ fontSize: '1.25rem', fontWeight: 600, color: 'var(--success)' }}>
                      {coalition.total_kills.toLocaleString()}
                    </p>
                  </div>
                  <div>
                    <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>Losses</p>
                    <p style={{ fontSize: '1.25rem', fontWeight: 600, color: 'var(--danger)' }}>
                      {coalition.total_losses.toLocaleString()}
                    </p>
                  </div>
                  <div>
                    <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>ISK Destroyed</p>
                    <p style={{ fontSize: '1rem', fontWeight: 600, fontFamily: 'monospace' }}>
                      {(coalition.isk_destroyed / 1_000_000_000).toFixed(1)}B
                    </p>
                  </div>
                  <div>
                    <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>ISK Lost</p>
                    <p style={{ fontSize: '1rem', fontWeight: 600, fontFamily: 'monospace' }}>
                      {(coalition.isk_lost / 1_000_000_000).toFixed(1)}B
                    </p>
                  </div>
                </div>

                <div style={{ borderTop: '1px solid var(--border-color)', paddingTop: '0.75rem' }}>
                  <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginBottom: '0.5rem' }}>Key Members</p>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
                    {coalition.members.slice(0, 4).map((member) => (
                      <span
                        key={member.alliance_id}
                        style={{
                          fontSize: '0.75rem',
                          padding: '0.25rem 0.5rem',
                          background: 'var(--bg-surface)',
                          borderRadius: '4px',
                          color: 'var(--text-primary)'
                        }}
                      >
                        {member.name}
                      </span>
                    ))}
                    {coalition.member_count > 4 && (
                      <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', padding: '0.25rem' }}>
                        +{coalition.member_count - 4} more
                      </span>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>

          {/* Unaffiliated Alliances */}
          {report.unaffiliated_alliances && report.unaffiliated_alliances.length > 0 && (
            <div style={{ marginTop: '1.5rem' }}>
              <h3 style={{ fontSize: '1rem', color: 'var(--text-secondary)', marginBottom: '1rem' }}>
                Independent Operators
              </h3>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.75rem' }}>
                {report.unaffiliated_alliances.slice(0, 8).map((alliance) => (
                  <div
                    key={alliance.alliance_id}
                    style={{
                      padding: '0.5rem 1rem',
                      background: 'var(--bg-elevated)',
                      borderRadius: '6px',
                      border: '1px solid var(--border-color)',
                      fontSize: '0.875rem'
                    }}
                  >
                    <span style={{ fontWeight: 500 }}>{alliance.name}</span>
                    <span style={{ marginLeft: '0.5rem', color: 'var(--text-secondary)' }}>
                      {alliance.kills.toLocaleString()} kills
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Active Conflicts - Full List */}
      <div className="card" style={{ marginTop: '1.5rem' }}>
        <h2>Active Conflicts</h2>
        <p style={{ color: 'var(--text-secondary)', marginBottom: '1.5rem' }}>
          Ongoing alliance wars ranked by intensity and strategic significance
        </p>

        {report.conflicts.map((conflict) => {
          const warKey = `${conflict.alliance_1_id}-${conflict.alliance_2_id}`;
          const isExpanded = expandedWar === warKey;

          return (
            <div
              key={warKey}
              className="card"
              style={{
                marginBottom: '1.5rem',
                background: 'var(--bg-elevated)',
                border: '1px solid var(--border-color)',
                cursor: 'pointer',
                transition: 'all 0.2s ease'
              }}
              onClick={() => toggleExpand(warKey)}
            >
              {/* Conflict Header */}
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
                <div>
                  <h3 style={{ fontSize: '1.25rem', marginBottom: '0.5rem' }}>
                    <span style={{ color: 'var(--accent-blue)' }}>{conflict.alliance_1_name}</span>
                    {' vs '}
                    <span style={{ color: 'var(--danger)' }}>{conflict.alliance_2_name}</span>
                    <span style={{ marginLeft: '0.5rem', fontSize: '0.875rem', color: 'var(--text-secondary)' }}>
                      {isExpanded ? '▼' : '▶'}
                    </span>
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

            {/* EXPANDED DETAIL VIEW */}
            {isExpanded && (
              <div style={{
                marginTop: '1.5rem',
                paddingTop: '1.5rem',
                borderTop: '2px solid var(--border-color)',
                animation: 'fadeIn 0.3s ease-in-out'
              }}>
                <h3 style={{ fontSize: '1.125rem', marginBottom: '1rem', color: 'var(--accent-purple)' }}>
                  📊 Detailed War Intelligence
                </h3>

                {/* Economic Metrics */}
                <div className="card" style={{ background: 'var(--bg-surface)', marginBottom: '1.5rem' }}>
                  <h4 style={{ fontSize: '1rem', marginBottom: '1rem' }}>💰 Economic Analysis</h4>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem' }}>
                    <div>
                      <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>Average Kill Value</p>
                      <p style={{ fontSize: '1.5rem', fontWeight: 700, fontFamily: 'monospace', color: 'var(--warning)' }}>
                        {((conflict.avg_kill_value || 0) / 1_000_000).toFixed(1)}M ISK
                      </p>
                    </div>
                    <div>
                      <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>Biggest Loss - {conflict.alliance_1_name}</p>
                      <p style={{ fontSize: '1.5rem', fontWeight: 700, fontFamily: 'monospace', color: 'var(--danger)' }}>
                        {((conflict.alliance_1_biggest_loss?.value || 0) / 1_000_000).toFixed(1)}M ISK
                      </p>
                    </div>
                    <div>
                      <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>Biggest Loss - {conflict.alliance_2_name}</p>
                      <p style={{ fontSize: '1.5rem', fontWeight: 700, fontFamily: 'monospace', color: 'var(--danger)' }}>
                        {((conflict.alliance_2_biggest_loss?.value || 0) / 1_000_000).toFixed(1)}M ISK
                      </p>
                    </div>
                  </div>
                </div>

                {/* Ship Class Analysis */}
                <div className="card" style={{ background: 'var(--bg-surface)', marginBottom: '1.5rem' }}>
                  <h4 style={{ fontSize: '1rem', marginBottom: '1rem' }}>🚀 Ship Class Breakdown</h4>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '2rem' }}>
                    {/* Alliance 1 Ship Classes */}
                    <div>
                      <h5 style={{ fontSize: '0.875rem', color: 'var(--accent-blue)', marginBottom: '0.75rem' }}>
                        {conflict.alliance_1_name} - Ships Lost
                      </h5>
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                        {Object.entries(conflict.alliance_1_ship_classes || {})
                          .filter(([_, count]) => count > 0)
                          .sort((a, b) => b[1] - a[1])  // Sort by count descending
                          .map(([shipClass, count]) => {
                            const getShipClassColor = (cls: string) => {
                              switch(cls) {
                                case 'capital': return 'var(--danger)';
                                case 'battleship': return '#ff6b00';
                                case 'battlecruiser': return '#ff9500';
                                case 'cruiser': return 'var(--accent-blue)';
                                case 'destroyer': return '#a855f7';
                                case 'frigate': return 'var(--success)';
                                case 'logistics': return '#22d3ee';  // Cyan for support ships
                                case 'stealth_bomber': return '#dc2626';  // Red for bombers
                                case 'industrial': return '#8b949e';
                                case 'hauler': return '#6e7681';
                                case 'mining': return '#d29922';
                                case 'capsule': return '#4a5568';
                                default: return 'var(--text-secondary)';
                              }
                            };
                            const getShipClassLabel = (cls: string) => {
                              switch(cls) {
                                case 'battlecruiser': return 'Battlecruiser';
                                case 'stealth_bomber': return 'Stealth Bomber';
                                case 'capsule': return 'Capsule/Pod';
                                default: return cls.charAt(0).toUpperCase() + cls.slice(1);
                              }
                            };
                            return (
                            <div key={shipClass} style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                              <div style={{
                                width: '110px',
                                fontSize: '0.75rem',
                                color: 'var(--text-secondary)'
                              }}>
                                {getShipClassLabel(shipClass)}
                              </div>
                              <div style={{
                                flex: 1,
                                height: '24px',
                                background: 'var(--bg-elevated)',
                                borderRadius: '4px',
                                overflow: 'hidden'
                              }}>
                                <div style={{
                                  height: '100%',
                                  width: `${(count / Math.max(...Object.values(conflict.alliance_1_ship_classes || {}))) * 100}%`,
                                  background: getShipClassColor(shipClass),
                                  transition: 'width 0.3s ease'
                                }}></div>
                              </div>
                              <div style={{
                                width: '50px',
                                textAlign: 'right',
                                fontWeight: 600,
                                fontSize: '0.875rem'
                              }}>
                                {count.toLocaleString()}
                              </div>
                            </div>
                          )})}
                      </div>
                    </div>

                    {/* Alliance 2 Ship Classes */}
                    <div>
                      <h5 style={{ fontSize: '0.875rem', color: 'var(--danger)', marginBottom: '0.75rem' }}>
                        {conflict.alliance_2_name} - Ships Lost
                      </h5>
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                        {Object.entries(conflict.alliance_2_ship_classes || {})
                          .filter(([_, count]) => count > 0)
                          .sort((a, b) => b[1] - a[1])  // Sort by count descending
                          .map(([shipClass, count]) => {
                            const getShipClassColor = (cls: string) => {
                              switch(cls) {
                                case 'capital': return 'var(--danger)';
                                case 'battleship': return '#ff6b00';
                                case 'battlecruiser': return '#ff9500';
                                case 'cruiser': return 'var(--accent-blue)';
                                case 'destroyer': return '#a855f7';
                                case 'frigate': return 'var(--success)';
                                case 'logistics': return '#22d3ee';  // Cyan for support ships
                                case 'stealth_bomber': return '#dc2626';  // Red for bombers
                                case 'industrial': return '#8b949e';
                                case 'hauler': return '#6e7681';
                                case 'mining': return '#d29922';
                                case 'capsule': return '#4a5568';
                                default: return 'var(--text-secondary)';
                              }
                            };
                            const getShipClassLabel = (cls: string) => {
                              switch(cls) {
                                case 'battlecruiser': return 'Battlecruiser';
                                case 'stealth_bomber': return 'Stealth Bomber';
                                case 'capsule': return 'Capsule/Pod';
                                default: return cls.charAt(0).toUpperCase() + cls.slice(1);
                              }
                            };
                            return (
                            <div key={shipClass} style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                              <div style={{
                                width: '110px',
                                fontSize: '0.75rem',
                                color: 'var(--text-secondary)'
                              }}>
                                {getShipClassLabel(shipClass)}
                              </div>
                              <div style={{
                                flex: 1,
                                height: '24px',
                                background: 'var(--bg-elevated)',
                                borderRadius: '4px',
                                overflow: 'hidden'
                              }}>
                                <div style={{
                                  height: '100%',
                                  width: `${(count / Math.max(...Object.values(conflict.alliance_2_ship_classes || {}))) * 100}%`,
                                  background: getShipClassColor(shipClass),
                                  transition: 'width 0.3s ease'
                                }}></div>
                              </div>
                              <div style={{
                                width: '50px',
                                textAlign: 'right',
                                fontWeight: 600,
                                fontSize: '0.875rem'
                              }}>
                                {count.toLocaleString()}
                              </div>
                            </div>
                          )})}
                      </div>
                    </div>
                  </div>
                </div>

                {/* Activity Timeline */}
                {conflict.hourly_activity && Object.keys(conflict.hourly_activity).length > 0 && (
                  <div className="card" style={{ background: 'var(--bg-surface)', marginBottom: '1.5rem' }}>
                    <h4 style={{ fontSize: '1rem', marginBottom: '1rem' }}>⏰ Activity Timeline (24h)</h4>
                    <div style={{ display: 'flex', alignItems: 'flex-end', gap: '2px', height: '150px' }}>
                      {Array.from({ length: 24 }, (_, hour) => {
                        const kills = conflict.hourly_activity?.[hour] || 0;
                        const maxKills = Math.max(...Object.values(conflict.hourly_activity || {}));
                        const heightPercent = maxKills > 0 ? (kills / maxKills) * 100 : 0;
                        const isPeak = conflict.peak_hours?.includes(hour);

                        return (
                          <div key={hour} style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '4px' }}>
                            <div style={{
                              width: '100%',
                              height: '150px',
                              display: 'flex',
                              alignItems: 'flex-end'
                            }}>
                              <div style={{
                                width: '100%',
                                height: `${heightPercent}%`,
                                background: isPeak ? 'var(--danger)' : 'var(--accent-blue)',
                                borderRadius: '2px 2px 0 0',
                                transition: 'height 0.3s ease',
                                position: 'relative',
                                cursor: 'help'
                              }} title={`${hour}:00 - ${kills} kills`}>
                              </div>
                            </div>
                            {hour % 3 === 0 && (
                              <div style={{ fontSize: '0.625rem', color: 'var(--text-secondary)' }}>
                                {hour}h
                              </div>
                            )}
                          </div>
                        );
                      })}
                    </div>
                    <div style={{ marginTop: '1rem', fontSize: '0.875rem' }}>
                      <span style={{ color: 'var(--text-secondary)' }}>Peak Activity Hours: </span>
                      <span style={{ fontWeight: 600, color: 'var(--danger)' }}>
                        {conflict.peak_hours?.map(h => `${h}:00`).join(', ') || 'N/A'}
                      </span>
                    </div>
                  </div>
                )}

                {/* Detailed System Hotspots */}
                {conflict.active_systems && conflict.active_systems.length > 0 && (
                  <div className="card" style={{ background: 'var(--bg-surface)' }}>
                    <h4 style={{ fontSize: '1rem', marginBottom: '1rem' }}>🗺️ Combat Zones</h4>
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(250px, 1fr))', gap: '1rem' }}>
                      {conflict.active_systems.map((system) => (
                        <div
                          key={system.system_id}
                          style={{
                            padding: '1rem',
                            background: 'var(--bg-elevated)',
                            borderRadius: '6px',
                            border: '1px solid var(--border-color)'
                          }}
                        >
                          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '0.5rem' }}>
                            <h5 style={{ fontSize: '0.875rem', fontWeight: 600, color: 'var(--warning)' }}>
                              {system.system_name}
                            </h5>
                            <span style={{
                              fontSize: '1.125rem',
                              fontWeight: 700,
                              color: 'var(--accent-blue)'
                            }}>
                              {system.kills}
                            </span>
                          </div>
                          <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                            {system.region_name}
                          </div>
                          <div style={{
                            marginTop: '0.5rem',
                            fontSize: '0.75rem',
                            color: system.security >= 0.5 ? 'var(--success)' :
                                   system.security > 0 ? 'var(--warning)' : 'var(--danger)'
                          }}>
                            Security: {system.security?.toFixed(1) || 'Unknown'}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
          );
        })}
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
