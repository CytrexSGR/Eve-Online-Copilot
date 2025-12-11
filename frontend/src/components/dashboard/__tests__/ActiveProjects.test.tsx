import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import ActiveProjects from '../ActiveProjects';

// Mock fetch globally
global.fetch = vi.fn();

// Mock project data
const mockProjects = [
  {
    id: 1,
    name: 'Raven Production Run',
    completed_items: 3,
    total_items: 10,
    created_at: '2025-12-10T10:00:00Z'
  },
  {
    id: 2,
    name: 'Ammunition Stockpile',
    completed_items: 7,
    total_items: 15,
    created_at: '2025-12-09T14:30:00Z'
  },
  {
    id: 3,
    name: 'Module Shopping',
    completed_items: 0,
    total_items: 5,
    created_at: '2025-12-11T08:15:00Z'
  }
];

describe('ActiveProjects', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders project items with progress bars', async () => {
    // Mock successful API response
    (global.fetch as any).mockResolvedValueOnce({
      ok: true,
      json: async () => mockProjects
    });

    render(<ActiveProjects />);

    // Wait for projects to load
    await waitFor(() => {
      expect(screen.getByText('Raven Production Run')).toBeInTheDocument();
    });

    // Verify all projects are rendered
    expect(screen.getByText('Raven Production Run')).toBeInTheDocument();
    expect(screen.getByText('Ammunition Stockpile')).toBeInTheDocument();
    expect(screen.getByText('Module Shopping')).toBeInTheDocument();

    // Verify progress bars exist
    const progressBars = screen.getAllByRole('progressbar', { hidden: true });
    expect(progressBars.length).toBe(3);
  });

  it('displays project status text', async () => {
    // Mock successful API response
    (global.fetch as any).mockResolvedValueOnce({
      ok: true,
      json: async () => mockProjects
    });

    render(<ActiveProjects />);

    // Wait for status text to appear
    await waitFor(() => {
      expect(screen.getByText('3/10 items')).toBeInTheDocument();
    });

    // Verify all status texts
    expect(screen.getByText('3/10 items')).toBeInTheDocument();
    expect(screen.getByText('7/15 items')).toBeInTheDocument();
    expect(screen.getByText('0/5 items')).toBeInTheDocument();
  });

  it('shows empty state when no projects', async () => {
    // Mock empty response
    (global.fetch as any).mockResolvedValueOnce({
      ok: true,
      json: async () => []
    });

    render(<ActiveProjects />);

    // Wait for empty state to appear
    await waitFor(() => {
      expect(screen.getByText('No active projects')).toBeInTheDocument();
    });

    // Verify empty state message and icon
    expect(screen.getByText('No active projects')).toBeInTheDocument();
    expect(screen.getByText(/➕/)).toBeInTheDocument();
  });

  it('calculates progress percentage correctly', async () => {
    // Mock successful API response
    (global.fetch as any).mockResolvedValueOnce({
      ok: true,
      json: async () => mockProjects
    });

    render(<ActiveProjects />);

    // Wait for projects to load
    await waitFor(() => {
      expect(screen.getByText('Raven Production Run')).toBeInTheDocument();
    });

    // Get progress bars
    const progressBars = screen.getAllByRole('progressbar', { hidden: true });

    // Project 1: 3/10 = 30%
    expect(progressBars[0]).toHaveStyle({ width: '30%' });

    // Project 2: 7/15 = 46.67% (rounded to 47%)
    const width2 = parseFloat(progressBars[1].style.width);
    expect(width2).toBeGreaterThan(46);
    expect(width2).toBeLessThan(48);

    // Project 3: 0/5 = 0%
    expect(progressBars[2]).toHaveStyle({ width: '0%' });
  });
});
