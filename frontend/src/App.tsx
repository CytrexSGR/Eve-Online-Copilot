import { BrowserRouter, Routes, Route, NavLink } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { TrendingUp, Search, Factory, BarChart3, Star, Package, Swords, Wand2, List } from 'lucide-react';
import MarketScanner from './pages/MarketScanner';
import ArbitrageFinder from './pages/ArbitrageFinder';
import ProductionPlanner from './pages/ProductionPlanner';
import ItemDetail from './pages/ItemDetail';
import Bookmarks from './pages/Bookmarks';
import MaterialsOverview from './pages/MaterialsOverview';
import ShoppingPlanner from './pages/ShoppingPlanner';
import { ShoppingWizard } from './components/shopping';
import WarRoom from './pages/WarRoom';
import WarRoomShipsDestroyed from './pages/WarRoomShipsDestroyed';
import WarRoomMarketGaps from './pages/WarRoomMarketGaps';
import WarRoomTopShips from './pages/WarRoomTopShips';
import WarRoomCombatHotspots from './pages/WarRoomCombatHotspots';
import WarRoomFWHotspots from './pages/WarRoomFWHotspots';
import WarRoomGalaxySummary from './pages/WarRoomGalaxySummary';
import './App.css';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 60000,
      retry: 2,
    },
  },
});

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <div className="app">
          <nav className="sidebar">
            <div className="logo">
              <BarChart3 size={32} />
              <span>EVE Co-Pilot</span>
            </div>
            <ul className="nav-links">
              <li>
                <NavLink to="/" className={({ isActive }) => isActive ? 'active' : ''}>
                  <TrendingUp size={20} />
                  <span>Market Scanner</span>
                </NavLink>
              </li>
              <li>
                <NavLink to="/arbitrage" className={({ isActive }) => isActive ? 'active' : ''}>
                  <Search size={20} />
                  <span>Arbitrage Finder</span>
                </NavLink>
              </li>
              <li>
                <NavLink to="/production" className={({ isActive }) => isActive ? 'active' : ''}>
                  <Factory size={20} />
                  <span>Production Planner</span>
                </NavLink>
              </li>
              <li>
                <NavLink to="/bookmarks" className={({ isActive }) => isActive ? 'active' : ''}>
                  <Star size={20} />
                  <span>Bookmarks</span>
                </NavLink>
              </li>
              <li>
                <NavLink to="/materials" className={({ isActive }) => isActive ? 'active' : ''}>
                  <Package size={20} />
                  <span>Materials</span>
                </NavLink>
              </li>
              <li>
                <NavLink to="/shopping" className={({ isActive }) => isActive ? 'active' : ''}>
                  <Wand2 size={20} />
                  <span>Shopping Wizard</span>
                </NavLink>
              </li>
              <li>
                <NavLink to="/shopping-lists" className={({ isActive }) => isActive ? 'active' : ''}>
                  <List size={20} />
                  <span>Shopping Lists</span>
                </NavLink>
              </li>
              <li>
                <NavLink to="/war-room" className={({ isActive }) => isActive ? 'active' : ''}>
                  <Swords size={20} />
                  <span>War Room</span>
                </NavLink>
              </li>
            </ul>
          </nav>
          <main className="content">
            <Routes>
              <Route path="/" element={<MarketScanner />} />
              <Route path="/item/:typeId" element={<ItemDetail />} />
              <Route path="/arbitrage" element={<ArbitrageFinder />} />
              <Route path="/production" element={<ProductionPlanner />} />
              <Route path="/bookmarks" element={<Bookmarks />} />
              <Route path="/materials" element={<MaterialsOverview />} />
              <Route path="/shopping" element={<ShoppingWizard />} />
              <Route path="/shopping-lists" element={<ShoppingPlanner />} />
              <Route path="/war-room" element={<WarRoom />} />
              <Route path="/war-room/ships-destroyed" element={<WarRoomShipsDestroyed />} />
              <Route path="/war-room/market-gaps" element={<WarRoomMarketGaps />} />
              <Route path="/war-room/top-ships" element={<WarRoomTopShips />} />
              <Route path="/war-room/combat-hotspots" element={<WarRoomCombatHotspots />} />
              <Route path="/war-room/fw-hotspots" element={<WarRoomFWHotspots />} />
              <Route path="/war-room/galaxy-summary" element={<WarRoomGalaxySummary />} />
            </Routes>
          </main>
        </div>
      </BrowserRouter>
    </QueryClientProvider>
  );
}

export default App;
