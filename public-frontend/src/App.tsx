import { lazy, Suspense } from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { Layout } from './components/Layout';
import { Home } from './pages/Home';
import './App.css';

// Lazy load pages to reduce initial bundle size
const BattleReport = lazy(() => import('./pages/BattleReport').then(m => ({ default: m.BattleReport })));
const BattleMap = lazy(() => import('./pages/BattleMap').then(m => ({ default: m.BattleMap })));
const WarProfiteering = lazy(() => import('./pages/WarProfiteering').then(m => ({ default: m.WarProfiteering })));
const AllianceWars = lazy(() => import('./pages/AllianceWars').then(m => ({ default: m.AllianceWars })));
const TradeRoutes = lazy(() => import('./pages/TradeRoutes').then(m => ({ default: m.TradeRoutes })));
const Impressum = lazy(() => import('./pages/Impressum').then(m => ({ default: m.Impressum })));
const Datenschutz = lazy(() => import('./pages/Datenschutz').then(m => ({ default: m.Datenschutz })));
const NotFound = lazy(() => import('./pages/NotFound').then(m => ({ default: m.NotFound })));

// Loading fallback component
const PageLoader = () => (
  <div style={{
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    minHeight: '400px',
    color: 'var(--text-secondary)'
  }}>
    <div className="skeleton" style={{ width: '100%', height: '400px' }} />
  </div>
);

function App() {
  return (
    <BrowserRouter>
      <Layout>
        <Suspense fallback={<PageLoader />}>
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/battle-report" element={<BattleReport />} />
            <Route path="/battle-map" element={<BattleMap />} />
            <Route path="/war-profiteering" element={<WarProfiteering />} />
            <Route path="/alliance-wars" element={<AllianceWars />} />
            <Route path="/trade-routes" element={<TradeRoutes />} />
            <Route path="/impressum" element={<Impressum />} />
            <Route path="/datenschutz" element={<Datenschutz />} />
            <Route path="*" element={<NotFound />} />
          </Routes>
        </Suspense>
      </Layout>
    </BrowserRouter>
  );
}

export default App;
