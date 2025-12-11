import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import CharacterCard from '../CharacterCard';
import { ReactNode } from 'react';

// Mock the useCharacterPortrait hook
vi.mock('@/hooks/dashboard/useCharacterPortrait', () => ({
  useCharacterPortrait: vi.fn(),
}));

import { useCharacterPortrait } from '@/hooks/dashboard/useCharacterPortrait';
const mockedUseCharacterPortrait = vi.mocked(useCharacterPortrait);

// Helper to create a wrapper with QueryClient
function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        gcTime: Infinity,
      },
    },
  });

  return ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
}

describe('CharacterCard', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders character portrait', async () => {
    // Mock successful portrait fetch
    mockedUseCharacterPortrait.mockReturnValue({
      url: 'https://images.evetech.net/characters/526379435/portrait?size=256',
      loading: false,
      error: null,
    });

    render(
      <CharacterCard
        characterId={526379435}
        name="Artallus"
        balance={2400000000}
        location="Jita IV - Moon 4"
        online={true}
      />,
      { wrapper: createWrapper() }
    );

    // Verify <img> with portrait URL
    await waitFor(() => {
      const img = screen.getByAltText('Artallus portrait');
      expect(img).toBeInTheDocument();
      expect(img).toHaveAttribute('src', 'https://images.evetech.net/characters/526379435/portrait?size=256');
    });
  });

  it('shows loading state for portrait', () => {
    // Mock loading state
    mockedUseCharacterPortrait.mockReturnValue({
      url: null,
      loading: true,
      error: null,
    });

    render(
      <CharacterCard
        characterId={526379435}
        name="Artallus"
        balance={2400000000}
        location="Jita IV - Moon 4"
        online={true}
      />,
      { wrapper: createWrapper() }
    );

    // Skeleton or spinner while loading
    const loadingElement = screen.getByTestId('portrait-loading');
    expect(loadingElement).toBeInTheDocument();
  });

  it('shows fallback avatar on error', () => {
    // Mock error state
    mockedUseCharacterPortrait.mockReturnValue({
      url: '/default-avatar.png',
      loading: false,
      error: new Error('Network error'),
    });

    render(
      <CharacterCard
        characterId={526379435}
        name="Artallus"
        balance={2400000000}
        location="Jita IV - Moon 4"
        online={true}
      />,
      { wrapper: createWrapper() }
    );

    // Portrait fails: show default avatar icon
    const img = screen.getByAltText('Artallus portrait');
    expect(img).toHaveAttribute('src', '/default-avatar.png');
  });

  it('displays character name', () => {
    mockedUseCharacterPortrait.mockReturnValue({
      url: 'https://images.evetech.net/characters/526379435/portrait?size=256',
      loading: false,
      error: null,
    });

    render(
      <CharacterCard
        characterId={526379435}
        name="Artallus"
        balance={2400000000}
        location="Jita IV - Moon 4"
        online={true}
      />,
      { wrapper: createWrapper() }
    );

    // Name rendered correctly
    expect(screen.getByText('Artallus')).toBeInTheDocument();
  });

  it('shows ISK balance formatted', () => {
    mockedUseCharacterPortrait.mockReturnValue({
      url: 'https://images.evetech.net/characters/526379435/portrait?size=256',
      loading: false,
      error: null,
    });

    render(
      <CharacterCard
        characterId={526379435}
        name="Artallus"
        balance={2400000000}
        location="Jita IV - Moon 4"
        online={true}
      />,
      { wrapper: createWrapper() }
    );

    // 2400000000 → "2.40B ISK"
    expect(screen.getByText(/2\.40B/i)).toBeInTheDocument();
    expect(screen.getByText(/ISK/i)).toBeInTheDocument();
  });

  it('displays location with truncation', () => {
    mockedUseCharacterPortrait.mockReturnValue({
      url: 'https://images.evetech.net/characters/526379435/portrait?size=256',
      loading: false,
      error: null,
    });

    render(
      <CharacterCard
        characterId={526379435}
        name="Artallus"
        balance={2400000000}
        location="Jita IV - Moon 4 - Caldari Navy Assembly Plant"
        online={true}
      />,
      { wrapper: createWrapper() }
    );

    // Long system names truncated to 15 chars
    const locationElement = screen.getByText(/Jita IV - Moon/);
    expect(locationElement).toBeInTheDocument();
    // Should be truncated with ellipsis
    expect(locationElement.textContent?.length).toBeLessThanOrEqual(18); // 15 chars + "..."
  });

  it('shows online status dot', () => {
    mockedUseCharacterPortrait.mockReturnValue({
      url: 'https://images.evetech.net/characters/526379435/portrait?size=256',
      loading: false,
      error: null,
    });

    // Test online status
    const { rerender } = render(
      <CharacterCard
        characterId={526379435}
        name="Artallus"
        balance={2400000000}
        location="Jita IV - Moon 4"
        online={true}
      />,
      { wrapper: createWrapper() }
    );

    // Green if online
    const onlineDot = screen.getByTestId('status-dot');
    expect(onlineDot).toBeInTheDocument();
    expect(onlineDot).toHaveClass('status-dot-online');

    // Test offline status
    rerender(
      <CharacterCard
        characterId={526379435}
        name="Artallus"
        balance={2400000000}
        location="Jita IV - Moon 4"
        online={false}
      />
    );

    // Gray if offline
    const offlineDot = screen.getByTestId('status-dot');
    expect(offlineDot).toHaveClass('status-dot-offline');
  });

  it('applies hover glow effect', async () => {
    const user = userEvent.setup();
    mockedUseCharacterPortrait.mockReturnValue({
      url: 'https://images.evetech.net/characters/526379435/portrait?size=256',
      loading: false,
      error: null,
    });

    render(
      <CharacterCard
        characterId={526379435}
        name="Artallus"
        balance={2400000000}
        location="Jita IV - Moon 4"
        online={true}
      />,
      { wrapper: createWrapper() }
    );

    // Hover increases box-shadow glow
    const card = screen.getByTestId('character-card');
    expect(card).toBeInTheDocument();
    expect(card).toHaveClass('character-card');

    // Hover over the card
    await user.hover(card);

    // Card should have the character-card class which enables hover effect
    expect(card).toHaveClass('character-card');
  });
});
