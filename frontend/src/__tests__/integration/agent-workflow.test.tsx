import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import AgentDashboard from '../../pages/AgentDashboard';

// Mock agent client
vi.mock('../../api/agent-client', () => ({
  agentClient: {
    createSession: vi.fn().mockResolvedValue({
      session_id: 'sess-test-123',
      status: 'idle',
      autonomy_level: 'RECOMMENDATIONS',
      created_at: new Date().toISOString(),
    }),
    executePlan: vi.fn().mockResolvedValue(undefined),
    rejectPlan: vi.fn().mockResolvedValue(undefined),
  },
}));

// Mock WebSocket
class MockWebSocket {
  onopen: ((event: Event) => void) | null = null;
  onmessage: ((event: MessageEvent) => void) | null = null;
  readyState = WebSocket.CONNECTING;

  constructor(public url: string) {
    setTimeout(() => {
      this.readyState = WebSocket.OPEN;
      this.onopen?.(new Event('open'));
    }, 0);
  }

  send(data: string) {}
  close() {}
  addEventListener() {}
}

global.WebSocket = MockWebSocket as any;

describe('Agent Workflow Integration', () => {
  it('should create session and show connected status', async () => {
    render(
      <BrowserRouter>
        <AgentDashboard />
      </BrowserRouter>
    );

    // Initial state - no session
    expect(screen.getByText(/create agent session/i)).toBeInTheDocument();

    // Create session
    const createButton = screen.getByText(/create session/i);
    fireEvent.click(createButton);

    // Wait for session to be created
    await waitFor(() => {
      expect(screen.getByText(/sess-test-123/i)).toBeInTheDocument();
    });

    // Check connected status
    await waitFor(() => {
      expect(screen.getByText(/connected/i)).toBeInTheDocument();
    });
  });
});
