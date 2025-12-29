import { useState, useEffect, useRef, useCallback } from 'react';
import type { AgentEvent } from '../types/agent-events';

export interface UseAgentWebSocketOptions {
  sessionId: string;
  onEvent?: (event: AgentEvent) => void;
  onConnect?: () => void;
  onDisconnect?: () => void;
  onError?: (error: Event) => void;
  autoReconnect?: boolean;
  reconnectInterval?: number;
}

export interface UseAgentWebSocketReturn {
  events: AgentEvent[];
  isConnected: boolean;
  error: string | null;
  clearEvents: () => void;
  reconnect: () => void;
}

const WS_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:8000';

export function useAgentWebSocket({
  sessionId,
  onEvent,
  onConnect,
  onDisconnect,
  onError,
  autoReconnect = true,
  reconnectInterval = 3000,
}: UseAgentWebSocketOptions): UseAgentWebSocketReturn {
  const [events, setEvents] = useState<AgentEvent[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<number | null>(null);
  const mountedRef = useRef(true);
  const pingIntervalRef = useRef<number | null>(null);
  const reconnectAttemptsRef = useRef(0);
  const maxReconnectAttempts = 5; // Stop after 5 failed attempts

  const connect = useCallback(() => {
    if (!mountedRef.current) return;

    // Don't connect if session ID is empty
    if (!sessionId || sessionId.trim() === '') {
      console.log('[AgentWS] Skipping connection - no session ID');
      return;
    }

    try {
      const ws = new WebSocket(`${WS_URL}/agent/stream/${sessionId}`);
      wsRef.current = ws;

      ws.onopen = () => {
        if (!mountedRef.current) return;
        console.log(`[AgentWS] Connected to session ${sessionId}`);
        setIsConnected(true);
        setError(null);
        reconnectAttemptsRef.current = 0; // Reset counter on successful connection
        onConnect?.();

        // Clear any existing ping interval before creating new one
        if (pingIntervalRef.current) {
          clearInterval(pingIntervalRef.current);
        }

        // Send ping to keep connection alive
        pingIntervalRef.current = setInterval(() => {
          if (ws.readyState === WebSocket.OPEN) {
            ws.send('ping');
          }
        }, 30000); // Every 30 seconds
      };

      ws.onmessage = (event) => {
        if (!mountedRef.current) return;

        if (event.data === 'pong') {
          return; // Ignore pong responses
        }

        try {
          const agentEvent: AgentEvent = JSON.parse(event.data);
          setEvents((prev) => [...prev, agentEvent]);
          onEvent?.(agentEvent);
        } catch (err) {
          console.error('[AgentWS] Failed to parse event:', err);
          setError('Failed to parse event data');
        }
      };

      ws.onerror = (event) => {
        if (!mountedRef.current) return;
        console.error('[AgentWS] WebSocket error:', event);
        setError('WebSocket connection error');

        // Clear ping interval on error
        if (pingIntervalRef.current) {
          clearInterval(pingIntervalRef.current);
          pingIntervalRef.current = null;
        }

        onError?.(event);
      };

      ws.onclose = (event) => {
        if (!mountedRef.current) return;
        console.log(`[AgentWS] Disconnected: ${event.code} ${event.reason}`);
        setIsConnected(false);
        onDisconnect?.();

        // Clear ping interval
        if (pingIntervalRef.current) {
          clearInterval(pingIntervalRef.current);
          pingIntervalRef.current = null;
        }

        // Auto-reconnect if enabled and not a normal closure
        if (autoReconnect && event.code !== 1000) {
          reconnectAttemptsRef.current++;

          if (reconnectAttemptsRef.current <= maxReconnectAttempts) {
            console.log(`[AgentWS] Reconnecting in ${reconnectInterval}ms... (Attempt ${reconnectAttemptsRef.current}/${maxReconnectAttempts})`);
            reconnectTimeoutRef.current = setTimeout(() => {
              connect();
            }, reconnectInterval);
          } else {
            console.log(`[AgentWS] Max reconnect attempts (${maxReconnectAttempts}) reached. Stopping.`);
            setError('WebSocket connection failed after multiple attempts');
          }
        }
      };
    } catch (err) {
      console.error('[AgentWS] Failed to connect:', err);
      setError('Failed to establish WebSocket connection');

      // Attempt reconnect if enabled
      if (autoReconnect && mountedRef.current) {
        reconnectAttemptsRef.current++;

        if (reconnectAttemptsRef.current <= maxReconnectAttempts) {
          console.log(`[AgentWS] Reconnecting in ${reconnectInterval}ms... (Attempt ${reconnectAttemptsRef.current}/${maxReconnectAttempts})`);
          reconnectTimeoutRef.current = setTimeout(() => {
            connect();
          }, reconnectInterval);
        } else {
          console.log(`[AgentWS] Max reconnect attempts (${maxReconnectAttempts}) reached. Stopping.`);
          setError('WebSocket connection failed after multiple attempts');
        }
      }
    }
  }, [sessionId, onEvent, onConnect, onDisconnect, onError, autoReconnect, reconnectInterval]);

  useEffect(() => {
    mountedRef.current = true;
    reconnectAttemptsRef.current = 0; // Reset counter on session change
    connect();

    return () => {
      mountedRef.current = false;

      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }

      if (pingIntervalRef.current) {
        clearInterval(pingIntervalRef.current);
      }

      if (wsRef.current) {
        wsRef.current.close(1000, 'Component unmounted');
        wsRef.current = null;
      }
    };
  }, [connect]);

  const clearEvents = useCallback(() => {
    setEvents([]);
  }, []);

  const reconnect = useCallback(() => {
    if (wsRef.current) {
      wsRef.current.close(1000, 'Manual reconnect');
    }
    connect();
  }, [connect]);

  return {
    events,
    isConnected,
    error,
    clearEvents,
    reconnect,
  };
}
