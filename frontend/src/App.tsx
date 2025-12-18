import { lazy, Suspense } from 'react';
import { BrowserRouter, Routes, Route, NavLink } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { TrendingUp, Search, Factory, BarChart3, Star, Package, Swords, Wand2, List } from 'lucide-react';
import { useGlobalShortcuts } from './hooks/useKeyboardShortcuts';
import { ShortcutsHelp } from './components/ShortcutsHelp';
import './App.css';

// Lazy load all pages for code splitting
const Dashboard = lazy(() => import('./pages/Dashboard'));
const ArbitrageFinder = lazy(() => import('./pages/ArbitrageFinder'));
const ProductionPlanner = lazy(() => import('./pages/ProductionPlanner'));
const ItemDetail = lazy(() => import('./pages/ItemDetail'));
const Bookmarks = lazy(() => import('./pages/Bookmarks'));
const MaterialsOverview = lazy(() => import('./pages/MaterialsOverview'));
const ShoppingPlanner = lazy(() => import('./pages/ShoppingPlanner'));
const ShoppingWizard = lazy(() => import('./components/shopping').then(m => ({ default: m.ShoppingWizard })));
const WarRoom = lazy(() => import('./pages/WarRoom'));
const WarRoomShipsDestroyed = lazy(() => import('./pages/WarRoomShipsDestroyed'));
const WarRoomMarketGaps = lazy(() => import('./pages/WarRoomMarketGaps'));
const WarRoomTopShips = lazy(() => import('./pages/WarRoomTopShips'));
const WarRoomCombatHotspots = lazy(() => import('./pages/WarRoomCombatHotspots'));
const WarRoomFWHotspots = lazy(() => import('./pages/WarRoomFWHotspots'));
const WarRoomGalaxySummary = lazy(() => import('./pages/WarRoomGalaxySummary'));

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000, // 5 minutes (most data changes slowly)
      gcTime: 10 * 60 * 1000, // 10 minutes (garbage collection time, keep in cache)
      retry: 2,
      refetchOnWindowFocus: false, // Don't refetch on tab focus (reduces load)
      refetchOnReconnect: true, // Refetch when connection restored
    },
  },
});

function AppContent() {
  // Enable global keyboard shortcuts
  useGlobalShortcuts();

  return (
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
            <Suspense fallback={
              <div className="loading">
                <div className="spinner"></div>
                Loading...
              </div>
            }>
              <Routes>
                <Route path="/" element={<Dashboard />} />
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
            </Suspense>
          </main>
          <ShortcutsHelp />
        </div>
  );
}

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <AppContent />
      </BrowserRouter>
    </QueryClientProvider>
  );
}

export default App;
