import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { Layout } from './components/Layout';
import { Home } from './pages/Home';
import { BattleReport } from './pages/BattleReport';
import { BattleMap } from './pages/BattleMap';
import { WarProfiteering } from './pages/WarProfiteering';
import { AllianceWars } from './pages/AllianceWars';
import { TradeRoutes } from './pages/TradeRoutes';
import { Impressum } from './pages/Impressum';
import { Datenschutz } from './pages/Datenschutz';
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
          <Route path="/impressum" element={<Impressum />} />
          <Route path="/datenschutz" element={<Datenschutz />} />
          <Route path="*" element={<NotFound />} />
        </Routes>
      </Layout>
    </BrowserRouter>
  );
}

export default App;
