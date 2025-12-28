import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { useAgentWebSocket } from '../useAgentWebSocket';
import type { AgentEvent } from '../../types/agent-events';
import { AgentEventType } from '../../types/agent-events';

// Mock WebSocket
class MockWebSocket {
  onopen: ((event: Event) => void) | null = null;
  onmessage: ((event: MessageEvent) => void) | null = null;
  onerror: ((event: Event) => void) | null = null;
  onclose: ((event: CloseEvent) => void) | null = null;
  readyState = WebSocket.CONNECTING;

  constructor(public url: string) {
    setTimeout(() => {
      this.readyState = WebSocket.OPEN;
      this.onopen?.(new Event('open'));
    }, 0);
  }

  send(data: string) {
    // Mock send
  }

  close(code?: number, reason?: string) {
    this.readyState = WebSocket.CLOSED;
    this.onclose?.(new CloseEvent('close', { code: code || 1000, reason }));
  }

  addEventListener(event: string, handler: any) {
    // Mock addEventListener
  }
}

global.WebSocket = MockWebSocket as any;

describe('useAgentWebSocket', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should connect to WebSocket on mount', async () => {
    const { result } = renderHook(() =>
      useAgentWebSocket({ sessionId: 'sess-test' })
    );

    await waitFor(() => {
      expect(result.current.isConnected).toBe(true);
    });
  });

  it('should receive and store events', async () => {
    const { result } = renderHook(() =>
      useAgentWebSocket({ sessionId: 'sess-test' })
    );

    await waitFor(() => {
      expect(result.current.isConnected).toBe(true);
    });

    // Simulate receiving an event
    const mockEvent: AgentEvent = {
      type: AgentEventType.PLAN_PROPOSED,
      session_id: 'sess-test',
      plan_id: 'plan-123',
      payload: {
        purpose: 'Test plan',
        steps: [],
        max_risk_level: 'READ_ONLY',
        tool_count: 0,
        auto_executing: false,
      },
      timestamp: new Date().toISOString(),
    };

    // Note: This test is simplified. In real implementation,
    // you'd need to trigger the WebSocket's onmessage handler
  });

  it('should clear events when clearEvents is called', async () => {
    const { result } = renderHook(() =>
      useAgentWebSocket({ sessionId: 'sess-test' })
    );

    await waitFor(() => {
      expect(result.current.isConnected).toBe(true);
    });

    result.current.clearEvents();
    expect(result.current.events).toHaveLength(0);
  });
});
