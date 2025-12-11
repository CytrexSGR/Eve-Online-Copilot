import type { Opportunity } from '../../hooks/dashboard/useOpportunities';
import { formatISK } from '../../utils/format';
import './OpportunityCard.css';

interface OpportunityCardProps {
  opportunity: Opportunity;
  onQuickAction: (opportunity: Opportunity) => void;
  onViewDetails: (opportunity: Opportunity) => void;
}

const CATEGORY_CONFIG = {
  production: {
    icon: '🏭',
    label: 'Production',
    color: '#3498db'
  },
  trade: {
    icon: '💰',
    label: 'Trade',
    color: '#2ecc71'
  },
  war_demand: {
    icon: '⚔️',
    label: 'War Demand',
    color: '#e74c3c'
  }
};

export default function OpportunityCard({
  opportunity,
  onQuickAction,
  onViewDetails
}: OpportunityCardProps) {
  const config = CATEGORY_CONFIG[opportunity.category];

  return (
    <div className="opportunity-card">
      <div className="opportunity-header">
        <div className="opportunity-icon" style={{ background: config.color }}>
          {config.icon}
        </div>
        <div className="opportunity-title">
          <h3>{opportunity.name}</h3>
          <span
            className="opportunity-badge"
            style={{ background: config.color }}
          >
            {config.label}
          </span>
        </div>
      </div>

      <div className="opportunity-stats">
        <div className="stat">
          <span className="stat-label">Profit</span>
          <span className="stat-value">{formatISK(opportunity.profit)}</span>
        </div>
        <div className="stat">
          <span className="stat-label">ROI</span>
          <span className="stat-value">{opportunity.roi.toFixed(1)}%</span>
        </div>
      </div>

      <div className="opportunity-actions">
        <button
          className="btn-quick-action"
          onClick={() => onQuickAction(opportunity)}
        >
          {opportunity.category === 'production' && 'Build Now'}
          {opportunity.category === 'trade' && 'Trade Now'}
          {opportunity.category === 'war_demand' && 'View Demand'}
        </button>
        <button
          className="btn-details"
          onClick={() => onViewDetails(opportunity)}
        >
          Details →
        </button>
      </div>
    </div>
  );
}
