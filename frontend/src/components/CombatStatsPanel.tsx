import { useQuery } from '@tanstack/react-query';
import { Swords } from 'lucide-react';
import { getItemCombatStats } from '../api';
import CollapsiblePanel from './CollapsiblePanel';

interface CombatStatsPanelProps {
  typeId: number;
  days?: number;
}

interface CombatStats {
  type_id: number;
  type_name: string;
  days: number;
  total_destroyed: number;
  by_region: Array<{
    region_id: number;
    region_name: string;
    destroyed: number;
  }>;
  market_comparison: Array<{
    region: string;
    region_name: string;
    destroyed: number;
    stock: number;
    gap: number;
  }>;
  has_data: boolean;
}

export default function CombatStatsPanel({ typeId, days = 7 }: CombatStatsPanelProps) {
  const { data, isLoading } = useQuery<CombatStats>({
    queryKey: ['combatStats', typeId, days],
    queryFn: () => getItemCombatStats(typeId, days),
  });

  const badgeValue = data?.has_data ? data.total_destroyed : undefined;
  const badgeColor = data?.has_data && data.total_destroyed > 0 ? 'red' : 'blue';

  return (
    <CollapsiblePanel
      title="Combat Stats"
      icon={Swords}
      defaultOpen={true}
      badge={badgeValue}
      badgeColor={badgeColor as 'red' | 'blue'}
    >
      {isLoading ? (
        <div className="loading-small">Loading combat data...</div>
      ) : !data?.has_data ? (
        <div className="no-data">
          <Swords size={24} style={{ opacity: 0.3 }} />
          <p>No recent combat data</p>
          <span className="no-data-hint">This item hasn't been destroyed in combat in the last {days} days</span>
        </div>
      ) : (
        <div className="combat-stats-content">
          <div className="combat-summary">
            <div className="combat-stat-big">
              <span className="stat-number">{data.total_destroyed.toLocaleString()}</span>
              <span className="stat-label">destroyed ({days}d)</span>
            </div>
          </div>

          <h4>By Region</h4>
          <div className="region-breakdown">
            {data.market_comparison.map((r) => (
              <div key={r.region} className="region-row">
                <span className="region-name">{r.region_name}</span>
                <div className="region-stats">
                  <span className="destroyed">{r.destroyed} lost</span>
                  <span className="stock">{r.stock} stock</span>
                  <span className={`gap ${r.gap >= 0 ? 'positive' : 'negative'}`}>
                    {r.gap >= 0 ? '+' : ''}{r.gap}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      <style>{`
        .loading-small {
          padding: 20px;
          text-align: center;
          color: var(--text-secondary);
        }

        .no-data {
          display: flex;
          flex-direction: column;
          align-items: center;
          padding: 24px;
          color: var(--text-secondary);
          text-align: center;
        }

        .no-data p {
          margin: 8px 0 4px;
          font-weight: 500;
        }

        .no-data-hint {
          font-size: 12px;
          opacity: 0.7;
        }

        .combat-stats-content h4 {
          margin: 16px 0 8px;
          font-size: 12px;
          text-transform: uppercase;
          color: var(--text-secondary);
        }

        .combat-summary {
          display: flex;
          gap: 16px;
        }

        .combat-stat-big {
          display: flex;
          flex-direction: column;
        }

        .stat-number {
          font-size: 32px;
          font-weight: 700;
          color: var(--color-error);
        }

        .stat-label {
          font-size: 12px;
          color: var(--text-secondary);
        }

        .region-breakdown {
          display: flex;
          flex-direction: column;
          gap: 8px;
        }

        .region-row {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 8px 12px;
          background: var(--bg-secondary);
          border-radius: 6px;
        }

        .region-name {
          font-weight: 500;
        }

        .region-stats {
          display: flex;
          gap: 16px;
          font-size: 13px;
        }

        .destroyed {
          color: var(--color-error);
        }

        .stock {
          color: var(--text-secondary);
        }

        .gap {
          font-weight: 600;
          min-width: 50px;
          text-align: right;
        }

        .gap.positive {
          color: var(--color-success);
        }

        .gap.negative {
          color: var(--color-error);
        }
      `}</style>
    </CollapsiblePanel>
  );
}
