import { QueryClient } from '@tanstack/react-query';

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      // Data stays fresh for 60 seconds
      staleTime: 60 * 1000,
      // Cache persists for 5 minutes
      gcTime: 5 * 60 * 1000,
      // Retry failed requests
      retry: 2,
      // Don't refetch on window focus in production
      refetchOnWindowFocus: import.meta.env.DEV,
      // Refetch on mount only if data is stale
      refetchOnMount: true,
    },
  },
});
