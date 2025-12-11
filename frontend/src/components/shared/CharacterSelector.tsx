import type { Character } from '../../hooks/useCharacterSelection';
import './CharacterSelector.css';

interface CharacterSelectorProps {
  characters: Character[];
  selectedCharacterId: number | null;
  onSelect: (characterId: number) => void;
  label?: string;
}

export default function CharacterSelector({
  characters,
  selectedCharacterId,
  onSelect,
  label = 'Select Character'
}: CharacterSelectorProps) {
  return (
    <div className="character-selector">
      {label && <label className="selector-label">{label}</label>}
      <select
        className="selector-dropdown"
        value={selectedCharacterId || ''}
        onChange={(e) => onSelect(Number(e.target.value))}
      >
        <option value="">Choose character...</option>
        {characters.map(char => (
          <option key={char.id} value={char.id}>
            {char.name}
          </option>
        ))}
      </select>
    </div>
  );
}
