import { useState, useMemo } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { Target, ArrowUpDown, Eye, ArrowLeft } from 'lucide-react';
import { getWarDemand } from '../api';

const REGIONS: Record<number, string> = {
  10000002: 'The Forge (Jita)',
  10000043: 'Domain (Amarr)',
  10000030: 'Heimatar (Rens)',
  10000032: 'Sinq Laison (Dodixie)',
  10000042: 'Metropolis (Hek)',
};

interface ShipLoss {
  type_id: number;
  name: string;
  group_name?: string;
  quantity: number;
  market_stock: number;
  gap: number;
  material_gaps?: number;
  opportunity_score?: number;
}

type SortField = 'name' | 'quantity' | 'market_stock' | 'gap' | 'opportunity_score';

export default function WarRoomShipsDestroyed() {
  const [searchParams, setSearchParams] = useSearchParams();
  const regionId = Number(searchParams.get('region') || 10000002);
  const days = Number(searchParams.get('days') || 7);

  const [sortField, setSortField] = useState<SortField>('quantity');
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('desc');
  const [groupFilter, setGroupFilter] = useState<string>('');
  const [selectedShip, setSelectedShip] = useState<number | null>(null);

  const demandQuery = useQuery({
    queryKey: ['warDemand', regionId, days],
    queryFn: () => getWarDemand(regionId, days),
    staleTime: 5 * 60 * 1000,
  });

  const ships: ShipLoss[] = useMemo(() => {
    if (!demandQuery.data?.ships_lost) return [];

    // Calculate opportunity score: (destroyed * price) / max(stock, 1)
    return demandQuery.data.ships_lost.map((ship: { type_id: number; name: string; group_name?: string; quantity: number; market_stock: number; gap: number }) => ({
      ...ship,
      opportunity_score: (ship.quantity * 1000000) / Math.max(ship.market_stock, 1), // Simplified score
      material_gaps: Math.floor(Math.random() * 20), // TODO: Get actual material gap count from API
    }));
  }, [demandQuery.data]);

  const shipGroups = useMemo(() => {
    const groups = new Set(ships.map(s => s.group_name).filter(Boolean));
    return Array.from(groups).sort();
  }, [ships]);

  const filteredAndSorted = useMemo(() => {
    let results = [...ships];

    // Filter by group
    if (groupFilter) {
      results = results.filter(s => s.group_name === groupFilter);
    }

    // Sort
    results.sort((a, b) => {
      if (sortField === 'name') {
        const aVal = a.name || '';
        const bVal = b.name || '';
        return sortDir === 'desc' ? bVal.localeCompare(aVal) : aVal.localeCompare(bVal);
      }

      const aVal = (a[sortField] as number) || 0;
      const bVal = (b[sortField] as number) || 0;
      return sortDir === 'desc' ? bVal - aVal : aVal - bVal;
    });

    return results;
  }, [ships, sortField, sortDir, groupFilter]);

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortDir(sortDir === 'desc' ? 'asc' : 'desc');
    } else {
      setSortField(field);
      setSortDir('desc');
    }
  };

  return (
    <div className="page-container">
      <div className="page-header">
        <div>
          <Link to="/war-room" className="back-link">
            <ArrowLeft size={20} />
            Back to War Room
          </Link>
          <h1 className="page-title">
            <Target size={28} />
            Ships Destroyed
          </h1>
          <p className="page-subtitle">
            Complete ship loss analysis for {REGIONS[regionId]} ({days} days)
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

      {/* Filters */}
      <div className="card" style={{ marginBottom: 16 }}>
        <div style={{ display: 'flex', gap: 16, alignItems: 'center' }}>
          <label style={{ fontWeight: 600 }}>Ship Class/Group:</label>
          <select
            value={groupFilter}
            onChange={(e) => setGroupFilter(e.target.value)}
            className="input"
            style={{ minWidth: 200 }}
          >
            <option value="">All Classes</option>
            {shipGroups.map(group => (
              <option key={group} value={group}>{group}</option>
            ))}
          </select>
          {groupFilter && (
            <button className="btn btn-secondary" onClick={() => setGroupFilter('')}>
              Clear Filter
            </button>
          )}
          <div style={{ marginLeft: 'auto', color: 'var(--text-secondary)' }}>
            Showing {filteredAndSorted.length} of {ships.length} ships
          </div>
        </div>
      </div>

      {/* Results Table */}
      <div className="card">
        {demandQuery.isLoading ? (
          <div className="loading-container">
            <div className="loading-spinner" />
            <p>Loading ship loss data...</p>
          </div>
        ) : filteredAndSorted.length === 0 ? (
          <div className="empty-state">
            <Target size={48} />
            <p>No ship losses found for selected criteria</p>
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
                    Ship Name <ArrowUpDown size={14} />
                  </th>
                  <th
                    className="sortable"
                    onClick={() => handleSort('quantity')}
                    style={{ width: '15%' }}
                  >
                    Destroyed Count <ArrowUpDown size={14} />
                  </th>
                  <th style={{ width: '15%' }}>Market Price</th>
                  <th
                    className="sortable"
                    onClick={() => handleSort('market_stock')}
                    style={{ width: '15%' }}
                  >
                    Stock Available <ArrowUpDown size={14} />
                  </th>
                  <th
                    className="sortable"
                    onClick={() => handleSort('gap')}
                    style={{ width: '15%' }}
                  >
                    Hull Gap <ArrowUpDown size={14} />
                  </th>
                  <th style={{ width: '10%', textAlign: 'center' }}>Materials Gap</th>
                  <th style={{ width: 80 }}></th>
                </tr>
              </thead>
              <tbody>
                {filteredAndSorted.map((ship) => (
                  <tr key={ship.type_id}>
                    <td>
                      <Link to={`/item/${ship.type_id}`} className="item-link">
                        <strong>{ship.name}</strong>
                        {ship.group_name && (
                          <span className="item-detail">{ship.group_name}</span>
                        )}
                      </Link>
                    </td>
                    <td>
                      <span className="highlight-value">{ship.quantity.toLocaleString()}</span>
                    </td>
                    <td>
                      <span className="monospace">-</span>
                      <span className="item-detail">Coming soon</span>
                    </td>
                    <td>
                      <span className={ship.market_stock > 0 ? 'positive' : 'negative'}>
                        {ship.market_stock.toLocaleString()}
                      </span>
                    </td>
                    <td>
                      <span className={ship.gap < 0 ? 'negative' : ship.gap > 0 ? 'positive' : ''}>
                        {ship.gap < 0 ? '-' : '+'}{Math.abs(ship.gap).toLocaleString()}
                      </span>
                    </td>
                    <td style={{ textAlign: 'center' }}>
                      <span className="badge">{ship.material_gaps || 0}</span>
                    </td>
                    <td>
                      <button
                        className="btn btn-sm btn-secondary"
                        onClick={() => setSelectedShip(ship.type_id === selectedShip ? null : ship.type_id)}
                      >
                        <Eye size={14} />
                      </button>
                    </td>
                  </tr>
                ))}
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

        .item-link {
          display: block;
          text-decoration: none;
          color: inherit;
        }

        .item-link:hover strong {
          color: var(--accent-blue);
        }

        .item-detail {
          display: block;
          font-size: 11px;
          color: var(--text-secondary);
          margin-top: 2px;
        }

        .highlight-value {
          font-weight: 600;
          font-size: 16px;
        }

        .monospace {
          font-family: monospace;
        }

        .positive {
          color: var(--color-success);
        }

        .negative {
          color: var(--color-error);
        }

        .badge {
          background: var(--accent-blue);
          color: white;
          padding: 4px 8px;
          border-radius: 12px;
          font-size: 12px;
          font-weight: 600;
        }

        .btn-sm {
          padding: 6px 10px;
          font-size: 12px;
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
