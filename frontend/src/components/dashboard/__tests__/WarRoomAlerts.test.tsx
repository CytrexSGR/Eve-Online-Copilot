import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import WarRoomAlerts from '../WarRoomAlerts';
import * as api from '@/api';

// Mock the API module
vi.mock('@/api', () => ({
  getWarAlerts: vi.fn(),
}));

describe('WarRoomAlerts', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders alert items with icons', async () => {
    const mockAlerts = [
      {
        id: 1,
        message: 'High conflict in Jita',
        priority: 'high',
        timestamp: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString(), // 2 hours ago
      },
      {
        id: 2,
        message: 'Medium activity detected',
        priority: 'medium',
        timestamp: new Date(Date.now() - 5 * 60 * 60 * 1000).toISOString(), // 5 hours ago
      },
    ];

    vi.mocked(api.getWarAlerts).mockResolvedValue(mockAlerts);

    render(<WarRoomAlerts />);

    await waitFor(() => {
      expect(screen.getByText('High conflict in Jita')).toBeInTheDocument();
    });

    // Check for high priority icon (🔴)
    const alertItems = screen.getAllByTestId(/^alert-item-/);
    expect(alertItems[0]).toHaveTextContent('🔴');

    // Check for medium priority icon (🟡)
    expect(alertItems[1]).toHaveTextContent('🟡');
  });

  it('shows timestamps in relative format', async () => {
    const mockAlerts = [
      {
        id: 1,
        message: 'Recent alert',
        priority: 'high',
        timestamp: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString(), // 2 hours ago
      },
      {
        id: 2,
        message: 'Older alert',
        priority: 'medium',
        timestamp: new Date(Date.now() - 5 * 60 * 60 * 1000).toISOString(), // 5 hours ago
      },
    ];

    vi.mocked(api.getWarAlerts).mockResolvedValue(mockAlerts);

    render(<WarRoomAlerts />);

    await waitFor(() => {
      // Check for relative time format (e.g., "2h ago", "5h ago")
      expect(screen.getByText(/2h ago/i)).toBeInTheDocument();
      expect(screen.getByText(/5h ago/i)).toBeInTheDocument();
    });
  });

  it('limits to 5 alerts with "View All" link', async () => {
    const mockAlerts = Array.from({ length: 8 }, (_, i) => ({
      id: i + 1,
      message: `Alert ${i + 1}`,
      priority: 'high',
      timestamp: new Date(Date.now() - i * 60 * 60 * 1000).toISOString(),
    }));

    vi.mocked(api.getWarAlerts).mockResolvedValue(mockAlerts);

    render(<WarRoomAlerts />);

    await waitFor(() => {
      const alertItems = screen.getAllByTestId(/^alert-item-/);
      // Should only show 5 alerts
      expect(alertItems).toHaveLength(5);
    });

    // Should show "View All" link
    expect(screen.getByText(/View All/i)).toBeInTheDocument();
  });

  it('shows empty state when no alerts', async () => {
    vi.mocked(api.getWarAlerts).mockResolvedValue([]);

    render(<WarRoomAlerts />);

    await waitFor(() => {
      expect(screen.getByText(/No active threats/i)).toBeInTheDocument();
      expect(screen.getByText('🛡️')).toBeInTheDocument();
    });
  });

  it('adds scrollbar when >5 alerts', async () => {
    const mockAlerts = Array.from({ length: 7 }, (_, i) => ({
      id: i + 1,
      message: `Alert ${i + 1}`,
      priority: 'high',
      timestamp: new Date(Date.now() - i * 60 * 60 * 1000).toISOString(),
    }));

    vi.mocked(api.getWarAlerts).mockResolvedValue(mockAlerts);

    render(<WarRoomAlerts />);

    await waitFor(() => {
      const alertsContainer = screen.getByTestId('alerts-container');
      // Check if the container has overflow-y style
      const styles = window.getComputedStyle(alertsContainer);
      expect(styles.overflowY).toBe('auto');
    });
  });
});
