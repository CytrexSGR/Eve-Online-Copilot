import { useState, useRef, useEffect } from 'react';
import { AgentEventType } from '../../types/agent-events';

interface EventFilterProps {
  selectedTypes: string[];
  onChange: (types: string[]) => void;
}

export function EventFilter({ selectedTypes, onChange }: EventFilterProps) {
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  const allEventTypes = Object.values(AgentEventType);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const toggleType = (type: string) => {
    if (selectedTypes.includes(type)) {
      onChange(selectedTypes.filter((t) => t !== type));
    } else {
      onChange([...selectedTypes, type]);
    }
  };

  const clearAll = () => {
    onChange([]);
  };

  const selectAll = () => {
    onChange(allEventTypes);
  };

  return (
    <div className="relative" ref={dropdownRef}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-2 px-3 py-1.5 bg-gray-700 hover:bg-gray-600 border border-gray-600 rounded text-sm text-gray-300 transition"
      >
        <span>🔍</span>
        <span>Filter Events</span>
        {selectedTypes.length > 0 && (
          <span className="bg-blue-600 text-white text-xs px-2 py-0.5 rounded-full">
            {selectedTypes.length} selected
          </span>
        )}
      </button>

      {isOpen && (
        <div className="absolute top-full left-0 mt-2 w-64 bg-gray-800 border border-gray-700 rounded shadow-lg z-50 max-h-96 overflow-y-auto">
          <div className="sticky top-0 bg-gray-800 p-2 border-b border-gray-700 flex gap-2">
            <button
              onClick={selectAll}
              className="flex-1 px-2 py-1 bg-blue-600 hover:bg-blue-700 text-white text-xs rounded transition"
            >
              Select All
            </button>
            <button
              onClick={clearAll}
              className="flex-1 px-2 py-1 bg-gray-700 hover:bg-gray-600 text-gray-300 text-xs rounded transition"
            >
              Clear All
            </button>
          </div>

          <div className="p-2">
            {allEventTypes.map((type) => (
              <label
                key={type}
                className="flex items-center gap-2 px-2 py-1.5 hover:bg-gray-700 rounded cursor-pointer"
              >
                <input
                  type="checkbox"
                  checked={selectedTypes.includes(type)}
                  onChange={() => toggleType(type)}
                  className="w-4 h-4 text-blue-600 bg-gray-700 border-gray-600 rounded focus:ring-blue-500"
                />
                <span className="text-sm text-gray-300">
                  {type.replace(/_/g, ' ').toLowerCase().replace(/\b\w/g, (l) => l.toUpperCase())}
                </span>
              </label>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
