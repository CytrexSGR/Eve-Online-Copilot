export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: string;
  isStreaming?: boolean;
}

export interface MessageHistoryProps {
  messages: ChatMessage[];
  autoScroll?: boolean;
  maxHeight?: string;
}
