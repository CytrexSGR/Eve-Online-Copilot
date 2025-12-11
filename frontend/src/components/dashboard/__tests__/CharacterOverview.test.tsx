import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import CharacterOverview from '../CharacterOverview';
import { get } from '@/api';

// Mock the API
vi.mock('@/api', () => ({
  get: vi.fn(),
}));

// Mock CharacterCard component
vi.mock('../CharacterCard', () => ({
  default: ({ characterId, name, balance, location, online }: any) => (
    <div data-testid="character-card" data-character-id={characterId}>
      <span data-testid="character-name">{name}</span>
      <span data-testid="character-balance">{balance}</span>
      <span data-testid="character-location">{location}</span>
      <span data-testid="character-online">{online ? 'online' : 'offline'}</span>
    </div>
  ),
}));

describe('CharacterOverview', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders 3 character cards', async () => {
    // Mock API response with 3 characters: Artallus, Cytrex, Cytricia
    const mockCharacters = [
      {
        character_id: 526379435,
        name: 'Artallus',
        isk_balance: 2400000000,
        location: { system_id: 30000142, system_name: 'Jita' },
        active_jobs: [],
        skill_queue: null,
      },
      {
        character_id: 1117367444,
        name: 'Cytrex',
        isk_balance: 1500000000,
        location: { system_id: 30000144, system_name: 'Isikemi' },
        active_jobs: [],
        skill_queue: null,
      },
      {
        character_id: 110592475,
        name: 'Cytricia',
        isk_balance: 850000000,
        location: { system_id: 30000142, system_name: 'Jita' },
        active_jobs: [],
        skill_queue: null,
      },
    ];

    vi.mocked(get).mockResolvedValue({ data: mockCharacters });

    render(<CharacterOverview />);

    // Wait for data to load
    await waitFor(() => {
      const cards = screen.getAllByTestId('character-card');
      expect(cards).toHaveLength(3);
    });

    // Verify all 3 characters are rendered
    expect(screen.getByText('Artallus')).toBeInTheDocument();
    expect(screen.getByText('Cytrex')).toBeInTheDocument();
    expect(screen.getByText('Cytricia')).toBeInTheDocument();
  });

  it('displays section header "Your Pilots"', () => {
    // Mock API response
    vi.mocked(get).mockResolvedValue({ data: [] });

    render(<CharacterOverview />);

    // Check for "Your Pilots" header (not "Your Characters")
    const header = screen.getByRole('heading', { name: /your pilots/i });
    expect(header).toBeInTheDocument();
  });

  it('fetches data for all 3 characters', async () => {
    // Mock API response
    const mockCharacters = [
      {
        character_id: 526379435,
        name: 'Artallus',
        isk_balance: 2400000000,
        location: { system_id: 30000142, system_name: 'Jita' },
        active_jobs: [],
        skill_queue: null,
      },
      {
        character_id: 1117367444,
        name: 'Cytrex',
        isk_balance: 1500000000,
        location: { system_id: 30000144, system_name: 'Isikemi' },
        active_jobs: [],
        skill_queue: null,
      },
      {
        character_id: 110592475,
        name: 'Cytricia',
        isk_balance: 850000000,
        location: { system_id: 30000142, system_name: 'Jita' },
        active_jobs: [],
        skill_queue: null,
      },
    ];

    vi.mocked(get).mockResolvedValue({ data: mockCharacters });

    render(<CharacterOverview />);

    // Wait for API call
    await waitFor(() => {
      expect(get).toHaveBeenCalledWith('/api/dashboard/characters/summary');
    });

    // Verify API was called exactly once
    expect(get).toHaveBeenCalledTimes(1);
  });

  it('shows loading state for all cards', () => {
    // Mock API with delayed response
    vi.mocked(get).mockImplementation(
      () => new Promise((resolve) => setTimeout(() => resolve({ data: [] }), 1000))
    );

    render(<CharacterOverview />);

    // Check for loading indicator
    const loadingElement = screen.getByTestId('characters-loading');
    expect(loadingElement).toBeInTheDocument();
  });

  it('handles API errors gracefully', async () => {
    // Mock API error
    vi.mocked(get).mockRejectedValue(new Error('API Error'));

    render(<CharacterOverview />);

    // Wait for error state
    await waitFor(() => {
      const errorElement = screen.getByTestId('characters-error');
      expect(errorElement).toBeInTheDocument();
    });

    // Verify error message is displayed
    expect(screen.getByText(/error loading characters/i)).toBeInTheDocument();
  });
});
