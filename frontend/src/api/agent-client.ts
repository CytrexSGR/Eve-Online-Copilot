import { api } from '../api'; // Existing axios instance

export interface CreateSessionRequest {
  character_id?: number;
  autonomy_level: 'READ_ONLY' | 'RECOMMENDATIONS' | 'ASSISTED' | 'SUPERVISED';
}

export interface CreateSessionResponse {
  session_id: string;
  status: string;
  autonomy_level: string;
  created_at: string;
}

export interface ExecutePlanRequest {
  session_id: string;
  plan_id: string;
}

export interface RejectPlanRequest {
  session_id: string;
  plan_id: string;
  reason?: string;
}

export const agentClient = {
  /**
   * Create new agent session
   */
  createSession: async (request: CreateSessionRequest): Promise<CreateSessionResponse> => {
    const response = await api.post('/agent/sessions', request);
    return response.data;
  },

  /**
   * Execute (approve) a pending plan
   */
  executePlan: async (request: ExecutePlanRequest): Promise<void> => {
    await api.post('/agent/execute', request);
  },

  /**
   * Reject a pending plan
   */
  rejectPlan: async (request: RejectPlanRequest): Promise<void> => {
    await api.post('/agent/reject', request);
  },

  /**
   * Get session details
   */
  getSession: async (sessionId: string) => {
    const response = await api.get(`/agent/sessions/${sessionId}`);
    return response.data;
  },
};
