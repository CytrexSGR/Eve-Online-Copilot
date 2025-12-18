import { useState, useEffect } from 'react';
import { X, Keyboard } from 'lucide-react';
import { GLOBAL_SHORTCUTS } from '../hooks/useKeyboardShortcuts';
import './ShortcutsHelp.css';

export function ShortcutsHelp() {
  const [isOpen, setIsOpen] = useState(false);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === '?' && !e.ctrlKey && !e.altKey && !e.shiftKey) {
        // Only open if not in input/textarea
        const target = e.target as HTMLElement;
        if (target.tagName !== 'INPUT' && target.tagName !== 'TEXTAREA') {
          e.preventDefault();
          setIsOpen(prev => !prev);
        }
      }
      if (e.key === 'Escape' && isOpen) {
        setIsOpen(false);
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen]);

  if (!isOpen) {
    return (
      <button
        className="shortcuts-help-trigger"
        onClick={() => setIsOpen(true)}
        title="Keyboard shortcuts (Press ?)"
      >
        <Keyboard size={18} />
      </button>
    );
  }

  return (
    <div className="shortcuts-help-overlay" onClick={() => setIsOpen(false)}>
      <div className="shortcuts-help-modal" onClick={(e) => e.stopPropagation()}>
        <div className="shortcuts-help-header">
          <h2>
            <Keyboard size={24} />
            Keyboard Shortcuts
          </h2>
          <button onClick={() => setIsOpen(false)} className="close-btn">
            <X size={20} />
          </button>
        </div>
        <div className="shortcuts-help-content">
          <div className="shortcuts-section">
            <h3>Navigation</h3>
            <div className="shortcuts-list">
              {GLOBAL_SHORTCUTS.map((shortcut, idx) => (
                <div key={idx} className="shortcut-item">
                  <kbd className="shortcut-keys">{shortcut.keys}</kbd>
                  <span className="shortcut-desc">{shortcut.description}</span>
                </div>
              ))}
            </div>
          </div>
          <div className="shortcuts-section">
            <h3>General</h3>
            <div className="shortcuts-list">
              <div className="shortcut-item">
                <kbd className="shortcut-keys">Esc</kbd>
                <span className="shortcut-desc">Close dialogs/modals</span>
              </div>
              <div className="shortcut-item">
                <kbd className="shortcut-keys">?</kbd>
                <span className="shortcut-desc">Toggle shortcuts help</span>
              </div>
            </div>
          </div>
        </div>
        <div className="shortcuts-help-footer">
          <p className="neutral">Press <kbd>Esc</kbd> or click outside to close</p>
        </div>
      </div>
    </div>
  );
}
