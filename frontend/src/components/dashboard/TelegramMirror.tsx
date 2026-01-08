import { useState, useEffect } from 'react';
import { getRecentTelegramAlerts } from '@/api';
import './TelegramMirror.css';

interface TelegramAlert {
  battle_id: number;
  system_name: string;
  region_name: string;
  security: number;
  alert_type: 'milestone' | 'new_battle' | 'ended' | 'unknown';
  milestone: number;
  total_kills: number;
  total_isk_destroyed: number;
  telegram_message_id: number;
  sent_at: string;
  status: 'active' | 'ended';
}

/**
 * TelegramMirror Component
 *
 * Displays recent Telegram alerts sent for battles
 *
 * Features:
 * - Shows last 5 Telegram notifications
 * - Different icons for alert types (🎯 milestone, ⚠️ new battle, ✅ ended)
 * - Displays system, kills, ISK, and time sent
 * - Links to Telegram channel
 * - Auto-refreshes every 60 seconds
 */
export default function TelegramMirror() {
  const [alerts, setAlerts] = useState<TelegramAlert[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchAlerts();
    const interval = setInterval(fetchAlerts, 60000); // Refresh every 60s
    return () => clearInterval(interval);
  }, []);

  const fetchAlerts = async () => {
    try:
      setError(null);
      const data = await getRecentTelegramAlerts(5);
      setAlerts(data.alerts || []);
      setLoading(false);
    } catch (err) {
      console.error('Error fetching telegram alerts:', err);
      setError('Error loading alerts');
      setLoading(false);
    }
  };

  /**
   * Get icon for alert type
   */
  const getAlertIcon = (alertType: string): string => {
    switch (alertType) {
      case 'milestone': return '🎯';
      case 'new_battle': return '⚠️';
      case 'ended': return '✅';
      default: return '📢';
    }
  };

  /**
   * Get alert title based on type
   */
  const getAlertTitle = (alert: TelegramAlert): string => {
    switch (alert.alert_type) {
      case 'milestone':
        return `MILESTONE: ${alert.milestone} kills`;
      case 'new_battle':
        return 'NEW BATTLE';
      case 'ended':
        return 'BATTLE ENDED';
      default:
        return 'BATTLE UPDATE';
    }
  };

  /**
   * Format ISK value to B (billions) or M (millions)
   */
  const formatISK = (isk: number): string => {
    if (isk >= 1_000_000_000) {
      return `${(isk / 1_000_000_000).toFixed(1)}B`;
    } else if (isk >= 1_000_000) {
      return `${(isk / 1_000_000).toFixed(0)}M`;
    }
    return `${isk.toLocaleString()}`;
  };

  /**
   * Format relative time (e.g., "2h ago")
   */
  const formatRelativeTime = (timestamp: string): string => {
    const now = new Date();
    const then = new Date(timestamp);
    const diffMs = now.getTime() - then.getTime();
    const diffMinutes = Math.floor(diffMs / (1000 * 60));
    const diffHours = Math.floor(diffMs / (1000 * 60 * 60));

    if (diffMinutes < 60) {
      return `${diffMinutes}m ago`;
    } else if (diffHours < 24) {
      return `${diffHours}h ago`;
    } else {
      const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));
      return `${diffDays}d ago`;
    }
  };

  if (loading) {
    return (
      <div className="telegram-mirror" data-testid="telegram-loading">
        <h3 className="telegram-header">📱 Telegram Alerts</h3>
        <div className="telegram-loading">Loading alerts...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="telegram-mirror" data-testid="telegram-error">
        <h3 className="telegram-header">📱 Telegram Alerts</h3>
        <div className="telegram-error">{error}</div>
      </div>
    );
  }

  if (alerts.length === 0) {
    return (
      <div className="telegram-mirror">
        <h3 className="telegram-header">📱 Telegram Alerts</h3>
        <div className="telegram-empty" data-testid="telegram-empty">
          <div className="empty-icon">📭</div>
          <div className="empty-text">No recent alerts</div>
        </div>
      </div>
    );
  }

  return (
    <div className="telegram-mirror">
      <div className="telegram-header-row">
        <h3 className="telegram-header">📱 Telegram Alerts</h3>
        <a
          href="https://t.me/infinimind_eve"
          target="_blank"
          rel="noopener noreferrer"
          className="telegram-link"
          title="Open Telegram Channel"
        >
          📢
        </a>
      </div>
      <div className="telegram-container" data-testid="telegram-container">
        {alerts.map((alert) => (
          <div
            key={`${alert.battle_id}-${alert.telegram_message_id}`}
            className="telegram-alert"
            data-testid={`alert-${alert.telegram_message_id}`}
          >
            <div className="alert-header">
              <div className="alert-icon">{getAlertIcon(alert.alert_type)}</div>
              <div className="alert-title">{getAlertTitle(alert)}</div>
            </div>
            <div className="alert-body">
              <div className="alert-location">
                {alert.system_name} - {alert.region_name}
              </div>
              <div className="alert-stats">
                {alert.total_kills.toLocaleString()} kills • {formatISK(alert.total_isk_destroyed)} ISK
              </div>
              <div className="alert-footer">
                <span className="alert-sent">📤 Sent {formatRelativeTime(alert.sent_at)}</span>
                <span className="alert-message-id">(#{alert.telegram_message_id})</span>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
