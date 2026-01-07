import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { Layout } from './components/Layout';
import { Home } from './pages/Home';
import { BattleReport } from './pages/BattleReport';
import { BattleMap } from './pages/BattleMap';
import { WarProfiteering } from './pages/WarProfiteering';
import { AllianceWars } from './pages/AllianceWars';
import { TradeRoutes } from './pages/TradeRoutes';
import { NotFound } from './pages/NotFound';
import './App.css';

function App() {
  return (
    <BrowserRouter>
      <Layout>
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/battle-report" element={<BattleReport />} />
          <Route path="/battle-map" element={<BattleMap />} />
          <Route path="/war-profiteering" element={<WarProfiteering />} />
          <Route path="/alliance-wars" element={<AllianceWars />} />
          <Route path="/trade-routes" element={<TradeRoutes />} />
          <Route path="/privacy" element={<div>Privacy Policy (Coming Soon)</div>} />
          <Route path="/cookies" element={<div>Cookie Policy (Coming Soon)</div>} />
          <Route path="*" element={<NotFound />} />
        </Routes>
      </Layout>
    </BrowserRouter>
  );
}

export default App;
