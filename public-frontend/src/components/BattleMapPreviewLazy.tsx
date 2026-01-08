import { lazy, Suspense } from 'react';
import type { BattleReport } from '../types/reports';

const BattleMapPreview = lazy(() =>
  import('./BattleMapPreview').then(m => ({ default: m.BattleMapPreview }))
);

interface BattleMapPreviewLazyProps {
  battleReport?: BattleReport;
  showAllLayers?: boolean;
}

export function BattleMapPreviewLazy(props: BattleMapPreviewLazyProps) {
  return (
    <Suspense
      fallback={
        <div style={{
          height: '500px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          background: 'var(--bg-elevated)',
          borderRadius: '8px'
        }}>
          <div style={{ textAlign: 'center', color: 'var(--text-secondary)' }}>
            <div className="skeleton" style={{ width: '100%', height: '500px' }} />
          </div>
        </div>
      }
    >
      <BattleMapPreview {...props} />
    </Suspense>
  );
}
