import { useState, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Package, Download, AlertCircle, CheckCircle, AlertTriangle, RefreshCw } from 'lucide-react';
import { Link } from 'react-router-dom';
import { api } from '../api';
import { formatISK, formatQuantity } from '../utils/format';

interface Bookmark {
  id: number;
  type_id: number;
  item_name: string;
}

interface Material {
  type_id: number;
  name: string;
  base_quantity: number;
  adjusted_quantity: number;
  prices_by_region: Record<string, number>;
}

interface ProductionData {
  materials: Material[];
}

interface VolumeData {
  volumes_by_region: Record<string, {
    sell_volume: number;
    lowest_sell: number | null;
  }>;
}

interface AggregatedMaterial {
  type_id: number;
  name: string;
  total_quantity: number;
  from_items: string[];
  prices_by_region: Record<string, number>;
  volumes_by_region: Record<string, number>;
}

const REGION_NAMES: Record<string, string> = {
  the_forge: 'Jita',
  domain: 'Amarr',
  heimatar: 'Rens',
  sinq_laison: 'Dodixie',
  metropolis: 'Hek',
};

const CORP_ID = 98785281; // MINDI

function AvailabilityBadge({ available, needed }: { available: number; needed: number }) {
  if (available === 0) {
    return <AlertCircle size={14} className="availability-low" />;
  }
  const ratio = available / needed;
  if (ratio >= 10) {
    return <CheckCircle size={14} className="availability-high" />;
  }
  if (ratio >= 1) {
    return <AlertTriangle size={14} className="availability-medium" />;
  }
  return <AlertCircle size={14} className="availability-low" />;
}

export default function MaterialsOverview() {
  const [selectedRegion, setSelectedRegion] = useState('the_forge');

  // Fetch bookmarks
  const { data: bookmarks, isLoading: bookmarksLoading } = useQuery<Bookmark[]>({
    queryKey: ['bookmarks', CORP_ID],
    queryFn: async () => {
      const response = await api.get('/api/bookmarks', {
        params: { corporation_id: CORP_ID }
      });
      return response.data;
    },
  });

  // Fetch production data for each bookmark
  const { data: productionDataMap, isLoading: productionLoading, refetch: refetchProduction } = useQuery<Record<number, ProductionData>>({
    queryKey: ['bookmarks-production', bookmarks?.map(b => b.type_id).join(',')],
    queryFn: async () => {
      if (!bookmarks || bookmarks.length === 0) return {};
      const result: Record<number, ProductionData> = {};

      await Promise.all(
        bookmarks.map(async (bookmark) => {
          try {
            const response = await api.get(`/api/production/optimize/${bookmark.type_id}`, {
              params: { me: 10 }
            });
            result[bookmark.type_id] = response.data;
          } catch {
            // Ignore items without blueprints
          }
        })
      );

      return result;
    },
    enabled: !!bookmarks && bookmarks.length > 0,
    staleTime: 60000,
  });

  // Aggregate materials from all bookmarks
  const aggregatedMaterials = useMemo(() => {
    if (!productionDataMap || !bookmarks) return [];

    const materialMap: Record<number, AggregatedMaterial> = {};

    for (const bookmark of bookmarks) {
      const production = productionDataMap[bookmark.type_id];
      if (!production?.materials) continue;

      for (const mat of production.materials) {
        if (!materialMap[mat.type_id]) {
          materialMap[mat.type_id] = {
            type_id: mat.type_id,
            name: mat.name,
            total_quantity: 0,
            from_items: [],
            prices_by_region: { ...mat.prices_by_region },
            volumes_by_region: {},
          };
        }

        materialMap[mat.type_id].total_quantity += mat.adjusted_quantity;
        if (!materialMap[mat.type_id].from_items.includes(bookmark.item_name)) {
          materialMap[mat.type_id].from_items.push(bookmark.item_name);
        }
      }
    }

    return Object.values(materialMap).sort((a, b) => {
      const costA = (a.prices_by_region[selectedRegion] || 0) * a.total_quantity;
      const costB = (b.prices_by_region[selectedRegion] || 0) * b.total_quantity;
      return costB - costA;
    });
  }, [productionDataMap, bookmarks, selectedRegion]);

  // Fetch volume data for aggregated materials
  const materialTypeIds = aggregatedMaterials.map(m => m.type_id);
  const { data: volumeDataMap } = useQuery<Record<number, VolumeData>>({
    queryKey: ['materials-volumes-overview', materialTypeIds.join(',')],
    queryFn: async () => {
      if (aggregatedMaterials.length === 0) return {};
      const volumes: Record<number, VolumeData> = {};

      await Promise.all(
        aggregatedMaterials.map(async (mat) => {
          try {
            const response = await api.get(`/api/materials/${mat.type_id}/volumes`);
            volumes[mat.type_id] = response.data;
          } catch {
            // Ignore errors
          }
        })
      );

      return volumes;
    },
    enabled: aggregatedMaterials.length > 0,
    staleTime: 60000,
  });

  // Calculate totals
  const totalCost = useMemo(() => {
    return aggregatedMaterials.reduce((sum, mat) => {
      const price = mat.prices_by_region[selectedRegion] || 0;
      return sum + (price * mat.total_quantity);
    }, 0);
  }, [aggregatedMaterials, selectedRegion]);

  // Export to clipboard (EVE multibuy format)
  const handleExport = () => {
    const lines = aggregatedMaterials.map(mat => `${mat.name} ${mat.total_quantity}`);
    navigator.clipboard.writeText(lines.join('\n'));
    alert('Copied to clipboard in EVE Multibuy format!');
  };

  const isLoading = bookmarksLoading || productionLoading;

  if (isLoading) {
    return (
      <div className="loading">
        <div className="spinner"></div>
        Loading materials from bookmarks...
      </div>
    );
  }

  if (!bookmarks?.length) {
    return (
      <div className="empty-state">
        <Package size={48} />
        <h3>No Bookmarks Yet</h3>
        <p className="neutral">Bookmark items in the Market Scanner to see aggregated materials here.</p>
        <Link to="/" className="btn btn-primary">Go to Market Scanner</Link>
      </div>
    );
  }

  if (aggregatedMaterials.length === 0) {
    return (
      <div className="empty-state">
        <Package size={48} />
        <h3>No Materials Found</h3>
        <p className="neutral">Your bookmarked items don't have blueprint data.</p>
      </div>
    );
  }

  return (
    <div>
      <div className="page-header">
        <div>
          <h1>Materials Overview</h1>
          <p>Aggregated materials from {bookmarks.length} bookmarked items</p>
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          <button className="btn btn-secondary" onClick={() => refetchProduction()}>
            <RefreshCw size={16} /> Refresh
          </button>
          <button className="btn btn-primary" onClick={handleExport}>
            <Download size={16} /> Export Multibuy
          </button>
        </div>
      </div>

      {/* Summary Stats */}
      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-label">Total Materials</div>
          <div className="stat-value">{aggregatedMaterials.length}</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">From Items</div>
          <div className="stat-value">{bookmarks.length}</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Total Cost ({REGION_NAMES[selectedRegion]})</div>
          <div className="stat-value isk">{formatISK(totalCost)}</div>
        </div>
      </div>

      {/* Region Selector */}
      <div className="card" style={{ marginBottom: 16 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
          <span className="neutral">Region:</span>
          <div className="filter-tabs">
            {Object.entries(REGION_NAMES).map(([key, name]) => (
              <button
                key={key}
                className={`tab ${selectedRegion === key ? 'active' : ''}`}
                onClick={() => setSelectedRegion(key)}
              >
                {name}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Materials Table */}
      <div className="card">
        <div className="table-container">
          <table>
            <thead>
              <tr>
                <th>Material</th>
                <th>Availability</th>
                <th>Total Needed</th>
                <th>Unit Price</th>
                <th>Total Cost</th>
                <th>Used In</th>
              </tr>
            </thead>
            <tbody>
              {aggregatedMaterials.map((mat) => {
                const unitPrice = mat.prices_by_region[selectedRegion] || 0;
                const totalMatCost = unitPrice * mat.total_quantity;
                const volume = volumeDataMap?.[mat.type_id]?.volumes_by_region?.[selectedRegion]?.sell_volume || 0;

                return (
                  <tr key={mat.type_id}>
                    <td>
                      <Link to={`/item/${mat.type_id}`} className="material-link">
                        {mat.name}
                      </Link>
                    </td>
                    <td>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                        <AvailabilityBadge available={volume} needed={mat.total_quantity} />
                        <span className="neutral">{formatQuantity(volume)}</span>
                      </div>
                    </td>
                    <td>{formatQuantity(mat.total_quantity)}</td>
                    <td className="isk">{formatISK(unitPrice, false)}</td>
                    <td className="isk">{formatISK(totalMatCost)}</td>
                    <td>
                      <span className="neutral" title={mat.from_items.join(', ')}>
                        {mat.from_items.length} item{mat.from_items.length !== 1 ? 's' : ''}
                      </span>
                    </td>
                  </tr>
                );
              })}
              <tr style={{ fontWeight: 'bold', background: 'var(--bg-dark)' }}>
                <td colSpan={4}>Total</td>
                <td className="isk positive">{formatISK(totalCost)}</td>
                <td></td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
