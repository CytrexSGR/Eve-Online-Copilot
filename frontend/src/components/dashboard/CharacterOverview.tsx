import { useState, useEffect } from 'react';
import { get } from '@/api';
import CharacterCard from './CharacterCard';
import './CharacterOverview.css';

interface CharacterSummary {
  character_id: number;
  name: string;
  isk_balance: number;
  location: {
    system_id: number | null;
    system_name: string;
  };
  active_jobs: any[];
  skill_queue: any;
}

/**
 * CharacterOverview Component
 *
 * Displays overview cards for all 3 characters: Artallus, Cytrex, Cytricia
 *
 * Features:
 * - Fetches data from /api/dashboard/characters/summary endpoint
 * - Displays 3 CharacterCard components in horizontal layout
 * - Shows "Your Pilots" header
 * - Handles loading and error states
 * - Each card shows portrait, ISK balance, location, and online status
 */
export default function CharacterOverview() {
  const [characters, setCharacters] = useState<CharacterSummary[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchCharacters();
  }, []);

  const fetchCharacters = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await get('/api/dashboard/characters/summary');
      setCharacters(response.data || []);
    } catch (err) {
      console.error('Error fetching characters:', err);
      setError('Error loading characters');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="character-overview" data-testid="characters-loading">
        <h2 className="character-overview-header">Your Pilots</h2>
        <div className="character-cards-container">
          <div className="character-loading-placeholder">Loading characters...</div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="character-overview" data-testid="characters-error">
        <h2 className="character-overview-header">Your Pilots</h2>
        <div className="character-cards-container">
          <div className="character-error-message">{error}</div>
        </div>
      </div>
    );
  }

  return (
    <div className="character-overview">
      <h2 className="character-overview-header">Your Pilots</h2>
      <div className="character-cards-container">
        {characters.map((character) => (
          <CharacterCard
            key={character.character_id}
            characterId={character.character_id}
            name={character.name}
            balance={character.isk_balance}
            location={character.location.system_name}
            online={false} // TODO: Implement online status detection
          />
        ))}
      </div>
    </div>
  );
}
