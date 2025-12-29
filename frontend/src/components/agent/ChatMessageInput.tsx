import { useState, type KeyboardEvent } from 'react';

interface ChatMessageInputProps {
  onSend: (message: string) => void;
  disabled?: boolean;
  placeholder?: string;
}

export function ChatMessageInput({
  onSend,
  disabled = false,
  placeholder = 'Type your message... (Ctrl+Enter to send)',
}: ChatMessageInputProps) {
  const [message, setMessage] = useState('');

  const handleSend = () => {
    if (message.trim()) {
      onSend(message.trim());
      setMessage('');
    }
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && e.ctrlKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', padding: '1rem', backgroundColor: 'var(--bg-darker)', borderTop: '1px solid var(--border)' }}>
      <textarea
        value={message}
        onChange={(e) => setMessage(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder={placeholder}
        disabled={disabled}
        style={{
          width: '100%',
          minHeight: '120px',
          padding: '0.75rem',
          backgroundColor: 'var(--bg-dark)',
          color: 'var(--text-primary)',
          border: '1px solid var(--border)',
          borderRadius: '6px',
          resize: 'vertical',
          fontFamily: 'inherit',
          fontSize: '14px',
          lineHeight: '1.5'
        }}
        className="focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
      />
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <span style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
          Ctrl+Enter to send
        </span>
        <button
          onClick={handleSend}
          disabled={disabled || !message.trim()}
          style={{
            padding: '0.75rem 2rem',
            backgroundColor: disabled || !message.trim() ? 'var(--bg-dark)' : '#3b82f6',
            color: 'white',
            fontWeight: '600',
            borderRadius: '6px',
            border: 'none',
            cursor: disabled || !message.trim() ? 'not-allowed' : 'pointer',
            transition: 'background-color 0.2s'
          }}
          onMouseEnter={(e) => {
            if (!disabled && message.trim()) {
              e.currentTarget.style.backgroundColor = '#2563eb';
            }
          }}
          onMouseLeave={(e) => {
            if (!disabled && message.trim()) {
              e.currentTarget.style.backgroundColor = '#3b82f6';
            }
          }}
        >
          Send Message
        </button>
      </div>
    </div>
  );
}
