import { AlertTriangle } from 'lucide-react';

interface DangerousSystem {
  name: string;
  kills: number;
  score: number;
}

interface ConflictAlertProps {
  dangerousSystems: DangerousSystem[];
  totalDanger: number;
  averageDanger?: number;
}

export default function ConflictAlert({ dangerousSystems, totalDanger, averageDanger }: ConflictAlertProps) {
  if (dangerousSystems.length === 0) {
    return null;
  }

  return (
    <div className="conflict-alert">
      <div className="conflict-alert-header">
        <AlertTriangle size={18} />
        <span>Route passes through conflict zone</span>
      </div>
      <div className="conflict-alert-systems">
        {dangerousSystems.map((sys, i) => (
          <span key={sys.name} className="dangerous-system">
            {sys.name} ({sys.kills} kills/24h)
            {i < dangerousSystems.length - 1 ? ', ' : ''}
          </span>
        ))}
      </div>
      <div className="conflict-alert-footer">
        Total danger score: {totalDanger}
        {averageDanger !== undefined && ` (avg: ${averageDanger})`}
      </div>

      <style>{`
        .conflict-alert {
          background: rgba(239, 68, 68, 0.1);
          border: 1px solid rgba(239, 68, 68, 0.3);
          border-radius: 8px;
          padding: 12px 16px;
          margin-bottom: 16px;
        }

        .conflict-alert-header {
          display: flex;
          align-items: center;
          gap: 8px;
          color: var(--color-error);
          font-weight: 600;
          margin-bottom: 8px;
        }

        .conflict-alert-systems {
          font-size: 13px;
          color: var(--color-error);
          margin-bottom: 6px;
        }

        .dangerous-system {
          font-weight: 500;
        }

        .conflict-alert-footer {
          font-size: 11px;
          color: rgba(239, 68, 68, 0.7);
        }
      `}</style>
    </div>
  );
}
