import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { EventSearch } from '../EventSearch';

describe('EventSearch', () => {
  it('should render search input', () => {
    const onChange = vi.fn();
    render(<EventSearch value="" onChange={onChange} />);

    expect(screen.getByPlaceholderText(/search events/i)).toBeInTheDocument();
  });

  it('should call onChange when typing', () => {
    const onChange = vi.fn();
    render(<EventSearch value="" onChange={onChange} />);

    const input = screen.getByPlaceholderText(/search events/i);
    fireEvent.change(input, { target: { value: 'error' } });

    expect(onChange).toHaveBeenCalledWith('error');
  });

  it('should show clear button when has value', () => {
    const onChange = vi.fn();
    render(<EventSearch value="test" onChange={onChange} />);

    expect(screen.getByRole('button', { name: /clear/i })).toBeInTheDocument();
  });

  it('should clear search when clear button clicked', () => {
    const onChange = vi.fn();
    render(<EventSearch value="test" onChange={onChange} />);

    const clearButton = screen.getByRole('button', { name: /clear/i });
    fireEvent.click(clearButton);

    expect(onChange).toHaveBeenCalledWith('');
  });

  it('should not show clear button when empty', () => {
    const onChange = vi.fn();
    render(<EventSearch value="" onChange={onChange} />);

    expect(screen.queryByRole('button', { name: /clear/i })).not.toBeInTheDocument();
  });
});
