import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { reportsApi } from '../services/api';
import { RefreshIndicator } from '../components/RefreshIndicator';
import { useAutoRefresh } from '../hooks/useAutoRefresh';
import type {
  BattleReport,
  WarProfiteeringReport,
  AllianceWarsReport,
  TradeRoutesReport
} from '../types/reports';

export function Home() {
  const [battleReport, setBattleReport] = useState<BattleReport | null>(null);
  const [profiteering, setProfiteering] = useState<WarProfiteeringReport | null>(null);
  const [allianceWars, setAllianceWars] = useState<AllianceWarsReport | null>(null);
  const [tradeRoutes, setTradeRoutes] = useState<TradeRoutesReport | null>(null);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState(new Date());

  const fetchAllReports = async () => {
    try {
      setError(null);
      const [battle, profit, wars, routes] = await Promise.all([
        reportsApi.getBattleReport(),
        reportsApi.getWarProfiteering(),
        reportsApi.getAllianceWars(),
        reportsApi.getTradeRoutes(),
      ]);

      setBattleReport(battle);
      setProfiteering(profit);
      setAllianceWars(wars);
      setTradeRoutes(routes);
      setLastUpdated(new Date());
      setLoading(false);
    } catch (err) {
      setError('Failed to load reports. Please try again.');
      setLoading(false);
    }
  };

  // Initial load
  useEffect(() => {
    fetchAllReports();
  }, []);

  // Auto-refresh every 60 seconds
  useAutoRefresh(fetchAllReports, 60);

  if (loading) {
    return (
      <div>
        <div className="skeleton" style={{ height: '200px', marginBottom: '1rem' }} />
        <div className="skeleton" style={{ height: '200px', marginBottom: '1rem' }} />
        <div className="skeleton" style={{ height: '200px', marginBottom: '1rem' }} />
      </div>
    );
  }

  if (error) {
    return (
      <div className="card" style={{
        background: 'var(--danger)',
        color: 'white',
        textAlign: 'center',
        padding: '2rem'
      }}>
        <h2>❌ {error}</h2>
        <button
          onClick={fetchAllReports}
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
                  Hottest Region
                </p>
                <p style={{ fontSize: '1.25rem', fontWeight: 600, color: 'var(--warning)' }}>
                  {battleReport.global.most_active_region}
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
        {allianceWars && allianceWars.wars.length > 0 && (
          <>
            <p style={{ color: 'var(--text-secondary)', marginBottom: '1rem' }}>
              Top {allianceWars.wars.slice(0, 3).length} active conflicts
            </p>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              {allianceWars.wars.slice(0, 3).map((war) => (
                <div
                  key={`${war.alliance_a_id}-${war.alliance_b_id}`}
                  style={{
                    padding: '1rem',
                    background: 'var(--bg-elevated)',
                    borderRadius: '4px',
                    borderLeft: `4px solid ${
                      war.winner === 'a' ? 'var(--success)' :
                      war.winner === 'b' ? 'var(--danger)' :
                      'var(--warning)'
                    }`
                  }}
                >
                  <div style={{ fontWeight: 600, marginBottom: '0.5rem' }}>
                    {war.alliance_a_name} vs {war.alliance_b_name}
                  </div>
                  <div style={{
                    display: 'flex',
                    gap: '1.5rem',
                    fontSize: '0.875rem',
                    color: 'var(--text-secondary)'
                  }}>
                    <span>Kills: {war.total_kills}</span>
                    <span>Ratio: {war.kill_ratio_a.toFixed(2)}</span>
                    <span>Efficiency: {(war.isk_efficiency_a * 100).toFixed(1)}%</span>
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
              {tradeRoutes.routes.slice(0, 5).map((route) => (
                <div
                  key={`${route.from_hub}-${route.to_hub}`}
                  style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    padding: '0.75rem',
                    background: 'var(--bg-elevated)',
                    borderRadius: '4px'
                  }}
                >
                  <span>
                    {route.from_hub} → {route.to_hub}
                  </span>
                  <span style={{
                    fontWeight: 600,
                    color:
                      route.danger_level === 'SAFE' ? 'var(--success)' :
                      route.danger_level === 'LOW' ? 'var(--accent-blue)' :
                      route.danger_level === 'MODERATE' ? 'var(--warning)' :
                      'var(--danger)'
                  }}>
                    {route.danger_level}
                  </span>
                </div>
              ))}
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
