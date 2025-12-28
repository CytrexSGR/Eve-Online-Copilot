import { useState, useCallback } from 'react';

export interface UseStreamingMessageReturn {
  content: string;
  isStreaming: boolean;
  appendChunk: (chunk: string) => void;
  complete: () => void;
  reset: () => void;
  setContent: (content: string) => void;
}

export function useStreamingMessage(): UseStreamingMessageReturn {
  const [content, setContentState] = useState('');
  const [isStreaming, setIsStreaming] = useState(false);

  const appendChunk = useCallback((chunk: string) => {
    setContentState((prev) => prev + chunk);
    setIsStreaming(true);
  }, []);

  const complete = useCallback(() => {
    setIsStreaming(false);
  }, []);

  const reset = useCallback(() => {
    setContentState('');
    setIsStreaming(false);
  }, []);

  const setContent = useCallback((newContent: string) => {
    setContentState(newContent);
    setIsStreaming(false);
  }, []);

  return {
    content,
    isStreaming,
    appendChunk,
    complete,
    reset,
    setContent,
  };
}
