import { useState, useMemo } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { MapPin, ArrowUpDown, ArrowLeft } from 'lucide-react';
import { getWarHeatmap } from '../api';

export default function WarRoomCombatHotspots() {
  const [searchParams, setSearchParams] = useSearchParams();
  const days = Number(searchParams.get('days') || 7);

  const [sortField, setSortField] = useState<'name' | 'kills' | 'security'>('kills');
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('desc');

  const heatmapQuery = useQuery({
    queryKey: ['warHeatmap', days, 1],
    queryFn: () => getWarHeatmap(days, 1),
    staleTime: 5 * 60 * 1000,
  });

  const systems = useMemo(() => {
    if (!heatmapQuery.data?.systems) return [];
    return heatmapQuery.data.systems;
  }, [heatmapQuery.data]);

  const filteredAndSorted = useMemo(() => {
    let results = [...systems];

    results.sort((a: any, b: any) => {
      const aVal = a[sortField] || 0;
      const bVal = b[sortField] || 0;

      if (typeof aVal === 'string') {
        return sortDir === 'desc' ? bVal.localeCompare(aVal) : aVal.localeCompare(bVal);
      }

      return sortDir === 'desc' ? bVal - aVal : aVal - bVal;
    });

    return results;
  }, [systems, sortField, sortDir]);

  const handleSort = (field: typeof sortField) => {
    if (sortField === field) {
      setSortDir(sortDir === 'desc' ? 'asc' : 'desc');
    } else {
      setSortField(field);
      setSortDir('desc');
    }
  };

  const getSecurityColor = (sec: number) => {
    if (sec >= 0.5) return 'var(--color-success)';
    if (sec > 0) return 'var(--color-warning)';
    return 'var(--color-error)';
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
            <MapPin size={28} />
            Combat Hotspots
          </h1>
          <p className="page-subtitle">Systems with highest combat activity ({days} days)</p>
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

      {/* Results Table */}
      <div className="card">
        {heatmapQuery.isLoading ? (
          <div className="loading-container">
            <div className="loading-spinner" />
            <p>Loading combat hotspot data...</p>
          </div>
        ) : filteredAndSorted.length === 0 ? (
          <div className="empty-state">
            <MapPin size={48} />
            <p>No combat data available</p>
          </div>
        ) : (
          <div className="table-container">
            <table>
              <thead>
                <tr>
                  <th className="sortable" onClick={() => handleSort('name')} style={{ width: '30%' }}>
                    System Name <ArrowUpDown size={14} />
                  </th>
                  <th className="sortable" onClick={() => handleSort('kills')} style={{ width: '20%' }}>
                    Kills <ArrowUpDown size={14} />
                  </th>
                  <th style={{ width: '25%' }}>Region</th>
                  <th className="sortable" onClick={() => handleSort('security')} style={{ width: '15%' }}>
                    Security <ArrowUpDown size={14} />
                  </th>
                  <th style={{ width: '10%' }}>Danger</th>
                </tr>
              </thead>
              <tbody>
                {filteredAndSorted.map((system: any) => {
                  const dangerLevel = system.kills > 500 ? 'extreme' : system.kills > 200 ? 'high' : system.kills > 50 ? 'medium' : 'low';

                  return (
                    <tr key={system.system_id} className={`danger-${dangerLevel}`}>
                      <td>
                        <strong>{system.name}</strong>
                      </td>
                      <td>
                        <span className="highlight-value">{system.kills.toLocaleString()}</span>
                      </td>
                      <td>
                        <span className="region-name">{system.region}</span>
                      </td>
                      <td>
                        <span
                          className="security-status"
                          style={{ color: getSecurityColor(system.security) }}
                        >
                          {system.security.toFixed(1)}
                        </span>
                      </td>
                      <td>
                        <span className={`danger-badge ${dangerLevel}`}>
                          {dangerLevel.toUpperCase()}
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

        .danger-extreme {
          border-left: 4px solid var(--color-error);
        }

        .danger-high {
          border-left: 4px solid #ff8800;
        }

        .danger-medium {
          border-left: 4px solid var(--color-warning);
        }

        .region-name {
          color: var(--text-secondary);
          font-size: 13px;
        }

        .highlight-value {
          font-weight: 600;
          font-size: 16px;
        }

        .security-status {
          font-weight: 600;
          font-family: monospace;
        }

        .danger-badge {
          padding: 4px 8px;
          border-radius: 4px;
          font-size: 10px;
          font-weight: 600;
          text-transform: uppercase;
        }

        .danger-badge.extreme {
          background: var(--color-error);
          color: white;
        }

        .danger-badge.high {
          background: #ff8800;
          color: white;
        }

        .danger-badge.medium {
          background: var(--color-warning);
          color: black;
        }

        .danger-badge.low {
          background: var(--bg-tertiary);
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
