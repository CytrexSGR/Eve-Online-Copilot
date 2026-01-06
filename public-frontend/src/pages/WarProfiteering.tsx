import { useState, useEffect } from 'react';
import { reportsApi } from '../services/api';
import { RefreshIndicator } from '../components/RefreshIndicator';
import { useAutoRefresh } from '../hooks/useAutoRefresh';
import type { WarProfiteering as WarProfiteeringType } from '../types/reports';

export function WarProfiteering() {
  const [report, setReport] = useState<WarProfiteeringType | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState(new Date());

  const fetchReport = async () => {
    try {
      setError(null);
      const data = await reportsApi.getWarProfiteering();
      setReport(data);
      setLastUpdated(new Date());
      setLoading(false);
    } catch (err) {
      setError('Failed to load war profiteering report');
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
          <h1>💰 War Profiteering Report</h1>
          <p style={{ color: 'var(--text-secondary)' }}>Top destroyed items and market opportunities from combat</p>
        </div>
        <RefreshIndicator lastUpdated={lastUpdated} autoRefreshSeconds={60} />
      </div>

      {/* Global Summary */}
      <div className="card card-elevated">
        <h2>Global Summary</h2>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', gap: '2rem', marginTop: '1.5rem' }}>
          <div>
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.875rem' }}>Total Opportunity Value</p>
            <p style={{ fontSize: '2.5rem', fontWeight: 700, color: 'var(--success)' }}>
              {(report.global.total_opportunity_value / 1_000_000_000).toFixed(2)}B ISK
            </p>
          </div>
          <div>
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.875rem' }}>Total Items Destroyed</p>
            <p style={{ fontSize: '2.5rem', fontWeight: 700, color: 'var(--danger)' }}>
              {report.global.total_items_destroyed.toLocaleString()}
            </p>
          </div>
          <div>
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.875rem' }}>Unique Item Types</p>
            <p style={{ fontSize: '2.5rem', fontWeight: 700, color: 'var(--accent-blue)' }}>
              {report.global.unique_item_types}
            </p>
          </div>
          <div>
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.875rem' }}>Most Valuable Item</p>
            <p style={{ fontSize: '1.5rem', fontWeight: 600, color: 'var(--warning)' }}>
              {report.global.most_valuable_item}
            </p>
          </div>
        </div>
      </div>

      {/* Top Profiteering Items - Full List */}
      <div className="card" style={{ marginTop: '1.5rem' }}>
        <h2>Top Profiteering Opportunities</h2>
        <p style={{ color: 'var(--text-secondary)', marginBottom: '1.5rem' }}>
          Items destroyed in combat ranked by total market value opportunity
        </p>

        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ borderBottom: '2px solid var(--border-color)', textAlign: 'left' }}>
                <th style={{ padding: '1rem', color: 'var(--text-secondary)', fontSize: '0.875rem' }}>Rank</th>
                <th style={{ padding: '1rem', color: 'var(--text-secondary)', fontSize: '0.875rem' }}>Item Name</th>
                <th style={{ padding: '1rem', color: 'var(--text-secondary)', fontSize: '0.875rem', textAlign: 'right' }}>Quantity Destroyed</th>
                <th style={{ padding: '1rem', color: 'var(--text-secondary)', fontSize: '0.875rem', textAlign: 'right' }}>Market Price (ISK)</th>
                <th style={{ padding: '1rem', color: 'var(--text-secondary)', fontSize: '0.875rem', textAlign: 'right' }}>Total Opportunity Value</th>
              </tr>
            </thead>
            <tbody>
              {report.items.map((item, idx) => (
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
                    {(item.market_price / 1_000_000).toFixed(2)}M
                  </td>
                  <td style={{ padding: '1rem', textAlign: 'right', fontWeight: 600, color: 'var(--success)', fontFamily: 'monospace' }}>
                    {(item.opportunity_value / 1_000_000_000).toFixed(2)}B ISK
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Item Categories Breakdown */}
      {report.categories && report.categories.length > 0 && (
        <div className="card" style={{ marginTop: '1.5rem' }}>
          <h2>Top Categories</h2>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '1rem', marginTop: '1rem' }}>
            {report.categories.map((category) => (
              <div
                key={category.category_name}
                style={{
                  padding: '1.5rem',
                  background: 'var(--bg-elevated)',
                  borderRadius: '8px',
                  border: '1px solid var(--border-color)'
                }}
              >
                <h3 style={{ fontSize: '1.125rem', marginBottom: '0.5rem', color: 'var(--accent-blue)' }}>
                  {category.category_name}
                </h3>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '1rem' }}>
                  <div>
                    <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>Items Destroyed</p>
                    <p style={{ fontSize: '1.5rem', fontWeight: 600, color: 'var(--danger)' }}>
                      {category.total_destroyed.toLocaleString()}
                    </p>
                  </div>
                  <div style={{ textAlign: 'right' }}>
                    <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>Total Value</p>
                    <p style={{ fontSize: '1.5rem', fontWeight: 600, color: 'var(--success)' }}>
                      {(category.total_value / 1_000_000_000).toFixed(2)}B
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
