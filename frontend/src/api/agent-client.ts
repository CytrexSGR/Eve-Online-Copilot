import { api } from '../api'; // Existing axios instance
import type { ChatMessage } from '../types/chat-messages';

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

  /**
   * Send a message (non-streaming, saves to database)
   */
  sendMessage: async (
    sessionId: string,
    message: string,
    characterId: number
  ): Promise<void> => {
    await api.post('/agent/chat', {
      message,
      session_id: sessionId,
      character_id: characterId,
    });
  },

  /**
   * Get chat history for a session
   */
  getChatHistory: async (sessionId: string): Promise<ChatMessage[]> => {
    const response = await api.get(`/agent/chat/history/${sessionId}`);
    return response.data.messages.map((msg: any) => ({
      id: msg.id,
      role: msg.role as 'user' | 'assistant' | 'system',
      content: msg.content,
      timestamp: msg.created_at,
      isStreaming: false,
    }));
  },

  /**
   * Stream chat response via SSE
   * Note: Uses fetch API since EventSource doesn't support POST with body
   */
  streamChatResponse: (
    sessionId: string,
    message: string,
    characterId: number,
    onChunk: (text: string) => void,
    onDone: (messageId: string) => void,
    onError: (error: string) => void
  ): (() => void) => {
    const controller = new AbortController();

    // Start the streaming request
    (async () => {
      try {
        const response = await fetch('/agent/chat/stream', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            message,
            session_id: sessionId,
            character_id: characterId,
          }),
          signal: controller.signal,
        });

        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }

        const reader = response.body?.getReader();
        if (!reader) {
          throw new Error('Response body is not readable');
        }

        const decoder = new TextDecoder();
        let buffer = '';

        while (true) {
          const { done, value } = await reader.read();

          if (done) break;

          // Decode the chunk and add to buffer
          buffer += decoder.decode(value, { stream: true });

          // Process complete SSE messages (separated by \n\n)
          const lines = buffer.split('\n\n');
          buffer = lines.pop() || ''; // Keep incomplete message in buffer

          for (const line of lines) {
            if (!line.trim()) continue;

            // SSE format: "data: <json>"
            const dataMatch = line.match(/^data: (.+)$/m);
            if (dataMatch) {
              try {
                const data = JSON.parse(dataMatch[1]);

                if (data.type === 'text') {
                  onChunk(data.text);
                } else if (data.type === 'done') {
                  onDone(data.message_id);
                  return; // Stream complete
                } else if (data.type === 'error') {
                  onError(data.error);
                  return;
                }
              } catch (e) {
                console.error('Failed to parse SSE event:', e);
              }
            }
          }
        }
      } catch (error: any) {
        if (error.name === 'AbortError') {
          console.log('Stream aborted');
        } else {
          console.error('Stream error:', error);
          onError(error.message || 'Connection error');
        }
      }
    })();

    // Return cleanup function
    return () => controller.abort();
  },
};
