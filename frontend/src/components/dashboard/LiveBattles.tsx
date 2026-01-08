import { useState, useEffect } from 'react';
import { getActiveBattles } from '@/api';
import './LiveBattles.css';

interface Battle {
  battle_id: number;
  system_id: number;
  system_name: string;
  region_name: string;
  security: number;
  total_kills: number;
  total_isk_destroyed: number;
  last_milestone: number;
  started_at: string;
  last_kill_at: string;
  duration_minutes: number;
  telegram_sent: boolean;
  intensity: 'extreme' | 'high' | 'moderate' | 'low';
}

/**
 * LiveBattles Component
 *
 * Displays currently active battles in real-time
 *
 * Features:
 * - Shows top 5 active battles by kill count
 * - Color-coded intensity indicators (🔴 extreme, 🟠 high, 🟡 moderate)
 * - Displays kill count, ISK destroyed, and milestone reached
 * - Shows time since battle started
 * - Clickable to navigate to Battle Map
 * - Auto-refreshes every 30 seconds
 */
export default function LiveBattles() {
  const [battles, setBattles] = useState<Battle[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [totalActive, setTotalActive] = useState<number>(0);

  useEffect(() => {
    fetchBattles();
    const interval = setInterval(fetchBattles, 30000); // Refresh every 30s
    return () => clearInterval(interval);
  }, []);

  const fetchBattles = async () => {
    try {
      setError(null);
      const data = await getActiveBattles(5);
      setBattles(data.battles || []);
      setTotalActive(data.total_active || 0);
      setLoading(false);
    } catch (err) {
      console.error('Error fetching live battles:', err);
      setError('Error loading battles');
      setLoading(false);
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
   * Format duration to human-readable time
   */
  const formatDuration = (minutes: number): string => {
    const hours = Math.floor(minutes / 60);
    const mins = minutes % 60;
    if (hours > 0) {
      return `${hours}h ${mins}m`;
    }
    return `${mins}m`;
  };

  /**
   * Get intensity icon based on battle intensity
   */
  const getIntensityIcon = (intensity: string): string => {
    switch (intensity) {
      case 'extreme': return '🔴';
      case 'high': return '🟠';
      case 'moderate': return '🟡';
      default: return '⚪';
    }
  };

  /**
   * Navigate to Battle Map with system focused
   */
  const handleBattleClick = (systemId: number) => {
    window.location.href = `/battle-map?system=${systemId}`;
  };

  if (loading) {
    return (
      <div className="live-battles" data-testid="live-battles-loading">
        <h3 className="live-battles-header">⚔️ Live Battles</h3>
        <div className="live-battles-loading">Loading battles...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="live-battles" data-testid="live-battles-error">
        <h3 className="live-battles-header">⚔️ Live Battles</h3>
        <div className="live-battles-error">{error}</div>
      </div>
    );
  }

  if (battles.length === 0) {
    return (
      <div className="live-battles">
        <h3 className="live-battles-header">⚔️ Live Battles</h3>
        <div className="live-battles-empty" data-testid="battles-empty">
          <div className="empty-icon">🕊️</div>
          <div className="empty-text">No active battles</div>
        </div>
      </div>
    );
  }

  return (
    <div className="live-battles">
      <div className="live-battles-header-row">
        <h3 className="live-battles-header">⚔️ Live Battles</h3>
        <span className="battles-count">({totalActive})</span>
      </div>
      <div className="live-battles-container" data-testid="battles-container">
        {battles.map((battle) => (
          <div
            key={battle.battle_id}
            className="battle-item"
            data-testid={`battle-item-${battle.battle_id}`}
            onClick={() => handleBattleClick(battle.system_id)}
          >
            <div className="battle-header">
              <div className="battle-intensity">{getIntensityIcon(battle.intensity)}</div>
              <div className="battle-location">
                <div className="system-name">{battle.system_name}</div>
                <div className="region-name">{battle.region_name}</div>
              </div>
            </div>
            <div className="battle-stats">
              <div className="stat-line">
                <span className="stat-value">{battle.total_kills.toLocaleString()}</span>
                <span className="stat-label">kills</span>
                <span className="stat-separator">•</span>
                <span className="stat-value">{formatISK(battle.total_isk_destroyed)}</span>
                <span className="stat-label">ISK</span>
              </div>
              {battle.last_milestone > 0 && (
                <div className="milestone-line">
                  🎯 Milestone: <strong>{battle.last_milestone} kills</strong>
                </div>
              )}
              <div className="time-line">
                📊 {formatDuration(battle.duration_minutes)} ago
              </div>
            </div>
          </div>
        ))}
      </div>
      {totalActive > 5 && (
        <div className="live-battles-footer">
          <a href="/battle-map" className="view-all-link">
            View All ({totalActive}) →
          </a>
        </div>
      )}
    </div>
  );
}
