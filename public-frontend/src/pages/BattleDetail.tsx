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
  ship_name?: string;
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
  battle_id?: number;
  system_id?: number;
  hours?: number;
  total_kills: number;
  group_by: string;
  breakdown: {
    [key: string]: number;
  };
}

interface ParticipantAlliance {
  alliance_id: number;
  alliance_name: string;
  kills?: number;
  losses?: number;
  isk_lost?: number;
  corps_involved: number;
}

interface ParticipantCorp {
  corporation_id: number;
  corporation_name: string;
  alliance_id: number | null;
  kills?: number;
  losses?: number;
  isk_lost?: number;
}

interface BattleParticipants {
  battle_id: number;
  attackers: {
    alliances: ParticipantAlliance[];
    corporations: ParticipantCorp[];
    total_alliances: number;
    total_kills: number;
  };
  defenders: {
    alliances: ParticipantAlliance[];
    corporations: ParticipantCorp[];
    total_alliances: number;
    total_losses: number;
    total_isk_lost: number;
  };
}

export function BattleDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [battle, setBattle] = useState<ActiveBattle | null>(null);
  const [recentKills, setRecentKills] = useState<Killmail[]>([]);
  const [systemDanger, setSystemDanger] = useState<SystemDanger | null>(null);
  const [shipClasses, setShipClasses] = useState<ShipClassData | null>(null);
  const [participants, setParticipants] = useState<BattleParticipants | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

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
            const [killsData, dangerData, shipClassData, participantsData] = await Promise.all([
              battleApi.getBattleKills(foundBattle.battle_id, 500),
              battleApi.getSystemDanger(foundBattle.system_id),
              battleApi.getBattleShipClasses(foundBattle.battle_id, 'category'),
              battleApi.getBattleParticipants(foundBattle.battle_id)
            ]);
            setRecentKills(killsData.kills || []);
            setSystemDanger(dangerData);
            setShipClasses(shipClassData);
            setParticipants(participantsData);
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
  const npcKills = recentKills.filter(k => k.is_npc).length;

  const getShipClassColor = (cls: string) => {
    const lowerCls = cls.toLowerCase();
    if (lowerCls.includes('capital') || lowerCls.includes('titan') || lowerCls.includes('supercarrier')) return 'var(--danger)';
    if (lowerCls.includes('battleship')) return '#ff6b00';
    if (lowerCls.includes('battlecruiser')) return '#ff9500';
    if (lowerCls.includes('cruiser')) return 'var(--accent-blue)';
    if (lowerCls.includes('destroyer')) return '#a855f7';
    if (lowerCls.includes('frigate')) return 'var(--success)';
    if (lowerCls.includes('logistics')) return '#22d3ee';
    if (lowerCls.includes('stealth') || lowerCls.includes('bomber')) return '#dc2626';
    if (lowerCls.includes('industrial') || lowerCls.includes('hauler')) return '#8b949e';
    if (lowerCls.includes('mining')) return '#fb923c';
    if (lowerCls.includes('capsule') || lowerCls.includes('pod')) return '#6b7280';
    return 'var(--text-tertiary)';
  };

  const getShipClassLabel = (cls: string) => {
    if (cls.includes(':')) {
      const [category, role] = cls.split(':');
      const categoryLabel = category.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
      const roleLabel = role.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
      return `${categoryLabel} (${roleLabel})`;
    }
    return cls.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
  };

  return (
    <div>
      {/* Back Button */}
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

      {/* Battle Header Card */}
      <div className="card card-elevated" style={{ marginBottom: '1.5rem' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '1rem', marginBottom: '1.5rem' }}>
          <div>
            <h1 style={{ fontSize: '1.75rem', marginBottom: '0.5rem' }}>
              ⚔️ Battle in {battle.system_name}
            </h1>
            <div style={{
              display: 'flex',
              gap: '1rem',
              fontSize: '0.875rem',
              color: 'var(--text-secondary)',
              flexWrap: 'wrap'
            }}>
              <span>📍 {battle.region_name}</span>
              <span>•</span>
              <span style={{
                color: battle.security >= 0.5 ? 'var(--success)' :
                       battle.security > 0 ? 'var(--warning)' : 'var(--danger)',
                fontWeight: 600
              }}>
                {battle.security.toFixed(1)} Security
              </span>
              <span>•</span>
              <span>⏱️ {battle.duration_minutes < 60 ? `${battle.duration_minutes}m` : `${Math.floor(battle.duration_minutes / 60)}h ${battle.duration_minutes % 60}m`} duration</span>
              {systemDanger && systemDanger.is_dangerous && (
                <>
                  <span>•</span>
                  <span style={{ color: 'var(--danger)', fontWeight: 600 }}>
                    ⚠️ High Activity System
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
            fontSize: '0.875rem',
            fontWeight: 700,
            textTransform: 'uppercase'
          }}>
            {battle.intensity} Intensity
          </div>
        </div>

        {/* Main Statistics Grid */}
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
          gap: '1.5rem'
        }}>
          <div style={{ padding: '1rem', background: 'var(--bg-primary)', borderRadius: '8px', borderLeft: '4px solid var(--accent-blue)' }}>
            <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginBottom: '0.5rem', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
              Total Kills
            </p>
            <p style={{ fontSize: '2rem', fontWeight: 700, color: 'var(--accent-blue)' }}>
              {battle.total_kills.toLocaleString()}
            </p>
          </div>

          <div style={{ padding: '1rem', background: 'var(--bg-primary)', borderRadius: '8px', borderLeft: '4px solid var(--danger)' }}>
            <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginBottom: '0.5rem', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
              ISK Destroyed
            </p>
            <p style={{ fontSize: '2rem', fontWeight: 700, color: 'var(--danger)', fontFamily: 'monospace' }}>
              {formatISK(battle.total_isk_destroyed)}
            </p>
          </div>

          <div style={{ padding: '1rem', background: 'var(--bg-primary)', borderRadius: '8px', borderLeft: '4px solid var(--warning)' }}>
            <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginBottom: '0.5rem', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
              Avg Kill Value
            </p>
            <p style={{ fontSize: '2rem', fontWeight: 700, color: 'var(--warning)', fontFamily: 'monospace' }}>
              {formatISK(avgKillValue)}
            </p>
          </div>

          <div style={{ padding: '1rem', background: 'var(--bg-primary)', borderRadius: '8px', borderLeft: '4px solid var(--success)' }}>
            <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginBottom: '0.5rem', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
              Biggest Kill
            </p>
            <p style={{ fontSize: '2rem', fontWeight: 700, color: 'var(--success)', fontFamily: 'monospace' }}>
              {formatISK(biggestKill)}
            </p>
          </div>
        </div>
      </div>

      {/* Battle Participants Card */}
      {participants && (participants.attackers.alliances.length > 0 || participants.defenders.alliances.length > 0) && (
        <div className="card" style={{ marginBottom: '1.5rem' }}>
          <h3 style={{ fontSize: '1.125rem', marginBottom: '1rem' }}>⚔️ Konfliktparteien</h3>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '1.5rem' }}>
            {/* Attackers */}
            <div style={{ padding: '1rem', background: 'var(--bg-primary)', borderRadius: '8px', borderLeft: '4px solid var(--danger)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
                <h4 style={{ margin: 0, color: 'var(--danger)', fontSize: '1rem' }}>
                  🗡️ Angreifer
                </h4>
                <span style={{ fontSize: '0.875rem', color: 'var(--text-secondary)' }}>
                  {participants.attackers.total_kills} Kills
                </span>
              </div>

              {participants.attackers.alliances.length > 0 ? (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                  {participants.attackers.alliances.map((alliance) => (
                    <div key={alliance.alliance_id} style={{
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center',
                      padding: '0.5rem',
                      background: 'var(--bg-elevated)',
                      borderRadius: '4px'
                    }}>
                      <a
                        href={`https://zkillboard.com/alliance/${alliance.alliance_id}/`}
                        target="_blank"
                        rel="noopener noreferrer"
                        style={{ color: 'var(--accent-blue)', textDecoration: 'none', fontWeight: 600 }}
                      >
                        {alliance.alliance_name}
                      </a>
                      <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
                        <span style={{
                          padding: '0.2rem 0.5rem',
                          borderRadius: '4px',
                          background: 'rgba(248, 81, 73, 0.2)',
                          color: 'var(--danger)',
                          fontSize: '0.75rem',
                          fontWeight: 600
                        }}>
                          {alliance.kills} kills
                        </span>
                        <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                          ({alliance.corps_involved} corps)
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <p style={{ color: 'var(--text-secondary)', fontSize: '0.875rem' }}>Keine Alliance-Daten</p>
              )}

              {/* Top Attacker Corps */}
              {participants.attackers.corporations.length > 0 && (
                <div style={{ marginTop: '1rem', paddingTop: '1rem', borderTop: '1px solid var(--border-color)' }}>
                  <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginBottom: '0.5rem' }}>Top Corporations</p>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
                    {participants.attackers.corporations.slice(0, 5).map((corp) => (
                      <div key={corp.corporation_id} style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem' }}>
                        <a
                          href={`https://zkillboard.com/corporation/${corp.corporation_id}/`}
                          target="_blank"
                          rel="noopener noreferrer"
                          style={{ color: 'var(--text-primary)', textDecoration: 'none' }}
                        >
                          {corp.corporation_name}
                        </a>
                        <span style={{ color: 'var(--danger)', fontWeight: 600 }}>{corp.kills} kills</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {/* Defenders */}
            <div style={{ padding: '1rem', background: 'var(--bg-primary)', borderRadius: '8px', borderLeft: '4px solid var(--accent-blue)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
                <h4 style={{ margin: 0, color: 'var(--accent-blue)', fontSize: '1rem' }}>
                  🛡️ Verteidiger
                </h4>
                <span style={{ fontSize: '0.875rem', color: 'var(--text-secondary)' }}>
                  {participants.defenders.total_losses} Verluste
                </span>
              </div>

              {participants.defenders.alliances.length > 0 ? (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                  {participants.defenders.alliances.map((alliance) => (
                    <div key={alliance.alliance_id} style={{
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center',
                      padding: '0.5rem',
                      background: 'var(--bg-elevated)',
                      borderRadius: '4px'
                    }}>
                      <a
                        href={`https://zkillboard.com/alliance/${alliance.alliance_id}/`}
                        target="_blank"
                        rel="noopener noreferrer"
                        style={{ color: 'var(--accent-blue)', textDecoration: 'none', fontWeight: 600 }}
                      >
                        {alliance.alliance_name}
                      </a>
                      <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
                        <span style={{
                          padding: '0.2rem 0.5rem',
                          borderRadius: '4px',
                          background: 'rgba(88, 166, 255, 0.2)',
                          color: 'var(--accent-blue)',
                          fontSize: '0.75rem',
                          fontWeight: 600
                        }}>
                          {alliance.losses} lost
                        </span>
                        <span style={{ fontSize: '0.75rem', color: 'var(--danger)', fontFamily: 'monospace' }}>
                          {formatISK(alliance.isk_lost || 0)}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <p style={{ color: 'var(--text-secondary)', fontSize: '0.875rem' }}>Keine Alliance-Daten</p>
              )}

              {/* ISK Summary */}
              {participants.defenders.total_isk_lost > 0 && (
                <div style={{ marginTop: '1rem', paddingTop: '1rem', borderTop: '1px solid var(--border-color)' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>Gesamt ISK Verlust</span>
                    <span style={{ fontSize: '1rem', fontWeight: 700, color: 'var(--danger)', fontFamily: 'monospace' }}>
                      {formatISK(participants.defenders.total_isk_lost)}
                    </span>
                  </div>
                </div>
              )}

              {/* Top Victim Corps */}
              {participants.defenders.corporations.length > 0 && (
                <div style={{ marginTop: '1rem', paddingTop: '1rem', borderTop: '1px solid var(--border-color)' }}>
                  <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginBottom: '0.5rem' }}>Top Corporations (Verluste)</p>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
                    {participants.defenders.corporations.slice(0, 5).map((corp) => (
                      <div key={corp.corporation_id} style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem' }}>
                        <a
                          href={`https://zkillboard.com/corporation/${corp.corporation_id}/`}
                          target="_blank"
                          rel="noopener noreferrer"
                          style={{ color: 'var(--text-primary)', textDecoration: 'none' }}
                        >
                          {corp.corporation_name}
                        </a>
                        <span style={{ color: 'var(--accent-blue)' }}>{corp.losses} lost • <span style={{ color: 'var(--danger)' }}>{formatISK(corp.isk_lost || 0)}</span></span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Two Column Layout */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(400px, 1fr))', gap: '1.5rem', marginBottom: '1.5rem' }}>

        {/* Combat Analysis Card */}
        <div className="card">
          <h3 style={{ fontSize: '1.125rem', marginBottom: '1rem' }}>📊 Combat Analysis</h3>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', marginBottom: '1.5rem' }}>
            <div style={{ padding: '1rem', background: 'var(--bg-primary)', borderRadius: '6px', textAlign: 'center' }}>
              <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginBottom: '0.25rem' }}>Solo Kills</p>
              <p style={{ fontSize: '1.5rem', fontWeight: 700, color: 'var(--accent-blue)' }}>{soloKills}</p>
            </div>
            <div style={{ padding: '1rem', background: 'var(--bg-primary)', borderRadius: '6px', textAlign: 'center' }}>
              <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginBottom: '0.25rem' }}>Fleet Kills</p>
              <p style={{ fontSize: '1.5rem', fontWeight: 700, color: 'var(--danger)' }}>{fleetKills}</p>
            </div>
            <div style={{ padding: '1rem', background: 'var(--bg-primary)', borderRadius: '6px', textAlign: 'center' }}>
              <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginBottom: '0.25rem' }}>NPC Kills</p>
              <p style={{ fontSize: '1.5rem', fontWeight: 700, color: 'var(--warning)' }}>{npcKills}</p>
            </div>
            <div style={{ padding: '1rem', background: 'var(--bg-primary)', borderRadius: '6px', textAlign: 'center' }}>
              <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginBottom: '0.25rem' }}>24h System Kills</p>
              <p style={{ fontSize: '1.5rem', fontWeight: 700, color: 'var(--success)' }}>{systemDanger?.kills_24h || 0}</p>
            </div>
          </div>

          {/* Kill Type Distribution Bar */}
          {recentKills.length > 0 && (
            <div>
              <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginBottom: '0.5rem' }}>Kill Type Distribution</p>
              <div style={{ display: 'flex', height: '24px', borderRadius: '4px', overflow: 'hidden' }}>
                {soloKills > 0 && (
                  <div style={{
                    width: `${(soloKills / recentKills.length) * 100}%`,
                    background: 'var(--accent-blue)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    fontSize: '0.75rem',
                    fontWeight: 600,
                    color: 'white'
                  }}>
                    {soloKills > 2 && `${soloKills}`}
                  </div>
                )}
                {fleetKills > 0 && (
                  <div style={{
                    width: `${(fleetKills / recentKills.length) * 100}%`,
                    background: 'var(--danger)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    fontSize: '0.75rem',
                    fontWeight: 600,
                    color: 'white'
                  }}>
                    {fleetKills > 2 && `${fleetKills}`}
                  </div>
                )}
                {npcKills > 0 && (
                  <div style={{
                    width: `${(npcKills / recentKills.length) * 100}%`,
                    background: 'var(--warning)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    fontSize: '0.75rem',
                    fontWeight: 600,
                    color: 'white'
                  }}>
                    {npcKills > 2 && `${npcKills}`}
                  </div>
                )}
              </div>
              <div style={{ display: 'flex', gap: '1rem', marginTop: '0.5rem', fontSize: '0.75rem' }}>
                <span><span style={{ color: 'var(--accent-blue)' }}>●</span> Solo</span>
                <span><span style={{ color: 'var(--danger)' }}>●</span> Fleet</span>
                <span><span style={{ color: 'var(--warning)' }}>●</span> NPC</span>
              </div>
            </div>
          )}
        </div>

        {/* Ship Class Breakdown Card */}
        <div className="card">
          <h3 style={{ fontSize: '1.125rem', marginBottom: '1rem' }}>🚀 Ship Classes Destroyed</h3>

          {shipClasses && shipClasses.total_kills > 0 ? (
            <>
              <p style={{ fontSize: '0.875rem', color: 'var(--text-secondary)', marginBottom: '1rem' }}>
                {shipClasses.total_kills} ships analyzed during this battle
              </p>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                {Object.entries(shipClasses.breakdown)
                  .filter(([_, count]) => count > 0)
                  .sort((a, b) => b[1] - a[1])
                  .slice(0, 8)
                  .map(([shipClass, count]) => {
                    const maxCount = Math.max(...Object.values(shipClasses.breakdown));
                    const percentage = (count / maxCount) * 100;

                    return (
                      <div key={shipClass} style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                        <div style={{ width: '120px', fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                          {getShipClassLabel(shipClass)}
                        </div>
                        <div style={{ flex: 1, height: '20px', background: 'var(--bg-primary)', borderRadius: '4px', overflow: 'hidden' }}>
                          <div style={{
                            height: '100%',
                            width: `${percentage}%`,
                            background: getShipClassColor(shipClass),
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'flex-end',
                            paddingRight: '0.5rem',
                            transition: 'width 0.3s ease'
                          }}>
                            {percentage > 20 && (
                              <span style={{ fontSize: '0.7rem', fontWeight: 600, color: 'white' }}>{count}</span>
                            )}
                          </div>
                        </div>
                        <div style={{ width: '35px', textAlign: 'right', fontWeight: 600, fontSize: '0.875rem' }}>
                          {count}
                        </div>
                      </div>
                    );
                  })}
              </div>
            </>
          ) : (
            <div style={{ padding: '2rem', textAlign: 'center', color: 'var(--text-secondary)' }}>
              <p>No ship class data available</p>
            </div>
          )}
        </div>
      </div>

      {/* Battle Timeline Card */}
      <div className="card" style={{ marginBottom: '1.5rem' }}>
        <h3 style={{ fontSize: '1.125rem', marginBottom: '1rem' }}>📅 Battle Timeline</h3>
        <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap' }}>
          <div style={{ flex: '1 1 200px', padding: '1rem', background: 'var(--bg-primary)', borderRadius: '6px', borderLeft: '4px solid var(--success)' }}>
            <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginBottom: '0.25rem' }}>Battle Started</p>
            <p style={{ fontSize: '0.875rem', fontWeight: 600 }}>
              {new Date(battle.started_at).toLocaleString('de-DE')}
            </p>
          </div>
          <div style={{ flex: '1 1 200px', padding: '1rem', background: 'var(--bg-primary)', borderRadius: '6px', borderLeft: '4px solid var(--accent-blue)' }}>
            <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginBottom: '0.25rem' }}>Last Kill</p>
            <p style={{ fontSize: '0.875rem', fontWeight: 600 }}>
              {new Date(battle.last_kill_at).toLocaleString('de-DE')}
            </p>
          </div>
          {battle.last_milestone > 0 && (
            <div style={{ flex: '1 1 200px', padding: '1rem', background: 'var(--bg-primary)', borderRadius: '6px', borderLeft: '4px solid var(--warning)' }}>
              <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginBottom: '0.25rem' }}>Last Milestone</p>
              <p style={{ fontSize: '0.875rem', fontWeight: 600 }}>{battle.last_milestone} kills</p>
            </div>
          )}
          <div style={{ flex: '1 1 200px', padding: '1rem', background: 'var(--bg-primary)', borderRadius: '6px', borderLeft: `4px solid ${battle.telegram_sent ? 'var(--accent-purple)' : 'var(--text-tertiary)'}` }}>
            <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginBottom: '0.25rem' }}>Telegram Alert</p>
            <p style={{ fontSize: '0.875rem', fontWeight: 600, color: battle.telegram_sent ? 'var(--accent-purple)' : 'var(--text-tertiary)' }}>
              {battle.telegram_sent ? '✓ Sent' : '✗ Not Sent'}
            </p>
          </div>
        </div>
      </div>

      {/* Killmails Table Card */}
      <div className="card">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
          <h3 style={{ fontSize: '1.125rem', margin: 0 }}>🔴 Battle Killmails</h3>
          {recentKills.length > 0 && (
            <span style={{ fontSize: '0.875rem', color: 'var(--text-secondary)', padding: '0.25rem 0.75rem', background: 'var(--bg-primary)', borderRadius: '4px' }}>
              {recentKills.length} {recentKills.length === 1 ? 'kill' : 'kills'}
            </span>
          )}
        </div>

        {recentKills.length === 0 ? (
          <div style={{ padding: '3rem', textAlign: 'center', color: 'var(--text-secondary)' }}>
            <div style={{ fontSize: '3rem', marginBottom: '1rem' }}>📭</div>
            <p style={{ fontWeight: 600, marginBottom: '0.5rem' }}>No detailed killmail data</p>
            <p style={{ fontSize: '0.875rem' }}>
              Battle reports {battle.total_kills} kills but detailed records are not yet available.
            </p>
          </div>
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.875rem' }}>
              <thead>
                <tr style={{ borderBottom: '2px solid var(--border-color)', textAlign: 'left' }}>
                  <th style={{ padding: '0.75rem', color: 'var(--text-secondary)', fontWeight: 600 }}>Time</th>
                  <th style={{ padding: '0.75rem', color: 'var(--text-secondary)', fontWeight: 600 }}>Ship</th>
                  <th style={{ padding: '0.75rem', color: 'var(--text-secondary)', fontWeight: 600 }}>Value</th>
                  <th style={{ padding: '0.75rem', color: 'var(--text-secondary)', fontWeight: 600 }}>Type</th>
                  <th style={{ padding: '0.75rem', color: 'var(--text-secondary)', fontWeight: 600 }}>Attackers</th>
                  <th style={{ padding: '0.75rem', color: 'var(--text-secondary)', fontWeight: 600 }}>Link</th>
                </tr>
              </thead>
              <tbody>
                {recentKills.slice(0, 50).map((kill) => (
                  <tr
                    key={kill.killmail_id}
                    style={{ borderBottom: '1px solid var(--border-color)', transition: 'background 0.2s' }}
                    onMouseOver={(e) => { (e.currentTarget as HTMLElement).style.background = 'var(--bg-elevated)'; }}
                    onMouseOut={(e) => { (e.currentTarget as HTMLElement).style.background = 'transparent'; }}
                  >
                    <td style={{ padding: '0.75rem', color: 'var(--text-secondary)', whiteSpace: 'nowrap' }}>
                      {formatTime(kill.killmail_time)}
                    </td>
                    <td style={{ padding: '0.75rem', color: 'var(--text-primary)' }}>
                      {kill.ship_name || `Ship #${kill.ship_type_id}`}
                    </td>
                    <td style={{ padding: '0.75rem', fontWeight: 600, color: 'var(--danger)', fontFamily: 'monospace' }}>
                      {formatISK(kill.ship_value)}
                    </td>
                    <td style={{ padding: '0.75rem' }}>
                      {kill.is_solo ? (
                        <span style={{ padding: '0.2rem 0.5rem', borderRadius: '4px', background: 'rgba(88, 166, 255, 0.2)', color: 'var(--accent-blue)', fontSize: '0.75rem', fontWeight: 600 }}>SOLO</span>
                      ) : kill.is_npc ? (
                        <span style={{ padding: '0.2rem 0.5rem', borderRadius: '4px', background: 'rgba(210, 153, 34, 0.2)', color: 'var(--warning)', fontSize: '0.75rem', fontWeight: 600 }}>NPC</span>
                      ) : (
                        <span style={{ padding: '0.2rem 0.5rem', borderRadius: '4px', background: 'rgba(248, 81, 73, 0.2)', color: 'var(--danger)', fontSize: '0.75rem', fontWeight: 600 }}>FLEET</span>
                      )}
                    </td>
                    <td style={{ padding: '0.75rem', color: 'var(--text-primary)', textAlign: 'center' }}>
                      {kill.attacker_count}
                    </td>
                    <td style={{ padding: '0.75rem' }}>
                      <a
                        href={`https://zkillboard.com/kill/${kill.killmail_id}/`}
                        target="_blank"
                        rel="noopener noreferrer"
                        style={{ color: 'var(--accent-blue)', textDecoration: 'none', fontWeight: 600 }}
                      >
                        zkill →
                      </a>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {recentKills.length > 50 && (
              <div style={{ padding: '1rem', textAlign: 'center', color: 'var(--text-secondary)', fontSize: '0.875rem' }}>
                Showing first 50 of {recentKills.length} kills
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
