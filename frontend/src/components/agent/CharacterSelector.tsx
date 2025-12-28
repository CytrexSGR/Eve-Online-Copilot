interface Character {
  id: number;
  name: string;
}

interface CharacterSelectorProps {
  characters: Character[];
  selectedId: number | null;
  onChange: (characterId: number | null) => void;
  disabled?: boolean;
}

export function CharacterSelector({
  characters,
  selectedId,
  onChange,
  disabled = false,
}: CharacterSelectorProps) {
  const handleChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const value = e.target.value;
    onChange(value ? parseInt(value, 10) : null);
  };

  return (
    <div className="flex items-center gap-2">
      <label className="text-sm font-medium text-gray-300">
        Character:
      </label>
      <select
        value={selectedId || ''}
        onChange={handleChange}
        disabled={disabled}
        className="bg-gray-700 border border-gray-600 rounded px-3 py-1.5 text-gray-100 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
      >
        <option value="">Select a character...</option>
        {characters.map((char) => (
          <option key={char.id} value={char.id}>
            {char.name}
          </option>
        ))}
      </select>
    </div>
  );
}

export type { Character };
