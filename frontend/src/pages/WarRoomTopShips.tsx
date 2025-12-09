import { useState, useMemo } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { Target, ArrowUpDown, ArrowLeft } from 'lucide-react';
import { getTopShips } from '../api';

export default function WarRoomTopShips() {
  const [searchParams, setSearchParams] = useSearchParams();
  const days = Number(searchParams.get('days') || 7);

  const [sortField, setSortField] = useState<'name' | 'quantity' | 'value'>('quantity');
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('desc');
  const [groupFilter, setGroupFilter] = useState<string>('');

  const shipsQuery = useQuery({
    queryKey: ['topShips', days, 1000],
    queryFn: () => getTopShips(days, 1000),
    staleTime: 5 * 60 * 1000,
  });

  const ships = useMemo(() => {
    if (!shipsQuery.data?.ships) return [];
    return shipsQuery.data.ships;
  }, [shipsQuery.data]);

  const shipGroups = useMemo(() => {
    const groups = new Set(ships.map((s: any) => s.group).filter(Boolean));
    return Array.from(groups).sort();
  }, [ships]);

  const filteredAndSorted = useMemo(() => {
    let results = [...ships];

    if (groupFilter) {
      results = results.filter((s: any) => s.group === groupFilter);
    }

    results.sort((a: any, b: any) => {
      const aVal = a[sortField] || 0;
      const bVal = b[sortField] || 0;

      if (typeof aVal === 'string') {
        return sortDir === 'desc' ? bVal.localeCompare(aVal) : aVal.localeCompare(bVal);
      }

      return sortDir === 'desc' ? bVal - aVal : aVal - bVal;
    });

    return results;
  }, [ships, sortField, sortDir, groupFilter]);

  const handleSort = (field: typeof sortField) => {
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
            Top Ships Galaxy-Wide
          </h1>
          <p className="page-subtitle">Most destroyed ships across all regions ({days} days)</p>
        </div>
        <div>
          <select
            value={days}
            onChange={(e) => setSearchParams({ days: e.target.value })}
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
              <option key={group as string} value={group as string}>{group as string}</option>
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
        {shipsQuery.isLoading ? (
          <div className="loading-container">
            <div className="loading-spinner" />
            <p>Loading top ships data...</p>
          </div>
        ) : filteredAndSorted.length === 0 ? (
          <div className="empty-state">
            <Target size={48} />
            <p>No data available</p>
          </div>
        ) : (
          <div className="table-container">
            <table>
              <thead>
                <tr>
                  <th className="sortable" onClick={() => handleSort('name')} style={{ width: '40%' }}>
                    Ship Name <ArrowUpDown size={14} />
                  </th>
                  <th style={{ width: '20%' }}>Ship Group</th>
                  <th className="sortable" onClick={() => handleSort('quantity')} style={{ width: '20%' }}>
                    Destroyed Count <ArrowUpDown size={14} />
                  </th>
                  <th className="sortable" onClick={() => handleSort('value')} style={{ width: '20%' }}>
                    Total Value Lost <ArrowUpDown size={14} />
                  </th>
                </tr>
              </thead>
              <tbody>
                {filteredAndSorted.map((ship: any) => (
                  <tr key={ship.type_id}>
                    <td>
                      <Link to={`/item/${ship.type_id}`} className="item-link">
                        <strong>{ship.name}</strong>
                      </Link>
                    </td>
                    <td>
                      <span className="ship-group">{ship.group}</span>
                    </td>
                    <td>
                      <span className="highlight-value">{ship.quantity.toLocaleString()}</span>
                    </td>
                    <td>
                      <span className="monospace negative">
                        {(ship.value / 1000000).toFixed(1)}M ISK
                      </span>
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
          text-decoration: none;
          color: inherit;
        }

        .item-link:hover strong {
          color: var(--accent-blue);
        }

        .ship-group {
          font-size: 13px;
          color: var(--text-secondary);
        }

        .highlight-value {
          font-weight: 600;
          font-size: 16px;
        }

        .monospace {
          font-family: monospace;
        }

        .negative {
          color: var(--color-error);
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
