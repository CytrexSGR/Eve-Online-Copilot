import { useState, useEffect } from 'react';

export interface Character {
  id: number;
  name: string;
}

export const CHARACTERS: Character[] = [
  { id: 526379435, name: 'Artallus' },
  { id: 1117367444, name: 'Cytrex' },
  { id: 110592475, name: 'Cytricia' }
];

type ActionType = 'production' | 'shopping' | 'trade' | 'general';

export function useCharacterSelection(actionType: ActionType) {
  const [selectedCharacterId, setSelectedCharacterId] = useState<number | null>(null);

  useEffect(() => {
    // Load last used character for this action type
    const stored = localStorage.getItem('lastUsedCharacter');
    if (stored) {
      try {
        const data = JSON.parse(stored);
        if (data[actionType]) {
          setSelectedCharacterId(data[actionType]);
        }
      } catch (e) {
        console.error('Error loading character selection:', e);
      }
    }
  }, [actionType]);

  const selectCharacter = (characterId: number) => {
    setSelectedCharacterId(characterId);

    // Save to localStorage
    const stored = localStorage.getItem('lastUsedCharacter');
    const data = stored ? JSON.parse(stored) : {};
    data[actionType] = characterId;
    localStorage.setItem('lastUsedCharacter', JSON.stringify(data));
  };

  const getSelectedCharacter = (): Character | null => {
    if (!selectedCharacterId) return null;
    return CHARACTERS.find(c => c.id === selectedCharacterId) || null;
  };

  return {
    selectedCharacterId,
    selectedCharacter: getSelectedCharacter(),
    selectCharacter,
    characters: CHARACTERS
  };
}
