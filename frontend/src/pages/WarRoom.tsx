import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { Swords, Shield, Target, AlertTriangle, MapPin, TrendingUp, RefreshCw } from 'lucide-react';
import {
  getWarDemand,
  getWarHeatmap,
  getWarCampaigns,
  getFWHotspots,
  getWarSummary,
  getTopShips
} from '../api';

const REGIONS: Record<number, string> = {
  10000002: 'The Forge (Jita)',
  10000043: 'Domain (Amarr)',
  10000030: 'Heimatar (Rens)',
  10000032: 'Sinq Laison (Dodixie)',
  10000042: 'Metropolis (Hek)',
};

interface DemandData {
  region_id: number;
  days: number;
  ships_lost: Array<{
    type_id: number;
    name: string;
    quantity: number;
    market_stock: number;
    gap: number;
  }>;
  items_lost: Array<{
    type_id: number;
    name: string;
    quantity: number;
    market_stock: number;
    gap: number;
  }>;
  market_gaps: Array<{
    type_id: number;
    name: string;
    quantity: number;
    market_stock: number;
    gap: number;
  }>;
}

interface Campaign {
  campaign_id: number;
  event_type: string;
  solar_system_id: number;
  solar_system_name: string;
  region_name: string;
  defender_id: number;
  defender_name: string;
  attacker_score: number;
  defender_score: number;
  start_time: string;
  hours_until_start?: number;
}

interface FWHotspot {
  solar_system_id: number;
  solar_system_name: string;
  region_name: string;
  owner_faction_name: string;
  occupier_faction_name: string;
  contested_percent: number;
}

interface HeatmapSystem {
  system_id: number;
  name: string;
  region_id: number;
  region: string;
  security: number;
  x: number;
  z: number;
  kills: number;
}

export default function WarRoom() {
  const [regionId, setRegionId] = useState(10000002);
  const [days, setDays] = useState(7);

  // Queries
  const demandQuery = useQuery({
    queryKey: ['warDemand', regionId, days],
    queryFn: () => getWarDemand(regionId, days),
    staleTime: 0,
    refetchInterval: 5 * 60 * 1000, // 5 minutes
  });

  const campaignsQuery = useQuery({
    queryKey: ['warCampaigns'],
    queryFn: () => getWarCampaigns(48),
    staleTime: 60 * 1000,
    refetchInterval: 5 * 60 * 1000,
  });

  const fwQuery = useQuery({
    queryKey: ['fwHotspots'],
    queryFn: () => getFWHotspots(50),
    staleTime: 60 * 1000,
    refetchInterval: 5 * 60 * 1000,
  });

  const heatmapQuery = useQuery({
    queryKey: ['warHeatmap', days],
    queryFn: () => getWarHeatmap(days, 5),
    staleTime: 0,
    refetchInterval: 5 * 60 * 1000,
  });

  const summaryQuery = useQuery({
    queryKey: ['warSummary', days],
    queryFn: () => getWarSummary(days),
    staleTime: 0,
    refetchInterval: 5 * 60 * 1000,
  });

  const topShipsQuery = useQuery({
    queryKey: ['topShips', days],
    queryFn: () => getTopShips(days, 10),
    staleTime: 0,
    refetchInterval: 5 * 60 * 1000,
  });

  const demand = demandQuery.data as DemandData | undefined;
  const campaigns = campaignsQuery.data?.campaigns as Campaign[] | undefined;
  const fwHotspots = fwQuery.data?.hotspots as FWHotspot[] | undefined;
  const heatmapSystems = heatmapQuery.data?.systems as HeatmapSystem[] | undefined;
  const regionalSummary = summaryQuery.data?.regions as Array<{
    region_id: number;
    region_name: string;
    active_systems: number;
    total_kills: number;
    total_value: number;
  }> | undefined;
  const topShips = topShipsQuery.data?.ships as Array<{
    type_id: number;
    name: string;
    group: string;
    quantity: number;
    value: number;
  }> | undefined;

  const isLoading = demandQuery.isLoading || campaignsQuery.isLoading || fwQuery.isLoading;

  const refreshAll = () => {
    demandQuery.refetch();
    campaignsQuery.refetch();
    fwQuery.refetch();
    heatmapQuery.refetch();
    summaryQuery.refetch();
    topShipsQuery.refetch();
  };

  return (
    <div className="page-container">
      <div className="page-header">
        <div>
          <h1 className="page-title">
            <Swords size={28} />
            War Room
          </h1>
          <p className="page-subtitle">Combat analysis and demand forecasting</p>
        </div>
        <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
          <select
            value={regionId}
            onChange={(e) => setRegionId(Number(e.target.value))}
            className="input"
            style={{ minWidth: '180px' }}
          >
            {Object.entries(REGIONS).map(([id, name]) => (
              <option key={id} value={id}>{name}</option>
            ))}
          </select>
          <select
            value={days}
            onChange={(e) => setDays(Number(e.target.value))}
            className="input"
          >
            <option value={1}>24 hours</option>
            <option value={3}>3 days</option>
            <option value={7}>7 days</option>
            <option value={14}>14 days</option>
          </select>
          <button className="btn btn-secondary" onClick={refreshAll}>
            <RefreshCw size={16} />
            Refresh
          </button>
        </div>
      </div>

      {isLoading ? (
        <div className="loading-container">
          <div className="loading-spinner" />
          <p>Loading war data...</p>
        </div>
      ) : (
        <div className="grid-container">
          {/* Row 1: Key Metrics */}
          <div className="card" style={{ gridColumn: 'span 4' }}>
            <h3 className="card-title">
              <TrendingUp size={18} />
              Galaxy Combat Summary ({days} days)
            </h3>
            <div className="stats-grid">
              {regionalSummary?.slice(0, 5).map((region) => (
                <div key={region.region_id} className="stat-card">
                  <span className="stat-label">{region.region_name}</span>
                  <span className="stat-value">{region.total_kills.toLocaleString()}</span>
                  <span className="stat-detail">{region.active_systems} systems</span>
                </div>
              ))}
            </div>
          </div>

          {/* Row 2: Ships Destroyed, Items Destroyed, Market Gaps */}
          <div className="card">
            <h3 className="card-title">
              <Target size={18} />
              Ships Destroyed
            </h3>
            <div className="scrollable-list" style={{ maxHeight: '300px' }}>
              {demand?.ships_lost?.slice(0, 15).map((ship) => (
                <Link key={ship.type_id} to={`/item/${ship.type_id}`} className="list-item clickable">
                  <span className="item-name">{ship.name}</span>
                  <span className="item-value">{ship.quantity.toLocaleString()}</span>
                </Link>
              ))}
              {(!demand?.ships_lost || demand.ships_lost.length === 0) && (
                <div className="empty-state">No ship loss data available</div>
              )}
            </div>
          </div>

          <div className="card">
            <h3 className="card-title">
              <Target size={18} />
              Top Ships Galaxy-Wide
            </h3>
            <div className="scrollable-list" style={{ maxHeight: '300px' }}>
              {topShips?.map((ship) => (
                <Link key={ship.type_id} to={`/item/${ship.type_id}`} className="list-item clickable">
                  <div>
                    <span className="item-name">{ship.name}</span>
                    <span className="item-detail">{ship.group}</span>
                  </div>
                  <span className="item-value">{ship.quantity.toLocaleString()}</span>
                </Link>
              ))}
              {(!topShips || topShips.length === 0) && (
                <div className="empty-state">No data available</div>
              )}
            </div>
          </div>

          <div className="card">
            <h3 className="card-title" style={{ color: 'var(--color-error)' }}>
              <AlertTriangle size={18} />
              Market Gaps
            </h3>
            <div className="scrollable-list" style={{ maxHeight: '300px' }}>
              {demand?.market_gaps?.length ? (
                demand.market_gaps.map((item) => (
                  <Link key={item.type_id} to={`/item/${item.type_id}`} className="list-item clickable">
                    <div>
                      <span className="item-name">{item.name}</span>
                      <span className="item-detail">
                        Lost: {item.quantity.toLocaleString()} | Stock: {item.market_stock.toLocaleString()}
                      </span>
                    </div>
                    <span className="item-value negative">-{item.gap.toLocaleString()}</span>
                  </Link>
                ))
              ) : (
                <div className="empty-state">No significant gaps detected</div>
              )}
            </div>
          </div>

          {/* Row 3: Sovereignty Campaigns */}
          <div className="card" style={{ gridColumn: 'span 2' }}>
            <h3 className="card-title">
              <Shield size={18} />
              Upcoming Sovereignty Battles
            </h3>
            <div className="scrollable-list" style={{ maxHeight: '280px' }}>
              {campaigns && campaigns.length > 0 ? (
                campaigns.slice(0, 8).map((c) => (
                  <div key={c.campaign_id} className="campaign-item">
                    <div className="campaign-header">
                      <span className="campaign-system">{c.solar_system_name || `System ${c.solar_system_id}`}</span>
                      <span className="campaign-region">{c.region_name || 'Unknown Region'}</span>
                    </div>
                    <div className="campaign-details">
                      <span className="campaign-type">{c.event_type}</span>
                      <span className="campaign-defender">Defender: {c.defender_name || 'Unknown'}</span>
                    </div>
                    <div className="campaign-time">
                      {new Date(c.start_time).toLocaleString()}
                      {c.hours_until_start !== undefined && (
                        <span className="time-until"> ({c.hours_until_start.toFixed(1)}h)</span>
                      )}
                    </div>
                  </div>
                ))
              ) : (
                <div className="empty-state">No upcoming campaigns in the next 48 hours</div>
              )}
            </div>
          </div>

          {/* Row 3: FW Hotspots */}
          <div className="card" style={{ gridColumn: 'span 2' }}>
            <h3 className="card-title">
              <Swords size={18} />
              Faction Warfare Hotspots
            </h3>
            <div className="scrollable-list" style={{ maxHeight: '280px' }}>
              {fwHotspots && fwHotspots.length > 0 ? (
                fwHotspots.slice(0, 10).map((h) => (
                  <div key={h.solar_system_id} className="fw-item">
                    <div className="fw-header">
                      <span className="fw-system">{h.solar_system_name}</span>
                      <span
                        className="fw-contested"
                        style={{
                          color: h.contested_percent >= 90 ? 'var(--color-error)' :
                                 h.contested_percent >= 70 ? 'var(--color-warning)' :
                                 'var(--color-success)'
                        }}
                      >
                        {h.contested_percent.toFixed(1)}%
                      </span>
                    </div>
                    <div className="fw-factions">
                      {h.owner_faction_name} vs {h.occupier_faction_name}
                    </div>
                  </div>
                ))
              ) : (
                <div className="empty-state">No active FW hotspots</div>
              )}
            </div>
          </div>

          {/* Row 4: Combat Hotspots Heatmap */}
          <div className="card" style={{ gridColumn: 'span 4' }}>
            <h3 className="card-title">
              <MapPin size={18} />
              Combat Hotspots (Top Systems)
            </h3>
            <div className="hotspot-grid">
              {heatmapSystems?.slice(0, 15).map((s) => (
                <div
                  key={s.system_id}
                  className="hotspot-item"
                  style={{
                    backgroundColor: `rgba(239, 68, 68, ${Math.min(s.kills / 200, 0.8)})`
                  }}
                >
                  <span className="hotspot-name">{s.name}</span>
                  <span className="hotspot-kills">{s.kills} kills</span>
                  <span className="hotspot-region">{s.region}</span>
                  <span className="hotspot-security" style={{
                    color: s.security >= 0.5 ? 'var(--color-success)' :
                           s.security > 0 ? 'var(--color-warning)' :
                           'var(--color-error)'
                  }}>
                    {s.security.toFixed(1)}
                  </span>
                </div>
              ))}
              {(!heatmapSystems || heatmapSystems.length === 0) && (
                <div className="empty-state">No combat data available</div>
              )}
            </div>
          </div>
        </div>
      )}

      <style>{`
        .grid-container {
          display: grid;
          grid-template-columns: repeat(4, 1fr);
          gap: 16px;
        }

        .stats-grid {
          display: flex;
          gap: 16px;
          flex-wrap: wrap;
        }

        .stat-card {
          display: flex;
          flex-direction: column;
          padding: 12px 16px;
          background: var(--bg-secondary);
          border-radius: 8px;
          min-width: 140px;
        }

        .stat-label {
          font-size: 12px;
          color: var(--text-secondary);
        }

        .stat-value {
          font-size: 24px;
          font-weight: 600;
          color: var(--text-primary);
        }

        .stat-detail {
          font-size: 11px;
          color: var(--text-tertiary);
        }

        .scrollable-list {
          overflow-y: auto;
        }

        .list-item {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 8px 0;
          border-bottom: 1px solid var(--border-color);
        }

        .list-item:last-child {
          border-bottom: none;
        }

        .item-name {
          font-weight: 500;
        }

        .item-detail {
          display: block;
          font-size: 11px;
          color: var(--text-secondary);
        }

        .item-value {
          font-family: monospace;
          font-weight: 600;
        }

        .item-value.negative {
          color: var(--color-error);
        }

        .campaign-item, .fw-item {
          padding: 12px;
          margin-bottom: 8px;
          background: var(--bg-secondary);
          border-radius: 6px;
        }

        .campaign-header, .fw-header {
          display: flex;
          justify-content: space-between;
          margin-bottom: 4px;
        }

        .campaign-system, .fw-system {
          font-weight: 600;
        }

        .campaign-region {
          font-size: 12px;
          color: var(--text-secondary);
        }

        .campaign-details {
          display: flex;
          gap: 12px;
          font-size: 12px;
          color: var(--text-secondary);
        }

        .campaign-type {
          background: var(--accent-blue);
          color: white;
          padding: 2px 6px;
          border-radius: 4px;
          font-size: 10px;
        }

        .campaign-time {
          margin-top: 8px;
          font-size: 12px;
        }

        .time-until {
          color: var(--color-warning);
          font-weight: 500;
        }

        .fw-contested {
          font-weight: 700;
          font-size: 14px;
        }

        .fw-factions {
          font-size: 11px;
          color: var(--text-secondary);
        }

        .hotspot-grid {
          display: grid;
          grid-template-columns: repeat(5, 1fr);
          gap: 8px;
        }

        .hotspot-item {
          padding: 10px;
          border-radius: 6px;
          color: white;
          text-shadow: 0 1px 2px rgba(0,0,0,0.5);
        }

        .hotspot-name {
          display: block;
          font-weight: 600;
          font-size: 13px;
        }

        .hotspot-kills {
          display: block;
          font-size: 14px;
          font-weight: 700;
        }

        .hotspot-region {
          display: block;
          font-size: 10px;
          opacity: 0.8;
        }

        .hotspot-security {
          display: block;
          font-size: 11px;
          font-weight: 600;
        }

        .empty-state {
          padding: 20px;
          text-align: center;
          color: var(--text-secondary);
          font-style: italic;
        }

        .loading-container {
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          padding: 60px;
          gap: 16px;
        }

        .loading-spinner {
          width: 40px;
          height: 40px;
          border: 3px solid var(--border-color);
          border-top-color: var(--accent-blue);
          border-radius: 50%;
          animation: spin 1s linear infinite;
        }

        @keyframes spin {
          to { transform: rotate(360deg); }
        }

        .list-item.clickable {
          text-decoration: none;
          color: inherit;
          transition: background 0.15s;
        }

        .list-item.clickable:hover {
          background: var(--bg-tertiary);
        }
      `}</style>
    </div>
  );
}
