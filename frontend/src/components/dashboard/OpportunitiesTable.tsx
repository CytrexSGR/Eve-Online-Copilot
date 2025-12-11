import { useState, useMemo } from 'react';
import type { Opportunity } from '../../hooks/dashboard/useOpportunities';
import { formatISK } from '../../utils/format';
import './OpportunitiesTable.css';

interface OpportunitiesTableProps {
  opportunities: Opportunity[];
  onRowClick?: (opportunity: Opportunity) => void;
  loading?: boolean;
}

type SortColumn = 'name' | 'profit' | 'roi' | 'category';
type SortDirection = 'asc' | 'desc';

const CATEGORY_CONFIG = {
  production: { label: 'PROD', icon: '🏭', color: '#3498db' },
  trade: { label: 'TRADE', icon: '💰', color: '#2ecc71' },
  war_demand: { label: 'WAR', icon: '⚔️', color: '#e74c3c' }
};

export default function OpportunitiesTable({
  opportunities,
  onRowClick,
  loading = false
}: OpportunitiesTableProps) {
  const [sortColumn, setSortColumn] = useState<SortColumn>('profit');
  const [sortDirection, setSortDirection] = useState<SortDirection>('desc');

  // Sort opportunities
  const sortedOpportunities = useMemo(() => {
    const sorted = [...opportunities];
    sorted.sort((a, b) => {
      let aValue: string | number;
      let bValue: string | number;

      switch (sortColumn) {
        case 'name':
          aValue = a.name.toLowerCase();
          bValue = b.name.toLowerCase();
          break;
        case 'profit':
          aValue = a.profit;
          bValue = b.profit;
          break;
        case 'roi':
          aValue = a.roi;
          bValue = b.roi;
          break;
        case 'category':
          aValue = a.category;
          bValue = b.category;
          break;
        default:
          return 0;
      }

      if (aValue < bValue) return sortDirection === 'asc' ? -1 : 1;
      if (aValue > bValue) return sortDirection === 'asc' ? 1 : -1;
      return 0;
    });
    return sorted;
  }, [opportunities, sortColumn, sortDirection]);

  const handleHeaderClick = (column: SortColumn) => {
    if (sortColumn === column) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      setSortColumn(column);
      setSortDirection('desc');
    }
  };

  const handleRowClick = (opportunity: Opportunity) => {
    if (onRowClick) {
      onRowClick(opportunity);
    }
  };

  // Get profit color based on value
  const getProfitColor = (profit: number): string => {
    if (profit >= 5000000000) return '#3fb950'; // Bright green for >5B
    if (profit >= 1000000000) return '#2ea043'; // Medium green for >1B
    return '#238636'; // Muted green
  };

  // Get ROI color based on thresholds
  const getRoiColor = (roi: number): string => {
    if (roi >= 40) return '#3fb950'; // Bright green for >40%
    if (roi >= 20) return '#2ea043'; // Medium green for 20-40%
    return '#8b949e'; // Muted gray for <20%
  };

  if (loading) {
    return (
      <div className="opportunities-table-container">
        <div className="loading-state">Loading opportunities...</div>
      </div>
    );
  }

  if (opportunities.length === 0) {
    return (
      <div className="opportunities-table-container">
        <div className="empty-state">No opportunities found</div>
      </div>
    );
  }

  return (
    <div className="opportunities-table-container">
      <table className="opportunities-table">
        <thead>
          <tr>
            <th>Icon</th>
            <th
              className="sortable"
              onClick={() => handleHeaderClick('name')}
            >
              Item Name
              {sortColumn === 'name' && (
                <span className="sort-indicator">
                  {sortDirection === 'asc' ? ' ↑' : ' ↓'}
                </span>
              )}
            </th>
            <th
              className="sortable"
              onClick={() => handleHeaderClick('profit')}
            >
              Profit
              {sortColumn === 'profit' && (
                <span className="sort-indicator">
                  {sortDirection === 'asc' ? ' ↑' : ' ↓'}
                </span>
              )}
            </th>
            <th
              className="sortable"
              onClick={() => handleHeaderClick('roi')}
            >
              ROI
              {sortColumn === 'roi' && (
                <span className="sort-indicator">
                  {sortDirection === 'asc' ? ' ↑' : ' ↓'}
                </span>
              )}
            </th>
            <th
              className="sortable"
              onClick={() => handleHeaderClick('category')}
            >
              Category
              {sortColumn === 'category' && (
                <span className="sort-indicator">
                  {sortDirection === 'asc' ? ' ↑' : ' ↓'}
                </span>
              )}
            </th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {sortedOpportunities.map((opportunity) => {
            const config = CATEGORY_CONFIG[opportunity.category] || {
              label: 'UNKNOWN',
              icon: '❓',
              color: '#6e7681'
            };
            return (
              <tr
                key={opportunity.type_id}
                className="table-row"
                onClick={() => handleRowClick(opportunity)}
              >
                <td className="icon-cell">
                  <span
                    className="category-icon"
                    style={{ background: config.color }}
                  >
                    {config.icon}
                  </span>
                </td>
                <td className="name-cell">{opportunity.name}</td>
                <td
                  className="profit-cell"
                  style={{ color: getProfitColor(opportunity.profit) }}
                >
                  {formatISK(opportunity.profit)}
                </td>
                <td
                  className="roi-cell"
                  style={{ color: getRoiColor(opportunity.roi) }}
                >
                  {opportunity.roi.toFixed(1)}%
                </td>
                <td className="category-cell">
                  <span
                    className="category-badge"
                    style={{ background: config.color }}
                  >
                    {config.label}
                  </span>
                </td>
                <td className="actions-cell">
                  <button
                    className="action-button"
                    onClick={(e) => {
                      e.stopPropagation();
                      handleRowClick(opportunity);
                    }}
                  >
                    View Details
                  </button>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
