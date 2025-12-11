import { useOpportunities, type Opportunity } from '../../hooks/dashboard/useOpportunities';
import OpportunityCard from './OpportunityCard';
import './OpportunitiesFeed.css';

export default function OpportunitiesFeed() {
  const { data: opportunities, isLoading, error } = useOpportunities(10);

  const handleQuickAction = (opportunity: Opportunity) => {
    console.log('Quick action for:', opportunity);
    // TODO: Open character selector, then navigate to appropriate page
  };

  const handleViewDetails = (opportunity: Opportunity) => {
    console.log('View details for:', opportunity);
    // TODO: Navigate to appropriate analysis page
  };

  if (isLoading) {
    return (
      <div className="opportunities-feed">
        <h2>Top Opportunities</h2>
        <div className="loading">Loading opportunities...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="opportunities-feed">
        <h2>Top Opportunities</h2>
        <div className="error">Error loading opportunities. Please try again.</div>
      </div>
    );
  }

  return (
    <div className="opportunities-feed">
      <h2>Top Opportunities</h2>
      <div className="opportunities-grid">
        {opportunities?.map((op, index) => (
          <OpportunityCard
            key={`${op.type_id}-${op.category}-${index}`}
            opportunity={op}
            onQuickAction={handleQuickAction}
            onViewDetails={handleViewDetails}
          />
        ))}
      </div>

      {opportunities?.length === 0 && (
        <div className="empty-state">
          No opportunities found. Check back later!
        </div>
      )}
    </div>
  );
}
