import { useState, useMemo } from 'react';
import { Link, useSearchParams, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { AlertTriangle, ArrowUpDown, ArrowLeft, TrendingUp, Plus } from 'lucide-react';
import { getWarDemand, api } from '../api';

const REGIONS: Record<number, string> = {
  10000002: 'The Forge (Jita)',
  10000043: 'Domain (Amarr)',
  10000030: 'Heimatar (Rens)',
  10000032: 'Sinq Laison (Dodixie)',
  10000042: 'Metropolis (Hek)',
};

interface MarketGap {
  type_id: number;
  name: string;
  quantity: number;
  market_stock: number;
  gap: number;
}

interface EconomicsData {
  type_id: number;
  profitability: {
    roi_sell_percent: number;
    profit_sell: number;
  };
}

type SortField = 'name' | 'quantity' | 'market_stock' | 'gap' | 'roi';

export default function WarRoomMarketGaps() {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const regionId = Number(searchParams.get('region') || 10000002);
  const days = Number(searchParams.get('days') || 7);

  const [sortField, setSortField] = useState<SortField>('gap');
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('asc'); // asc for most negative gaps first
  const [showProfitableOnly, setShowProfitableOnly] = useState(false);

  const demandQuery = useQuery({
    queryKey: ['warDemand', regionId, days],
    queryFn: () => getWarDemand(regionId, days),
    staleTime: 5 * 60 * 1000,
  });

  const gaps: MarketGap[] = useMemo(() => {
    if (!demandQuery.data?.market_gaps) return [];
    return demandQuery.data.market_gaps;
  }, [demandQuery.data]);

  // Fetch production economics for top 30 items
  const topItemIds = useMemo(() => {
    return gaps
      .sort((a, b) => a.gap - b.gap) // Most negative gaps first
      .slice(0, 30)
      .map(g => g.type_id);
  }, [gaps]);

  const { data: economicsMap } = useQuery<Record<number, EconomicsData>>({
    queryKey: ['warGaps-economics', regionId, topItemIds.join(',')],
    queryFn: async () => {
      if (topItemIds.length === 0) return {};
      const results: Record<number, EconomicsData> = {};

      // Fetch economics for each item (limit concurrency to 5)
      const chunks: number[][] = [];
      for (let i = 0; i < topItemIds.length; i += 5) {
        chunks.push(topItemIds.slice(i, i + 5));
      }

      for (const chunk of chunks) {
        await Promise.all(
          chunk.map(async (typeId) => {
            try {
              const response = await api.get(`/api/production/economics/${typeId}`, {
                params: { region_id: regionId, me: 10 }
              });
              results[typeId] = response.data;
            } catch {
              // Not manufacturable or no economics data
            }
          })
        );
      }

      return results;
    },
    enabled: topItemIds.length > 0,
    staleTime: 300000, // 5 minutes
    retry: false,
  });

  const filteredAndSorted = useMemo(() => {
    let results = [...gaps];

    // Filter: Show profitable only
    if (showProfitableOnly && economicsMap) {
      results = results.filter(item => {
        const economics = economicsMap[item.type_id];
        return economics && economics.profitability.roi_sell_percent > 10;
      });
    }

    // Sort
    results.sort((a, b) => {
      if (sortField === 'roi') {
        const aRoi = economicsMap?.[a.type_id]?.profitability?.roi_sell_percent || -999;
        const bRoi = economicsMap?.[b.type_id]?.profitability?.roi_sell_percent || -999;
        return sortDir === 'desc' ? bRoi - aRoi : aRoi - bRoi;
      }

      let aVal: any = a[sortField];
      let bVal: any = b[sortField];

      if (sortField === 'name') {
        aVal = aVal || '';
        bVal = bVal || '';
        return sortDir === 'desc' ? bVal.localeCompare(aVal) : aVal.localeCompare(bVal);
      }

      aVal = aVal || 0;
      bVal = bVal || 0;
      return sortDir === 'desc' ? bVal - aVal : aVal - bVal;
    });

    return results;
  }, [gaps, sortField, sortDir, showProfitableOnly, economicsMap]);

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortDir(sortDir === 'desc' ? 'asc' : 'desc');
    } else {
      setSortField(field);
      setSortDir(field === 'gap' ? 'asc' : field === 'roi' ? 'desc' : 'desc');
    }
  };

  const handlePlanProduction = (typeId: number) => {
    // Navigate to Production Planner with pre-selected item
    navigate(`/production?item=${typeId}`);
  };

  const stats = useMemo(() => {
    const criticalGaps = gaps.filter(g => g.gap < -1000).length;
    const totalShortage = gaps.reduce((sum, g) => sum + Math.abs(Math.min(g.gap, 0)), 0);
    const avgGap = gaps.length > 0 ? totalShortage / gaps.length : 0;

    // Count profitable items
    const profitableItems = economicsMap ? Object.values(economicsMap).filter(
      e => e.profitability.roi_sell_percent > 10
    ).length : 0;

    return { criticalGaps, totalShortage, avgGap, profitableItems };
  }, [gaps, economicsMap]);

  return (
    <div className="page-container">
      <div className="page-header">
        <div>
          <Link to="/war-room" className="back-link">
            <ArrowLeft size={20} />
            Back to War Room
          </Link>
          <h1 className="page-title">
            <AlertTriangle size={28} />
            Market Gaps Analysis
          </h1>
          <p className="page-subtitle">
            Supply shortages for {REGIONS[regionId]} ({days} days)
          </p>
        </div>
        <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
          <select
            value={regionId}
            onChange={(e) => setSearchParams({ region: e.target.value, days: days.toString() })}
            className="input"
            style={{ minWidth: '180px' }}
          >
            {Object.entries(REGIONS).map(([id, name]) => (
              <option key={id} value={id}>{name}</option>
            ))}
          </select>
          <select
            value={days}
            onChange={(e) => setSearchParams({ region: regionId.toString(), days: e.target.value })}
            className="input"
          >
            <option value={1}>24 hours</option>
            <option value={3}>3 days</option>
            <option value={7}>7 days</option>
            <option value={14}>14 days</option>
          </select>
        </div>
      </div>

      {/* Stats */}
      <div className="stats-grid" style={{ marginBottom: 16 }}>
        <div className="stat-card">
          <div className="stat-label">Total Gaps</div>
          <div className="stat-value">{gaps.length.toLocaleString()}</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Critical Gaps</div>
          <div className="stat-value negative">{stats.criticalGaps.toLocaleString()}</div>
          <div className="stat-detail">Gap &lt; -1,000</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Total Shortage</div>
          <div className="stat-value negative">{stats.totalShortage.toLocaleString()}</div>
          <div className="stat-detail">Items needed</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Avg Gap Size</div>
          <div className="stat-value">{Math.round(stats.avgGap).toLocaleString()}</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">
            <TrendingUp size={14} style={{ display: 'inline', marginRight: 4 }} />
            Profitable Items
          </div>
          <div className="stat-value positive">{stats.profitableItems.toLocaleString()}</div>
          <div className="stat-detail">ROI &gt; 10%</div>
        </div>
      </div>

      {/* Filter Toggle */}
      {economicsMap && Object.keys(economicsMap).length > 0 && (
        <div className="card" style={{ marginBottom: 16, padding: 16 }}>
          <label style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer', userSelect: 'none' }}>
            <input
              type="checkbox"
              checked={showProfitableOnly}
              onChange={(e) => setShowProfitableOnly(e.target.checked)}
              style={{ width: 18, height: 18, cursor: 'pointer' }}
            />
            <span style={{ fontWeight: 500 }}>
              Show Profitable Items Only (ROI &gt; 10%)
            </span>
            <span className="neutral" style={{ fontSize: 13 }}>
              ({stats.profitableItems} items)
            </span>
          </label>
        </div>
      )}

      {/* Results Table */}
      <div className="card">
        {demandQuery.isLoading ? (
          <div className="loading-container">
            <div className="loading-spinner" />
            <p>Loading market gap data...</p>
          </div>
        ) : filteredAndSorted.length === 0 ? (
          <div className="empty-state">
            <AlertTriangle size={48} />
            <p>No market gaps detected</p>
          </div>
        ) : (
          <div className="table-container">
            <table>
              <thead>
                <tr>
                  <th
                    className="sortable"
                    onClick={() => handleSort('name')}
                    style={{ width: '30%' }}
                  >
                    Item Name <ArrowUpDown size={14} />
                  </th>
                  <th
                    className="sortable"
                    onClick={() => handleSort('quantity')}
                    style={{ width: '12%' }}
                  >
                    Lost <ArrowUpDown size={14} />
                  </th>
                  <th
                    className="sortable"
                    onClick={() => handleSort('market_stock')}
                    style={{ width: '12%' }}
                  >
                    Market <ArrowUpDown size={14} />
                  </th>
                  <th
                    className="sortable"
                    onClick={() => handleSort('gap')}
                    style={{ width: '12%' }}
                  >
                    Gap <ArrowUpDown size={14} />
                  </th>
                  <th
                    className="sortable"
                    onClick={() => handleSort('roi')}
                    style={{ width: '18%' }}
                  >
                    Production ROI <ArrowUpDown size={14} />
                  </th>
                  <th style={{ width: '16%' }}>
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody>
                {filteredAndSorted.map((item) => {
                  const severity = Math.abs(item.gap);
                  const severityClass =
                    severity > 10000
                      ? 'critical'
                      : severity > 1000
                      ? 'high'
                      : severity > 100
                      ? 'medium'
                      : 'low';

                  const economics = economicsMap?.[item.type_id];
                  const roi = economics?.profitability?.roi_sell_percent;
                  const isProfitable = roi !== undefined && roi > 10;

                  return (
                    <tr key={item.type_id} className={`gap-row ${severityClass}`}>
                      <td>
                        <Link to={`/item/${item.type_id}`} className="item-link">
                          <strong>{item.name}</strong>
                        </Link>
                      </td>
                      <td>
                        <span className="highlight-value">
                          {item.quantity.toLocaleString()}
                        </span>
                      </td>
                      <td>
                        <span className={item.market_stock > 0 ? 'positive' : 'negative'}>
                          {item.market_stock.toLocaleString()}
                        </span>
                      </td>
                      <td>
                        <span className={`gap-value ${severityClass}`}>
                          {item.gap < 0 ? '' : '+'}
                          {item.gap.toLocaleString()}
                        </span>
                      </td>
                      <td>
                        {economics ? (
                          <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                            <span className={isProfitable ? 'positive roi-badge' : 'neutral'} style={{ fontWeight: 600, fontSize: 14 }}>
                              {roi!.toFixed(1)}% ROI
                            </span>
                            <span className="neutral" style={{ fontSize: 11 }}>
                              {economics.profitability.profit_sell >= 0 ? '+' : ''}
                              {(economics.profitability.profit_sell / 1000000).toFixed(1)}M ISK
                            </span>
                          </div>
                        ) : (
                          <span className="neutral" style={{ fontSize: 12 }}>-</span>
                        )}
                      </td>
                      <td>
                        {isProfitable && (
                          <button
                            className="btn btn-primary btn-sm"
                            onClick={() => handlePlanProduction(item.type_id)}
                            title="Plan production in Production Planner"
                          >
                            <Plus size={14} style={{ marginRight: 4 }} />
                            Plan
                          </button>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <style>{`
        .back-link {
          display: inline-flex;
          align-items: center;
          gap: 8px;
          color: var(--accent-blue);
          text-decoration: none;
          margin-bottom: 8px;
          font-size: 14px;
        }

        .back-link:hover {
          text-decoration: underline;
        }

        .stats-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
          gap: 16px;
        }

        .stat-card {
          background: var(--bg-secondary);
          padding: 16px;
          border-radius: 8px;
        }

        .stat-label {
          font-size: 12px;
          color: var(--text-secondary);
          margin-bottom: 4px;
        }

        .stat-value {
          font-size: 28px;
          font-weight: 600;
          color: var(--text-primary);
        }

        .stat-detail {
          font-size: 11px;
          color: var(--text-tertiary);
          margin-top: 4px;
        }

        .table-container {
          overflow-x: auto;
        }

        table {
          width: 100%;
          border-collapse: collapse;
        }

        th, td {
          padding: 12px;
          text-align: left;
          border-bottom: 1px solid var(--border-color);
        }

        th {
          background: var(--bg-secondary);
          font-weight: 600;
          font-size: 12px;
          text-transform: uppercase;
          color: var(--text-secondary);
        }

        th.sortable {
          cursor: pointer;
          user-select: none;
        }

        th.sortable:hover {
          background: var(--bg-tertiary);
        }

        tbody tr:hover {
          background: var(--bg-secondary);
        }

        .gap-row.critical {
          border-left: 4px solid var(--color-error);
        }

        .gap-row.high {
          border-left: 4px solid #ff8800;
        }

        .gap-row.medium {
          border-left: 4px solid var(--color-warning);
        }

        .item-link {
          text-decoration: none;
          color: inherit;
        }

        .item-link:hover strong {
          color: var(--accent-blue);
        }

        .highlight-value {
          font-weight: 600;
        }

        .positive {
          color: var(--color-success);
        }

        .negative {
          color: var(--color-error);
          font-weight: 600;
        }

        .gap-value {
          font-family: monospace;
          font-weight: 600;
          font-size: 16px;
        }

        .gap-value.critical {
          color: var(--color-error);
        }

        .gap-value.high {
          color: #ff8800;
        }

        .gap-value.medium {
          color: var(--color-warning);
        }

        .gap-value.low {
          color: var(--text-secondary);
        }

        .empty-state {
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          padding: 60px;
          gap: 16px;
          color: var(--text-secondary);
        }

        .loading-container {
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          padding: 60px;
          gap: 16px;
        }

        .loading-spinner {
          width: 40px;
          height: 40px;
          border: 3px solid var(--border-color);
          border-top-color: var(--accent-blue);
          border-radius: 50%;
          animation: spin 1s linear infinite;
        }

        @keyframes spin {
          to { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
}
