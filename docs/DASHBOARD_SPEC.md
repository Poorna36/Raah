# Dashboard Specification

Two separate frontend applications. Same backend API, different Socket.IO namespaces.

| App | Target | Port | Namespace |
|-----|--------|------|-----------|
| `authority-dashboard` | Desktop/PC browser (1280px+ optimized) | 5173 | `/authority` |
| `commuter-app` | Mobile browser (375px–428px primary, responsive up) | 5174 | `/commuter` |

---

## Authority Dashboard

### Layout Structure

```
┌──────────────────────────────────────────────────────────────────┐
│  Top Nav Bar (fixed, 56px height)                                │
│  [RAAH Logo] [Highway: NH-275 ▼] [Live View] [Risk Heatmap]      │
│  [Evasion Cases] [Analytics]          [Sim Controls] [User ▼]    │
├────────────────────────────────────────┬─────────────────────────┤
│                                        │                         │
│  Main Content Area (60% width)         │  Right Sidebar (40%)    │
│                                        │                         │
│  ┌──────────────────────────────────┐  │  ┌───────────────────┐  │
│  │                                  │  │  │  Alert Feed        │  │
│  │  Map / Tab Content               │  │  │  (scrollable)      │  │
│  │  (changes per tab)               │  │  │                   │  │
│  │                                  │  │  │  [Legal Alert]     │  │
│  │                                  │  │  │  [ML Alert]        │  │
│  │                                  │  │  │  [Wildlife Alert]  │  │
│  │                                  │  │  │                   │  │
│  │                                  │  │  │  Filter: [All ▼]   │  │
│  └──────────────────────────────────┘  │  └───────────────────┘  │
│                                        │                         │
│  ┌──────────────────────────────────┐  │  ┌───────────────────┐  │
│  │  Stats Bar (below map)           │  │  │  Quick Stats       │  │
│  │  Active Vehicles | Evasions      │  │  │  Evasion count     │  │
│  │  Today | Incidents | Revenue     │  │  │  Revenue today     │  │
│  └──────────────────────────────────┘  │  │  Model accuracy    │  │
│                                        │  └───────────────────┘  │
└────────────────────────────────────────┴─────────────────────────┘
```

### Top Nav Bar

| Element | Behavior |
|---------|----------|
| RAAH Logo | Home / refresh |
| Highway Selector | Dropdown: `NH-275 (Mysore-BLR)`, `NH-48 (Mumbai-Pune)`. Only NH-275 active for demo. |
| Live View tab | Default. Live Section Mode map + corridor strip + alerts |
| Risk Heatmap tab | Map with risk coloring + time slider |
| Evasion Cases tab | Case list replaces map area. Evidence viewer |
| Analytics tab | Charts replace map area. Model metrics |
| Sim Controls | Dropdown: 5 scenario buttons + reset + status |
| Heartbeat indicator | Pulsing green dot + `1,247 events/sec` — proves system is alive |
| About System | Question mark icon button — opens legal compliance modal |
| User dropdown | Role badge, logout |

### About System Modal (Legal Compliance Display)

**Trigger**: Clicking the question mark (?) icon in top nav bar.

**Modal Layout**:
```
┌─────────────────────────────────────────────────────────────────┐
│  RAAH System — Legal Compliance Framework              [X]      │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ Statutory Basis                                          │   │
│  ├─────────────────────────────────────────────────────────┤   │
│  │ • National Highways Fee Rules, 2008 (Rules 5, 7, 14, 15)│   │
│  │ • Motor Vehicles Act, 1988 (Sections 39, 66, 112, 183, │   │
│  │   192, 177, 192A) — Amended 2019                        │   │
│  │ • Information Technology Act, 2000 (Sections 4, 43A, 65B)│   │
│  │ • Bharatiya Sakshya Adhiniyam, 2023 (Sections 61, 63)   │   │
│  │ • Digital Personal Data Protection Act, 2023 (Sections 4, │   │
│  │   8, 17)                                                │   │
│  │ • NHAI Act, 1988 (Sections 16, 8A)                      │   │
│  │ • Wildlife Protection Act, 1972 (Schedule I, Section 38O)│   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ Enforcement Logic                                        │   │
│  ├─────────────────────────────────────────────────────────┤   │
│  │ Layer 1: Hard Logic (Deterministic)                      │   │
│  │ • Non-Payment (Rule 5) • Underpayment (Rule 7, 15)      │   │
│  │ • Misclassification (Rule 7, 15) • Unregistered (Sec 39) │   │
│  │ • Speed/Cloned Plate (Sec 112, 183, 192A)                │   │
│  │                                                          │   │
│  │ Layer 2: ML Intelligence (Probabilistic)                 │   │
│  │ • Evasion pattern detection • Zone anomaly detection     │   │
│  │ • Wildlife intrusion detection • Risk zone scoring       │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ Data Protection (DPDP Act 2023)                          │   │
│  ├─────────────────────────────────────────────────────────┤   │
│  │ • Lawful basis: State function & public interest (Sec 17)│   │
│  │ • 90-day retention with anonymization (Sec 8)           │   │
│  │ • Electronic records admissible (IT Act Sec 65B, BSA   │   │
│  │   Sec 63)                                               │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  [View Full Legal Framework] — links to docs/LEGAL_FRAMEWORK.md│
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**Visual Design**:
- Modal width: 600px max, centered
- Background: `slate-800` (`#1e293b`)
- Text: `slate-200` (`#e2e8f0`)
- Headers: White, 600 weight
- Lists: Bullet points with `primary-blue` accent
- Link button at bottom: Outlined style, links to full documentation

**Button Style**:
```css
.about-system-btn {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: transparent;
  border: 1px solid #475569;
  color: #94a3b8;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.2s;
}
.about-system-btn:hover {
  background: #334155;
  color: #f8fafc;
  border-color: #64748b;
}
```

### Tab: Live View (Default)

**Main area**: Leaflet map centered on NH-275 corridor. Operates in **Live Section Mode** (see `MAP_VISUALIZATION.md`).

**Map elements**:

| Element | Visual | Data Source |
|---------|--------|-------------|
| Highway line | Blue polyline following NH-275 actual route | Static GeoJSON |
| Checkpoints | Numbered circle markers at KM positions | `GET /checkpoints` |
| Section segments | Polylines between CPs, colored by status | `zone_update` |
| Vehicle count badges| Floating number on each section | `GET /zones` |
| Vehicle dots | Small animated dots between checkpoints | `journey_update` |
| Alert pins | Pulsing icon at incident/wildlife location | `ml_alert`, `wildlife_alert` |

**Interactivity**:
- Click any section/checkpoint to open the **Live Status Panel** replacing the Alert Feed temporarily.
- Panel shows: Checkpoint name, active incidents, camera inventory (`camera_ids`), and a mini sparkline of the last 5 minutes of motion index.

**Vehicle dot position**: Interpolated between `last_checkpoint` KM and next expected checkpoint KM based on time elapsed vs expected segment time.

**Stats bar** (below map, 4 cards):
- Active Vehicles: `{count}` — from `GET /dashboard/stats`
- Evasion Cases Today: `{count}` — updates in real-time
- Active Incidents: `{count}` with zone indicator
- Est. Revenue Today: `₹{amount}` — sum of FASTag transactions

### Corridor Strip View

Horizontal linear representation of the full 120km highway, displayed above the map (height: 80px). More readable than a map during demo presentations.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ CP-01  CP-02  CP-03  CP-04  CP-05  CP-06  CP-07  CP-08  CP-09  CP-10  ...│
│   ●──────●──────●──────●──────●──────●──────●──────●──────●──────●──────●  │
│   ▲      ▲   [TOLL]         [WILDLIFE]   [TOLL]  [WILDLIFE]        [TOLL] │
│  entry  mon   ₹80    ──cauvery──    ₹80   ──mandya──    mon   ₹80   ₹80  │
│         ···•····•·····                ▲                                    │
│              vehicles (moving dots)   incident (pulsing red)              │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Elements**:
- Checkpoints as labeled circles (toll=blue, monitor=gray, wildlife=green)
- Zone segments as colored bars between checkpoints (green/yellow/orange/red)
- Vehicle dots as small circles moving along the strip (animated, CSS transition)
- Incident/wildlife markers as pulsing icons
- Toll amounts labeled at toll plazas
- Click any checkpoint → popup with details

**Right sidebar — Alert Feed**:
- Scrollable list, newest first
- Each alert card shows: type badge (Legal/ML/Wildlife), plate, zone, severity color, time, summary
- Legal alerts: solid red left border
- ML alerts: dashed orange left border
- Wildlife alerts: green left border
- Click alert → expands inline with evidence preview + feedback buttons
- Filter dropdown: All, Legal Only, ML Only, Wildlife, Pending Review

### Tab: Risk Heatmap (Historical Insights)

**Main area**: Same Leaflet map but operating in **Historical Insights Mode** (30-day view).

**Visuals**:
- Zone segments show risk tier colors (Low=Green, Moderate=Yellow, High=Orange, Critical=Red) from `zone_risk_profiles`.
- Heatmap overlay (gradient blur) showing geographic density of historical accidents and confirmed evasions.

**Additional elements**:
- Time slider (24 hours): Slide to see how risk tiers change by hour. Data from `time_risk_curve` in risk profiles.
- **Interactivity**: Click on zone → opens Insights Panel showing dominant risk type, 30d incident count, 30d evasion density, and a 24h peak risk bar chart.

**Right sidebar**: Zone risk table — all 11 zones sorted by risk score. Each row: zone name, tier badge, dominant type, peak hours.

### Tab: Evasion Cases

**Main area** (replaces map): Paginated table of evasion cases.

| Column | Content |
|--------|---------|
| Time | Timestamp |
| Plate | Vehicle plate number |
| Type | Rule code (E1–E5) or ML |
| Source | `Hard Logic` badge or `ML (91%)` badge with score |
| Checkpoint | Where detected |
| Est. Loss | ₹ amount |
| Status | Pending / Confirmed / Dismissed badge |
| Action | [View Evidence] button |

**Evidence viewer** (opens as slide-over panel from right):
- Journey timeline: horizontal bar showing all checkpoints, green ticks for visited, red X for missed
- ANPR reads: list of all reads with timestamps and confidence
- FASTag reads: list or "NO FASTAG RECORDED" red banner
- Timing proof: if E5 triggered, shows calculation
- ML score breakdown: feature importance bar chart (if ML source)
- Revenue loss calculation
- **Feedback buttons**: [Confirm Case] [Dismiss — Sensor Error] [Dismiss — Legitimate Exception] [Dismiss — Insufficient Evidence]

### Tab: Analytics

**Main area** (replaces map): 4 chart panels in 2×2 grid.

| Panel | Chart Type | Data |
|-------|-----------|------|
| Model Accuracy Trend | Line chart (Recharts) | 7-day rolling accuracy per model |
| False Positive Rate | Line chart | 7-day rolling FPR per alert type |
| Confirmed Case Rate | Line chart | 7-day confirmed/total ratio |
| Sensor Reliability | Horizontal bar chart | Per-checkpoint reliability score |

**Right sidebar**: Summary stats — total cases processed, confirmation rate, top evasion hotspot checkpoint, model version info.

### Simulator Controls (dropdown in top nav)

| Button | Action | API Call |
|--------|--------|----------|
| 🚧 Simulate Incident | Triggers incident in ZONE-06 (Maddur) | `POST /simulator/scenario {scenario:"incident", params:{zone_id:"ZONE-06", duration_minutes:5}}` |
| 💰 Show Evasion Case | Injects plaza-skip evasion vehicle | `POST /simulator/scenario {scenario:"evasion"}` |
| 🦌 Trigger Wildlife Alert | Wildlife event in Cauvery corridor | `POST /simulator/scenario {scenario:"wildlife", params:{zone_id:"ZONE-04"}}` |
| 👻 Ghost Vehicle | Unregistered plate appears | `POST /simulator/scenario {scenario:"ghost_vehicle"}` |
| ⚠️ High Risk Hour | Spikes incident + evasion frequency | `POST /simulator/scenario {scenario:"high_risk_hour", params:{duration_minutes:5}}` |
| 🔄 Reset Simulator | Clears active scenarios | `POST /simulator/reset` |

Each button shows a brief toast notification when scenario activates.

---

## Demo Enhancement Features

### Notification Sounds

Play subtle audio cues when alerts arrive. Different tones per alert type. Uses Web Audio API — no external files needed.

| Alert Type | Sound | Implementation |
|------------|-------|----------------|
| Legal alert | Short sharp beep (800Hz, 100ms) | `OscillatorNode` — square wave |
| ML alert | Two-tone chime (600Hz→800Hz, 200ms) | `OscillatorNode` — sine wave |
| Wildlife alert | Soft bell (400Hz, 300ms, fade out) | `OscillatorNode` — sine wave with gain ramp |
| Incident zone change | Low tone (300Hz, 150ms) | `OscillatorNode` — triangle wave |

Mute toggle button in top nav. Default: unmuted.

### Animated Vehicle Movement

Vehicle dots on both the map and corridor strip must animate smoothly — never jump.

```javascript
// On journey_update event:
// 1. Get current position (last_checkpoint KM)
// 2. Get next expected checkpoint KM
// 3. Calculate interpolated position based on time elapsed
// 4. Use CSS transition (duration: 2s, ease-in-out) to move dot

// CSS:
.vehicle-dot {
  transition: left 2s ease-in-out, top 2s ease-in-out;
  width: 8px;
  height: 8px;
  border-radius: 50%;
}
.vehicle-dot.flagged { animation: pulse 1.5s infinite; }
.vehicle-dot.evasion { background: #ef4444; animation: pulse 1s infinite; }

@keyframes pulse {
  0%, 100% { transform: scale(1); opacity: 1; }
  50% { transform: scale(1.5); opacity: 0.7; }
}
```

### System Heartbeat Indicator

Top nav bar, right side. Shows system is alive and processing.

```
● 1,247 events/sec | ⏱ 14:30 sim time
```

- Green pulsing dot (CSS animation)
- Events/sec: computed from Redis Stream throughput, updated every 2s
- Sim time: current simulated clock time
- Data source: `GET /simulator/status` polled every 2s, or add a `heartbeat` Socket.IO event emitted every 2s

---

## Commuter App (Mobile-Optimized)

### Design Principles

- **Mobile-first**: Primary viewport 375px–428px width
- **Touch-friendly**: Minimum tap target 44px
- **Bottom navigation**: Thumb-reachable nav bar
- **Progressive disclosure**: Show summary first, details on tap
- **Dark mode default**: Easier on eyes for night driving

### Layout Structure

```
┌──────────────────────────┐
│  Header (48px)           │
│  RAAH • Commuter         │
├──────────────────────────┤
│                          │
│  Page Content            │
│  (scrollable)            │
│                          │
│                          │
│                          │
│                          │
│                          │
│                          │
├──────────────────────────┤
│  Bottom Nav (56px)       │
│  [🏠 Home] [🚗 Trip]     │
│  [📍 Track]              │
└──────────────────────────┘
```

### Page: Home (Route Query)

**Components**:

1. **Route Query Form** (card at top):
   - Origin: dropdown of checkpoints (default CP-01)
   - Destination: dropdown of checkpoints (default CP-12)
   - Vehicle Class: selector (Car, LMV, Bus, Truck, MAV)
   - Departure Time: date-time picker (defaults to now)
   - [Get Route Info] button — full width, prominent

2. **Route Results** (appears below form after query):
   - **Journey Time Card**: `~1 hr 55 min` large text, confidence range below in smaller text
   - **Toll Cost Card**: Total `₹320` large text. Expandable to show per-plaza breakdown
   - **Risk Warnings** (list of cards, one per affected zone):
     - Zone name, severity badge (color-coded), warning text
     - Tap to expand: suggested action, anomaly details
   - **Departure Recommendation** (conditional card):
     - Only shows if there's an active issue on route
     - Green card if "good to go", yellow/orange if "consider delaying"
     - Shows recommended departure time if delay suggested

3. **Highway Status Banner** (bottom of page):
   - Simple 120km horizontal bar showing zone colors
   - Tap any segment → zone name + current status

### Page: Active Trip

**Components**:

1. **Vehicle Input** (if not tracking):
   - Plate number input field
   - Direction selector (Mysore→Bangalore / Bangalore→Mysore)
   - [Start Tracking] button
   - Connects to `track_journey` Socket.IO event

2. **Trip Dashboard** (once tracking active):
   - **Mini Map**: Small Leaflet map showing vehicle position on highway line
   - **Progress Bar**: Horizontal bar showing journey progress (% of route completed)
   - **Position Card**: "Last seen at CP-06 (Maddur Toll) • 2 min ago"
   - **ETA Card**: "Estimated arrival: ~35 min"
   - **Remaining Tolls Card**: Count and total ₹ remaining
   - **Ahead Warnings**: Cards for upcoming zone issues on route
     - Pushed via `route_alert` Socket.IO event
     - Appear as slide-down notifications

3. **Trip Summary** (when journey completes):
   - Total time, distance, tolls paid, zones passed
   - Any incidents encountered

### Page: Track (Journey History)

- List of past journey queries (stored in localStorage)
- Quick re-query buttons
- Current highway status overview

### Socket.IO Integration (Commuter)

```javascript
// Connect
const socket = io('http://localhost:8000/commuter', {
  auth: { token: `Bearer ${jwt}` }
});

// Start tracking
socket.emit('track_journey', { plate: 'KA09AB1234', direction: 'MB' });

// Listen for updates
socket.on('journey_progress', (data) => {
  // { plate, last_checkpoint, estimated_km, remaining_km, eta_minutes }
  updateTripDashboard(data);
});

socket.on('route_alert', (data) => {
  // { zone_id, warning, severity, message }
  showAlertNotification(data);
});

// Stop tracking
socket.emit('stop_tracking', { plate: 'KA09AB1234' });
```

---

## Shared Design Tokens

Both apps should use consistent colors for data categories:

| Category | Color | Hex |
|----------|-------|-----|
| Legal alert | Red | `#ef4444` |
| ML alert | Orange | `#f97316` |
| Wildlife alert | Emerald | `#10b981` |
| Zone safe | Green | `#22c55e` |
| Zone warning | Yellow | `#eab308` |
| Zone danger | Orange | `#f97316` |
| Zone critical | Red | `#ef4444` |
| Primary accent | Blue | `#3b82f6` |
| Background (dark) | Slate 900 | `#0f172a` |
| Surface (dark) | Slate 800 | `#1e293b` |
| Text primary | White | `#f8fafc` |
| Text secondary | Slate 400 | `#94a3b8` |

### Typography

- Font family: `Inter` (Google Fonts)
- Headings: 600 weight
- Body: 400 weight
- Monospace (plates, IDs): `JetBrains Mono`

---

## Demo Flow Mapping

Each step of the 4-minute demo maps to specific UI interactions:

| Step | Action | UI Result |
|------|--------|-----------|
| 1 | Open authority dashboard | Live View tab. Corridor strip + map shows vehicles. Zones green. Heartbeat pulsing. Stats bar populated |
| 2 | Click "Simulate Incident" | ZONE-06 turns amber→red on both corridor strip and map. Alert sound plays. Alert appears in sidebar. Stats bar "Active Incidents: 1" |
| 3 | Click "Show Evasion Case" | ML alert appears in sidebar with chime. Click it → evidence panel shows journey timeline, 91% score, ₹320 loss |
| 4 | Click "Trigger Wildlife Alert" | ZONE-04 flashes on corridor strip and map. Wildlife bell sound. Alert in sidebar with forest department notification |
| 5 | Open commuter app | Query Mysore→Bangalore, 9pm, sedan. Results: 1h55m, ₹320, Zone 6 warning, Cauvery advisory, departure recommendation |
| 6 | Click "Confirm" on evasion alert | Feedback processed. Analytics tab: accuracy chart ticks up, FPR updates |
