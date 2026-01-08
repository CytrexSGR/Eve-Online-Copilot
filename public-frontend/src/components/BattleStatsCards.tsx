import { useState, useEffect } from 'react';
import { battleApi } from '../services/api';
import './BattleStatsCards.css';

interface BattleStats {
  activeBattles: number;
  totalKills: number;
  totalISK: number;
  milestonesReached: number;
}

/**
 * BattleStatsCards Component
 *
 * Displays key battle statistics in card format
 *
 * Features:
 * - 4 cards showing: Active Battles, Total Kills, ISK Destroyed, Milestones Today
 * - Auto-refreshes every 60 seconds
 * - Clickable to navigate to Battle Map
 */
export default function BattleStatsCards() {
  const [stats, setStats] = useState<BattleStats>({
    activeBattles: 0,
    totalKills: 0,
    totalISK: 0,
    milestonesReached: 0
  });
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    fetchStats();
    const interval = setInterval(fetchStats, 60000); // Refresh every 60s
    return () => clearInterval(interval);
  }, []);

  const fetchStats = async () => {
    try {
      const data = await battleApi.getActiveBattles(50); // Get all battles

      let totalKills = 0;
      let totalISK = 0;
      let milestonesCount = 0;

      data.battles.forEach((battle: any) => {
        totalKills += battle.total_kills;
        totalISK += battle.total_isk_destroyed;
        // Count milestones (10, 25, 50, 100, 200, 500)
        if (battle.last_milestone >= 500) milestonesCount += 6;
        else if (battle.last_milestone >= 200) milestonesCount += 5;
        else if (battle.last_milestone >= 100) milestonesCount += 4;
        else if (battle.last_milestone >= 50) milestonesCount += 3;
        else if (battle.last_milestone >= 25) milestonesCount += 2;
        else if (battle.last_milestone >= 10) milestonesCount += 1;
      });

      setStats({
        activeBattles: data.total_active || 0,
        totalKills,
        totalISK,
        milestonesReached: milestonesCount
      });
      setLoading(false);
    } catch (err) {
      console.error('Error fetching battle stats:', err);
      setLoading(false);
    }
  };

  /**
   * Format large numbers with K/M/B suffix
   */
  const formatNumber = (num: number): string => {
    if (num >= 1_000_000_000) {
      return `${(num / 1_000_000_000).toFixed(1)}B`;
    } else if (num >= 1_000_000) {
      return `${(num / 1_000_000).toFixed(1)}M`;
    } else if (num >= 1_000) {
      return `${(num / 1_000).toFixed(1)}K`;
    }
    return num.toString();
  };

  const handleCardClick = () => {
    window.location.href = '/battle-map';
  };

  if (loading) {
    return (
      <div className="battle-stats-cards loading">
        <div className="stat-card skeleton"></div>
        <div className="stat-card skeleton"></div>
        <div className="stat-card skeleton"></div>
        <div className="stat-card skeleton"></div>
      </div>
    );
  }

  return (
    <div className="battle-stats-cards">
      <div className="stat-card" onClick={handleCardClick}>
        <div className="card-icon">⚔️</div>
        <div className="card-content">
          <div className="card-label">Active Battles</div>
          <div className="card-value">{stats.activeBattles}</div>
        </div>
      </div>

      <div className="stat-card" onClick={handleCardClick}>
        <div className="card-icon">📊</div>
        <div className="card-content">
          <div className="card-label">Total Kills</div>
          <div className="card-value">{formatNumber(stats.totalKills)}</div>
        </div>
      </div>

      <div className="stat-card" onClick={handleCardClick}>
        <div className="card-icon">💰</div>
        <div className="card-content">
          <div className="card-label">ISK Destroyed</div>
          <div className="card-value">{formatNumber(stats.totalISK)}</div>
        </div>
      </div>

      <div className="stat-card" onClick={handleCardClick}>
        <div className="card-icon">🎯</div>
        <div className="card-content">
          <div className="card-label">Milestones</div>
          <div className="card-value">{stats.milestonesReached}</div>
        </div>
      </div>
    </div>
  );
}
