import axios from 'axios';
import type {
  BattleReport,
  WarProfiteeringReport,
  AllianceWarsReport,
  TradeRoutesReport
} from '../types/reports';

const API_BASE_URL = import.meta.env.PROD
  ? 'https://eve.infinimind-creations.com/api'
  : '/api';

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// API methods
export const reportsApi = {
  getBattleReport: async (): Promise<BattleReport> => {
    const { data } = await api.get('/reports/battle-24h');
    return data;
  },

  getWarProfiteering: async (): Promise<WarProfiteeringReport> => {
    const { data } = await api.get('/reports/war-profiteering');
    return data;
  },

  getAllianceWars: async (): Promise<AllianceWarsReport> => {
    const { data } = await api.get('/reports/alliance-wars');
    return data;
  },

  getTradeRoutes: async (): Promise<TradeRoutesReport> => {
    const { data } = await api.get('/reports/trade-routes');
    return data;
  },

  getHealth: async () => {
    const { data } = await api.get('/health');
    return data;
  }
};

export default api;
