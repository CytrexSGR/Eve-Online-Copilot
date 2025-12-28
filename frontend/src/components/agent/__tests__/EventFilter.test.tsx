import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { EventFilter } from '../EventFilter';
import { AgentEventType } from '../../../types/agent-events';

describe('EventFilter', () => {
  it('should render filter dropdown', () => {
    const onChange = vi.fn();
    render(<EventFilter selectedTypes={[]} onChange={onChange} />);

    expect(screen.getByText(/filter events/i)).toBeInTheDocument();
  });

  it('should show all event types as options', () => {
    const onChange = vi.fn();
    render(<EventFilter selectedTypes={[]} onChange={onChange} />);

    const button = screen.getByText(/filter events/i);
    fireEvent.click(button);

    // Check for some event types (exact text match to avoid conflicts)
    expect(screen.getByText('Plan Proposed')).toBeInTheDocument();
    expect(screen.getByText('Tool Call Started')).toBeInTheDocument();
    expect(screen.getByText('Session Created')).toBeInTheDocument();
  });

  it('should toggle event type selection', () => {
    const onChange = vi.fn();
    render(<EventFilter selectedTypes={[]} onChange={onChange} />);

    fireEvent.click(screen.getByText(/filter events/i));
    fireEvent.click(screen.getByText(/plan proposed/i));

    expect(onChange).toHaveBeenCalledWith([AgentEventType.PLAN_PROPOSED]);
  });

  it('should show selected count in button', () => {
    const onChange = vi.fn();
    render(
      <EventFilter
        selectedTypes={[AgentEventType.PLAN_PROPOSED, AgentEventType.ERROR]}
        onChange={onChange}
      />
    );

    expect(screen.getByText(/2 selected/i)).toBeInTheDocument();
  });

  it('should clear all filters', () => {
    const onChange = vi.fn();
    render(
      <EventFilter
        selectedTypes={[AgentEventType.PLAN_PROPOSED]}
        onChange={onChange}
      />
    );

    fireEvent.click(screen.getByText(/filter events/i));
    fireEvent.click(screen.getByText(/clear all/i));

    expect(onChange).toHaveBeenCalledWith([]);
  });
});
