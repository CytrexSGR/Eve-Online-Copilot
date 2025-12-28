import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { PlanApprovalCard } from '../PlanApprovalCard';
import type { PlanProposedEventPayload } from '../../../types/agent-events';

describe('PlanApprovalCard', () => {
  const mockPayload: PlanProposedEventPayload = {
    purpose: 'Analyze market data',
    steps: [
      { tool: 'get_market_stats', arguments: { type_id: 34 } },
      { tool: 'calculate_profit', arguments: {} },
    ],
    max_risk_level: 'READ_ONLY',
    tool_count: 2,
    auto_executing: false,
  };

  it('should render plan details', () => {
    const onApprove = vi.fn();
    const onReject = vi.fn();

    render(
      <PlanApprovalCard
        planId="plan-123"
        payload={mockPayload}
        onApprove={onApprove}
        onReject={onReject}
      />
    );

    expect(screen.getByText(/analyze market data/i)).toBeInTheDocument();
    expect(screen.getByText(/tool count:/i)).toBeInTheDocument();
    expect(screen.getByText(/2/)).toBeInTheDocument();
  });

  it('should call onApprove when approve button clicked', async () => {
    const onApprove = vi.fn().mockResolvedValue(undefined);
    const onReject = vi.fn();

    render(
      <PlanApprovalCard
        planId="plan-123"
        payload={mockPayload}
        onApprove={onApprove}
        onReject={onReject}
      />
    );

    const approveButton = screen.getByText(/approve & execute/i);
    fireEvent.click(approveButton);

    await waitFor(() => {
      expect(onApprove).toHaveBeenCalledWith('plan-123');
    });
  });

  it('should show reject reason input when reject clicked', () => {
    const onApprove = vi.fn();
    const onReject = vi.fn();

    render(
      <PlanApprovalCard
        planId="plan-123"
        payload={mockPayload}
        onApprove={onApprove}
        onReject={onReject}
      />
    );

    const rejectButton = screen.getByText(/✗ reject/i);
    fireEvent.click(rejectButton);

    expect(screen.getByPlaceholderText(/provide a reason/i)).toBeInTheDocument();
  });

  it('should call onReject with reason when confirmed', async () => {
    const onApprove = vi.fn();
    const onReject = vi.fn().mockResolvedValue(undefined);

    render(
      <PlanApprovalCard
        planId="plan-123"
        payload={mockPayload}
        onApprove={onApprove}
        onReject={onReject}
      />
    );

    // Click reject to show textarea
    const rejectButton = screen.getByText(/✗ reject/i);
    fireEvent.click(rejectButton);

    // Enter rejection reason
    const textarea = screen.getByPlaceholderText(/provide a reason/i);
    fireEvent.change(textarea, { target: { value: 'Too risky' } });

    // Confirm rejection
    const confirmButton = screen.getByText(/confirm rejection/i);
    fireEvent.click(confirmButton);

    await waitFor(() => {
      expect(onReject).toHaveBeenCalledWith('plan-123', 'Too risky');
    });
  });

  it('should hide reject reason when cancel clicked', () => {
    const onApprove = vi.fn();
    const onReject = vi.fn();

    render(
      <PlanApprovalCard
        planId="plan-123"
        payload={mockPayload}
        onApprove={onApprove}
        onReject={onReject}
      />
    );

    // Click reject to show textarea
    const rejectButton = screen.getByText(/✗ reject/i);
    fireEvent.click(rejectButton);

    // Click cancel
    const cancelButton = screen.getByText(/cancel/i);
    fireEvent.click(cancelButton);

    // Textarea should be hidden
    expect(screen.queryByPlaceholderText(/provide a reason/i)).not.toBeInTheDocument();
  });

  it('should display risk level with correct color', () => {
    const onApprove = vi.fn();
    const onReject = vi.fn();

    render(
      <PlanApprovalCard
        planId="plan-123"
        payload={mockPayload}
        onApprove={onApprove}
        onReject={onReject}
      />
    );

    const riskLevel = screen.getByText(/READ_ONLY/);
    expect(riskLevel).toHaveClass('text-green-400');
  });

  it('should display all steps with tool names', () => {
    const onApprove = vi.fn();
    const onReject = vi.fn();

    render(
      <PlanApprovalCard
        planId="plan-123"
        payload={mockPayload}
        onApprove={onApprove}
        onReject={onReject}
      />
    );

    expect(screen.getByText('get_market_stats')).toBeInTheDocument();
    expect(screen.getByText('calculate_profit')).toBeInTheDocument();
  });

  it('should show loading state when approving', async () => {
    const onApprove = vi.fn(() => new Promise(() => {})); // Never resolves
    const onReject = vi.fn();

    render(
      <PlanApprovalCard
        planId="plan-123"
        payload={mockPayload}
        onApprove={onApprove}
        onReject={onReject}
      />
    );

    const approveButton = screen.getByText(/approve & execute/i);
    fireEvent.click(approveButton);

    await waitFor(() => {
      expect(screen.getByText(/approving.../i)).toBeInTheDocument();
    });
  });
});
