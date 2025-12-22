import { useState, useEffect } from 'react';
import { api } from './services/api';
import './styles/app.css';
import ChatWindow from './components/ChatWindow';
import ContextPanel from './components/ContextPanel';
import { ChatContext } from './types';

function App() {
  const [context, setContext] = useState<ChatContext | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    // Create session on mount
    const initSession = async () => {
      try {
        const session = await api.createSession();
        setContext({
          sessionId: session.session_id,
          regionId: session.region_id,
          characterId: session.character_id
        });
      } catch (err) {
        setError('Failed to initialize session');
        console.error(err);
      } finally {
        setLoading(false);
      }
    };

    initSession();
  }, []);

  if (loading) {
    return (
      <div className="app-loading">
        <div className="spinner"></div>
        <p>Initializing EVE Co-Pilot...</p>
      </div>
    );
  }

  if (error || !context) {
    return (
      <div className="app-error">
        <h2>Connection Error</h2>
        <p>{error || 'Failed to connect to copilot server'}</p>
        <button onClick={() => window.location.reload()}>Retry</button>
      </div>
    );
  }

  return (
    <div className="app">
      <header className="app-header">
        <h1>
          <span className="logo">⚡</span>
          EVE Co-Pilot AI
        </h1>
        <div className="header-actions">
          <span className="session-id">Session: {context.sessionId.slice(0, 8)}</span>
        </div>
      </header>

      <div className="app-main">
        <ContextPanel context={context} onContextChange={setContext} />
        <ChatWindow context={context} />
      </div>
    </div>
  );
}

export default App;
