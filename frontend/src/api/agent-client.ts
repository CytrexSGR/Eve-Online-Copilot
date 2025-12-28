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
   * Note: Backend creates sessions implicitly via /agent/chat endpoint
   */
  createSession: async (_request: CreateSessionRequest): Promise<CreateSessionResponse> => {
    // The backend doesn't have a dedicated /agent/sessions endpoint
    // Sessions are created via the /agent/chat endpoint with an initial message
    // For now, we'll return a mock response until this is properly integrated
    throw new Error('Session creation should be done via chat endpoint. Use agentClient.chat() instead.');
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
