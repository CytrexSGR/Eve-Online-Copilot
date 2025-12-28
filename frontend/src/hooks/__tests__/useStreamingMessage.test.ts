import { describe, it, expect, vi } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useStreamingMessage } from '../useStreamingMessage';

describe('useStreamingMessage', () => {
  it('should initialize with empty content', () => {
    const { result } = renderHook(() => useStreamingMessage());

    expect(result.current.content).toBe('');
    expect(result.current.isStreaming).toBe(false);
  });

  it('should append chunks to content', () => {
    const { result } = renderHook(() => useStreamingMessage());

    act(() => {
      result.current.appendChunk('Hello ');
    });

    expect(result.current.content).toBe('Hello ');
    expect(result.current.isStreaming).toBe(true);

    act(() => {
      result.current.appendChunk('world!');
    });

    expect(result.current.content).toBe('Hello world!');
  });

  it('should complete streaming', () => {
    const { result } = renderHook(() => useStreamingMessage());

    act(() => {
      result.current.appendChunk('Test');
      result.current.complete();
    });

    expect(result.current.content).toBe('Test');
    expect(result.current.isStreaming).toBe(false);
  });

  it('should reset content', () => {
    const { result } = renderHook(() => useStreamingMessage());

    act(() => {
      result.current.appendChunk('Test content');
      result.current.reset();
    });

    expect(result.current.content).toBe('');
    expect(result.current.isStreaming).toBe(false);
  });

  it('should set complete content at once', () => {
    const { result } = renderHook(() => useStreamingMessage());

    act(() => {
      result.current.setContent('Complete message');
    });

    expect(result.current.content).toBe('Complete message');
    expect(result.current.isStreaming).toBe(false);
  });
});
