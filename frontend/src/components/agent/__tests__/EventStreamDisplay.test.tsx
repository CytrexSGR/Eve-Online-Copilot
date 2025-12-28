import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { EventStreamDisplay } from '../EventStreamDisplay';
import { AgentEventType } from '../../../types/agent-events';
import type { AgentEvent } from '../../../types/agent-events';

describe('EventStreamDisplay', () => {
  it('should show empty state when no events', () => {
    render(<EventStreamDisplay events={[]} />);
    expect(screen.getByText(/no events yet/i)).toBeInTheDocument();
  });

  it('should render events when provided', () => {
    const events: AgentEvent[] = [
      {
        type: AgentEventType.PLAN_PROPOSED,
        session_id: 'sess-test',
        plan_id: 'plan-123',
        payload: {
          purpose: 'Test plan',
          steps: [],
          max_risk_level: 'READ_ONLY',
          tool_count: 3,
          auto_executing: true,
        },
        timestamp: new Date().toISOString(),
      },
    ];

    render(<EventStreamDisplay events={events} />);
    expect(screen.getByText(/plan proposed/i)).toBeInTheDocument();
    expect(screen.getByText(/test plan/i)).toBeInTheDocument();
  });

  it('should render multiple events', () => {
    const events: AgentEvent[] = [
      {
        type: AgentEventType.PLAN_PROPOSED,
        session_id: 'sess-test',
        payload: {
          purpose: 'Test plan',
          steps: [],
          max_risk_level: 'READ_ONLY',
          tool_count: 2,
          auto_executing: false,
        },
        timestamp: new Date().toISOString(),
      },
      {
        type: AgentEventType.TOOL_CALL_STARTED,
        session_id: 'sess-test',
        payload: { tool: 'get_market_stats', step_index: 0, arguments: {} },
        timestamp: new Date().toISOString(),
      },
    ];

    render(<EventStreamDisplay events={events} />);
    expect(screen.getByText(/plan proposed/i)).toBeInTheDocument();
    expect(screen.getByText(/tool call started/i)).toBeInTheDocument();
  });

  it('should render event icons and colors', () => {
    const events: AgentEvent[] = [
      {
        type: AgentEventType.SESSION_CREATED,
        session_id: 'sess-test',
        payload: {},
        timestamp: new Date().toISOString(),
      },
    ];

    const { container } = render(<EventStreamDisplay events={events} />);

    // Check that event is rendered with proper structure
    expect(screen.getByText(/session created/i)).toBeInTheDocument();

    // Check for emoji icon in the document
    const eventItems = container.querySelectorAll('.text-2xl');
    expect(eventItems.length).toBeGreaterThan(0);
  });

  it('should handle tool call completed events', () => {
    const events: AgentEvent[] = [
      {
        type: AgentEventType.TOOL_CALL_COMPLETED,
        session_id: 'sess-test',
        payload: {
          step_index: 0,
          tool: 'get_market_stats',
          duration_ms: 150,
          result_preview: 'Success',
        },
        timestamp: new Date().toISOString(),
      },
    ];

    render(<EventStreamDisplay events={events} />);
    expect(screen.getByText(/tool call completed/i)).toBeInTheDocument();
    expect(screen.getByText(/get_market_stats/i)).toBeInTheDocument();
    expect(screen.getByText(/150ms/i)).toBeInTheDocument();
  });

  it('should handle tool call failed events with retry indicator', () => {
    const events: AgentEvent[] = [
      {
        type: AgentEventType.TOOL_CALL_FAILED,
        session_id: 'sess-test',
        payload: {
          step_index: 0,
          tool: 'get_market_stats',
          error: 'Connection timeout',
          retry_count: 2,
        },
        timestamp: new Date().toISOString(),
      },
    ];

    render(<EventStreamDisplay events={events} />);
    expect(screen.getByText(/tool call failed/i)).toBeInTheDocument();
    expect(screen.getByText(/connection timeout/i)).toBeInTheDocument();
    // With retry_count > 0, should show RetryIndicator with attempt count
    expect(screen.getByText(/attempt 3 of 4/i)).toBeInTheDocument();
    expect(screen.getByText(/retrying: get_market_stats/i)).toBeInTheDocument();
  });

  it('should handle tool call failed events without retry indicator', () => {
    const events: AgentEvent[] = [
      {
        type: AgentEventType.TOOL_CALL_FAILED,
        session_id: 'sess-test',
        payload: {
          step_index: 0,
          tool: 'calculate_profit',
          error: 'Invalid input',
          retry_count: 0,
        },
        timestamp: new Date().toISOString(),
      },
    ];

    render(<EventStreamDisplay events={events} />);
    expect(screen.getByText(/tool call failed/i)).toBeInTheDocument();
    expect(screen.getByText(/calculate_profit/i)).toBeInTheDocument();
    expect(screen.getByText(/invalid input/i)).toBeInTheDocument();
    // With retry_count === 0, should show simple error display
    expect(screen.getByText(/retries: 0/i)).toBeInTheDocument();
  });

  it('should handle authorization denied events', () => {
    const events: AgentEvent[] = [
      {
        type: AgentEventType.AUTHORIZATION_DENIED,
        session_id: 'sess-test',
        payload: {
          tool: 'delete_file',
          reason: 'Insufficient permissions',
        },
        timestamp: new Date().toISOString(),
      },
    ];

    render(<EventStreamDisplay events={events} />);
    expect(screen.getByText(/authorization denied/i)).toBeInTheDocument();
    expect(screen.getByText(/delete_file/i)).toBeInTheDocument();
    expect(screen.getByText(/insufficient permissions/i)).toBeInTheDocument();
  });

  it('should handle answer ready events', () => {
    const events: AgentEvent[] = [
      {
        type: AgentEventType.ANSWER_READY,
        session_id: 'sess-test',
        payload: {
          answer: 'Market analysis complete',
          tool_calls_count: 5,
          duration_ms: 2500,
        },
        timestamp: new Date().toISOString(),
      },
    ];

    render(<EventStreamDisplay events={events} />);
    expect(screen.getByText(/answer ready/i)).toBeInTheDocument();
    expect(screen.getByText(/market analysis complete/i)).toBeInTheDocument();
  });

  it('should apply custom maxHeight prop', () => {
    const events: AgentEvent[] = [
      {
        type: AgentEventType.SESSION_CREATED,
        session_id: 'sess-test',
        payload: {},
        timestamp: new Date().toISOString(),
      },
    ];

    const { container } = render(
      <EventStreamDisplay events={events} maxHeight="300px" />
    );

    const scrollContainer = container.querySelector('.overflow-y-auto');
    expect(scrollContainer).toHaveStyle({ maxHeight: '300px' });
  });

  it('should format event types correctly', () => {
    const events: AgentEvent[] = [
      {
        type: AgentEventType.WAITING_FOR_APPROVAL,
        session_id: 'sess-test',
        payload: {},
        timestamp: new Date().toISOString(),
      },
    ];

    render(<EventStreamDisplay events={events} />);
    // Event type should be formatted as "WAITING FOR APPROVAL"
    expect(screen.getByText(/waiting for approval/i)).toBeInTheDocument();
  });

  it('should display timestamps', () => {
    const now = new Date();
    const events: AgentEvent[] = [
      {
        type: AgentEventType.SESSION_CREATED,
        session_id: 'sess-test',
        payload: {},
        timestamp: now.toISOString(),
      },
    ];

    const { container } = render(<EventStreamDisplay events={events} />);

    // Check that timestamp is rendered (format will be locale-specific)
    const timestamps = container.querySelectorAll('.text-xs.text-gray-500');
    expect(timestamps.length).toBeGreaterThan(0);
  });
});
