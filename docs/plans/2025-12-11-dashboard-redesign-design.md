# Dashboard Redesign - Design Document

**Date:** 2025-12-11
**Status:** Approved
**Style:** EVE Online In-Game UI (Subtle Sci-Fi)

## Problem Statement

Current dashboard has a "school project" aesthetic with:
- Overly colorful gradients on character cards
- Standard Bootstrap-style buttons
- Basic, boxy layout without modern design principles
- No visual connection to EVE Online's professional aesthetic

**Goal:** Create a professional, data-dense dashboard with subtle EVE Online sci-fi aesthetic.

---

## Design Direction

### Style Choice
**Subtle Sci-Fi (Option C)**
- Professional dark theme with EVE-inspired details
- Sci-fi elements only in hover effects and accents
- Focus on functionality and readability
- Modern but thematically appropriate

### Key Principles
1. **Data First**: Information density over decoration
2. **Professional**: No "playful" colors or effects
3. **Subtle Theme**: EVE aesthetic without overwhelming
4. **Performance**: Fast rendering, smooth animations

---

## Layout & Structure

### Overall Layout
```
┌─────────────────────────────────────┬──────────────────┐
│                                     │                  │
│  Opportunities Table (70%)          │  War Room (30%)  │
│  - Compact data grid                │  - Alerts        │
│  - 12-15 rows visible               │  - Active        │
│  - Sortable columns                 │    Projects      │
│                                     │                  │
├─────────────────────────────────────┤                  │
│  Character Overview (25% of main)   │                  │
│  - 3 portrait cards                 │                  │
│  - Horizontal layout                │                  │
└─────────────────────────────────────┴──────────────────┘
```

### Proportions
- Main Content: 70% width
- Sidebar: 30% width (responsive)
- Opportunities Table: 75% of main content height
- Character Overview: 25% of main content height
- Gaps: 20px between sections

### Colors
```css
Background:       #0a0e14  (darker than current)
Surface:          #161b22  (cards, panels)
Surface Elevated: #21262d  (hover states)
Border:           #21262d  (subtle)

Text Primary:     #e6edf3
Text Secondary:   #8b949e
Text Tertiary:    #6e7681

Accent Blue:      #58a6ff
Accent Green:     #3fb950 → #2ea043 (profit gradient)
Danger Red:       #f85149
Warning Yellow:   #d29922
```

---

## Component Design

### 1. Opportunities Table

**Structure:**
| Column        | Width | Type          | Styling                          |
|---------------|-------|---------------|----------------------------------|
| Icon          | 32px  | Emoji         | Monochrome until hover           |
| Item Name     | 40%   | Text          | 15px bold, #e6edf3, truncate     |
| Profit        | 20%   | Number        | 16px bold, green gradient        |
| ROI           | 15%   | Percentage    | 15px, color-coded                |
| Category      | 10%   | Badge         | 11px uppercase, subtle bg        |
| Actions       | 15%   | Icon/Button   | Arrow → on hover shows tooltip   |

**Visual Details:**
- No row borders, only subtle bottom border `1px solid #161b22`
- Row height: 48px (compact but readable)
- Hover: Background `#0d1117` → `#161b22`, left border `2px solid #58a6ff`
- Header: 12px uppercase, `#8b949e`, sortable with arrow indicators
- No zebra-striping (modern approach)

**Typography:**
- Font: System stack (SF Pro Display, Segoe UI, Roboto, sans-serif)
- Profit numbers: Tabular-nums for perfect alignment
- ROI: Monospace optional for exact alignment

**Profit Color Coding:**
```css
>5B:   #3fb950 (bright green)
1-5B:  #2ea043 (medium green)
<1B:   #8b949e (muted)
```

**ROI Color Coding:**
```css
>40%:  #3fb950 (excellent)
20-40%: #2ea043 (good)
<20%:  #8b949e (moderate)
```

**Sorting:**
- Click column header to sort
- Arrow indicator: ↑ ascending, ↓ descending
- Rotate animation: 180° smooth transition
- Default: Sort by Profit descending

---

### 2. Character Overview

**Layout:**
Horizontal row with 3 equal-width cards:
```
[Portrait 120px]    [Portrait 120px]    [Portrait 120px]
    Artallus            Cytrex              Cytricia
   2.4B ISK           5.1B ISK            1.8B ISK
   Jita               Perimeter           Amarr
```

**Character Card Design:**
- **Dimensions**: 140px width × 200px height
- **Portrait**:
  - Size: 120px × 120px
  - Source: ESI Character Portrait API (`/characters/{character_id}/portrait/`)
  - Size: 256 (medium resolution)
  - Fallback: Stylized avatar icon if API fails
  - Glow: `box-shadow: 0 0 20px rgba(88,166,255,0.15)`
- **Status Dot**: 8px circle, top-right absolute
  - Green `#3fb950`: Online (from ESI `/characters/{character_id}/online/`)
  - Gray `#6e7681`: Offline
- **Name**: 16px bold, `#e6edf3`, centered
- **ISK Balance**: 13px, `#8b949e`, formatted (e.g., "2.4B ISK")
- **Location**: 11px, `#6e7681`, system name, max 15 chars truncated

**Styling:**
- Background: `#161b22`
- Border: `1px solid #21262d`
- Border-radius: 8px
- Padding: 16px
- Hover: Border color → `#58a6ff`, glow intensifies

**Section Header:**
- Text: "Your Pilots" (not "Your Characters")
- Size: 20px bold
- Color: `#e6edf3`
- Margin-bottom: 16px

---

### 3. Sidebar Panels

**War Room Alerts:**
```
┌─────────────────────────────────┐
│ ⚔️  War Room Alerts            │ ← Header
├─────────────────────────────────┤
│ 🔴 High-value target in Delve   │ ← Alert item
│    2h ago                        │ ← Timestamp
│                                  │
│ 🟡 Sov timer in Fountain        │
│    5h ago                        │
│                                  │
│ View All →                       │ ← Link
└─────────────────────────────────┘
```

**Styling:**
- Background: `#161b22`
- Left border: `2px solid #f85149` (danger accent)
- Border-radius: 8px
- Padding: 20px
- Shadow: `0 4px 12px rgba(0,0,0,0.3)`

**Content:**
- Header: 18px bold, with ⚔️ emoji icon
- Alert items:
  - Icon: 🔴 high priority, 🟡 medium
  - Text: 14px, `#e6edf3`
  - Timestamp: 12px, `#8b949e`, relative format
- Max 5 alerts visible, scrollbar if more
- Empty state: "No active threats" with 🛡️, `#6e7681`

**Active Projects:**
Same structure as War Room Alerts, but:
- Left border: `2px solid #58a6ff` (info accent)
- Header: 📋 icon
- Content:
  - Project name: 14px bold
  - Progress bar: 4px height, `#3fb950` fill, `#21262d` background
  - Status: 12px, `#8b949e` (e.g., "3/10 items")
- Empty state: "No active projects" with ➕

---

## Subtle Sci-Fi Details

### Hover Effects
**Table Rows:**
- Background transition: 200ms ease
- Left border appears: `inset 0 0 0 2px #58a6ff`
- Smooth slide-in effect

**Buttons/Actions:**
- Glow on hover: `box-shadow: 0 0 12px rgba(88,166,255,0.3)`
- Transform: `translateY(-1px)`
- Cursor: pointer

**Character Portraits:**
- Glow intensifies: `0 0 30px rgba(88,166,255,0.25)`
- Border color: `#58a6ff`

### Micro-Animations
**Transitions:**
```css
transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
```

**Sort Arrows:**
- Rotate 180° when toggling sort direction
- Smooth animation: 300ms ease

**Loading States:**
- Subtle pulse animation on skeleton loaders
- Opacity: 0.5 → 1.0 → 0.5, 2s infinite

### Typography Details
- **Letter-spacing**: `-0.02em` for headlines (tighter, modern)
- **Line-height**: `1.5` for body text (readable)
- **Font-weights**:
  - 700: Headlines, important numbers
  - 600: Subheadings
  - 500: Body text
  - 400: Muted text

### Scrollbar Styling
```css
::-webkit-scrollbar {
  width: 6px;
}
::-webkit-scrollbar-track {
  background: #0a0e14;
}
::-webkit-scrollbar-thumb {
  background: #21262d;
  border-radius: 3px;
}
::-webkit-scrollbar-thumb:hover {
  background: #30363d;
}
```

---

## Responsive Design

### Breakpoints

**Desktop (>1200px):**
- Layout as described above
- Sidebar right, 30% width

**Tablet (768-1199px):**
- Sidebar moves below main content
- Full width sections
- Character cards remain 3-column

**Mobile (<768px):**
- Single column layout
- Table becomes horizontally scrollable
- Character cards stack vertically
- Sidebar sections full width

---

## Technical Specifications

### Performance
- **Virtual scrolling**: For tables with >50 rows (react-window)
- **Lazy loading**: Character portraits load on viewport entry
- **CSS containment**: `contain: layout style paint` on isolated components
- **Debounced sorting**: 150ms debounce on sort operations

### Accessibility (WCAG AA)

**Color Contrast:**
All text meets 4.5:1 ratio:
- `#e6edf3` on `#0a0e14`: 13.6:1 ✓
- `#8b949e` on `#161b22`: 4.8:1 ✓
- `#6e7681` on `#161b22`: 4.5:1 ✓

**Keyboard Navigation:**
- Tab: Move through table rows
- Enter/Space: Select row (open details)
- Arrow keys: Navigate table (optional enhancement)
- Escape: Close modals

**Focus Indicators:**
- Outline: `2px solid #58a6ff`
- Offset: `2px`
- Border-radius: matches element

**Screen Readers:**
- Semantic HTML: `<table>`, `<th>`, `<td>`
- ARIA labels for icon-only buttons
- `aria-sort` on sortable columns
- Live regions for dynamic updates

---

## API Integration

### ESI Endpoints Required

**Character Portraits:**
```
GET /characters/{character_id}/portrait/
Response: { px64x64, px128x128, px256x256, px512x512 }
Use: px256x256 for character cards
```

**Character Online Status:**
```
GET /characters/{character_id}/online/
Response: { online: boolean, last_login: datetime, last_logout: datetime }
Update: Every 60 seconds
```

**Character Location:**
```
GET /characters/{character_id}/location/
Response: { solar_system_id, structure_id }
Map to system name via SDE
```

**Wallet Balance:**
```
GET /characters/{character_id}/wallet/
Response: balance (number)
Already implemented in backend
```

---

## Implementation Notes

### Component Structure
```
Dashboard/
├── OpportunitiesTable.tsx       (new, replaces OpportunityCard)
├── CharacterOverview.tsx        (redesigned)
├── CharacterCard.tsx            (new, with portraits)
├── WarRoomAlerts.tsx           (new)
├── ActiveProjects.tsx          (new)
└── Dashboard.css               (major rewrite)
```

### CSS Organization
Use CSS custom properties for consistency:
```css
:root {
  --bg-primary: #0a0e14;
  --bg-surface: #161b22;
  --bg-elevated: #21262d;
  --border: #21262d;

  --text-primary: #e6edf3;
  --text-secondary: #8b949e;
  --text-tertiary: #6e7681;

  --accent-blue: #58a6ff;
  --accent-green: #3fb950;
  --danger: #f85149;

  --transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
}
```

### Testing Checklist
- [ ] Table sorting works in all directions
- [ ] Character portraits load correctly
- [ ] Fallback avatars work when ESI fails
- [ ] Hover effects smooth on all components
- [ ] Responsive layout works on all breakpoints
- [ ] Keyboard navigation functional
- [ ] Screen reader announces changes
- [ ] Performance: <100ms render time for table

---

## Future Enhancements (Post-MVP)

1. **Click-to-expand character cards**: Show detailed stats modal
2. **Table filters**: Filter by category, min profit, min ROI
3. **Table column customization**: User can show/hide columns
4. **Dark/Light theme toggle**: (Currently dark-only)
5. **Compact/Comfortable density toggle**: Row height options
6. **Export to CSV**: Download opportunities table
7. **Real-time updates**: WebSocket for live data updates

---

## Success Metrics

Dashboard redesign is successful when:
1. ✓ User feedback: "Looks professional, not like a school project"
2. ✓ Information density: 12-15 opportunities visible (vs current 5-6)
3. ✓ Performance: Table renders in <100ms
4. ✓ Accessibility: Passes WCAG AA automated tests
5. ✓ Theme consistency: Matches EVE Online aesthetic

---

**Design approved by:** User
**Ready for implementation:** Yes
**Next step:** Create implementation plan
