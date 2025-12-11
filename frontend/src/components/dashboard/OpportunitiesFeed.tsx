import { useState } from 'react';
import { useOpportunities, type Opportunity } from '../../hooks/dashboard/useOpportunities';
import OpportunityCard from './OpportunityCard';
import CharacterSelector from '../shared/CharacterSelector';
import { useCharacterSelection } from '../../hooks/useCharacterSelection';
import './OpportunitiesFeed.css';

export default function OpportunitiesFeed() {
  const [showCharacterSelector, setShowCharacterSelector] = useState(false);
  const [selectedOpportunity, setSelectedOpportunity] = useState<Opportunity | null>(null);

  const {
    characters,
    selectedCharacterId,
    selectCharacter
  } = useCharacterSelection('production');

  const { data: opportunities, isLoading, error } = useOpportunities(10);

  const handleQuickAction = (opportunity: Opportunity) => {
    setSelectedOpportunity(opportunity);
    setShowCharacterSelector(true);
  };

  const handleCharacterSelected = (characterId: number) => {
    selectCharacter(characterId);
    setShowCharacterSelector(false);

    // Navigate to appropriate page based on opportunity category
    if (selectedOpportunity) {
      console.log(`Action for ${selectedOpportunity.name} with character ${characterId}`);
      // TODO: Navigate to production/trade page
    }
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

      {showCharacterSelector && selectedOpportunity && (
        <div className="character-selector-modal">
          <div className="modal-content">
            <h3>Select Character</h3>
            <p>Who should perform this action?</p>
            <CharacterSelector
              characters={characters}
              selectedCharacterId={selectedCharacterId}
              onSelect={handleCharacterSelected}
            />
            <button onClick={() => setShowCharacterSelector(false)}>
              Cancel
            </button>
          </div>
        </div>
      )}

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
