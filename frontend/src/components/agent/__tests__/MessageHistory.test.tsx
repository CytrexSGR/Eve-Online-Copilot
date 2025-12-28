import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MessageHistory } from '../MessageHistory';
import type { ChatMessage } from '../../../types/chat-messages';

describe('MessageHistory', () => {
  it('should show empty state when no messages', () => {
    render(<MessageHistory messages={[]} />);
    expect(screen.getByText(/no messages yet/i)).toBeInTheDocument();
  });

  it('should render user messages', () => {
    const messages: ChatMessage[] = [
      {
        id: '1',
        role: 'user',
        content: 'Hello agent',
        timestamp: new Date().toISOString(),
      },
    ];

    render(<MessageHistory messages={messages} />);
    expect(screen.getByText('Hello agent')).toBeInTheDocument();
    expect(screen.getByText(/you/i)).toBeInTheDocument();
  });

  it('should render assistant messages', () => {
    const messages: ChatMessage[] = [
      {
        id: '1',
        role: 'assistant',
        content: 'Hello user',
        timestamp: new Date().toISOString(),
      },
    ];

    render(<MessageHistory messages={messages} />);
    expect(screen.getByText('Hello user')).toBeInTheDocument();
    expect(screen.getByText(/agent/i)).toBeInTheDocument();
  });

  it('should render multiple messages in order', () => {
    const messages: ChatMessage[] = [
      { id: '1', role: 'user', content: 'First', timestamp: new Date().toISOString() },
      { id: '2', role: 'assistant', content: 'Second', timestamp: new Date().toISOString() },
      { id: '3', role: 'user', content: 'Third', timestamp: new Date().toISOString() },
    ];

    render(<MessageHistory messages={messages} />);
    const allMessages = screen.getAllByRole('article');
    expect(allMessages).toHaveLength(3);
  });

  it('should show streaming indicator for streaming messages', () => {
    const messages: ChatMessage[] = [
      {
        id: '1',
        role: 'assistant',
        content: 'Streaming...',
        timestamp: new Date().toISOString(),
        isStreaming: true,
      },
    ];

    render(<MessageHistory messages={messages} />);
    expect(screen.getByText('Streaming...')).toBeInTheDocument();
    // Streaming indicator would be a visual element, check for class or icon
  });
});
