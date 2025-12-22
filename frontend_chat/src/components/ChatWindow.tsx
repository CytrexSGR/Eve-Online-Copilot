import { useState, useEffect, useRef } from 'react';
import { ChatContext, Message } from '../types';
import { useWebSocket } from '../hooks/useWebSocket';
import MessageList from './MessageList';
import ChatInput from './ChatInput';
import '../styles/chat.css';

interface ChatWindowProps {
  context: ChatContext;
}

function ChatWindow({ context }: ChatWindowProps) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isTyping, setIsTyping] = useState(false);
  const { connected, messages: wsMessages, sendMessage } = useWebSocket(context.sessionId);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    // Process WebSocket messages
    wsMessages.forEach(wsMsg => {
      if (wsMsg.type === 'message' && wsMsg.message) {
        setMessages(prev => [...prev, {
          id: Date.now().toString(),
          role: 'assistant',
          content: wsMsg.message!,
          tool_calls: wsMsg.tool_calls,
          timestamp: new Date()
        }]);
        setIsTyping(false);
      } else if (wsMsg.type === 'typing') {
        setIsTyping(wsMsg.is_typing || false);
      } else if (wsMsg.type === 'error') {
        setMessages(prev => [...prev, {
          id: Date.now().toString(),
          role: 'assistant',
          content: `Error: ${wsMsg.error}`,
          timestamp: new Date()
        }]);
        setIsTyping(false);
      }
    });
  }, [wsMessages]);

  useEffect(() => {
    // Auto-scroll to bottom
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isTyping]);

  const handleSendMessage = (message: string) => {
    // Add user message
    setMessages(prev => [...prev, {
      id: Date.now().toString(),
      role: 'user',
      content: message,
      timestamp: new Date()
    }]);

    // Send via WebSocket
    sendMessage(message);
    setIsTyping(true);
  };

  return (
    <div className="chat-window">
      <div className="chat-header">
        <div className="connection-status">
          <span className={`status-dot ${connected ? 'connected' : 'disconnected'}`}></span>
          {connected ? 'Connected' : 'Disconnected'}
        </div>
      </div>

      <MessageList messages={messages} isTyping={isTyping} />
      <div ref={messagesEndRef} />

      <ChatInput onSendMessage={handleSendMessage} disabled={!connected} />
    </div>
  );
}

export default ChatWindow;
