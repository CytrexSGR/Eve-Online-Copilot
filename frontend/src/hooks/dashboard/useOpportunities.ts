import { useQuery } from '@tanstack/react-query';
import axios from 'axios';

export interface Opportunity {
  category: 'production' | 'trade' | 'war_demand';
  type_id: number;
  name: string;
  profit: number;
  roi: number;
  difficulty?: number;
  material_cost?: number;
  sell_price?: number;
  buy_region_id?: number;
  sell_region_id?: number;
  region_id?: number;
  destroyed_count?: number;
  market_stock?: number;
}

export function useOpportunities(limit: number = 10) {
  return useQuery<Opportunity[]>({
    queryKey: ['dashboard', 'opportunities', limit],
    queryFn: async () => {
      const response = await axios.get(`/api/dashboard/opportunities`, {
        params: { limit }
      });
      return response.data;
    },
    staleTime: 5 * 60 * 1000, // 5 minutes
    refetchOnWindowFocus: true
  });
}
