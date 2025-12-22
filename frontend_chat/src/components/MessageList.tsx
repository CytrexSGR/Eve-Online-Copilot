import { Message as MessageType } from '../types';
import Message from './Message';
import '../styles/message.css';

interface MessageListProps {
  messages: MessageType[];
  isTyping: boolean;
}

function MessageList({ messages, isTyping }: MessageListProps) {
  if (messages.length === 0) {
    return (
      <div className="message-list empty">
        <div className="welcome-message">
          <h2>Welcome to EVE Co-Pilot AI</h2>
          <p>Your intelligent assistant for EVE Online</p>
          <div className="suggestions">
            <button>📊 Show market opportunities</button>
            <button>⚙️ Calculate production costs</button>
            <button>⚔️ Check war room intel</button>
            <button>🛒 Create shopping list</button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="message-list">
      {messages.map(message => (
        <Message key={message.id} message={message} />
      ))}
      {isTyping && (
        <div className="typing-indicator">
          <span></span>
          <span></span>
          <span></span>
        </div>
      )}
    </div>
  );
}

export default MessageList;
