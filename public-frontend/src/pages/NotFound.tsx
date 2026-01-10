import { Link } from 'react-router-dom';

export function NotFound() {
  return (
    <div style={{
      maxWidth: '800px',
      margin: '60px auto',
      padding: '40px',
      backgroundColor: '#161b22',
      borderRadius: '12px',
      border: '1px solid #30363d'
    }}>
      <div style={{ textAlign: 'center', marginBottom: '40px' }}>
        <h1 style={{
          fontSize: '72px',
          margin: '0',
          color: '#f85149',
          fontWeight: '700'
        }}>404</h1>
        <h2 style={{
          fontSize: '24px',
          margin: '10px 0',
          color: '#e6edf3'
        }}>Page Not Found</h2>
        <p style={{
          color: '#8b949e',
          fontSize: '16px',
          margin: '10px 0'
        }}>
          The page you're looking for doesn't exist or has been moved.
        </p>
      </div>

      <div style={{ marginBottom: '30px' }}>
        <h3 style={{
          color: '#e6edf3',
          fontSize: '18px',
          marginBottom: '15px',
          borderBottom: '1px solid #30363d',
          paddingBottom: '10px'
        }}>
          Available Pages:
        </h3>

        <div style={{ display: 'grid', gap: '10px' }}>
          <Link
            to="/"
            style={{
              display: 'block',
              padding: '12px 16px',
              backgroundColor: '#21262d',
              border: '1px solid #30363d',
              borderRadius: '6px',
              color: '#58a6ff',
              textDecoration: 'none',
              transition: 'all 0.2s'
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.backgroundColor = '#30363d';
              e.currentTarget.style.borderColor = '#58a6ff';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.backgroundColor = '#21262d';
              e.currentTarget.style.borderColor = '#30363d';
            }}
          >
            <strong>🏠 Home</strong>
            <div style={{ fontSize: '14px', color: '#8b949e', marginTop: '4px' }}>
              Dashboard with all reports overview
            </div>
          </Link>

          <Link
            to="/battle-report"
            style={{
              display: 'block',
              padding: '12px 16px',
              backgroundColor: '#21262d',
              border: '1px solid #30363d',
              borderRadius: '6px',
              color: '#58a6ff',
              textDecoration: 'none',
              transition: 'all 0.2s'
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.backgroundColor = '#30363d';
              e.currentTarget.style.borderColor = '#58a6ff';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.backgroundColor = '#21262d';
              e.currentTarget.style.borderColor = '#30363d';
            }}
          >
            <strong>📊 Battle Report</strong>
            <div style={{ fontSize: '14px', color: '#8b949e', marginTop: '4px' }}>
              24-hour combat intelligence analysis
            </div>
          </Link>

          <Link
            to="/battle-map"
            style={{
              display: 'block',
              padding: '12px 16px',
              backgroundColor: '#21262d',
              border: '1px solid #30363d',
              borderRadius: '6px',
              color: '#58a6ff',
              textDecoration: 'none',
              transition: 'all 0.2s'
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.backgroundColor = '#30363d';
              e.currentTarget.style.borderColor = '#58a6ff';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.backgroundColor = '#21262d';
              e.currentTarget.style.borderColor = '#30363d';
            }}
          >
            <strong>🗺️ Battle Map</strong>
            <div style={{ fontSize: '14px', color: '#8b949e', marginTop: '4px' }}>
              Interactive universe map with live battle tracking
            </div>
          </Link>

          <Link
            to="/war-profiteering"
            style={{
              display: 'block',
              padding: '12px 16px',
              backgroundColor: '#21262d',
              border: '1px solid #30363d',
              borderRadius: '6px',
              color: '#58a6ff',
              textDecoration: 'none',
              transition: 'all 0.2s'
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.backgroundColor = '#30363d';
              e.currentTarget.style.borderColor = '#58a6ff';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.backgroundColor = '#21262d';
              e.currentTarget.style.borderColor = '#30363d';
            }}
          >
            <strong>💰 War Profiteering</strong>
            <div style={{ fontSize: '14px', color: '#8b949e', marginTop: '4px' }}>
              Most destroyed items and market opportunities
            </div>
          </Link>

          <Link
            to="/alliance-wars"
            style={{
              display: 'block',
              padding: '12px 16px',
              backgroundColor: '#21262d',
              border: '1px solid #30363d',
              borderRadius: '6px',
              color: '#58a6ff',
              textDecoration: 'none',
              transition: 'all 0.2s'
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.backgroundColor = '#30363d';
              e.currentTarget.style.borderColor = '#58a6ff';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.backgroundColor = '#21262d';
              e.currentTarget.style.borderColor = '#30363d';
            }}
          >
            <strong>⚔️ Alliance Wars</strong>
            <div style={{ fontSize: '14px', color: '#8b949e', marginTop: '4px' }}>
              Active conflicts and war statistics
            </div>
          </Link>

          <Link
            to="/trade-routes"
            style={{
              display: 'block',
              padding: '12px 16px',
              backgroundColor: '#21262d',
              border: '1px solid #30363d',
              borderRadius: '6px',
              color: '#58a6ff',
              textDecoration: 'none',
              transition: 'all 0.2s'
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.backgroundColor = '#30363d';
              e.currentTarget.style.borderColor = '#58a6ff';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.backgroundColor = '#21262d';
              e.currentTarget.style.borderColor = '#30363d';
            }}
          >
            <strong>🚚 Trade Routes</strong>
            <div style={{ fontSize: '14px', color: '#8b949e', marginTop: '4px' }}>
              High-value trade corridors and risk assessment
            </div>
          </Link>
        </div>
      </div>

      <div style={{
        textAlign: 'center',
        padding: '20px',
        backgroundColor: '#0d1117',
        borderRadius: '6px',
        border: '1px solid #30363d'
      }}>
        <p style={{
          color: '#8b949e',
          fontSize: '14px',
          margin: '0 0 10px 0'
        }}>
          Need help? Contact us or check the documentation.
        </p>
        <Link
          to="/"
          style={{
            display: 'inline-block',
            padding: '10px 20px',
            backgroundColor: '#238636',
            color: '#ffffff',
            textDecoration: 'none',
            borderRadius: '6px',
            fontWeight: '600',
            transition: 'background-color 0.2s'
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.backgroundColor = '#2ea043';
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.backgroundColor = '#238636';
          }}
        >
          Go to Homepage
        </Link>
      </div>
    </div>
  );
}
