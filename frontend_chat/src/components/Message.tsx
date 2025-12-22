import { Message as MessageType } from '../types';
import ReactMarkdown from 'react-markdown';

interface MessageProps {
  message: MessageType;
}

function Message({ message }: MessageProps) {
  return (
    <div className={`message ${message.role}`}>
      <div className="message-avatar">
        {message.role === 'user' ? '👤' : '🤖'}
      </div>
      <div className="message-content">
        <ReactMarkdown>{message.content}</ReactMarkdown>

        {message.tool_calls && message.tool_calls.length > 0 && (
          <div className="tool-calls">
            <details>
              <summary>🔧 Used {message.tool_calls.length} tool(s)</summary>
              <ul>
                {message.tool_calls.map((tool, idx) => (
                  <li key={idx}>
                    <strong>{tool.tool}</strong>
                    <code>{JSON.stringify(tool.input, null, 2)}</code>
                  </li>
                ))}
              </ul>
            </details>
          </div>
        )}

        <div className="message-timestamp">
          {message.timestamp.toLocaleTimeString()}
        </div>
      </div>
    </div>
  );
}

export default Message;
