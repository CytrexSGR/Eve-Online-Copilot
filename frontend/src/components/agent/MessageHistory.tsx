import { useRef, useEffect } from 'react';
import type { MessageHistoryProps, ChatMessage } from '../../types/chat-messages';

export function MessageHistory({
  messages,
  autoScroll = true,
  maxHeight = '500px',
}: MessageHistoryProps) {
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (autoScroll && scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, autoScroll]);

  if (messages.length === 0) {
    return (
      <div className="flex items-center justify-center h-32 bg-gray-900 rounded border border-gray-700">
        <p className="text-gray-500">No messages yet. Start a conversation with the agent...</p>
      </div>
    );
  }

  return (
    <div
      ref={scrollRef}
      className="space-y-4 overflow-y-auto bg-gray-900 p-4 rounded"
      style={{ maxHeight }}
    >
      {messages.map((message) => (
        <MessageItem key={message.id} message={message} />
      ))}
    </div>
  );
}

function MessageItem({ message }: { message: ChatMessage }) {
  const isUser = message.role === 'user';
  const timestamp = new Date(message.timestamp).toLocaleTimeString();

  return (
    <article
      className={`flex gap-3 ${isUser ? 'justify-end' : 'justify-start'}`}
    >
      <div
        className={`max-w-[70%] rounded-lg p-3 ${
          isUser
            ? 'bg-blue-900 bg-opacity-50'
            : 'bg-gray-800'
        }`}
      >
        <div className="flex items-center gap-2 mb-1">
          <span className={`text-sm font-semibold ${
            isUser ? 'text-blue-400' : 'text-green-400'
          }`}>
            {isUser ? 'You' : 'Agent'}
          </span>
          <span className="text-xs text-gray-500">{timestamp}</span>
          {message.isStreaming && (
            <span className="text-xs text-yellow-400 animate-pulse">●</span>
          )}
        </div>
        <div className="text-gray-100 whitespace-pre-wrap break-words">
          {message.content}
        </div>
      </div>
    </article>
  );
}
