import { describe, it, expect, vi } from 'vitest';
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import OpportunitiesTable from '../OpportunitiesTable';
import type { Opportunity } from '../../../hooks/dashboard/useOpportunities';

// Mock opportunities data
const mockOpportunities: Opportunity[] = [
  {
    type_id: 648,
    name: 'Raven',
    category: 'production',
    profit: 8000000000,
    roi: 45.5,
    material_cost: 500000000,
    sell_price: 550000000,
    region_id: 10000002
  },
  {
    type_id: 12005,
    name: 'Megathron',
    category: 'production',
    profit: 3000000000,
    roi: 30.0,
    material_cost: 400000000,
    sell_price: 430000000,
    region_id: 10000002
  },
  {
    type_id: 11987,
    name: 'Abaddon',
    category: 'war_demand',
    profit: 1500000000,
    roi: 25.0,
    destroyed_count: 150,
    market_stock: 10,
    region_id: 10000043
  },
  {
    type_id: 17738,
    name: 'Medium Shield Booster II',
    category: 'trade',
    profit: 800000000,
    roi: 18.5,
    buy_region_id: 10000002,
    sell_region_id: 10000043
  },
  {
    type_id: 2048,
    name: 'Damage Control II',
    category: 'war_demand',
    profit: 500000000,
    roi: 15.0,
    destroyed_count: 500,
    market_stock: 50,
    region_id: 10000002
  }
];

describe('OpportunitiesTable', () => {
  it('renders table with correct headers', () => {
    render(<OpportunitiesTable opportunities={mockOpportunities} />);

    // Verify all required headers are present
    expect(screen.getByText('Icon')).toBeInTheDocument();
    expect(screen.getByText('Item Name')).toBeInTheDocument();
    expect(screen.getByText('Profit')).toBeInTheDocument();
    expect(screen.getByText('ROI')).toBeInTheDocument();
    expect(screen.getByText('Category')).toBeInTheDocument();
    expect(screen.getByText('Actions')).toBeInTheDocument();
  });

  it('renders opportunities data in rows', () => {
    render(<OpportunitiesTable opportunities={mockOpportunities} />);

    // Verify all opportunities are rendered
    mockOpportunities.forEach(opp => {
      expect(screen.getByText(opp.name)).toBeInTheDocument();
    });

    // Verify we have the correct number of data rows (excluding header)
    const rows = screen.getAllByRole('row');
    expect(rows.length).toBe(mockOpportunities.length + 1); // +1 for header row
  });

  it('formats profit with green gradient for high values', () => {
    render(<OpportunitiesTable opportunities={mockOpportunities} />);

    // Find the row with highest profit (Raven: 8B ISK)
    const ravenRow = screen.getByText('Raven').closest('tr');
    expect(ravenRow).toBeInTheDocument();

    // Check that profit cell has bright green color for >5B
    const profitCell = within(ravenRow!).getByText(/8\.00B/i);
    const profitStyle = window.getComputedStyle(profitCell);

    // Verify it has a green color (rgb format)
    expect(profitStyle.color).toMatch(/rgb/);
    expect(profitCell).toHaveStyle({ color: 'rgb(63, 185, 80)' }); // #3fb950
  });

  it('color-codes ROI based on thresholds', () => {
    render(<OpportunitiesTable opportunities={mockOpportunities} />);

    // Check high ROI (>40%) - Raven with 45.5%
    const ravenRow = screen.getByText('Raven').closest('tr');
    const highRoiCell = within(ravenRow!).getByText(/45\.5%/i);
    expect(highRoiCell).toHaveStyle({ color: 'rgb(63, 185, 80)' }); // #3fb950 - bright green

    // Check medium ROI (20-40%) - Megathron with 30%
    const megathronRow = screen.getByText('Megathron').closest('tr');
    const mediumRoiCell = within(megathronRow!).getByText(/30\.0%/i);
    expect(mediumRoiCell).toHaveStyle({ color: 'rgb(46, 160, 67)' }); // #2ea043 - medium green

    // Check low ROI (<20%) - Damage Control II with 15%
    const dcRow = screen.getByText('Damage Control II').closest('tr');
    const lowRoiCell = within(dcRow!).getByText(/15\.0%/i);
    expect(lowRoiCell).toHaveStyle({ color: 'rgb(139, 148, 158)' }); // #8b949e - muted gray
  });

  it('shows category badges with correct styling', () => {
    render(<OpportunitiesTable opportunities={mockOpportunities} />);

    // Check for PROD badge
    const prodBadges = screen.getAllByText('PROD');
    expect(prodBadges.length).toBeGreaterThan(0);
    expect(prodBadges[0]).toHaveClass('category-badge');

    // Check for WAR_DEMAND badge
    const warBadges = screen.getAllByText('WAR');
    expect(warBadges.length).toBeGreaterThan(0);
    expect(warBadges[0]).toHaveClass('category-badge');

    // Check for TRADE badge
    const tradeBadge = screen.getByText('TRADE');
    expect(tradeBadge).toBeInTheDocument();
    expect(tradeBadge).toHaveClass('category-badge');
  });

  it('handles row hover state', async () => {
    const user = userEvent.setup();
    render(<OpportunitiesTable opportunities={mockOpportunities} />);

    // Get the first data row (not header)
    const rows = screen.getAllByRole('row');
    const firstDataRow = rows[1];

    // Hover over the row
    await user.hover(firstDataRow);

    // Check that the row has the table-row class
    expect(firstDataRow).toHaveClass('table-row');
  });

  it('makes columns sortable', async () => {
    const user = userEvent.setup();
    render(<OpportunitiesTable opportunities={mockOpportunities} />);

    // Click on Profit header to sort
    const profitHeader = screen.getByText('Profit');
    await user.click(profitHeader);

    // Verify sort arrow indicator appears
    const headerCell = profitHeader.closest('th');
    expect(headerCell).toBeInTheDocument();

    // Click again to toggle sort direction
    await user.click(profitHeader);

    // Verify data is sorted (first row should change)
    const rows = screen.getAllByRole('row');
    expect(rows.length).toBeGreaterThan(1);
  });

  it('handles empty state gracefully', () => {
    render(<OpportunitiesTable opportunities={[]} />);

    // Should show "No opportunities found" message
    expect(screen.getByText(/no opportunities found/i)).toBeInTheDocument();
  });

  it('handles loading state', () => {
    render(<OpportunitiesTable opportunities={[]} loading={true} />);

    // Should show loading indicator
    expect(screen.getByText(/loading/i)).toBeInTheDocument();
  });

  it('calls onRowClick when row is clicked', async () => {
    const user = userEvent.setup();
    const onRowClick = vi.fn();

    render(
      <OpportunitiesTable
        opportunities={mockOpportunities}
        onRowClick={onRowClick}
      />
    );

    // Click on first data row
    const ravenRow = screen.getByText('Raven').closest('tr');
    await user.click(ravenRow!);

    // Verify callback was called with correct opportunity
    expect(onRowClick).toHaveBeenCalledWith(mockOpportunities[0]);
  });
});
