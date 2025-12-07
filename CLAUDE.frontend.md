# Frontend Development Guide

> **Back to:** [CLAUDE.md](CLAUDE.md)

---

## Quick Start

```bash
cd /home/cytrex/eve_copilot/frontend

# Development (with hot reload)
npm run dev -- --host 0.0.0.0

# Access: http://localhost:5173 or http://77.24.99.81:5173

# Production build
npm run build
# Output in dist/
```

---

## Tech Stack

| Technology | Purpose |
|------------|---------|
| React 18 | UI Framework |
| TypeScript | Type safety |
| Vite | Build tool, dev server |
| React Router | Client-side routing |
| TanStack Query | Server state management |
| Axios | HTTP client |
| Lucide React | Icons |

---

## Project Structure

```
frontend/
├── src/
│   ├── App.tsx              # Root component, routes, navigation
│   ├── App.css              # Global styles
│   ├── api.ts               # API client, types, functions
│   ├── main.tsx             # Entry point
│   ├── index.css            # Base CSS
│   │
│   ├── pages/               # Page components
│   │   ├── MarketScanner.tsx
│   │   ├── ArbitrageFinder.tsx
│   │   ├── ProductionPlanner.tsx
│   │   ├── ShoppingPlanner.tsx
│   │   ├── Bookmarks.tsx
│   │   ├── MaterialsOverview.tsx
│   │   ├── ItemDetail.tsx
│   │   └── WarRoom.tsx
│   │
│   ├── components/          # Reusable components
│   │   ├── CollapsiblePanel.tsx
│   │   ├── CombatStatsPanel.tsx
│   │   ├── ConflictAlert.tsx
│   │   ├── AddToListModal.tsx
│   │   └── BookmarkButton.tsx
│   │
│   └── utils/
│       └── format.ts        # Formatting utilities
│
├── public/                  # Static assets
├── index.html               # HTML template
├── vite.config.ts           # Vite configuration
├── tsconfig.json            # TypeScript configuration
└── package.json             # Dependencies
```

---

## Pages

| Page | Route | Purpose |
|------|-------|---------|
| Market Scanner | `/` | Find manufacturing opportunities |
| Item Detail | `/item/:typeId` | Detailed item view with combat stats |
| Arbitrage Finder | `/arbitrage` | Find trade opportunities |
| Production Planner | `/production` | Plan production runs |
| Bookmarks | `/bookmarks` | Manage saved items |
| Materials | `/materials` | Material availability overview |
| Shopping | `/shopping` | Shopping list management |
| War Room | `/war-room` | Combat intelligence dashboard |

---

## API Client

### Configuration

```typescript
// src/api.ts
import axios from 'axios';

const API_BASE = '';  // Uses Vite proxy in development

export const api = axios.create({
  baseURL: API_BASE,
  timeout: 300000,  // 5 minutes for long scans
});
```

### Available Functions

```typescript
// Market
runMarketScan(params)          // Scan for opportunities
getItemArbitrage(typeId)       // Find arbitrage
compareRegionPrices(typeId)    // Compare prices across regions
optimizeProduction(typeId, me) // Production optimization

// Search
searchItems(query)             // Search items by name

// War Room
getWarLosses(regionId, days)   // Combat losses
getWarDemand(regionId, days)   // Demand analysis
getWarHeatmap(days, minKills)  // Galaxy heatmap
getWarCampaigns(hours)         // Sovereignty campaigns
getFWHotspots(minContested)    // FW hotspots
getWarDoctrines(regionId)      // Detected doctrines
getWarConflicts(days)          // Alliance conflicts
getItemCombatStats(typeId)     // Item combat statistics
```

### Usage Example

```typescript
import { useQuery } from '@tanstack/react-query';
import { optimizeProduction } from '../api';

function MyComponent({ typeId }: { typeId: number }) {
  const { data, isLoading, error } = useQuery({
    queryKey: ['production', typeId],
    queryFn: () => optimizeProduction(typeId, 10),
  });

  if (isLoading) return <div>Loading...</div>;
  if (error) return <div>Error: {error.message}</div>;

  return <div>{data.item_name}</div>;
}
```

---

## Components

### CollapsiblePanel

Expandable content section with header.

```typescript
import CollapsiblePanel from '../components/CollapsiblePanel';

<CollapsiblePanel title="Production Details" defaultOpen={true}>
  <div>Content here</div>
</CollapsiblePanel>
```

### CombatStatsPanel

Display combat statistics for an item.

```typescript
import CombatStatsPanel from '../components/CombatStatsPanel';

<CombatStatsPanel typeId={648} />
```

### ConflictAlert

Warning for dangerous routes.

```typescript
import ConflictAlert from '../components/ConflictAlert';

<ConflictAlert systemId={30000142} />
```

### AddToListModal

Modal to add items to shopping lists.

```typescript
import AddToListModal from '../components/AddToListModal';

<AddToListModal
  isOpen={showModal}
  onClose={() => setShowModal(false)}
  typeId={648}
  typeName="Badger"
  quantity={1}
/>
```

---

## Styling Patterns

### CSS Classes

```css
/* Common patterns in App.css */

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}

.card {
  background: var(--card-bg);
  border-radius: 8px;
  padding: 16px;
  border: 1px solid var(--border-color);
}

.table {
  width: 100%;
  border-collapse: collapse;
}

.table th,
.table td {
  padding: 12px;
  text-align: left;
  border-bottom: 1px solid var(--border-color);
}

.btn {
  padding: 8px 16px;
  border-radius: 4px;
  cursor: pointer;
  transition: background 0.2s;
}

.btn-primary {
  background: var(--primary-color);
  color: white;
  border: none;
}
```

### EVE Item Icons

```typescript
// Use EVE Image Server CDN
const iconUrl = `https://images.evetech.net/types/${typeId}/icon?size=64`;
const renderUrl = `https://images.evetech.net/types/${typeId}/render?size=128`;

<img src={iconUrl} alt={itemName} />
```

---

## Critical Patterns

### 1. React Cannot Render Objects as Strings

```typescript
// WRONG - causes browser freeze
{items.map((item: any) => <span>{item}</span>)}
// item might be { name: "...", ... } not a string

// CORRECT - access specific fields
{items.map((item: any) => <span>{item.name}</span>)}
```

### 2. Always Handle Loading States

```typescript
const { data, isLoading, error } = useQuery({...});

if (isLoading) return <LoadingSpinner />;
if (error) return <ErrorMessage error={error} />;
if (!data) return <EmptyState />;

return <DataDisplay data={data} />;
```

### 3. Use TypeScript Interfaces

```typescript
interface Item {
  type_id: number;
  name: string;
  quantity: number;
  price: number | null;
}

function ItemRow({ item }: { item: Item }) {
  return (
    <tr>
      <td>{item.name}</td>
      <td>{item.quantity}</td>
      <td>{item.price?.toLocaleString() ?? 'N/A'}</td>
    </tr>
  );
}
```

### 4. Handle Null/Undefined Prices

```typescript
// Prices might be null from API
const price = item.price ?? 0;
const formattedPrice = price > 0
  ? price.toLocaleString() + ' ISK'
  : 'No data';
```

### 5. Format Large Numbers

```typescript
// utils/format.ts
export function formatISK(value: number): string {
  if (value >= 1_000_000_000) {
    return (value / 1_000_000_000).toFixed(2) + 'B';
  }
  if (value >= 1_000_000) {
    return (value / 1_000_000).toFixed(2) + 'M';
  }
  if (value >= 1_000) {
    return (value / 1_000).toFixed(2) + 'K';
  }
  return value.toFixed(0);
}

export function formatPercent(value: number): string {
  return (value * 100).toFixed(1) + '%';
}
```

---

## Adding a New Page

### 1. Create Page Component

```typescript
// src/pages/NewPage.tsx
import { useQuery } from '@tanstack/react-query';
import { api } from '../api';

function NewPage() {
  const { data, isLoading } = useQuery({
    queryKey: ['newData'],
    queryFn: async () => {
      const response = await api.get('/api/new-endpoint');
      return response.data;
    },
  });

  if (isLoading) return <div className="loading">Loading...</div>;

  return (
    <div className="page">
      <div className="page-header">
        <h1>New Page</h1>
      </div>
      <div className="card">
        {/* Content */}
      </div>
    </div>
  );
}

export default NewPage;
```

### 2. Add Route in App.tsx

```typescript
import NewPage from './pages/NewPage';

<Routes>
  {/* existing routes */}
  <Route path="/new-page" element={<NewPage />} />
</Routes>
```

### 3. Add Navigation Link

```typescript
<li>
  <NavLink to="/new-page" className={({ isActive }) => isActive ? 'active' : ''}>
    <SomeIcon size={20} />
    <span>New Page</span>
  </NavLink>
</li>
```

---

## Adding a New Component

```typescript
// src/components/NewComponent.tsx
import { useState } from 'react';

interface NewComponentProps {
  title: string;
  onAction?: () => void;
}

function NewComponent({ title, onAction }: NewComponentProps) {
  const [isActive, setIsActive] = useState(false);

  return (
    <div className={`component ${isActive ? 'active' : ''}`}>
      <h3>{title}</h3>
      {onAction && (
        <button onClick={onAction}>Action</button>
      )}
    </div>
  );
}

export default NewComponent;
```

---

## TanStack Query Patterns

### Basic Query

```typescript
const { data, isLoading, error, refetch } = useQuery({
  queryKey: ['items', typeId],
  queryFn: () => fetchItems(typeId),
  staleTime: 60000,  // 1 minute
});
```

### Query with Dependencies

```typescript
const { data: items } = useQuery({
  queryKey: ['items'],
  queryFn: fetchItems,
});

const { data: details } = useQuery({
  queryKey: ['details', items?.[0]?.id],
  queryFn: () => fetchDetails(items![0].id),
  enabled: !!items?.length,  // Only run when items exist
});
```

### Mutation

```typescript
const mutation = useMutation({
  mutationFn: (data: CreateItemRequest) => api.post('/api/items', data),
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: ['items'] });
  },
});

// Usage
mutation.mutate({ name: 'New Item', quantity: 1 });
```

---

## Vite Configuration

```typescript
// vite.config.ts
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0',
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/mcp': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
});
```

---

## Troubleshooting

### Frontend won't start

```bash
# Check port
lsof -i :5173

# Reinstall dependencies
cd frontend
rm -rf node_modules
npm install

# Start with verbose
npm run dev -- --host 0.0.0.0 --debug
```

### API calls fail

1. Check backend is running on port 8000
2. Check Vite proxy configuration
3. Look at browser DevTools Network tab
4. Check CORS if accessing directly

### Build fails

```bash
# Type check
npx tsc --noEmit

# Fix common issues
npm run build 2>&1 | head -50
```

### Hot reload not working

- Save file again
- Check for TypeScript errors
- Restart Vite dev server

---

## Dependencies

```json
{
  "dependencies": {
    "react": "^18.x",
    "react-dom": "^18.x",
    "react-router-dom": "^6.x",
    "@tanstack/react-query": "^5.x",
    "axios": "^1.x",
    "lucide-react": "^0.x"
  },
  "devDependencies": {
    "typescript": "^5.x",
    "vite": "^5.x",
    "@vitejs/plugin-react": "^4.x",
    "@types/react": "^18.x",
    "@types/react-dom": "^18.x"
  }
}
```

---

**Last Updated:** 2025-12-07
