import axios from 'axios';
import type {
  BattleReport,
  WarProfiteering,
  AllianceWars,
  TradeRoutes
} from '../types/reports';

const API_BASE_URL = import.meta.env.PROD
  ? 'https://eve.infinimind-creations.com/api'
  : '/api';

console.log('API Configuration:', {
  isProd: import.meta.env.PROD,
  mode: import.meta.env.MODE,
  baseURL: API_BASE_URL
});

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 60000,  // 60 seconds for initial report generation
  headers: {
    'Content-Type': 'application/json',
  },
});

// API methods
export const reportsApi = {
  getBattleReport: async (): Promise<BattleReport> => {
    const { data } = await api.get('/war/pilot-intelligence');
    return data;
  },

  getWarProfiteering: async (): Promise<WarProfiteering> => {
    const { data } = await api.get('/reports/war-profiteering');
    return data;
  },

  getAllianceWars: async (): Promise<AllianceWars> => {
    const { data } = await api.get('/reports/alliance-wars');
    return data;
  },

  getTradeRoutes: async (): Promise<TradeRoutes> => {
    const { data } = await api.get('/reports/trade-routes');
    return data;
  },

  getHealth: async () => {
    const { data } = await api.get('/health');
    return data;
  }
};

// Battle API for live battle tracking and Telegram alerts
export const battleApi = {
  getActiveBattles: async (limit = 10) => {
    const { data } = await api.get('/war/battles/active', { params: { limit } });
    return data;
  },

  getRecentTelegramAlerts: async (limit = 5) => {
    const { data } = await api.get('/war/telegram/recent', { params: { limit } });
    return data;
  }
};

export default api;
