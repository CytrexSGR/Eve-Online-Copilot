import { BrowserRouter, Routes, Route, NavLink } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { TrendingUp, Search, Factory, BarChart3, Star, Package, ShoppingCart, Swords } from 'lucide-react';
import MarketScanner from './pages/MarketScanner';
import ArbitrageFinder from './pages/ArbitrageFinder';
import ProductionPlanner from './pages/ProductionPlanner';
import ItemDetail from './pages/ItemDetail';
import Bookmarks from './pages/Bookmarks';
import MaterialsOverview from './pages/MaterialsOverview';
import ShoppingPlanner from './pages/ShoppingPlanner';
import WarRoom from './pages/WarRoom';
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
                  <ShoppingCart size={20} />
                  <span>Shopping</span>
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
              <Route path="/shopping" element={<ShoppingPlanner />} />
              <Route path="/war-room" element={<WarRoom />} />
            </Routes>
          </main>
        </div>
      </BrowserRouter>
    </QueryClientProvider>
  );
}

export default App;
