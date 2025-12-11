import { useState, useEffect } from 'react';
import { getWarAlerts } from '@/api';
import './WarRoomAlerts.css';

interface WarAlert {
  id: number;
  message: string;
  priority: 'high' | 'medium';
  timestamp: string;
}

/**
 * WarRoomAlerts Component
 *
 * Displays recent war room alerts and high-priority events
 *
 * Features:
 * - Fetches alerts from /api/war/alerts endpoint
 * - Shows up to 5 alerts with priority icons (🔴 high, 🟡 medium)
 * - Displays timestamps in relative format (e.g., "2h ago")
 * - Shows "View All" link when more than 5 alerts exist
 * - Empty state: "No active threats" with shield icon 🛡️
 * - Red left border accent (2px solid #f85149)
 * - Scrollbar when content exceeds max height
 */
export default function WarRoomAlerts() {
  const [alerts, setAlerts] = useState<WarAlert[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchAlerts();
  }, []);

  const fetchAlerts = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await getWarAlerts(10); // Fetch 10 to check if we need "View All"
      setAlerts(data || []);
    } catch (err) {
      console.error('Error fetching war alerts:', err);
      setError('Error loading alerts');
    } finally {
      setLoading(false);
    }
  };

  /**
   * Format timestamp to relative time (e.g., "2h ago", "5h ago")
   */
  const formatRelativeTime = (timestamp: string): string => {
    const now = new Date();
    const then = new Date(timestamp);
    const diffMs = now.getTime() - then.getTime();
    const diffMinutes = Math.floor(diffMs / (1000 * 60));
    const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

    if (diffMinutes < 60) {
      return `${diffMinutes}m ago`;
    } else if (diffHours < 24) {
      return `${diffHours}h ago`;
    } else {
      return `${diffDays}d ago`;
    }
  };

  /**
   * Get icon for alert priority
   */
  const getPriorityIcon = (priority: 'high' | 'medium'): string => {
    return priority === 'high' ? '🔴' : '🟡';
  };

  if (loading) {
    return (
      <div className="war-room-alerts" data-testid="war-alerts-loading">
        <h3 className="war-alerts-header">War Room Alerts</h3>
        <div className="war-alerts-loading">Loading alerts...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="war-room-alerts" data-testid="war-alerts-error">
        <h3 className="war-alerts-header">War Room Alerts</h3>
        <div className="war-alerts-error">{error}</div>
      </div>
    );
  }

  // Show empty state if no alerts
  if (alerts.length === 0) {
    return (
      <div className="war-room-alerts">
        <h3 className="war-alerts-header">War Room Alerts</h3>
        <div className="war-alerts-empty" data-testid="alerts-empty">
          <div className="empty-icon">🛡️</div>
          <div className="empty-text">No active threats</div>
        </div>
      </div>
    );
  }

  // Limit display to 5 alerts
  const displayedAlerts = alerts.slice(0, 5);
  const hasMore = alerts.length > 5;

  return (
    <div className="war-room-alerts">
      <h3 className="war-alerts-header">War Room Alerts</h3>
      <div className="war-alerts-container" data-testid="alerts-container">
        {displayedAlerts.map((alert) => (
          <div
            key={alert.id}
            className="war-alert-item"
            data-testid={`alert-item-${alert.id}`}
          >
            <div className="alert-icon">{getPriorityIcon(alert.priority)}</div>
            <div className="alert-content">
              <div className="alert-message">{alert.message}</div>
              <div className="alert-timestamp">{formatRelativeTime(alert.timestamp)}</div>
            </div>
          </div>
        ))}
      </div>
      {hasMore && (
        <div className="war-alerts-footer">
          <a href="/war-room" className="view-all-link">
            View All →
          </a>
        </div>
      )}
    </div>
  );
}
