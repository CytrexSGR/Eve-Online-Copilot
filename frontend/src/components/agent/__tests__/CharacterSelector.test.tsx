import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { CharacterSelector } from '../CharacterSelector';

describe('CharacterSelector', () => {
  const mockCharacters = [
    { id: 526379435, name: 'Artallus' },
    { id: 1117367444, name: 'Cytrex' },
    { id: 110592475, name: 'Cytricia' },
  ];

  it('should render character dropdown', () => {
    const onChange = vi.fn();
    render(
      <CharacterSelector
        characters={mockCharacters}
        selectedId={null}
        onChange={onChange}
      />
    );

    expect(screen.getByRole('combobox')).toBeInTheDocument();
  });

  it('should show selected character', () => {
    const onChange = vi.fn();
    render(
      <CharacterSelector
        characters={mockCharacters}
        selectedId={526379435}
        onChange={onChange}
      />
    );

    const select = screen.getByRole('combobox') as HTMLSelectElement;
    expect(select.value).toBe('526379435');
  });

  it('should call onChange when character selected', () => {
    const onChange = vi.fn();
    render(
      <CharacterSelector
        characters={mockCharacters}
        selectedId={null}
        onChange={onChange}
      />
    );

    const select = screen.getByRole('combobox');
    fireEvent.change(select, { target: { value: '1117367444' } });

    expect(onChange).toHaveBeenCalledWith(1117367444);
  });

  it('should show placeholder when no character selected', () => {
    const onChange = vi.fn();
    render(
      <CharacterSelector
        characters={mockCharacters}
        selectedId={null}
        onChange={onChange}
      />
    );

    expect(screen.getByText(/select a character/i)).toBeInTheDocument();
  });

  it('should disable selector when disabled prop is true', () => {
    const onChange = vi.fn();
    render(
      <CharacterSelector
        characters={mockCharacters}
        selectedId={null}
        onChange={onChange}
        disabled={true}
      />
    );

    expect(screen.getByRole('combobox')).toBeDisabled();
  });
});
