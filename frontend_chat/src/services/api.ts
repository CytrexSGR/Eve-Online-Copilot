/**
 * API Client for AI Copilot
 * REST API communication
 */

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8001';

export interface ChatRequest {
  message: string;
  session_id?: string;
  character_id?: number;
  region_id?: number;
}

export interface ChatResponse {
  response: string;
  session_id: string;
  tool_calls: any[];
}

export interface Session {
  session_id: string;
  character_id?: number;
  region_id: number;
}

export const api = {
  async createSession(characterId?: number, regionId: number = 10000002): Promise<Session> {
    const response = await fetch(`${API_BASE_URL}/copilot/sessions`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ character_id: characterId, region_id: regionId })
    });

    if (!response.ok) {
      throw new Error('Failed to create session');
    }

    return response.json();
  },

  async sendMessage(request: ChatRequest): Promise<ChatResponse> {
    const response = await fetch(`${API_BASE_URL}/copilot/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(request)
    });

    if (!response.ok) {
      throw new Error('Failed to send message');
    }

    return response.json();
  },

  async transcribeAudio(audioBlob: Blob): Promise<{ text: string }> {
    const formData = new FormData();
    formData.append('audio', audioBlob, 'recording.webm');

    const response = await fetch(`${API_BASE_URL}/copilot/audio/transcribe`, {
      method: 'POST',
      body: formData
    });

    if (!response.ok) {
      throw new Error('Failed to transcribe audio');
    }

    return response.json();
  },

  async synthesizeSpeech(text: string, voice?: string): Promise<Blob> {
    const response = await fetch(`${API_BASE_URL}/copilot/audio/synthesize`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text, voice })
    });

    if (!response.ok) {
      throw new Error('Failed to synthesize speech');
    }

    const data = await response.json();
    // Convert hex string to blob
    const bytes = new Uint8Array(data.audio.match(/.{1,2}/g).map((byte: string) => parseInt(byte, 16)));
    return new Blob([bytes], { type: 'audio/mpeg' });
  },

  async getHealth(): Promise<any> {
    const response = await fetch(`${API_BASE_URL}/health`);
    return response.json();
  }
};
