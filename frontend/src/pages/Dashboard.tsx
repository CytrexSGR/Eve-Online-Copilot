import React from 'react';
import './Dashboard.css';

/**
 * Dashboard - Main landing page for EVE Co-Pilot 2.0
 *
 * Layout:
 * - Opportunities Feed (60% height) - Top profitable actions
 * - Character Overview (20% height) - 3 character cards
 * - War Room Alerts (sidebar right) - Combat intel
 * - Active Projects (sidebar right) - Shopping lists, bookmarks
 */
export default function Dashboard() {
  return (
    <div className="dashboard">
      <div className="dashboard-main">
        {/* Opportunities Feed */}
        <section className="opportunities-feed">
          <h2>Top Opportunities</h2>
          <p>Loading opportunities...</p>
        </section>

        {/* Character Overview */}
        <section className="character-overview">
          <h2>Your Characters</h2>
          <div className="character-cards">
            <div className="character-card">
              <h3>Artallus</h3>
              <p>Loading...</p>
            </div>
            <div className="character-card">
              <h3>Cytrex</h3>
              <p>Loading...</p>
            </div>
            <div className="character-card">
              <h3>Cytricia</h3>
              <p>Loading...</p>
            </div>
          </div>
        </section>
      </div>

      {/* Sidebar */}
      <aside className="dashboard-sidebar">
        <section className="war-alerts">
          <h3>War Room Alerts</h3>
          <p>Loading alerts...</p>
        </section>

        <section className="active-projects">
          <h3>Active Projects</h3>
          <p>Loading projects...</p>
        </section>
      </aside>
    </div>
  );
}
