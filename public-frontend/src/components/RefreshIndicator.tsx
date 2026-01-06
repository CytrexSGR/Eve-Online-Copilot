import { useEffect, useState } from 'react';

interface RefreshIndicatorProps {
  lastUpdated: Date;
  autoRefreshSeconds?: number;
}

export function RefreshIndicator({
  lastUpdated,
  autoRefreshSeconds = 60
}: RefreshIndicatorProps) {
  const [timeAgo, setTimeAgo] = useState('');

  useEffect(() => {
    const updateTimeAgo = () => {
      const seconds = Math.floor((Date.now() - lastUpdated.getTime()) / 1000);

      if (seconds < 60) {
        setTimeAgo(`${seconds}s ago`);
      } else if (seconds < 3600) {
        setTimeAgo(`${Math.floor(seconds / 60)}m ago`);
      } else {
        setTimeAgo(`${Math.floor(seconds / 3600)}h ago`);
      }
    };

    updateTimeAgo();
    const interval = setInterval(updateTimeAgo, 1000);
    return () => clearInterval(interval);
  }, [lastUpdated]);

  return (
    <div style={{
      display: 'flex',
      alignItems: 'center',
      gap: '0.5rem',
      fontSize: '0.875rem',
      color: 'var(--text-secondary)'
    }}>
      <span>🔄</span>
      <span>Updated {timeAgo}</span>
      <span style={{ color: 'var(--text-tertiary)' }}>
        • Auto-refresh {autoRefreshSeconds}s
      </span>
    </div>
  );
}
