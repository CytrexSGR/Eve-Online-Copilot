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

export interface ChatRequest {
  message: string;
  session_id?: string;
  character_id: number;
}

export interface ChatResponse {
  session_id: string;
  status: string;
}

export const agentClient = {
  /**
   * Create new agent session by sending an initial chat message
   */
  createSession: async (request: CreateSessionRequest): Promise<CreateSessionResponse> => {
    // Create session via chat endpoint with initial message
    const chatResponse = await api.post<ChatResponse>('/agent/chat', {
      message: 'Hello, I need help with EVE Online.',
      character_id: request.character_id || 526379435, // Default to Artallus
      session_id: undefined, // Force new session
    });

    // Fetch full session details
    const sessionDetails = await api.get(`/agent/session/${chatResponse.data.session_id}`);

    return {
      session_id: sessionDetails.data.id,
      status: sessionDetails.data.status,
      autonomy_level: sessionDetails.data.autonomy_level,
      created_at: sessionDetails.data.created_at,
    };
  },

  /**
   * Send a chat message to an existing or new session
   */
  chat: async (request: ChatRequest): Promise<ChatResponse> => {
    const response = await api.post<ChatResponse>('/agent/chat', request);
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
    const response = await api.get(`/agent/session/${sessionId}`);
    return response.data;
  },

  /**
   * Delete a session
   */
  deleteSession: async (sessionId: string): Promise<void> => {
    await api.delete(`/agent/session/${sessionId}`);
  },
};
