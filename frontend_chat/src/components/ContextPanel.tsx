import { ChatContext, MAJOR_REGIONS } from '../types';

interface ContextPanelProps {
  context: ChatContext;
  onContextChange: (context: ChatContext) => void;
}

function ContextPanel({ context, onContextChange }: ContextPanelProps) {
  const handleRegionChange = (regionId: number) => {
    onContextChange({ ...context, regionId });
  };

  return (
    <div className="context-panel">
      <h3>Context</h3>

      <div className="context-section">
        <label>Region</label>
        <select
          value={context.regionId}
          onChange={(e) => handleRegionChange(Number(e.target.value))}
        >
          {MAJOR_REGIONS.map(region => (
            <option key={region.region_id} value={region.region_id}>
              {region.name}
            </option>
          ))}
        </select>
      </div>

      <div className="context-section">
        <label>Character</label>
        <input
          type="text"
          placeholder="Not authenticated"
          disabled
          value={context.characterId || ''}
        />
        <small>EVE SSO login coming soon</small>
      </div>

      <div className="context-info">
        <h4>Quick Tips</h4>
        <ul>
          <li>Ask about market prices</li>
          <li>Request production costs</li>
          <li>Check war room intel</li>
          <li>Create shopping lists</li>
          <li>Find trade routes</li>
        </ul>
      </div>
    </div>
  );
}

export default ContextPanel;
