import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { ChatMessageInput } from '../ChatMessageInput';

describe('ChatMessageInput', () => {
  it('should render textarea and send button', () => {
    const onSend = vi.fn();
    render(<ChatMessageInput onSend={onSend} />);

    expect(screen.getByPlaceholderText(/type your message/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /send/i })).toBeInTheDocument();
  });

  it('should call onSend when send button clicked', () => {
    const onSend = vi.fn();
    render(<ChatMessageInput onSend={onSend} />);

    const textarea = screen.getByPlaceholderText(/type your message/i);
    const sendButton = screen.getByRole('button', { name: /send/i });

    fireEvent.change(textarea, { target: { value: 'Test message' } });
    fireEvent.click(sendButton);

    expect(onSend).toHaveBeenCalledWith('Test message');
  });

  it('should clear textarea after sending', () => {
    const onSend = vi.fn();
    render(<ChatMessageInput onSend={onSend} />);

    const textarea = screen.getByPlaceholderText(/type your message/i) as HTMLTextAreaElement;
    fireEvent.change(textarea, { target: { value: 'Test message' } });
    fireEvent.click(screen.getByRole('button', { name: /send/i }));

    expect(textarea.value).toBe('');
  });

  it('should disable send button when textarea is empty', () => {
    const onSend = vi.fn();
    render(<ChatMessageInput onSend={onSend} />);

    const sendButton = screen.getByRole('button', { name: /send/i });
    expect(sendButton).toBeDisabled();
  });

  it('should send message with Ctrl+Enter', () => {
    const onSend = vi.fn();
    render(<ChatMessageInput onSend={onSend} />);

    const textarea = screen.getByPlaceholderText(/type your message/i);
    fireEvent.change(textarea, { target: { value: 'Test message' } });
    fireEvent.keyDown(textarea, { key: 'Enter', ctrlKey: true });

    expect(onSend).toHaveBeenCalledWith('Test message');
  });
});
