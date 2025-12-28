import { describe, it, expect } from 'vitest';
import {
  AgentEventType,
  isPlanProposedEvent,
  isToolCallStartedEvent,
  type AgentEvent,
} from '../agent-events';

describe('AgentEventType', () => {
  it('should have all 19 event types', () => {
    const types = Object.values(AgentEventType);
    expect(types).toHaveLength(19);
    expect(types).toContain('plan_proposed');
    expect(types).toContain('tool_call_started');
    expect(types).toContain('answer_ready');
  });
});

describe('Type guards', () => {
  it('isPlanProposedEvent should identify plan_proposed events', () => {
    const event: AgentEvent = {
      type: AgentEventType.PLAN_PROPOSED,
      session_id: 'sess-123',
      plan_id: 'plan-456',
      payload: {
        purpose: 'Test',
        steps: [],
        max_risk_level: 'READ_ONLY',
        tool_count: 0,
        auto_executing: false,
      },
      timestamp: new Date().toISOString(),
    };

    expect(isPlanProposedEvent(event)).toBe(true);

    if (isPlanProposedEvent(event)) {
      expect(event.payload.purpose).toBe('Test');
    }
  });

  it('isPlanProposedEvent should reject non-plan events', () => {
    const event: AgentEvent = {
      type: AgentEventType.TOOL_CALL_STARTED,
      session_id: 'sess-123',
      payload: {},
      timestamp: new Date().toISOString(),
    };

    expect(isPlanProposedEvent(event)).toBe(false);
  });
});
