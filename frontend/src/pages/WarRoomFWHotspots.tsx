import { useState, useMemo } from 'react';
import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { Swords, ArrowUpDown, ArrowLeft } from 'lucide-react';
import { getFWHotspots } from '../api';
import type { FWHotspot, FWHotspotsResponse } from '../types/war';

export default function WarRoomFWHotspots() {
  const [sortField, setSortField] = useState<'solar_system_name' | 'contested_percent'>('contested_percent');
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('desc');

  const fwQuery = useQuery<FWHotspotsResponse>({
    queryKey: ['fwHotspots', 0],
    queryFn: () => getFWHotspots(0),
    staleTime: 5 * 60 * 1000,
  });

  const hotspots = useMemo<FWHotspot[]>(() => {
    if (!fwQuery.data?.hotspots) return [];
    return fwQuery.data.hotspots;
  }, [fwQuery.data]);

  const filteredAndSorted = useMemo(() => {
    const results = [...hotspots];

    results.sort((a, b) => {
      const aVal = a[sortField] || 0;
      const bVal = b[sortField] || 0;

      if (typeof aVal === 'string') {
        return sortDir === 'desc' ? bVal.localeCompare(aVal) : aVal.localeCompare(bVal);
      }

      return sortDir === 'desc' ? (bVal as number) - (aVal as number) : (aVal as number) - (bVal as number);
    });

    return results;
  }, [hotspots, sortField, sortDir]);

  const handleSort = (field: typeof sortField) => {
    if (sortField === field) {
      setSortDir(sortDir === 'desc' ? 'asc' : 'desc');
    } else {
      setSortField(field);
      setSortDir('desc');
    }
  };

  const getContestedColor = (percent: number) => {
    if (percent >= 90) return 'var(--color-error)';
    if (percent >= 70) return 'var(--color-warning)';
    return 'var(--color-success)';
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
            <Swords size={28} />
            Faction Warfare Hotspots
          </h1>
          <p className="page-subtitle">Most contested faction warfare systems</p>
        </div>
      </div>

      {/* Results Table */}
      <div className="card">
        {fwQuery.isLoading ? (
          <div className="loading-container">
            <div className="loading-spinner" />
            <p>Loading faction warfare data...</p>
          </div>
        ) : filteredAndSorted.length === 0 ? (
          <div className="empty-state">
            <Swords size={48} />
            <p>No active faction warfare hotspots</p>
          </div>
        ) : (
          <div className="table-container">
            <table>
              <thead>
                <tr>
                  <th className="sortable" onClick={() => handleSort('solar_system_name')} style={{ width: '25%' }}>
                    System <ArrowUpDown size={14} />
                  </th>
                  <th style={{ width: '20%' }}>Region</th>
                  <th className="sortable" onClick={() => handleSort('contested_percent')} style={{ width: '15%' }}>
                    Contested <ArrowUpDown size={14} />
                  </th>
                  <th style={{ width: '20%' }}>Owner</th>
                  <th style={{ width: '20%' }}>Occupier</th>
                </tr>
              </thead>
              <tbody>
                {filteredAndSorted.map((hotspot) => (
                  <tr key={hotspot.solar_system_id}>
                    <td>
                      <strong>{hotspot.solar_system_name}</strong>
                    </td>
                    <td>
                      <span className="region-name">{hotspot.region_name}</span>
                    </td>
                    <td>
                      <span
                        className="contested-value"
                        style={{ color: getContestedColor(hotspot.contested_percent) }}
                      >
                        {hotspot.contested_percent.toFixed(1)}%
                      </span>
                    </td>
                    <td>
                      <span className="faction-name">{hotspot.owner_faction_name}</span>
                    </td>
                    <td>
                      <span className="faction-name">{hotspot.occupier_faction_name}</span>
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

        .region-name {
          color: var(--text-secondary);
          font-size: 13px;
        }

        .contested-value {
          font-weight: 700;
          font-size: 16px;
        }

        .faction-name {
          font-size: 13px;
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
