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
  },

  getLiveKills: async (systemId: number, limit = 20) => {
    const { data } = await api.get('/war/live/kills', { params: { system_id: systemId, limit } });
    return data;
  },

  getSystemKills: async (systemId: number, limit = 500, hours = 24) => {
    const { data } = await api.get(`/war/system/${systemId}/kills`, { params: { limit, hours } });
    return data;
  },

  getBattleKills: async (battleId: number, limit = 500) => {
    const { data } = await api.get(`/war/battle/${battleId}/kills`, { params: { limit } });
    return data;
  },

  getBattleShipClasses: async (battleId: number, groupBy = 'category') => {
    const { data } = await api.get(`/war/battle/${battleId}/ship-classes`, {
      params: { group_by: groupBy }
    });
    return data;
  },

  getBattleParticipants: async (battleId: number) => {
    const { data } = await api.get(`/war/battle/${battleId}/participants`);
    return data;
  },

  getSystemDanger: async (systemId: number) => {
    const { data } = await api.get(`/war/system/${systemId}/danger`);
    return data;
  },

  getSystemShipClasses: async (systemId: number, hours = 24, groupBy = 'category') => {
    const { data } = await api.get(`/war/system/${systemId}/ship-classes`, {
      params: { hours, group_by: groupBy }
    });
    return data;
  },

  getMapSystems: async () => {
    const { data } = await api.get('/war/map/systems');
    return data;
  }
};

export default api;
