import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';

interface ShortcutConfig {
  key: string;
  ctrlKey?: boolean;
  altKey?: boolean;
  shiftKey?: boolean;
  action: () => void;
  description: string;
}

export function useKeyboardShortcuts(shortcuts: ShortcutConfig[]) {
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      for (const shortcut of shortcuts) {
        const ctrlMatch = shortcut.ctrlKey === undefined || shortcut.ctrlKey === e.ctrlKey;
        const altMatch = shortcut.altKey === undefined || shortcut.altKey === e.altKey;
        const shiftMatch = shortcut.shiftKey === undefined || shortcut.shiftKey === e.shiftKey;

        if (
          e.key.toLowerCase() === shortcut.key.toLowerCase() &&
          ctrlMatch &&
          altMatch &&
          shiftMatch
        ) {
          e.preventDefault();
          shortcut.action();
          break;
        }
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [shortcuts]);
}

// Global navigation shortcuts
export function useGlobalShortcuts() {
  const navigate = useNavigate();

  useKeyboardShortcuts([
    {
      key: 'h',
      altKey: true,
      action: () => navigate('/'),
      description: 'Alt+H - Go to Home/Dashboard',
    },
    {
      key: 'p',
      altKey: true,
      action: () => navigate('/production'),
      description: 'Alt+P - Go to Production Planner',
    },
    {
      key: 'm',
      altKey: true,
      action: () => navigate('/materials'),
      description: 'Alt+M - Go to Materials Overview',
    },
    {
      key: 's',
      altKey: true,
      action: () => navigate('/shopping-lists'),
      description: 'Alt+S - Go to Shopping Lists',
    },
    {
      key: 'w',
      altKey: true,
      action: () => navigate('/war-room'),
      description: 'Alt+W - Go to War Room',
    },
    {
      key: 'b',
      altKey: true,
      action: () => navigate('/bookmarks'),
      description: 'Alt+B - Go to Bookmarks',
    },
    {
      key: 'a',
      altKey: true,
      action: () => navigate('/arbitrage'),
      description: 'Alt+A - Go to Arbitrage Finder',
    },
  ]);
}

// Helper to display shortcuts
export const GLOBAL_SHORTCUTS = [
  { keys: 'Alt + H', description: 'Home/Dashboard' },
  { keys: 'Alt + P', description: 'Production Planner' },
  { keys: 'Alt + M', description: 'Materials Overview' },
  { keys: 'Alt + S', description: 'Shopping Lists' },
  { keys: 'Alt + W', description: 'War Room' },
  { keys: 'Alt + B', description: 'Bookmarks' },
  { keys: 'Alt + A', description: 'Arbitrage Finder' },
  { keys: '?', description: 'Show shortcuts (when implemented)' },
];
