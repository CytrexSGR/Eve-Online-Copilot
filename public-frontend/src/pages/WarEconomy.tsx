import { useState, useEffect } from 'react';
import { reportsApi } from '../services/api';
import { RefreshIndicator } from '../components/RefreshIndicator';
import { useAutoRefresh } from '../hooks/useAutoRefresh';
import type { WarEconomy as WarEconomyType } from '../types/reports';

export function WarEconomy() {
  const [report, setReport] = useState<WarEconomyType | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState(new Date());
  const [activeTab, setActiveTab] = useState<'regional' | 'items' | 'doctrines'>('regional');

  const fetchReport = async () => {
    try {
      setError(null);
      const data = await reportsApi.getWarEconomy();
      setReport(data);
      setLastUpdated(new Date());
      setLoading(false);
    } catch (err) {
      setError('Failed to load war economy report');
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchReport();
  }, []);

  useAutoRefresh(fetchReport, 120); // Refresh every 2 minutes

  /**
   * Format ISK value to B (billions) or M (millions)
   */
  const formatISK = (isk: number): string => {
    if (isk >= 1_000_000_000) {
      return `${(isk / 1_000_000_000).toFixed(2)}B`;
    } else if (isk >= 1_000_000) {
      return `${(isk / 1_000_000).toFixed(1)}M`;
    }
    return isk.toLocaleString();
  };

  if (loading) return <div className="skeleton" style={{ height: '500px' }} />;
  if (error) return <div className="card" style={{ background: 'var(--danger)', color: 'white' }}>{error}</div>;
  if (!report) return null;

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2rem' }}>
        <div>
          <h1>War Economy</h1>
          <p style={{ color: 'var(--text-secondary)' }}>
            Combat-driven market intelligence: Where battles happen, demand rises
          </p>
        </div>
        <RefreshIndicator lastUpdated={lastUpdated} autoRefreshSeconds={120} />
      </div>

      {/* Global Summary */}
      <div className="card card-elevated">
        <h2>Market Impact Summary</h2>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '2rem', marginTop: '1.5rem' }}>
          <div>
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.875rem' }}>Total Market Opportunity</p>
            <p style={{ fontSize: '2.5rem', fontWeight: 700, color: 'var(--success)' }}>
              {formatISK(report.global_summary.total_opportunity_value)} ISK
            </p>
          </div>
          <div>
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.875rem' }}>Active Combat Regions</p>
            <p style={{ fontSize: '2.5rem', fontWeight: 700, color: 'var(--accent-blue)' }}>
              {report.global_summary.total_regions_active}
            </p>
          </div>
          <div>
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.875rem' }}>Total Kills (24h)</p>
            <p style={{ fontSize: '2.5rem', fontWeight: 700, color: 'var(--danger)' }}>
              {report.global_summary.total_kills_24h.toLocaleString()}
            </p>
          </div>
          <div>
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.875rem' }}>Hottest Region</p>
            <p style={{ fontSize: '1.5rem', fontWeight: 600, color: 'var(--warning)' }}>
              {report.global_summary.hottest_region?.region_name || 'N/A'}
            </p>
            {report.global_summary.hottest_region && (
              <p style={{ color: 'var(--text-tertiary)', fontSize: '0.875rem' }}>
                {report.global_summary.hottest_region.kills} kills
              </p>
            )}
          </div>
        </div>
      </div>

      {/* Tab Navigation */}
      <div style={{ display: 'flex', gap: '0.5rem', marginTop: '1.5rem', marginBottom: '1rem' }}>
        <button
          onClick={() => setActiveTab('regional')}
          style={{
            padding: '0.75rem 1.5rem',
            background: activeTab === 'regional' ? 'var(--accent-blue)' : 'var(--bg-elevated)',
            color: activeTab === 'regional' ? 'white' : 'var(--text-primary)',
            border: 'none',
            borderRadius: '8px',
            cursor: 'pointer',
            fontWeight: 500
          }}
        >
          Regional Demand
        </button>
        <button
          onClick={() => setActiveTab('items')}
          style={{
            padding: '0.75rem 1.5rem',
            background: activeTab === 'items' ? 'var(--accent-blue)' : 'var(--bg-elevated)',
            color: activeTab === 'items' ? 'white' : 'var(--text-primary)',
            border: 'none',
            borderRadius: '8px',
            cursor: 'pointer',
            fontWeight: 500
          }}
        >
          Hot Items
        </button>
        <button
          onClick={() => setActiveTab('doctrines')}
          style={{
            padding: '0.75rem 1.5rem',
            background: activeTab === 'doctrines' ? 'var(--accent-blue)' : 'var(--bg-elevated)',
            color: activeTab === 'doctrines' ? 'white' : 'var(--text-primary)',
            border: 'none',
            borderRadius: '8px',
            cursor: 'pointer',
            fontWeight: 500
          }}
        >
          Fleet Doctrines
        </button>
      </div>

      {/* Regional Demand Tab */}
      {activeTab === 'regional' && (
        <div className="card">
          <h2>Regional Market Demand</h2>
          <p style={{ color: 'var(--text-secondary)', marginBottom: '1.5rem' }}>
            Combat hotspots create local market demand - stock these items where fighting occurs
          </p>

          <div style={{ display: 'grid', gap: '1.5rem' }}>
            {report.regional_demand.map((region, idx) => (
              <div
                key={region.region_id}
                style={{
                  padding: '1.5rem',
                  background: idx % 2 === 0 ? 'var(--bg-elevated)' : 'transparent',
                  borderRadius: '8px',
                  border: '1px solid var(--border-color)'
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '1rem' }}>
                  <div>
                    <h3 style={{ fontSize: '1.25rem', color: 'var(--accent-blue)', marginBottom: '0.25rem' }}>
                      #{idx + 1} {region.region_name}
                    </h3>
                    <p style={{ color: 'var(--text-secondary)', fontSize: '0.875rem' }}>
                      {region.kills} kills | {formatISK(region.isk_destroyed)} ISK destroyed
                    </p>
                  </div>
                  <div style={{ textAlign: 'right' }}>
                    <p style={{ fontSize: '0.75rem', color: 'var(--text-tertiary)' }}>Demand Score</p>
                    <p style={{ fontSize: '1.5rem', fontWeight: 700, color: 'var(--success)' }}>
                      {formatISK(region.demand_score)}
                    </p>
                  </div>
                </div>

                {/* Top Demanded Items */}
                {region.top_demanded_items.length > 0 && (
                  <div>
                    <p style={{ fontSize: '0.875rem', fontWeight: 600, marginBottom: '0.5rem', color: 'var(--text-secondary)' }}>
                      Top Demanded Items:
                    </p>
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
                      {region.top_demanded_items.slice(0, 5).map((item) => (
                        <span
                          key={item.item_type_id}
                          style={{
                            padding: '0.375rem 0.75rem',
                            background: 'var(--bg-surface)',
                            borderRadius: '4px',
                            fontSize: '0.875rem',
                            border: '1px solid var(--border-color)'
                          }}
                        >
                          {item.item_name} ({item.quantity_destroyed}x)
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Hot Items Tab */}
      {activeTab === 'items' && (
        <div className="card">
          <h2>Hot Items - High Demand from Combat</h2>
          <p style={{ color: 'var(--text-secondary)', marginBottom: '1.5rem' }}>
            Items destroyed most frequently in combat - excellent restocking opportunities
          </p>

          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead>
                <tr style={{ borderBottom: '2px solid var(--border-color)', textAlign: 'left' }}>
                  <th style={{ padding: '1rem', color: 'var(--text-secondary)', fontSize: '0.875rem' }}>Rank</th>
                  <th style={{ padding: '1rem', color: 'var(--text-secondary)', fontSize: '0.875rem' }}>Item Name</th>
                  <th style={{ padding: '1rem', color: 'var(--text-secondary)', fontSize: '0.875rem', textAlign: 'right' }}>Quantity Destroyed</th>
                  <th style={{ padding: '1rem', color: 'var(--text-secondary)', fontSize: '0.875rem', textAlign: 'right' }}>Market Price</th>
                  <th style={{ padding: '1rem', color: 'var(--text-secondary)', fontSize: '0.875rem', textAlign: 'right' }}>Opportunity Value</th>
                </tr>
              </thead>
              <tbody>
                {report.hot_items.map((item, idx) => (
                  <tr
                    key={item.item_type_id}
                    style={{
                      borderBottom: '1px solid var(--border-color)',
                      background: idx % 2 === 0 ? 'var(--bg-elevated)' : 'transparent'
                    }}
                  >
                    <td style={{ padding: '1rem', fontWeight: 600, color: 'var(--accent-blue)' }}>
                      #{idx + 1}
                    </td>
                    <td style={{ padding: '1rem', fontWeight: 500 }}>
                      {item.item_name}
                    </td>
                    <td style={{ padding: '1rem', textAlign: 'right', color: 'var(--danger)' }}>
                      {item.quantity_destroyed.toLocaleString()}x
                    </td>
                    <td style={{ padding: '1rem', textAlign: 'right', fontFamily: 'monospace' }}>
                      {formatISK(item.market_price)}
                    </td>
                    <td style={{ padding: '1rem', textAlign: 'right', fontWeight: 600, color: 'var(--success)', fontFamily: 'monospace' }}>
                      {formatISK(item.opportunity_value || 0)} ISK
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Fleet Doctrines Tab */}
      {activeTab === 'doctrines' && (
        <div className="card">
          <h2>Detected Fleet Doctrines</h2>
          <p style={{ color: 'var(--text-secondary)', marginBottom: '1.5rem' }}>
            Ship class patterns reveal active fleet doctrines - anticipate module and ammunition demand
          </p>

          {report.fleet_compositions.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '2rem', color: 'var(--text-secondary)' }}>
              No fleet composition data available
            </div>
          ) : (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(350px, 1fr))', gap: '1.5rem' }}>
              {report.fleet_compositions.map((fleet) => (
                <div
                  key={fleet.region_id}
                  style={{
                    padding: '1.5rem',
                    background: 'var(--bg-elevated)',
                    borderRadius: '8px',
                    border: '1px solid var(--border-color)'
                  }}
                >
                  <div style={{ marginBottom: '1rem' }}>
                    <h3 style={{ fontSize: '1.125rem', color: 'var(--accent-blue)', marginBottom: '0.25rem' }}>
                      {fleet.region_name}
                    </h3>
                    <p style={{ color: 'var(--text-secondary)', fontSize: '0.875rem' }}>
                      {fleet.total_ships_lost} ships analyzed
                    </p>
                  </div>

                  {/* Doctrine Hints */}
                  {fleet.doctrine_hints.length > 0 && (
                    <div style={{ marginBottom: '1rem' }}>
                      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
                        {fleet.doctrine_hints.map((hint, idx) => (
                          <span
                            key={idx}
                            style={{
                              padding: '0.375rem 0.75rem',
                              background: 'var(--warning)',
                              color: 'black',
                              borderRadius: '4px',
                              fontSize: '0.75rem',
                              fontWeight: 600
                            }}
                          >
                            {hint}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Ship Class Breakdown */}
                  <div>
                    <p style={{ fontSize: '0.75rem', color: 'var(--text-tertiary)', marginBottom: '0.5rem' }}>
                      Ship Class Breakdown:
                    </p>
                    {Object.entries(fleet.composition)
                      .filter(([, data]) => data.count > 0)
                      .sort((a, b) => b[1].count - a[1].count)
                      .slice(0, 6)
                      .map(([shipClass, data]) => (
                        <div
                          key={shipClass}
                          style={{
                            display: 'flex',
                            justifyContent: 'space-between',
                            alignItems: 'center',
                            padding: '0.375rem 0',
                            borderBottom: '1px solid var(--border-color)'
                          }}
                        >
                          <span style={{ textTransform: 'capitalize' }}>{shipClass.replace('_', ' ')}</span>
                          <div style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
                            <span style={{ color: 'var(--text-secondary)', fontSize: '0.875rem' }}>
                              {data.count}x
                            </span>
                            <div
                              style={{
                                width: '60px',
                                height: '8px',
                                background: 'var(--bg-surface)',
                                borderRadius: '4px',
                                overflow: 'hidden'
                              }}
                            >
                              <div
                                style={{
                                  width: `${Math.min(data.percentage, 100)}%`,
                                  height: '100%',
                                  background: 'var(--accent-blue)',
                                  borderRadius: '4px'
                                }}
                              />
                            </div>
                            <span style={{ color: 'var(--accent-blue)', fontSize: '0.875rem', fontWeight: 500, width: '40px', textAlign: 'right' }}>
                              {data.percentage}%
                            </span>
                          </div>
                        </div>
                      ))}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Market Intelligence Note */}
      <div className="card" style={{ marginTop: '1.5rem', background: 'var(--bg-elevated)', borderLeft: '4px solid var(--accent-blue)' }}>
        <h3 style={{ marginBottom: '0.5rem' }}>Market Intelligence</h3>
        <p style={{ color: 'var(--text-secondary)', lineHeight: 1.6 }}>
          This report combines real-time combat data with market prices to identify restocking opportunities.
          High-demand items in active combat zones typically see increased local prices and faster sales.
          Consider hauling hot items to regional trade hubs near combat hotspots.
        </p>
      </div>
    </div>
  );
}
