import { useState, useMemo } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { TrendingUp, ArrowUpDown, ArrowLeft } from 'lucide-react';
import { getWarSummary } from '../api';
import type { RegionalSummary } from '../types/war';

interface WarSummaryResponse {
  regions: RegionalSummary[];
}

export default function WarRoomGalaxySummary() {
  const [searchParams, setSearchParams] = useSearchParams();
  const days = Number(searchParams.get('days') || 7);

  const [sortField, setSortField] = useState<'region_name' | 'total_kills' | 'active_systems'>('total_kills');
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('desc');

  const summaryQuery = useQuery<WarSummaryResponse>({
    queryKey: ['warSummary', days],
    queryFn: () => getWarSummary(days),
    staleTime: 5 * 60 * 1000,
  });

  const regions = useMemo<RegionalSummary[]>(() => {
    if (!summaryQuery.data?.regions) return [];
    return summaryQuery.data.regions;
  }, [summaryQuery.data]);

  const filteredAndSorted = useMemo(() => {
    const results = [...regions];

    results.sort((a, b) => {
      const aVal = a[sortField] || 0;
      const bVal = b[sortField] || 0;

      if (typeof aVal === 'string') {
        return sortDir === 'desc' ? bVal.localeCompare(aVal) : aVal.localeCompare(bVal);
      }

      return sortDir === 'desc' ? (bVal as number) - (aVal as number) : (aVal as number) - (bVal as number);
    });

    return results;
  }, [regions, sortField, sortDir]);

  const handleSort = (field: typeof sortField) => {
    if (sortField === field) {
      setSortDir(sortDir === 'desc' ? 'asc' : 'desc');
    } else {
      setSortField(field);
      setSortDir('desc');
    }
  };

  const stats = useMemo(() => {
    const totalKills = regions.reduce((sum, r) => sum + r.total_kills, 0);
    const totalSystems = regions.reduce((sum, r) => sum + r.active_systems, 0);
    const avgKillsPerRegion = regions.length > 0 ? totalKills / regions.length : 0;

    return { totalKills, totalSystems, avgKillsPerRegion };
  }, [regions]);

  return (
    <div className="page-container">
      <div className="page-header">
        <div>
          <Link to="/war-room" className="back-link">
            <ArrowLeft size={20} />
            Back to War Room
          </Link>
          <h1 className="page-title">
            <TrendingUp size={28} />
            Galaxy Combat Summary
          </h1>
          <p className="page-subtitle">Combat activity across all regions ({days} days)</p>
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

      {/* Stats */}
      <div className="stats-grid" style={{ marginBottom: 16 }}>
        <div className="stat-card">
          <div className="stat-label">Total Regions</div>
          <div className="stat-value">{regions.length}</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Total Kills</div>
          <div className="stat-value negative">{stats.totalKills.toLocaleString()}</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Active Systems</div>
          <div className="stat-value">{stats.totalSystems.toLocaleString()}</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Avg Kills/Region</div>
          <div className="stat-value">{Math.round(stats.avgKillsPerRegion).toLocaleString()}</div>
        </div>
      </div>

      {/* Results Table */}
      <div className="card">
        {summaryQuery.isLoading ? (
          <div className="loading-container">
            <div className="loading-spinner" />
            <p>Loading galaxy summary...</p>
          </div>
        ) : filteredAndSorted.length === 0 ? (
          <div className="empty-state">
            <TrendingUp size={48} />
            <p>No combat data available</p>
          </div>
        ) : (
          <div className="table-container">
            <table>
              <thead>
                <tr>
                  <th className="sortable" onClick={() => handleSort('region_name')} style={{ width: '40%' }}>
                    Region <ArrowUpDown size={14} />
                  </th>
                  <th className="sortable" onClick={() => handleSort('total_kills')} style={{ width: '30%' }}>
                    Total Kills <ArrowUpDown size={14} />
                  </th>
                  <th className="sortable" onClick={() => handleSort('active_systems')} style={{ width: '30%' }}>
                    Active Systems <ArrowUpDown size={14} />
                  </th>
                </tr>
              </thead>
              <tbody>
                {filteredAndSorted.map((region) => {
                  const activityLevel = region.total_kills > 3000 ? 'extreme' : region.total_kills > 1000 ? 'high' : region.total_kills > 500 ? 'medium' : 'low';

                  return (
                    <tr key={region.region_id} className={`activity-${activityLevel}`}>
                      <td>
                        <strong>{region.region_name}</strong>
                      </td>
                      <td>
                        <span className="highlight-value">{region.total_kills.toLocaleString()}</span>
                      </td>
                      <td>
                        <span className="systems-value">{region.active_systems} systems</span>
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

        .stat-value.negative {
          color: var(--color-error);
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

        .activity-extreme {
          border-left: 4px solid var(--color-error);
        }

        .activity-high {
          border-left: 4px solid #ff8800;
        }

        .activity-medium {
          border-left: 4px solid var(--color-warning);
        }

        .highlight-value {
          font-weight: 600;
          font-size: 16px;
        }

        .systems-value {
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
