/**
 * WebSocket Hook
 * React hook for WebSocket connection
 */

import { useEffect, useRef, useState } from 'react';
import { WebSocketClient, WebSocketMessage } from '../services/websocket';

const WS_BASE_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:8001';

export function useWebSocket(sessionId: string) {
  const [connected, setConnected] = useState(false);
  const [messages, setMessages] = useState<WebSocketMessage[]>([]);
  const wsRef = useRef<WebSocketClient | null>(null);

  useEffect(() => {
    // Create WebSocket client
    const ws = new WebSocketClient(WS_BASE_URL, sessionId);
    wsRef.current = ws;

    // Set up message handler
    const unsubscribeMessages = ws.onMessage((message) => {
      setMessages(prev => [...prev, message]);
    });

    // Set up connection handler
    const unsubscribeConnection = ws.onConnectionChange((isConnected) => {
      setConnected(isConnected);
    });

    // Connect
    ws.connect();

    // Cleanup
    return () => {
      unsubscribeMessages();
      unsubscribeConnection();
      ws.disconnect();
    };
  }, [sessionId]);

  const sendMessage = (message: string) => {
    wsRef.current?.sendMessage(message);
  };

  const setCharacter = (characterId: number) => {
    wsRef.current?.setCharacter(characterId);
  };

  const setRegion = (regionId: number) => {
    wsRef.current?.setRegion(regionId);
  };

  return {
    connected,
    messages,
    sendMessage,
    setCharacter,
    setRegion
  };
}
