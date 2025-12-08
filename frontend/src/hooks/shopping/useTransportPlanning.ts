import { useQuery } from '@tanstack/react-query';
import { useState } from 'react';
import type { CargoSummary, TransportOptions } from '../../types/shopping';
import { getCargoSummary, getTransportOptions } from '../../api/shopping';

/**
 * Hook for cargo summary and transport planning
 */
export function useTransportPlanning(listId: number | null, enabled: boolean = false) {
  const [safeRoutesOnly, setSafeRoutesOnly] = useState(true);
  const [transportFilter, setTransportFilter] = useState<string>('');

  // Fetch cargo summary
  const cargoSummary = useQuery<CargoSummary>({
    queryKey: ['shopping-cargo', listId],
    queryFn: () => getCargoSummary(listId!),
    enabled: !!listId,
  });

  // Fetch transport options
  const transportOptions = useQuery<TransportOptions>({
    queryKey: ['shopping-transport', listId, safeRoutesOnly],
    queryFn: () => getTransportOptions(listId!),
    enabled: !!listId && enabled,
  });

  return {
    cargoSummary,
    transportOptions,
    safeRoutesOnly,
    setSafeRoutesOnly,
    transportFilter,
    setTransportFilter,
  };
}
