import { useCharacterPortrait } from '@/hooks/dashboard/useCharacterPortrait';
import { formatISK } from '@/utils/format';
import './CharacterCard.css';

export interface CharacterCardProps {
  characterId: number;
  name: string;
  balance: number;
  location: string;
  online: boolean;
}

/**
 * CharacterCard Component
 *
 * Displays a character card with portrait, name, ISK balance, location, and online status.
 *
 * Features:
 * - Shows character portrait (120px × 120px) with glow effect
 * - Displays character name
 * - Shows formatted ISK balance (e.g., "2.40B ISK")
 * - Displays location (truncated to 15 characters)
 * - Online status indicator (green dot if online, gray if offline)
 * - Hover effect: intensified glow + blue border
 *
 * Dimensions: 140px width × 200px height
 */
export default function CharacterCard({
  characterId,
  name,
  balance,
  location,
  online,
}: CharacterCardProps) {
  const { url, loading } = useCharacterPortrait(characterId);

  // Truncate location to 15 characters
  const truncatedLocation = location.length > 15
    ? location.substring(0, 15) + '...'
    : location;

  return (
    <div className="character-card" data-testid="character-card">
      {/* Portrait Section */}
      <div className="character-portrait">
        {loading ? (
          <div className="portrait-loading" data-testid="portrait-loading">
            <div className="loading-spinner"></div>
          </div>
        ) : (
          <img
            src={url || '/default-avatar.png'}
            alt={`${name} portrait`}
            className="portrait-image"
          />
        )}
      </div>

      {/* Character Info Section */}
      <div className="character-info">
        {/* Name with online status dot */}
        <div className="character-name-row">
          <span
            className={`status-dot ${online ? 'status-dot-online' : 'status-dot-offline'}`}
            data-testid="status-dot"
          ></span>
          <h3 className="character-name">{name}</h3>
        </div>

        {/* ISK Balance */}
        <div className="character-balance">
          {formatISK(balance)} ISK
        </div>

        {/* Location */}
        <div className="character-location" title={location}>
          {truncatedLocation}
        </div>
      </div>
    </div>
  );
}
