# RAAH Map Visualization - Hackathon Demo Implementation Plan

> **Strategy**: Prioritize 4-minute demo impact.
> **Features**: 120km corridor, 500+ simulated vehicles, AI evasion visualization, wildlife radar, 11 dynamic zones, dark-mode UI.

---

## 1. Demo Script
Refer to `MAP_DEMO_SCRIPT.md` for presentation flow and script.

---

## 2. Core Map Components (Build Order)

### Phase 1: Static Foundation (Hour 1-2)
| Component | Priority | Visual Impact |
|-----------|----------|---------------|
| Dark base map (CartoDB) | Critical | Instant "pro" feel |
| NH-275 highway polyline | Critical | Defines the corridor |
| 12 checkpoint markers | Critical | Navigation anchors |
| 11 zone segment lines | Critical | Status visualization canvas |

### Phase 2: Animation Layer (Hour 3-4)
| Component | Priority | Demo Value |
|-----------|----------|------------|
| Animated vehicle dots | Critical | "Living highway" effect |
| Smooth interpolation | High | Professional polish |
| Direction indicators (MB/BM) | Medium | Shows flow patterns |
| Evasion flag pulsing | Critical | Visual alert impact |

### Phase 3: Interactive Features (Hour 5-6)
| Component | Priority | Demo Value |
|-----------|----------|------------|
| Click zone → detail panel | High | Engagement |
| Checkpoint radar | Critical | "Mission Control" moment |
| Real-time zone color updates | Critical | Shows AI working |
| Alert pins (wildlife/incident) | High | Drama/urgency |

### Phase 4: Polish (Hour 7-8)
| Component | Priority | Demo Value |
|-----------|----------|------------|
| Corridor strip view | High | Alternative visualization |
| Audio notifications | Medium | Multi-sensory experience |
| Connection status indicator | Low | Technical credibility |
| Loading states | Low | Smooth UX |

---

## 3. Visual Design System

### 3.1 Color Palette (Dark Mode Professional)

```css
/* Core UI */
--bg-primary: #0f172a;      /* Slate 900 - Background */
--bg-secondary: #1e293b;    /* Slate 800 - Panels */
--border: #334155;          /* Slate 700 - Dividers */
--text-primary: #f8fafc;    /* Slate 50 - Headings */
--text-secondary: #94a3b8;  /* Slate 400 - Body */

/* Highway & Zones */
--highway-glow: #60a5fa;    /* Blue 400 - Glow effect */
--highway-core: #3b82f6;    /* Blue 500 - Main line */

/* Zone Status */
--zone-normal: #22c55e;     /* Green 500 */
--zone-warning: #eab308;     /* Yellow 500 */
--zone-incident: #f97316;    /* Orange 500 */
--zone-critical: #ef4444;     /* Red 500 */
--zone-wildlife: #10b981;    /* Emerald 500 */

/* Checkpoints */
--cp-monitor: #64748b;       /* Slate 500 */
--cp-toll: #eab308;          /* Yellow 500 */
--cp-wildlife: #10b981;      /* Emerald 500 */

/* Vehicles */
--vehicle-normal: #22c55e;   /* Green */
--vehicle-flagged: #f97316;  /* Orange */
--vehicle-evasion: #ef4444;  /* Red - Pulsing */
```

### 3.2 Typography Scale

| Element | Font | Size | Weight |
|---------|------|------|--------|
| Zone labels | Inter | 12px | 600 |
| Checkpoint IDs | JetBrains Mono | 11px | 700 |
| Vehicle counts | Inter | 14px | 700 |
| Panel headings | Inter | 16px | 600 |
| Radar stats | JetBrains Mono | 18px | 700 |

### 3.3 Animation Specs

```css
/* Vehicle Movement */
.vehicle-dot {
  transition: transform 0.5s cubic-bezier(0.4, 0, 0.2, 1);
  will-change: transform;
}

/* Zone Color Transitions */
.zone-segment {
  transition: stroke 0.3s ease, stroke-width 0.2s ease;
}

/* Evasion Pulsing - FAST for urgency */
.pulse-evasion {
  animation: pulse-red 1s ease-in-out infinite;
}

@keyframes pulse-red {
  0%, 100% { transform: scale(1); opacity: 1; }
  50% { transform: scale(1.5); opacity: 0.6; }
}

/* Radar Sweep - Cinematic */
.radar-sweep {
  animation: sweep 4s linear infinite;
}

@keyframes sweep {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

/* Alert Ping */
.alert-ring {
  animation: ping 1.5s cubic-bezier(0, 0, 0.2, 1) infinite;
}

@keyframes ping {
  75%, 100% {
    transform: scale(2);
    opacity: 0;
  }
}
```

---

## 4. Component Specifications

### 4.1 HighwayMap (Main Container)

**Purpose**: Orchestrates all map layers and real-time data flow

**Props**:
```typescript
interface HighwayMapProps {
  mode: 'live' | 'historical' | 'risk-heatmap';
  showVehicles: boolean;
  showRadar: boolean;
  onZoneSelect: (zone: Zone) => void;
}
```

**Socket Events Handled**:
- `zone_update` → Update zone colors
- `journey_update` → Move vehicle dots
- `wildlife_alert` → Show wildlife pin + radar
- `ml_alert` → Flag vehicle (red pulse)
- `legal_alert` → Show legal violation pin

### 4.2 CorridorStripView

**Purpose**: Linear 1D representation above the map for presentations

**Visual Design**:
```
┌────────────────────────────────────────────────────────────────────────┐
│ CP-01  CP-02  CP-03  CP-04  CP-05  CP-06  CP-07  CP-08  CP-09  CP-10 │
│   ●──────●──────●──────●──────●──────●──────●──────●──────●──────●   │
│  [Mysore]    [₹80]   [🦌]      [₹80]   [🦌]      [₹80]    [Bangalore]│
│      🚗🚗      🚗                      🚨                           │
└────────────────────────────────────────────────────────────────────────┘
```

**Features**:
- Horizontal scroll synced with map
- Vehicle dots move along strip
- Zone segments color-coded
- Checkpoint icons (toll/wildlife/monitor)
- Alert indicators (pulsing icons)

### 4.3 CheckpointRadar

**Purpose**: Cinematic "Mission Control" visualization

**Design**:
- Circular 260px diameter
- Dark background with grid rings
- Rotating sweep line (4s rotation)
- Vehicle blips with direction colors:
  - Blue = Mysore→Bangalore (MB)
  - Orange = Bangalore→Mysore (BM)
- Range rings: 1km, 3km, 5km
- Real-time vehicle count stats

**Interaction**:
- Click checkpoint → Open radar
- Shows vehicles within 5km radius
- Lists closest 3 vehicles with speed/distance

### 4.4 ZoneDetailPanel

**Purpose**: Deep-dive into any highway segment

**Sections**:
1. **Header**: Zone ID, name, status badge
2. **Live Metrics**: Vehicle count, flow, motion index
3. **Risk Profile**: Historical risk tier + score
4. **Cameras**: Grid of camera badges
5. **Checkpoints**: Entry/exit flow diagram
6. **Mini Radar**: Quick checkpoint view

**Animation**: Slide in from right (300ms ease-out)

### 4.5 AlertPins

**Types**:
| Alert | Icon | Color | Animation |
|-------|------|-------|-----------|
| Wildlife | 🦌 | Emerald | Slow pulse |
| Incident | ⚠️ | Orange | Medium pulse |
| Evasion | 💰 | Red | Fast pulse |
| Critical | 🚨 | Deep Red | Rapid pulse + sound |

**Positioning**: Center of zone segment

---

## 5. Data Structure (For Map)

### 5.1 Checkpoint Configuration (12 Checkpoints)

| ID | Name | KM | Type | Toll (₹) | Purpose |
|----|------|-----|------|----------|---------|
| CP-01 | Mysore Entry | 0 | monitor | - | Entry registration, ANPR only |
| CP-02 | Srirangapatna | 12 | monitor | - | Traffic monitoring |
| **CP-03** | **Nidaghatta Toll** | **28** | **full_plaza** | **80** | **Toll Collection #1** |
| CP-04 | Cauvery Wildlife | 40 | wildlife_sensor | - | Wildlife corridor monitoring |
| CP-05 | Mandya North | 55 | monitor | - | Traffic monitoring |
| CP-06 | Maddur | 58 | monitor | - | High-risk zone marker |
| CP-07 | Mandya Forest | 62 | wildlife_sensor | - | Wildlife corridor monitoring |
| CP-08 | Ramanagara Entry | 71 | monitor | - | Traffic monitoring |
| CP-09 | Ramanagara Mid | 82 | monitor | - | Traffic monitoring |
| CP-10 | Bidadi | 95 | monitor | - | Traffic monitoring |
| **CP-11** | **Kengeri Toll** | **114** | **full_plaza** | **80** | **Toll Collection #2** |
| CP-12 | Bangalore Entry | 120 | monitor | - | Exit registration, ANPR only |

**Total Toll for Full Route**: ₹160 (Car/LMV) - 2 plazas × ₹80

### 5.2 Zone Definitions (11 Zones)

| Zone ID | Checkpoints | KM Range | Type | Special |
|---------|-------------|----------|------|---------|
| ZONE-01 | CP-01 → CP-02 | 0-12 | highway | Entry zone |
| ZONE-02 | CP-02 → CP-03 | 12-28 | highway | Approach to toll |
| ZONE-03 | CP-03 → CP-04 | 28-40 | highway | Post-toll |
| ZONE-04 | CP-04 → CP-05 | 40-55 | forest_corridor | Cauvery Wildlife |
| ZONE-05 | CP-05 → CP-06 | 55-58 | highway | Maddur approach |
| **ZONE-06** | CP-06 → CP-07 | 58-62 | highway | **High Risk Zone** |
| ZONE-07 | CP-07 → CP-08 | 62-71 | forest_corridor | Mandya Forest |
| ZONE-08 | CP-08 → CP-09 | 71-82 | highway | Ramanagara |
| ZONE-09 | CP-09 → CP-10 | 82-95 | highway | Pre-toll |
| ZONE-10 | CP-10 → CP-11 | 95-114 | highway | Approach to toll |
| ZONE-11 | CP-11 → CP-12 | 114-120 | highway | Exit zone |

### 5.3 Map Configuration Object

```typescript
interface MapConfig {
  highway: {
    id: 'NH-275';
    name: 'Mysore-Bangalore Expressway';
    lengthKm: 120;
    coordinates: [number, number][]; // GeoJSON LineString
  };
  checkpoints: Checkpoint[]; // 12 items
  zones: Zone[]; // 11 items
  cameras: Camera[]; // 28 items
}

interface Checkpoint {
  id: string; // CP-01 to CP-12
  name: string;
  km: number;
  type: 'monitor' | 'full_plaza' | 'wildlife_sensor';
  lat: number;
  lng: number;
  cameras: string[];
  tollRates?: Record<string, number>; // For full_plaza
}

interface Zone {
  id: string; // ZONE-01 to ZONE-11
  name: string;
  kmStart: number;
  kmEnd: number;
  type: 'highway' | 'forest_corridor';
  entryCheckpoint: string;
  exitCheckpoint: string;
  wildlifePriority?: boolean;
  highRisk?: boolean;
}
```

### 5.2 Real-Time State

```typescript
interface ZoneState {
  zoneId: string;
  status: 'normal' | 'warning' | 'incident' | 'critical' | 'wildlife';
  vehicleCount: number;
  anomalyScore?: number; // -1 to 1
  incidentType?: string;
  motionIndex?: number; // 0 to 1
}

interface VehiclePosition {
  plate: string;
  direction: 'MB' | 'BM';
  lat: number;
  lng: number;
  progress: number; // 0-1 between checkpoints
  isEvasion: boolean;
  isFlagged: boolean;
}
```

---

## 6. Implementation Strategy

### 6.1 OpenStreetMap GeoJSON Integration Pipeline

**Core Map Data Pipeline**:
- ✅ Real OpenStreetMap (OSM) download via Overpass API or predefined OSM GeoJSON file.
- ✅ Complex GeoJSON processing (Turf.js) for routing and spatial analysis.
- ✅ Dynamic coordinate extraction and interpolation directly from the OSM data.
- ✅ Simple JWT mock auth for demo purposes.

**How to integrate OSM GeoJSON & Analysis**:
1. **Fetch/Import**: Use an Overpass API query (`[out:json];way["highway"]["name"="NH-275"];out geom;`) or a pre-downloaded `nh275-osm.geojson` exported directly from OpenStreetMap.
2. **Spatial Analysis with Turf.js**: Use `@turf/turf` to analyze the map data:
   - Calculate exact segment lengths (`turf.length`).
   - Compute distances between moving vehicles and checkpoints (`turf.distance`).
   - Determine if a vehicle is inside a high-risk zone polygon (`turf.booleanPointInPolygon`).
   - Snap vehicle locations to the highway polyline (`turf.nearestPointOnLine`) for perfect visual alignment.
3. **Rendering**: Pass the parsed `GeoJSON` directly to `<GeoJSON data={osmData} />` in `react-leaflet`, applying style functions dynamically based on live `zone_update` properties.

### 6.2 Dynamic Coordinate Extraction (OSM GeoJSON)

Instead of hardcoded coordinate arrays, load the OpenStreetMap GeoJSON and enrich it with checkpoint metadata:

```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "properties": {
        "highway": "trunk",
        "name": "NH-275",
        "zone_id": "ZONE-06",
        "risk_tier": "critical"
      },
      "geometry": {
        "type": "LineString",
        "coordinates": [[76.8800, 12.8300], [76.8900, 12.8500], ...]
      }
    }
    // Checkpoints will be mapped as Point features dynamically
  ]
}
```
*Note: Checkpoint markers are dynamically placed along the OSM LineString using Turf.js length calculations to match their exact KM positions.*

### 6.3 Build Checklist (8-Hour Sprint)

**Hours 1-2: Foundation**
- [ ] Create `HighwayMap` component shell
- [ ] Add Leaflet with CartoDB dark tiles
- [ ] Draw highway polyline with glow effect
- [ ] Add 12 checkpoint markers

**Hours 3-4: Animation**
- [ ] Vehicle dot component
- [ ] Interpolation logic (checkpoint-to-checkpoint)
- [ ] Socket.IO connection
- [ ] Real-time position updates

**Hours 5-6: Interaction**
- [ ] Zone segments with click handlers
- [ ] Zone detail panel (slide-over)
- [ ] Checkpoint radar component
- [ ] Alert pins with animations

**Hours 7-8: Polish**
- [ ] Corridor strip view
- [ ] Audio notifications
- [ ] Demo scenario buttons
- [ ] Final styling pass

---

## 7. Demo Enhancement Features

### 7.1 Audio Notification System

**Web Audio API** (no external files):

```typescript
const playAlertSound = (type: AlertType) => {
  const audioCtx = new (window.AudioContext || (window as any).webkitAudioContext)();
  const oscillator = audioCtx.createOscillator();
  const gainNode = audioCtx.createGain();
  
  oscillator.connect(gainNode);
  gainNode.connect(audioCtx.destination);
  
  switch(type) {
    case 'legal':
      oscillator.type = 'square';
      oscillator.frequency.setValueAtTime(800, audioCtx.currentTime);
      gainNode.gain.setValueAtTime(0.1, audioCtx.currentTime);
      gainNode.gain.exponentialRampToValueAtTime(0.01, audioCtx.currentTime + 0.1);
      oscillator.start();
      oscillator.stop(audioCtx.currentTime + 0.1);
      break;
    case 'wildlife':
      oscillator.type = 'sine';
      oscillator.frequency.setValueAtTime(400, audioCtx.currentTime);
      gainNode.gain.setValueAtTime(0.1, audioCtx.currentTime);
      gainNode.gain.exponentialRampToValueAtTime(0.01, audioCtx.currentTime + 0.3);
      oscillator.start();
      oscillator.stop(audioCtx.currentTime + 0.3);
      break;
  }
};
```

**Trigger Points**:
- Legal alert → Sharp beep
- Wildlife alert → Soft bell
- Evasion detected → Two-tone chime

### 7.2 Corridor Strip View

**Purpose**: Alternative linear visualization for presentations

**Design**:
- Fixed height: 80px
- Full width of container
- Synced scroll with map
- Shows all 120km at a glance

**Elements**:
- Checkpoint circles (color-coded by type)
- Connecting line (zone colors)
- Moving vehicle dots (smaller than map)
- Pulsing alert indicators

### 7.3 Simulator Integration

**Demo Buttons** (in top nav dropdown):

| Button | Effect | Visual Result |
|--------|--------|---------------|
| 🚧 Simulate Incident | ZONE-06 turns red | Zone pulse, alert sound |
| 💰 Show Evasion | Vehicle skips tolls | Red vehicle dot, sidebar alert |
| 🦌 Wildlife Alert | ZONE-04 flash emerald | Wildlife pin, radar sweep |
| 👻 Ghost Vehicle | Unregistered plate | E4 legal alert |
| ⚠️ High Risk Hour | Spikes all incidents | Multiple zones change color |

---

## 8. Technical Dependencies

```json
{
  "dependencies": {
    "leaflet": "^1.9.4",
    "react-leaflet": "^4.2.1",
    "socket.io-client": "^4.7.5",
    "framer-motion": "^11.0.0",
    "@turf/turf": "^6.5.0",
    "axios": "^1.7.2"
  }
}
```

**Why Framer Motion**: Better animation control than CSS for complex vehicle movements.
**Why Turf.js**: Required for OpenStreetMap GeoJSON spatial analysis, point-on-line snapping, and zone poly-mapping.

---

## 9. File Structure (Final)

```
authority-dashboard/src/
├── components/
│   └── map/
│       ├── HighwayMap.tsx           # Main orchestrator
│       ├── CorridorStrip.tsx        # Linear view
│       ├── ZoneSegments.tsx         # 11 zone polylines
│       ├── CheckpointMarkers.tsx    # 12 markers
│       ├── VehicleLayer.tsx         # Animated dots
│       ├── CheckpointRadar.tsx      # Radar view
│       ├── ZoneDetailPanel.tsx      # Slide-over panel
│       └── AlertOverlay.tsx         # Pulsing pins
├── hooks/
│   ├── useSocket.ts                 # Real-time connection
│   └── useVehicleAnimation.ts       # Smooth interpolation
├── data/
│   └── nh275-osm.geojson            # OpenStreetMap GeoJSON data
└── styles/
    └── map.css                      # All map styles
```

---

## 10. Component API Reference

### 10.1 HighwayMap Component

```typescript
interface HighwayMapProps {
  mode: 'live' | 'historical' | 'risk-heatmap';
  showVehicles?: boolean;        // default: true
  showRadar?: boolean;          // default: false
  showCorridorStrip?: boolean;   // default: true
  onZoneSelect?: (zone: Zone) => void;
  onCheckpointSelect?: (checkpoint: Checkpoint) => void;
  className?: string;
}

interface HighwayMapState {
  selectedZone: Zone | null;
  selectedCheckpoint: Checkpoint | null;
  zoneStates: Record<string, ZoneState>;
  vehicles: VehiclePosition[];
  activeAlerts: Alert[];
  isConnected: boolean;
}
```

### 10.2 Vehicle Animation System

```typescript
interface VehicleAnimationConfig {
  updateInterval: number;      // ms between position updates (default: 1000)
  transitionDuration: number;  // CSS transition time (default: 500)
  interpolationSteps: number;  // Steps between checkpoints (default: 10)
}

// Animation Formula
const calculatePosition = (
  lastCheckpoint: Checkpoint,
  nextCheckpoint: Checkpoint,
  progress: number,  // 0.0 to 1.0
  curveOffset: number // Add slight curve for realism
) => {
  const lat = lastCheckpoint.lat + (nextCheckpoint.lat - lastCheckpoint.lat) * progress;
  const lng = lastCheckpoint.lng + (nextCheckpoint.lng - lastCheckpoint.lng) * progress;
  return { lat: lat + curveOffset, lng: lng + curveOffset };
};
```

### 10.3 Socket Event Handlers

```typescript
// Incoming Events
interface ZoneUpdateEvent {
  zoneId: string;
  status: ZoneStatus;
  vehicleCount: number;
  anomalyScore?: number;
  incidentType?: string;
  timestamp: string;
}

interface JourneyUpdateEvent {
  plate: string;
  direction: 'MB' | 'BM';
  lastCheckpoint: string;
  nextCheckpoint?: string;
  progress: number;  // 0.0 to 1.0 between checkpoints
  timestamp: string;
}

interface AlertEvent {
  alertId: string;
  type: 'wildlife' | 'incident' | 'evasion' | 'legal';
  zoneId?: string;
  checkpointId?: string;
  plate?: string;
  message: string;
  severity: 'low' | 'medium' | 'high' | 'critical';
  timestamp: string;
}
```

## 11. Troubleshooting Guide
- **Tiles not loading**: Check CartoDB URL.
- **No vehicle animation**: Verify socket connection & simulator port 8001.
- **Zone colors static**: Check backend `zone_update` emissions.
- **No audio**: Ensure initial user interaction (click) occurred.

## 12. Future Enhancements & Success Criteria
- **Future**: Multi-highway support, 3D terrain, historical replay, mobile-optimized website enhancements, RBAC.
- **Success Criteria**: Map loads <2s, 50+ animated vehicles, smooth radar, no console errors, <200MB memory usage.

---

**Document Version**: 2.1 (Hackathon Enhanced Edition)  
**Focus**: Demo impact over production robustness  
**Time Budget**: 8 hours implementation  
**Team Size**: 1-2 frontend developers  
**Last Updated**: 2024-05-12
