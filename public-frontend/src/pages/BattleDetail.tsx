import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { battleApi } from '../services/api';

interface ActiveBattle {
  battle_id: number;
  system_id: number;
  system_name: string;
  region_name: string;
  security: number;
  total_kills: number;
  total_isk_destroyed: number;
  last_milestone: number;
  started_at: string;
  last_kill_at: string;
  duration_minutes: number;
  telegram_sent: boolean;
  intensity: 'extreme' | 'high' | 'moderate' | 'low';
}

interface Killmail {
  killmail_id: number;
  killmail_time: string;
  solar_system_id: number;
  ship_type_id: number;
  ship_value: number;
  victim_character_id: number;
  victim_corporation_id: number;
  victim_alliance_id: number | null;
  attacker_count: number;
  is_solo: boolean;
  is_npc: boolean;
}

interface SystemDanger {
  system_id: number;
  danger_score: number;
  kills_24h: number;
  is_dangerous: boolean;
}

interface ShipClassData {
  system_id: number;
  hours: number;
  total_kills: number;
  group_by: string;
  breakdown: {
    [key: string]: number;
  };
}

export function BattleDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [battle, setBattle] = useState<ActiveBattle | null>(null);
  const [recentKills, setRecentKills] = useState<Killmail[]>([]);
  const [systemDanger, setSystemDanger] = useState<SystemDanger | null>(null);
  const [shipClasses, setShipClasses] = useState<ShipClassData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isExpanded, setIsExpanded] = useState(false);

  useEffect(() => {
    const fetchBattle = async () => {
      try {
        setLoading(true);
        setError(null);

        const data = await battleApi.getActiveBattles(1000);
        const foundBattle = data.battles?.find((b: ActiveBattle) => b.battle_id === parseInt(id || '0'));

        if (foundBattle) {
          setBattle(foundBattle);

          try {
            const [killsData, dangerData, shipClassData] = await Promise.all([
              battleApi.getLiveKills(foundBattle.system_id, 500),
              battleApi.getSystemDanger(foundBattle.system_id),
              battleApi.getSystemShipClasses(foundBattle.system_id, 24)
            ]);
            setRecentKills(killsData.kills || []);
            setSystemDanger(dangerData);
            setShipClasses(shipClassData);
          } catch (err) {
            console.error('Failed to fetch additional battle data:', err);
          }
        } else {
          setError('Battle not found or no longer active');
        }

        setLoading(false);
      } catch (err) {
        console.error('Failed to fetch battle:', err);
        setError('Failed to load battle details');
        setLoading(false);
      }
    };

    fetchBattle();
    const interval = setInterval(fetchBattle, 10000);
    return () => clearInterval(interval);
  }, [id]);

  if (loading) {
    return <div className="skeleton" style={{ height: '500px' }} />;
  }

  if (error || !battle) {
    return (
      <div className="card" style={{ textAlign: 'center', padding: '3rem' }}>
        <div style={{ fontSize: '4rem', marginBottom: '1rem' }}>⚠️</div>
        <h2 style={{ marginBottom: '1rem' }}>Battle Not Found</h2>
        <p style={{ color: 'var(--text-secondary)', marginBottom: '2rem' }}>
          {error || 'This battle is no longer active or does not exist.'}
        </p>
        <button
          onClick={() => navigate('/battle-map')}
          style={{
            padding: '0.75rem 1.5rem',
            background: 'var(--accent-blue)',
            color: 'white',
            border: 'none',
            borderRadius: '6px',
            fontSize: '1rem',
            fontWeight: 600,
            cursor: 'pointer',
          }}
        >
          ← Back to Battle Map
        </button>
      </div>
    );
  }

  const intensityColor =
    battle.intensity === 'extreme' ? 'var(--danger)' :
    battle.intensity === 'high' ? 'var(--warning)' :
    battle.intensity === 'moderate' ? 'var(--accent-blue)' :
    'var(--success)';

  const formatISK = (value: number): string => {
    if (value >= 1_000_000_000) return `${(value / 1_000_000_000).toFixed(2)}B`;
    if (value >= 1_000_000) return `${(value / 1_000_000).toFixed(2)}M`;
    if (value >= 1_000) return `${(value / 1_000).toFixed(2)}K`;
    return value.toFixed(0);
  };

  const formatTime = (timeStr: string): string => {
    const now = new Date();
    const then = new Date(timeStr);
    const diffMs = now.getTime() - then.getTime();
    const diffMins = Math.floor(diffMs / 60000);

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    const diffHours = Math.floor(diffMins / 60);
    if (diffHours < 24) return `${diffHours}h ago`;
    return `${Math.floor(diffHours / 24)}d ago`;
  };

  const avgKillValue = battle.total_kills > 0 ? battle.total_isk_destroyed / battle.total_kills : 0;
  const biggestKill = recentKills.length > 0 ? Math.max(...recentKills.map(k => k.ship_value)) : 0;
  const soloKills = recentKills.filter(k => k.is_solo).length;
  const fleetKills = recentKills.filter(k => !k.is_solo && !k.is_npc).length;

  return (
    <div>
      {/* Header */}
      <button
        onClick={() => navigate('/battle-map')}
        style={{
          padding: '0.5rem 1rem',
          background: 'var(--bg-elevated)',
          color: 'var(--text-primary)',
          border: '1px solid var(--border-color)',
          borderRadius: '6px',
          fontSize: '0.875rem',
          fontWeight: 600,
          cursor: 'pointer',
          marginBottom: '1.5rem',
        }}
      >
        ← Back to Battle Map
      </button>

      {/* Battle Overview Card */}
      <div
        className="card card-elevated"
        style={{
          marginBottom: '1.5rem',
          cursor: 'pointer',
          transition: 'all 0.2s ease'
        }}
        onClick={() => setIsExpanded(!isExpanded)}
      >
        {/* Battle Header */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '1rem', marginBottom: '1rem' }}>
          <div>
            <h1 style={{ fontSize: '1.5rem', marginBottom: '0.5rem' }}>
              ⚔️ {battle.system_name}
              <span style={{ marginLeft: '0.75rem', fontSize: '1rem', color: 'var(--text-secondary)' }}>
                {isExpanded ? '▼' : '▶'}
              </span>
            </h1>
            <div style={{
              display: 'flex',
              gap: '1rem',
              fontSize: '0.875rem',
              color: 'var(--text-secondary)',
              flexWrap: 'wrap'
            }}>
              <span>{battle.region_name}</span>
              <span>•</span>
              <span style={{
                color: battle.security >= 0.5 ? 'var(--success)' :
                       battle.security > 0 ? 'var(--warning)' : 'var(--danger)'
              }}>
                {battle.security.toFixed(1)} sec
              </span>
              <span>•</span>
              <span>{battle.duration_minutes < 60 ? `${battle.duration_minutes}m` : `${Math.floor(battle.duration_minutes / 60)}h ${battle.duration_minutes % 60}m`}</span>
              {systemDanger && systemDanger.is_dangerous && (
                <>
                  <span>•</span>
                  <span style={{ color: 'var(--danger)', fontWeight: 600 }}>
                    ⚠️ Dangerous System
                  </span>
                </>
              )}
            </div>
          </div>

          <div style={{
            padding: '0.5rem 1rem',
            borderRadius: '6px',
            background: intensityColor,
            color: 'white',
            fontSize: '0.75rem',
            fontWeight: 700,
            textTransform: 'uppercase'
          }}>
            {battle.intensity} Intensity
          </div>
        </div>

        {/* Combat Statistics Grid */}
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
          gap: '1.5rem',
          marginTop: '1rem'
        }}>
          {/* Total Kills */}
          <div>
            <p style={{ fontSize: '0.875rem', color: 'var(--text-secondary)', marginBottom: '0.5rem' }}>
              Total Kills
            </p>
            <p style={{ fontSize: '2rem', fontWeight: 700, color: 'var(--accent-blue)' }}>
              {battle.total_kills.toLocaleString()}
            </p>
          </div>

          {/* ISK Destroyed */}
          <div>
            <p style={{ fontSize: '0.875rem', color: 'var(--text-secondary)', marginBottom: '0.5rem' }}>
              ISK Destroyed
            </p>
            <p style={{ fontSize: '2rem', fontWeight: 700, color: 'var(--danger)', fontFamily: 'monospace' }}>
              {(battle.total_isk_destroyed / 1_000_000_000).toFixed(2)}B
            </p>
          </div>

          {/* Avg Kill Value */}
          <div>
            <p style={{ fontSize: '0.875rem', color: 'var(--text-secondary)', marginBottom: '0.5rem' }}>
              Avg Kill Value
            </p>
            <p style={{ fontSize: '2rem', fontWeight: 700, color: 'var(--warning)', fontFamily: 'monospace' }}>
              {formatISK(avgKillValue)}
            </p>
          </div>

          {/* System Activity */}
          {systemDanger && (
            <div>
              <p style={{ fontSize: '0.875rem', color: 'var(--text-secondary)', marginBottom: '0.5rem' }}>
                24h System Activity
              </p>
              <p style={{ fontSize: '2rem', fontWeight: 700, color: 'var(--success)' }}>
                {systemDanger.kills_24h} kills
              </p>
            </div>
          )}
        </div>

        {/* EXPANDED DETAIL VIEW */}
        {isExpanded && (
          <div style={{
            marginTop: '1.5rem',
            paddingTop: '1.5rem',
            borderTop: '2px solid var(--border-color)'
          }}>
            <h3 style={{ fontSize: '1.125rem', marginBottom: '1rem', color: 'var(--accent-purple)' }}>
              📊 Detailed Battle Intelligence
            </h3>

            {/* Economic Analysis */}
            <div className="card" style={{ background: 'var(--bg-primary)', marginBottom: '1.5rem' }}>
              <h4 style={{ fontSize: '1rem', marginBottom: '1rem' }}>💰 Economic Analysis</h4>
              <div style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
                gap: '1rem'
              }}>
                <div>
                  <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>Average Kill Value</p>
                  <p style={{ fontSize: '1.5rem', fontWeight: 700, fontFamily: 'monospace', color: 'var(--warning)' }}>
                    {formatISK(avgKillValue)} ISK
                  </p>
                </div>
                <div>
                  <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>Biggest Kill (Recent)</p>
                  <p style={{ fontSize: '1.5rem', fontWeight: 700, fontFamily: 'monospace', color: 'var(--danger)' }}>
                    {formatISK(biggestKill)} ISK
                  </p>
                </div>
                <div>
                  <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>Solo Kills (Recent {recentKills.length})</p>
                  <p style={{ fontSize: '1.5rem', fontWeight: 700, color: 'var(--accent-blue)' }}>
                    {soloKills}
                  </p>
                </div>
                <div>
                  <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>Fleet Kills (Recent {recentKills.length})</p>
                  <p style={{ fontSize: '1.5rem', fontWeight: 700, color: 'var(--danger)' }}>
                    {fleetKills}
                  </p>
                </div>
              </div>
            </div>

            {/* Ship Class Breakdown */}
            {shipClasses && shipClasses.total_kills > 0 && (
              <div className="card" style={{ background: 'var(--bg-primary)', marginBottom: '1.5rem' }}>
                <h4 style={{ fontSize: '1rem', marginBottom: '1rem' }}>🚀 Ship Class Breakdown</h4>
                <p style={{ fontSize: '0.875rem', color: 'var(--text-secondary)', marginBottom: '1rem' }}>
                  Analysis of {shipClasses.total_kills} kills in the last {shipClasses.hours} hours
                </p>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                  {Object.entries(shipClasses.breakdown)
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
                          case 'logistics': return '#22d3ee';
                          case 'stealth_bomber': return '#dc2626';
                          case 'industrial': return '#8b949e';
                          case 'hauler': return '#64748b';
                          case 'mining': return '#fb923c';
                          case 'capsule': return '#6b7280';
                          default: return 'var(--text-tertiary)';
                        }
                      };
                      const getShipClassLabel = (cls: string) => {
                        // Handle category:role format (e.g., "frigate:assault")
                        if (cls.includes(':')) {
                          const [category, role] = cls.split(':');
                          const categoryLabel = category.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
                          const roleLabel = role.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
                          return `${categoryLabel} (${roleLabel})`;
                        }

                        // Handle single values (category or role)
                        switch(cls) {
                          case 'battlecruiser': return 'Battlecruiser';
                          case 'stealth_bomber': return 'Stealth Bomber';
                          case 'heavy_assault': return 'Heavy Assault';
                          case 'covert_ops': return 'Covert Ops';
                          case 'electronic_attack': return 'Electronic Attack';
                          case 'heavy_interdictor': return 'Heavy Interdictor';
                          case 'capsule': return 'Capsule/Pod';
                          default: return cls.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
                        }
                      };

                      const maxCount = Math.max(...Object.values(shipClasses.breakdown));
                      const percentage = (count / maxCount) * 100;

                      return (
                        <div key={shipClass} style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                          <div style={{
                            width: '140px',
                            fontSize: '0.875rem',
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
                              width: `${percentage}%`,
                              background: getShipClassColor(shipClass),
                              transition: 'width 0.3s ease',
                              display: 'flex',
                              alignItems: 'center',
                              justifyContent: 'flex-end',
                              paddingRight: '0.5rem'
                            }}>
                              {percentage > 15 && (
                                <span style={{
                                  fontSize: '0.75rem',
                                  fontWeight: 600,
                                  color: 'white'
                                }}>
                                  {count}
                                </span>
                              )}
                            </div>
                          </div>
                          <div style={{
                            width: '50px',
                            textAlign: 'right',
                            fontWeight: 600,
                            fontSize: '0.875rem'
                          }}>
                            {count}
                          </div>
                        </div>
                      );
                    })}
                </div>
              </div>
            )}

            {/* Recent Killmails Table */}
            <div className="card" style={{ background: 'var(--bg-primary)', marginBottom: '1.5rem' }}>
              <h4 style={{ fontSize: '1rem', marginBottom: '1rem' }}>🔴 Recent Killmails</h4>

              {recentKills.length === 0 ? (
                <div style={{
                  padding: '3rem',
                  textAlign: 'center',
                  color: 'var(--text-secondary)'
                }}>
                  <div style={{ fontSize: '3rem', marginBottom: '1rem' }}>📭</div>
                  <p>No recent kills available</p>
                </div>
              ) : (
                <div style={{ overflowX: 'auto' }}>
                  <table style={{
                    width: '100%',
                    borderCollapse: 'collapse',
                    fontSize: '0.875rem'
                  }}>
                    <thead>
                      <tr style={{
                        borderBottom: '2px solid var(--border-color)',
                        textAlign: 'left'
                      }}>
                        <th style={{ padding: '0.75rem', color: 'var(--text-secondary)', fontWeight: 600 }}>Time</th>
                        <th style={{ padding: '0.75rem', color: 'var(--text-secondary)', fontWeight: 600 }}>Ship Value</th>
                        <th style={{ padding: '0.75rem', color: 'var(--text-secondary)', fontWeight: 600 }}>Type</th>
                        <th style={{ padding: '0.75rem', color: 'var(--text-secondary)', fontWeight: 600 }}>Attackers</th>
                        <th style={{ padding: '0.75rem', color: 'var(--text-secondary)', fontWeight: 600 }}>Link</th>
                      </tr>
                    </thead>
                    <tbody>
                      {recentKills.map((kill) => (
                        <tr
                          key={kill.killmail_id}
                          style={{
                            borderBottom: '1px solid var(--border-color)',
                            transition: 'background 0.2s'
                          }}
                          onMouseOver={(e) => {
                            (e.currentTarget as HTMLElement).style.background = 'var(--bg-elevated)';
                          }}
                          onMouseOut={(e) => {
                            (e.currentTarget as HTMLElement).style.background = 'transparent';
                          }}
                        >
                          <td style={{ padding: '0.75rem', color: 'var(--text-secondary)' }}>
                            {formatTime(kill.killmail_time)}
                          </td>
                          <td style={{ padding: '0.75rem', fontWeight: 600, color: 'var(--danger)', fontFamily: 'monospace' }}>
                            {formatISK(kill.ship_value)}
                          </td>
                          <td style={{ padding: '0.75rem' }}>
                            {kill.is_solo ? (
                              <span style={{
                                padding: '0.25rem 0.5rem',
                                borderRadius: '4px',
                                background: 'rgba(88, 166, 255, 0.2)',
                                color: 'var(--accent-blue)',
                                fontSize: '0.75rem',
                                fontWeight: 600
                              }}>
                                SOLO
                              </span>
                            ) : kill.is_npc ? (
                              <span style={{
                                padding: '0.25rem 0.5rem',
                                borderRadius: '4px',
                                background: 'rgba(210, 153, 34, 0.2)',
                                color: 'var(--warning)',
                                fontSize: '0.75rem',
                                fontWeight: 600
                              }}>
                                NPC
                              </span>
                            ) : (
                              <span style={{
                                padding: '0.25rem 0.5rem',
                                borderRadius: '4px',
                                background: 'rgba(248, 81, 73, 0.2)',
                                color: 'var(--danger)',
                                fontSize: '0.75rem',
                                fontWeight: 600
                              }}>
                                FLEET
                              </span>
                            )}
                          </td>
                          <td style={{ padding: '0.75rem', color: 'var(--text-primary)' }}>
                            {kill.attacker_count}
                          </td>
                          <td style={{ padding: '0.75rem' }}>
                            <a
                              href={`https://zkillboard.com/kill/${kill.killmail_id}/`}
                              target="_blank"
                              rel="noopener noreferrer"
                              style={{
                                color: 'var(--accent-blue)',
                                textDecoration: 'none',
                                fontWeight: 600
                              }}
                              onClick={(e) => e.stopPropagation()}
                            >
                              zkill →
                            </a>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>

            {/* Battle Timeline */}
            <div className="card" style={{ background: 'var(--bg-primary)' }}>
              <h4 style={{ fontSize: '1rem', marginBottom: '1rem' }}>📅 Battle Timeline</h4>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                {/* Started */}
                <div style={{
                  padding: '1rem',
                  background: 'var(--bg-elevated)',
                  borderRadius: '6px',
                  borderLeft: '4px solid var(--success)'
                }}>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginBottom: '0.25rem' }}>
                    Battle Started
                  </div>
                  <div style={{ fontSize: '1rem', fontWeight: 600 }}>
                    {new Date(battle.started_at).toLocaleString('de-DE', {
                      year: 'numeric',
                      month: '2-digit',
                      day: '2-digit',
                      hour: '2-digit',
                      minute: '2-digit',
                      second: '2-digit'
                    })}
                  </div>
                </div>

                {/* Last Milestone */}
                {battle.last_milestone > 0 && (
                  <div style={{
                    padding: '1rem',
                    background: 'var(--bg-elevated)',
                    borderRadius: '6px',
                    borderLeft: '4px solid var(--warning)'
                  }}>
                    <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginBottom: '0.25rem' }}>
                      Last Milestone Reached
                    </div>
                    <div style={{ fontSize: '1rem', fontWeight: 600 }}>
                      {battle.last_milestone} kills
                    </div>
                  </div>
                )}

                {/* Last Kill */}
                <div style={{
                  padding: '1rem',
                  background: 'var(--bg-elevated)',
                  borderRadius: '6px',
                  borderLeft: '4px solid var(--accent-blue)'
                }}>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginBottom: '0.25rem' }}>
                    Last Kill At
                  </div>
                  <div style={{ fontSize: '1rem', fontWeight: 600 }}>
                    {new Date(battle.last_kill_at).toLocaleString('de-DE', {
                      year: 'numeric',
                      month: '2-digit',
                      day: '2-digit',
                      hour: '2-digit',
                      minute: '2-digit',
                      second: '2-digit'
                    })}
                  </div>
                </div>

                {/* Telegram Alert Status */}
                <div style={{
                  padding: '1rem',
                  background: 'var(--bg-elevated)',
                  borderRadius: '6px',
                  borderLeft: `4px solid ${battle.telegram_sent ? 'var(--accent-purple)' : 'var(--text-tertiary)'}`
                }}>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginBottom: '0.25rem' }}>
                    Telegram Alert
                  </div>
                  <div style={{
                    fontSize: '1rem',
                    fontWeight: 600,
                    color: battle.telegram_sent ? 'var(--accent-purple)' : 'var(--text-tertiary)'
                  }}>
                    {battle.telegram_sent ? '✓ Alert Sent' : '✗ No Alert'}
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
