import { useState } from 'react';
import { ChevronDown, ChevronRight } from 'lucide-react';
import type { LucideIcon } from 'lucide-react';

interface CollapsiblePanelProps {
  title: string;
  icon: LucideIcon;
  defaultOpen?: boolean;
  children: React.ReactNode;
  badge?: string | number;
  badgeColor?: 'green' | 'red' | 'yellow' | 'blue';
}

export default function CollapsiblePanel({
  title,
  icon: Icon,
  defaultOpen = true,
  children,
  badge,
  badgeColor = 'blue'
}: CollapsiblePanelProps) {
  const [isOpen, setIsOpen] = useState(defaultOpen);

  const badgeColors = {
    green: 'var(--color-success)',
    red: 'var(--color-error)',
    yellow: 'var(--color-warning)',
    blue: 'var(--accent-blue)'
  };

  return (
    <div className="collapsible-panel">
      <button
        className="panel-header"
        onClick={() => setIsOpen(!isOpen)}
      >
        <div className="panel-title">
          {isOpen ? <ChevronDown size={18} /> : <ChevronRight size={18} />}
          <Icon size={18} />
          <span>{title}</span>
        </div>
        {badge !== undefined && (
          <span
            className="panel-badge"
            style={{ backgroundColor: badgeColors[badgeColor] }}
          >
            {badge}
          </span>
        )}
      </button>
      {isOpen && (
        <div className="panel-content">
          {children}
        </div>
      )}

      <style>{`
        .collapsible-panel {
          background: var(--bg-card);
          border: 1px solid var(--border-color);
          border-radius: 8px;
          margin-bottom: 12px;
          overflow: hidden;
        }

        .panel-header {
          width: 100%;
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 12px 16px;
          background: var(--bg-secondary);
          border: none;
          cursor: pointer;
          color: var(--text-primary);
          font-size: 14px;
          font-weight: 600;
        }

        .panel-header:hover {
          background: var(--bg-tertiary);
        }

        .panel-title {
          display: flex;
          align-items: center;
          gap: 8px;
        }

        .panel-badge {
          padding: 2px 8px;
          border-radius: 12px;
          font-size: 12px;
          font-weight: 600;
          color: white;
        }

        .panel-content {
          padding: 16px;
          border-top: 1px solid var(--border-color);
        }
      `}</style>
    </div>
  );
}
