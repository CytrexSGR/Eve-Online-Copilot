import { describe, it, expect, beforeEach, vi } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useSessionPersistence } from '../useSessionPersistence';

describe('useSessionPersistence', () => {
  beforeEach(() => {
    localStorage.clear();
    vi.clearAllMocks();
  });

  it('should initialize with null session', () => {
    const { result } = renderHook(() => useSessionPersistence());

    expect(result.current.sessionId).toBeNull();
  });

  it('should save session to localStorage', () => {
    const { result } = renderHook(() => useSessionPersistence());

    act(() => {
      result.current.saveSession('sess-123', 'RECOMMENDATIONS');
    });

    expect(result.current.sessionId).toBe('sess-123');
    expect(localStorage.getItem('agent_session_id')).toBe('sess-123');
    expect(localStorage.getItem('agent_autonomy_level')).toBe('RECOMMENDATIONS');
  });

  it('should restore session from localStorage on mount', () => {
    localStorage.setItem('agent_session_id', 'sess-456');
    localStorage.setItem('agent_autonomy_level', 'READ_ONLY');

    const { result } = renderHook(() => useSessionPersistence());

    expect(result.current.sessionId).toBe('sess-456');
    expect(result.current.autonomyLevel).toBe('READ_ONLY');
  });

  it('should clear session from localStorage', () => {
    localStorage.setItem('agent_session_id', 'sess-789');
    localStorage.setItem('agent_autonomy_level', 'ASSISTED');

    const { result } = renderHook(() => useSessionPersistence());

    act(() => {
      result.current.clearSession();
    });

    expect(result.current.sessionId).toBeNull();
    expect(result.current.autonomyLevel).toBeNull();
    expect(localStorage.getItem('agent_session_id')).toBeNull();
    expect(localStorage.getItem('agent_autonomy_level')).toBeNull();
  });

  it('should handle invalid localStorage data gracefully', () => {
    localStorage.setItem('agent_session_id', '');

    const { result } = renderHook(() => useSessionPersistence());

    expect(result.current.sessionId).toBeNull();
  });
});
