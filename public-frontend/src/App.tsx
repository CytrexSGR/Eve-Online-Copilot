import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { Layout } from './components/Layout';
import { Home } from './pages/Home';
import './App.css';

function App() {
  return (
    <BrowserRouter>
      <Layout>
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/battle-report" element={<div>Battle Report Detail (Coming Soon)</div>} />
          <Route path="/war-profiteering" element={<div>War Profiteering Detail (Coming Soon)</div>} />
          <Route path="/alliance-wars" element={<div>Alliance Wars Detail (Coming Soon)</div>} />
          <Route path="/trade-routes" element={<div>Trade Routes Detail (Coming Soon)</div>} />
          <Route path="/privacy" element={<div>Privacy Policy (Coming Soon)</div>} />
          <Route path="/cookies" element={<div>Cookie Policy (Coming Soon)</div>} />
          <Route path="*" element={<div>404 - Not Found</div>} />
        </Routes>
      </Layout>
    </BrowserRouter>
  );
}

export default App;
