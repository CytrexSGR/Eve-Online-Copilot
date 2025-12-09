import { useState, useMemo } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { AlertTriangle, ArrowUpDown, ArrowLeft } from 'lucide-react';
import { getWarDemand } from '../api';

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

type SortField = 'name' | 'quantity' | 'market_stock' | 'gap';

export default function WarRoomMarketGaps() {
  const [searchParams, setSearchParams] = useSearchParams();
  const regionId = Number(searchParams.get('region') || 10000002);
  const days = Number(searchParams.get('days') || 7);

  const [sortField, setSortField] = useState<SortField>('gap');
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('asc'); // asc for most negative gaps first

  const demandQuery = useQuery({
    queryKey: ['warDemand', regionId, days],
    queryFn: () => getWarDemand(regionId, days),
    staleTime: 5 * 60 * 1000,
  });

  const gaps: MarketGap[] = useMemo(() => {
    if (!demandQuery.data?.market_gaps) return [];
    return demandQuery.data.market_gaps;
  }, [demandQuery.data]);

  const filteredAndSorted = useMemo(() => {
    let results = [...gaps];

    results.sort((a, b) => {
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
  }, [gaps, sortField, sortDir]);

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortDir(sortDir === 'desc' ? 'asc' : 'desc');
    } else {
      setSortField(field);
      setSortDir(field === 'gap' ? 'asc' : 'desc'); // Default ascending for gaps (most negative first)
    }
  };

  const stats = useMemo(() => {
    const criticalGaps = gaps.filter(g => g.gap < -1000).length;
    const totalShortage = gaps.reduce((sum, g) => sum + Math.abs(Math.min(g.gap, 0)), 0);
    const avgGap = gaps.length > 0 ? totalShortage / gaps.length : 0;

    return { criticalGaps, totalShortage, avgGap };
  }, [gaps]);

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
      </div>

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
                    style={{ width: '40%' }}
                  >
                    Item Name <ArrowUpDown size={14} />
                  </th>
                  <th
                    className="sortable"
                    onClick={() => handleSort('quantity')}
                    style={{ width: '20%' }}
                  >
                    Lost <ArrowUpDown size={14} />
                  </th>
                  <th
                    className="sortable"
                    onClick={() => handleSort('market_stock')}
                    style={{ width: '20%' }}
                  >
                    Market Stock <ArrowUpDown size={14} />
                  </th>
                  <th
                    className="sortable"
                    onClick={() => handleSort('gap')}
                    style={{ width: '20%' }}
                  >
                    Gap <ArrowUpDown size={14} />
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
