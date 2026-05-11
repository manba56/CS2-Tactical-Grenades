# Tactic Visuals: Route Drawing + Grenade Screenshot Display

Date: 2026-05-10

## Context

The cs2-tactics-suite currently has structured tactic data (steps, lineups, utility types) but lacks visual representations of player movement routes and good-looking grenade screenshot displays. The user manually captures grenade aim screenshots and wants to draw player routes on radar images.

## Design

### 1. Radar Image Assets

Add high-quality radar PNGs for all competitive CS2 maps as static assets.

- **Source**: CS2 community radar images (simpleradar.com or extracted from game files)
- **Location**: `cs2-api/app/static/assets/maps/radars/`
- **Naming**: `{map-slug}-radar.png` (e.g. `mirage-radar.png`)
- **Maps**: mirage, inferno, nuke, ancient, anubis, dust2, vertigo, overpass, train

The existing custom SVG layouts (`mirage-layout.svg`, etc.) remain for the point overlay system. Radar images serve as the background for route drawing.

### 2. Route Drawing Tool (Admin Panel)

**Location**: New section in `TacticsAdminView.vue` (create/edit tactic form), or a dedicated route editor component.

**Interaction**:
- Radar image as the base layer
- Click to place nodes on the map
- Nodes auto-connect with arrowed lines
- Each player gets one route with a distinct color (orange, blue, green, yellow, purple for players 1-5)
- Nodes are draggable; right-click to delete a node
- Undo/redo support (basic)

**Data Model** — Add a `routes` field to the tactic:

```json
{
  "routes": [
    {
      "player": 1,
      "color": "#ff7a18",
      "label": "突破位",
      "points": [
        {"x": 30.5, "y": 60.2},
        {"x": 55.0, "y": 40.0},
        {"x": 78.0, "y": 41.0}
      ]
    }
  ]
}
```

Coordinates are in the same 0-100 percentage system used by map points.

**Storage**: New `routes` field on tactics in the JSON store. Update `TacticPayload` schema with optional `routes` field.

**Frontend display**: Render routes as SVG `<polyline>` / `<path>` elements with arrow markers overlaid on the radar image. Player labels at start/end points.

### 3. Grenade Screenshot Display (Frontend)

**TacticDetailView changes**:

Each step that references a lineup shows a media gallery card:

```
┌──────────────────────────────┐
│  #1 · 烟位                   │
│  出生点贴左墙 → 对准屋檐       │
│                              │
│  ┌────────┐ ┌────────┐      │
│  │ 📷 img1│ │ 📷 img2│      │
│  └────────┘ └────────┘      │
│  瞄点特写     落点位置        │
│                              │
│  道具: 烟雾弹 · 难度: 简单    │
└──────────────────────────────┘
```

- Screenshot cards in a responsive grid (max 3 per row)
- Rounded corners, subtle border + shadow
- Click to lightbox/fullscreen view
- Caption text under each image
- Empty state: dashed-border placeholder with "点击上传截图" text

**Lineup media field** already supports multiple URLs (`media: string[]`). The frontend currently only shows `media[0]`. Change to render all media items in the grid.

### 4. Data Flow

```
Admin: create tactic → add steps → reference lineups
                                    ↓
                              upload grenade screenshots via asset manager
                                    ↓
                              use route drawing tool on radar image
                                    ↓
Player frontend: tactic detail page
  ├─ Route map (radar bg + SVG route overlays)
  ├─ Step list with grenade screenshot gallery per step
  └─ Related tactics
```

## Files to Modify

| File | Change |
|------|--------|
| `cs2-api/app/schemas.py` | Add `routes` field to `TacticPayload` |
| `cs2-api/app/seed.py` | Add example route data to seed tactics |
| `cs2-api/app/main.py` | Support `routes` in tactic create/update |
| `cs2-admin/src/views/TacticsAdminView.vue` | Add route drawing tool component |
| `cs2-admin/src/components/RouteEditor.vue` | **New** — mouse-driven route drawing on radar |
| `cs2-web/src/views/TacticDetailView.vue` | Route display + media gallery per step |
| `cs2-web/src/style.css` | New styles for screenshot cards, route overlay |
| `cs2-api/app/static/assets/maps/radars/` | **New** — radar PNGs for all maps |

## Verification

1. Upload a grenade screenshot in admin → appears in tactic detail gallery
2. Draw a 3-node route on Mirage radar → saves → displays correctly on frontend
3. Existing seed tactics without routes/screenshots still render correctly (backward compat)
4. Multiple screenshots per step display in responsive grid without overflow
