import { useState, useEffect } from 'react';

const SESSION_ID_KEY = 'agent_session_id';
const AUTONOMY_LEVEL_KEY = 'agent_autonomy_level';

export interface UseSessionPersistenceReturn {
  sessionId: string | null;
  autonomyLevel: string | null;
  saveSession: (sessionId: string, autonomyLevel: string) => void;
  clearSession: () => void;
}

export function useSessionPersistence(): UseSessionPersistenceReturn {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [autonomyLevel, setAutonomyLevel] = useState<string | null>(null);

  // Restore from localStorage on mount
  useEffect(() => {
    try {
      const savedSessionId = localStorage.getItem(SESSION_ID_KEY);
      const savedAutonomyLevel = localStorage.getItem(AUTONOMY_LEVEL_KEY);

      if (savedSessionId && savedSessionId.trim()) {
        setSessionId(savedSessionId);
      }

      if (savedAutonomyLevel && savedAutonomyLevel.trim()) {
        setAutonomyLevel(savedAutonomyLevel);
      }
    } catch (error) {
      console.error('Failed to restore session from localStorage:', error);
    }
  }, []);

  const saveSession = (newSessionId: string, newAutonomyLevel: string) => {
    try {
      localStorage.setItem(SESSION_ID_KEY, newSessionId);
      localStorage.setItem(AUTONOMY_LEVEL_KEY, newAutonomyLevel);
      setSessionId(newSessionId);
      setAutonomyLevel(newAutonomyLevel);
    } catch (error) {
      console.error('Failed to save session to localStorage:', error);
    }
  };

  const clearSession = () => {
    try {
      localStorage.removeItem(SESSION_ID_KEY);
      localStorage.removeItem(AUTONOMY_LEVEL_KEY);
      setSessionId(null);
      setAutonomyLevel(null);
    } catch (error) {
      console.error('Failed to clear session from localStorage:', error);
    }
  };

  return {
    sessionId,
    autonomyLevel,
    saveSession,
    clearSession,
  };
}
