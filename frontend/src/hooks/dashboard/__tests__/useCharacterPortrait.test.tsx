import { describe, it, expect, beforeEach, vi } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useCharacterPortrait } from '../useCharacterPortrait';
import axios from 'axios';
import { ReactNode } from 'react';

// Mock axios
vi.mock('axios');
const mockedAxios = vi.mocked(axios);

// Helper to create a wrapper with QueryClient
function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false, // Disable retries in tests
        gcTime: Infinity, // Keep cache forever in tests
      },
    },
  });

  return ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
}

describe('useCharacterPortrait', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('fetches portrait from backend proxy API', async () => {
    // Mock ESI response with portrait URLs
    const mockResponse = {
      data: {
        px256x256: 'https://images.evetech.net/characters/526379435/portrait?size=256'
      }
    };

    mockedAxios.get.mockResolvedValueOnce(mockResponse);

    const { result } = renderHook(() => useCharacterPortrait(526379435), {
      wrapper: createWrapper(),
    });

    // Initially: loading should be true
    expect(result.current.loading).toBe(true);
    expect(result.current.url).toBe(null);
    expect(result.current.error).toBe(null);

    // Wait for the query to resolve
    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    // Verify returns px256x256 URL
    expect(result.current.url).toBe('https://images.evetech.net/characters/526379435/portrait?size=256');
    expect(result.current.error).toBe(null);

    // Verify API was called with correct endpoint
    expect(mockedAxios.get).toHaveBeenCalledWith('/api/character/526379435/portrait');
  });

  it('returns loading state while fetching', () => {
    // Mock a never-resolving promise to keep loading state
    mockedAxios.get.mockImplementation(() => new Promise(() => {}));

    const { result } = renderHook(() => useCharacterPortrait(526379435), {
      wrapper: createWrapper(),
    });

    // Should show loading state
    expect(result.current.loading).toBe(true);
    expect(result.current.url).toBe(null);
    expect(result.current.error).toBe(null);
  });

  it('returns error on API failure', async () => {
    // Mock API error (need to mock twice due to retry: 1)
    const mockError = new Error('Network error');
    mockedAxios.get.mockRejectedValueOnce(mockError);
    mockedAxios.get.mockRejectedValueOnce(mockError);

    const { result } = renderHook(() => useCharacterPortrait(526379435), {
      wrapper: createWrapper(),
    });

    // Wait for the query to resolve
    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    }, { timeout: 3000 });

    // Verify error state and fallback URL
    expect(result.current.error).toBeInstanceOf(Error);
    expect(result.current.url).toBe('/default-avatar.png'); // Fallback URL
  });

  it('returns fallback URL on 404', async () => {
    // Mock 404 error (character has no portrait) - need to mock twice due to retry: 1
    const mock404Error = {
      response: {
        status: 404,
        data: { detail: 'Character not found' }
      }
    };
    mockedAxios.get.mockRejectedValueOnce(mock404Error);
    mockedAxios.get.mockRejectedValueOnce(mock404Error);

    const { result } = renderHook(() => useCharacterPortrait(999999999), {
      wrapper: createWrapper(),
    });

    // Wait for the query to resolve
    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    }, { timeout: 3000 });

    // Should return fallback URL
    expect(result.current.url).toBe('/default-avatar.png');
    expect(result.current.error).toBeTruthy();
  });

  it('caches portrait URL after first fetch', async () => {
    const mockResponse = {
      data: {
        px256x256: 'https://images.evetech.net/characters/526379435/portrait?size=256'
      }
    };

    mockedAxios.get.mockResolvedValue(mockResponse);

    const wrapper = createWrapper();

    // First call
    const { result: result1 } = renderHook(() => useCharacterPortrait(526379435), {
      wrapper,
    });

    await waitFor(() => {
      expect(result1.current.loading).toBe(false);
    });

    expect(result1.current.url).toBe('https://images.evetech.net/characters/526379435/portrait?size=256');

    // Second call with same character ID (should use cache)
    const { result: result2 } = renderHook(() => useCharacterPortrait(526379435), {
      wrapper,
    });

    // Should immediately have data from cache
    await waitFor(() => {
      expect(result2.current.loading).toBe(false);
    });

    expect(result2.current.url).toBe('https://images.evetech.net/characters/526379435/portrait?size=256');

    // API should only be called once (first fetch)
    expect(mockedAxios.get).toHaveBeenCalledTimes(1);
  });
});
