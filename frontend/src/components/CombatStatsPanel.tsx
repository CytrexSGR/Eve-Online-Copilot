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
  total_destroyed: number;
  total_value_destroyed: number;
  regions_affected: number;
  systems_affected: number;
  top_regions: Array<{
    region_id: number;
    region_name: string;
    quantity: number;
  }>;
  top_systems: Array<{
    solar_system_id: number;
    system_name: string;
    quantity: number;
    security: number;
  }>;
}

export default function CombatStatsPanel({ typeId, days = 7 }: CombatStatsPanelProps) {
  const { data, isLoading } = useQuery<CombatStats>({
    queryKey: ['combatStats', typeId, days],
    queryFn: () => getItemCombatStats(typeId, days),
  });

  const hasData = data && data.total_destroyed > 0;
  const badgeValue = hasData ? data.total_destroyed : undefined;
  const badgeColor = hasData ? 'red' : 'blue';

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
      ) : !hasData ? (
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
            <div className="combat-stat-small">
              <span className="stat-number-small">{data.regions_affected}</span>
              <span className="stat-label">regions</span>
            </div>
            <div className="combat-stat-small">
              <span className="stat-number-small">{data.systems_affected}</span>
              <span className="stat-label">systems</span>
            </div>
          </div>

          {data.top_regions.length > 0 && (
            <>
              <h4>Top Regions</h4>
              <div className="region-breakdown">
                {data.top_regions.map((r) => (
                  <div key={r.region_id} className="region-row">
                    <span className="region-name">{r.region_name}</span>
                    <span className="destroyed">{r.quantity.toLocaleString()} destroyed</span>
                  </div>
                ))}
              </div>
            </>
          )}

          {data.top_systems.length > 0 && (
            <>
              <h4>Top Systems</h4>
              <div className="system-breakdown">
                {data.top_systems.map((s) => (
                  <div key={s.solar_system_id} className="system-row">
                    <div className="system-info">
                      <span className="system-name">{s.system_name}</span>
                      <span className={`security sec-${Math.floor(s.security * 10)}`}>
                        {s.security.toFixed(1)}
                      </span>
                    </div>
                    <span className="destroyed">{s.quantity.toLocaleString()} destroyed</span>
                  </div>
                ))}
              </div>
            </>
          )}
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
          gap: 24px;
          margin-bottom: 16px;
        }

        .combat-stat-big {
          display: flex;
          flex-direction: column;
        }

        .combat-stat-small {
          display: flex;
          flex-direction: column;
        }

        .stat-number {
          font-size: 32px;
          font-weight: 700;
          color: var(--color-error);
        }

        .stat-number-small {
          font-size: 24px;
          font-weight: 600;
          color: var(--text-primary);
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

        .destroyed {
          color: var(--color-error);
          font-size: 13px;
          font-weight: 500;
        }

        .system-breakdown {
          display: flex;
          flex-direction: column;
          gap: 8px;
        }

        .system-row {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 8px 12px;
          background: var(--bg-secondary);
          border-radius: 6px;
        }

        .system-info {
          display: flex;
          align-items: center;
          gap: 8px;
        }

        .system-name {
          font-weight: 500;
        }

        .security {
          font-size: 11px;
          padding: 2px 6px;
          border-radius: 4px;
          font-weight: 600;
          font-family: monospace;
        }

        .sec-10, .sec-9, .sec-8 {
          background: rgba(46, 204, 113, 0.2);
          color: #2ecc71;
        }

        .sec-7, .sec-6, .sec-5 {
          background: rgba(241, 196, 15, 0.2);
          color: #f1c40f;
        }

        .sec-4, .sec-3, .sec-2, .sec-1, .sec-0 {
          background: rgba(231, 76, 60, 0.2);
          color: #e74c3c;
        }
      `}</style>
    </CollapsiblePanel>
  );
}
