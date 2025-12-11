import OpportunitiesTable from '../components/dashboard/OpportunitiesTable';
import CharacterOverview from '../components/dashboard/CharacterOverview';
import WarRoomAlerts from '../components/dashboard/WarRoomAlerts';
import ActiveProjects from '../components/dashboard/ActiveProjects';
import { useOpportunities } from '../hooks/dashboard/useOpportunities';
import './Dashboard.css';

/**
 * Dashboard - Main landing page for EVE Co-Pilot 2.0
 *
 * Layout (70/30 split):
 * - Main Content (70%):
 *   - OpportunitiesTable (75%) - Top profitable actions in table format
 *   - CharacterOverview (25%) - 3 character cards with stats
 * - Sidebar (30%):
 *   - WarRoomAlerts (top) - Combat intel and alerts
 *   - ActiveProjects (bottom) - Shopping lists and active tasks
 */
export default function Dashboard() {
  const { data: opportunities = [], isLoading } = useOpportunities();

  return (
    <div className="dashboard">
      <div className="dashboard-main">
        <OpportunitiesTable
          opportunities={opportunities}
          loading={isLoading}
        />
        <CharacterOverview />
      </div>

      <aside className="dashboard-sidebar">
        <WarRoomAlerts />
        <ActiveProjects />
      </aside>
    </div>
  );
}
