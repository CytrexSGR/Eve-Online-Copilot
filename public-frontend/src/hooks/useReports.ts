import { useQuery } from '@tanstack/react-query';
import type { UseQueryOptions } from '@tanstack/react-query';
import { reportsApi } from '../services/api';
import type {
  BattleReport,
  WarProfiteering,
  AllianceWars,
  TradeRoutes
} from '../types/reports';

// Query keys for cache management
export const reportKeys = {
  all: ['reports'] as const,
  battleReport: () => [...reportKeys.all, 'battle'] as const,
  warProfiteering: () => [...reportKeys.all, 'profiteering'] as const,
  allianceWars: () => [...reportKeys.all, 'alliance-wars'] as const,
  tradeRoutes: () => [...reportKeys.all, 'trade-routes'] as const,
};

// Battle Report Hook
export function useBattleReport(options?: Omit<UseQueryOptions<BattleReport>, 'queryKey' | 'queryFn'>) {
  return useQuery({
    queryKey: reportKeys.battleReport(),
    queryFn: reportsApi.getBattleReport,
    ...options,
  });
}

// War Profiteering Hook
export function useWarProfiteering(options?: Omit<UseQueryOptions<WarProfiteering>, 'queryKey' | 'queryFn'>) {
  return useQuery({
    queryKey: reportKeys.warProfiteering(),
    queryFn: reportsApi.getWarProfiteering,
    ...options,
  });
}

// Alliance Wars Hook
export function useAllianceWars(options?: Omit<UseQueryOptions<AllianceWars>, 'queryKey' | 'queryFn'>) {
  return useQuery({
    queryKey: reportKeys.allianceWars(),
    queryFn: reportsApi.getAllianceWars,
    ...options,
  });
}

// Trade Routes Hook
export function useTradeRoutes(options?: Omit<UseQueryOptions<TradeRoutes>, 'queryKey' | 'queryFn'>) {
  return useQuery({
    queryKey: reportKeys.tradeRoutes(),
    queryFn: reportsApi.getTradeRoutes,
    ...options,
  });
}

// Combined hook for all reports (critical data first)
export function useAllReports() {
  const battleReport = useBattleReport();

  // Non-critical reports - only fetch after battle report succeeds
  const profiteering = useWarProfiteering({
    enabled: battleReport.isSuccess,
  });

  const allianceWars = useAllianceWars({
    enabled: battleReport.isSuccess,
  });

  const tradeRoutes = useTradeRoutes({
    enabled: battleReport.isSuccess,
  });

  return {
    battleReport: battleReport.data,
    profiteering: profiteering.data,
    allianceWars: allianceWars.data,
    tradeRoutes: tradeRoutes.data,
    isLoading: battleReport.isLoading,
    isError: battleReport.isError || profiteering.isError || allianceWars.isError || tradeRoutes.isError,
    error: battleReport.error || profiteering.error || allianceWars.error || tradeRoutes.error,
    refetch: () => {
      battleReport.refetch();
      profiteering.refetch();
      allianceWars.refetch();
      tradeRoutes.refetch();
    },
  };
}
