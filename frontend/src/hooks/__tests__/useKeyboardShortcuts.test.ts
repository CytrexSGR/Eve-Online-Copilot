import { describe, it, expect, vi } from 'vitest';
import { renderHook } from '@testing-library/react';
import { useKeyboardShortcuts } from '../useKeyboardShortcuts';

describe('useKeyboardShortcuts', () => {
  it('should call handler when shortcut pressed', () => {
    const handler = vi.fn();
    const shortcuts = {
      'ctrl+k': handler,
    };

    renderHook(() => useKeyboardShortcuts(shortcuts));

    const event = new KeyboardEvent('keydown', { key: 'k', ctrlKey: true });
    document.dispatchEvent(event);

    expect(handler).toHaveBeenCalled();
  });

  it('should handle multiple shortcuts', () => {
    const handler1 = vi.fn();
    const handler2 = vi.fn();
    const shortcuts = {
      'ctrl+k': handler1,
      'ctrl+/': handler2,
    };

    renderHook(() => useKeyboardShortcuts(shortcuts));

    document.dispatchEvent(new KeyboardEvent('keydown', { key: 'k', ctrlKey: true }));
    document.dispatchEvent(new KeyboardEvent('keydown', { key: '/', ctrlKey: true }));

    expect(handler1).toHaveBeenCalledTimes(1);
    expect(handler2).toHaveBeenCalledTimes(1);
  });

  it('should support shift modifier', () => {
    const handler = vi.fn();
    const shortcuts = {
      'ctrl+shift+p': handler,
    };

    renderHook(() => useKeyboardShortcuts(shortcuts));

    document.dispatchEvent(new KeyboardEvent('keydown', { key: 'p', ctrlKey: true, shiftKey: true }));

    expect(handler).toHaveBeenCalled();
  });

  it('should not trigger when input is focused', () => {
    const handler = vi.fn();
    const shortcuts = {
      'ctrl+k': handler,
    };

    renderHook(() => useKeyboardShortcuts(shortcuts));

    const input = document.createElement('input');
    document.body.appendChild(input);
    input.focus();

    // Dispatch event on the input, which will bubble to document
    const event = new KeyboardEvent('keydown', { key: 'k', ctrlKey: true, bubbles: true });
    input.dispatchEvent(event);

    expect(handler).not.toHaveBeenCalled();

    document.body.removeChild(input);
  });

  it('should cleanup event listeners on unmount', () => {
    const handler = vi.fn();
    const shortcuts = {
      'ctrl+k': handler,
    };

    const { unmount } = renderHook(() => useKeyboardShortcuts(shortcuts));

    unmount();

    document.dispatchEvent(new KeyboardEvent('keydown', { key: 'k', ctrlKey: true }));

    expect(handler).not.toHaveBeenCalled();
  });
});
