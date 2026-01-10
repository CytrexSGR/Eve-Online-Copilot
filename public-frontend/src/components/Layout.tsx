import React from 'react';
import { Link } from 'react-router-dom';

interface LayoutProps {
  children: React.ReactNode;
}

export function Layout({ children }: LayoutProps) {
  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      {/* Header */}
      <header style={{
        background: 'var(--bg-secondary)',
        borderBottom: '1px solid var(--border-color)',
        padding: '1rem 0'
      }}>
        <div className="container">
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <div>
              <Link to="/" style={{ textDecoration: 'none' }}>
                <h1 style={{
                  fontSize: '1.5rem',
                  color: 'var(--accent-blue)',
                  margin: 0
                }}>
                  ⚔️ EVE Intelligence
                </h1>
              </Link>
              <p style={{
                color: 'var(--text-secondary)',
                fontSize: '0.875rem',
                margin: 0
              }}>
                Real-time Combat Intelligence for New Eden
              </p>
            </div>

            <nav style={{ display: 'flex', gap: '1.5rem' }}>
              <Link to="/battle-map">Battle Map</Link>
              <Link to="/battle-report">Battle Report</Link>
              <Link to="/war-economy">War Economy</Link>
              <Link to="/alliance-wars">Alliance Wars</Link>
              <Link to="/trade-routes">Trade Routes</Link>
            </nav>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main style={{ flex: 1, padding: '2rem 0' }}>
        <div className="container">
          {children}
        </div>
      </main>

      {/* Footer */}
      <footer style={{
        background: 'var(--bg-secondary)',
        borderTop: '1px solid var(--border-color)',
        padding: '2rem 0',
        marginTop: '3rem'
      }}>
        <div className="container">
          <div style={{
            display: 'flex',
            justifyContent: 'space-between',
            flexWrap: 'wrap',
            gap: '2rem'
          }}>
            <div>
              <p style={{ color: 'var(--text-secondary)', fontSize: '0.875rem' }}>
                © 2026 Infinimind Creations | Data from zKillboard & ESI
              </p>
              <p style={{ color: 'var(--text-tertiary)', fontSize: '0.75rem', marginTop: '0.5rem' }}>
                EVE Online and the EVE logo are trademarks of CCP hf.
              </p>
            </div>
            <div style={{ display: 'flex', gap: '1.5rem' }}>
              <Link to="/impressum" style={{ fontSize: '0.875rem' }}>Legal Notice</Link>
              <Link to="/datenschutz" style={{ fontSize: '0.875rem' }}>Privacy Policy</Link>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}
