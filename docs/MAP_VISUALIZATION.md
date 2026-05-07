# Map Visualization Engine

## Overview

The Map Visualization Engine is a core GIS component within the Authority Dashboard. It uses OpenStreetMap tiles (via Leaflet) styled to resemble a clean, professional dark-mode map (similar to Google Maps night mode). It provides a high-level spatial understanding of the NH-275 corridor without overwhelming the user with raw data streams.

This feature consumes existing data from the AI and hard logic layers; it serves purely as a visualization tool to make the system's insights instantly comprehensible to control room operators.

## Map Modes

The map operates in two distinct, toggleable modes.

### 1. Live Section Mode

Visualizes the current, near real-time state of the highway. The 120km stretch is divided into 11 distinct sections (zones between checkpoints).

**Visual Architecture:**
*   **Base Map:** Dark-themed vector tiles (e.g., CartoDB Dark Matter) to make data overlays pop.
*   **Highway Track:** A thick polyline representing NH-275.
*   **Section Coloring:** The polyline is segmented. Each segment is color-coded based on its current anomaly score or active incidents:
    *   Green: Normal flow
    *   Yellow: Elevated motion index or minor anomaly
    *   Orange: Active wildlife alert or medium incident
    *   Red: Critical incident / blockage
*   **Live Metrics:** Floating badges attached to the center of each section display the current number of active vehicles in that specific zone.

**Interactivity (On-Click):**
Clicking on any colored section or checkpoint node opens a detail panel (replacing the alert feed sidebar temporarily) containing:
*   **Zone / Checkpoint Name** (e.g., "Maddur–Mandya Forest Entry")
*   **Live Status:** Active incident descriptions or wildlife alerts.
*   **Current Vehicle Density:** Live count from the `GET /zones` API.
*   **Infrastructure Inventory:** A list of all `camera_ids` (e.g., CAM-028, CAM-029) monitoring this specific section.
*   **Motion Index:** A mini sparkline chart showing the CCTV motion average over the last 5 minutes.

### 2. Historical Insights Mode (30-Day)

Switches the map to visualize aggregated ML insights and historical data over the past 30 days. This mode is crucial for long-term planning and patrol deployment.

**Visual Architecture:**
*   **Section Coloring:** Segments are color-coded based on their 30-day overall `risk_tier` (Low/Moderate/High/Critical) computed by the nightly Risk Zone Scorer.
*   **Hotspot Heatmap:** A gradient blur overlay (red/yellow/blue) layered over the route, showing the geographic density of *confirmed evasion cases* and *historical accidents*.

**Interactivity (On-Click):**
Clicking a section in Historical Mode opens an insights panel containing:
*   **Dominant Risk Type:** Why is this zone risky? (e.g., `evasion_concentration`, `wildlife_crossings`).
*   **Incident Count (30d):** Total accidents/breakdowns recorded in this segment.
*   **Evasion Density:** Number of confirmed hard-logic and ML evasion cases in the last 30 days.
*   **Peak Risk Hours:** A 24-hour bar chart showing the time-of-day risk curve for this specific segment (e.g., showing risk spikes at 2 AM for truck traffic).

## Technical Implementation Guidelines

### Frontend (React)
*   **Libraries:** `react-leaflet` for map rendering, `leaflet.heat` for the 30-day hotspot overlay.
*   **GeoJSON:** The exact curves of NH-275 should be extracted as a static GeoJSON file. The polyline should be split into 11 `Feature` objects matching the `zone_id`s.
*   **State Management:** The map component subscribes to the `zone_update` Socket.IO event to gracefully change section colors and update vehicle count badges without full re-renders.

### Connectivity to Existing Architecture
This feature fits seamlessly into the planned backend:
*   **Live Mode** relies entirely on the output of the **Zone State Aggregator** (`zone_state:{zone_id}` in Redis) and the `checkpoints` table for camera inventory.
*   **Historical Mode** relies entirely on the output of the **Risk Zone Scorer** (`zone_risk_profiles` table) and the seeded `historical_incidents` table.

### API Connectivity Note
The data required for these visualizations is already covered by the existing API contracts:
*   Live section colors and vehicle counts: `GET /zones?highway_id=NH-275`
*   Historical risk colors and 24-hour curves: `GET /zones/{zone_id}/risk-profile`
*   Camera list per checkpoint: `GET /checkpoints?highway_id=NH-275`

---

## Scalability: Multi-Highway Support (Product Vision)

While the hackathon prototype specifically simulates and monitors the **Mysore–Bangalore Expressway (NH-275)**, the visualization engine and underlying architecture are designed for national scale.

**How it scales:**
1.  **Global Highway Selector:** The Authority Dashboard features a top-level dropdown (e.g., `NH-275 (Mysore-BLR)`, `NH-48 (Mumbai-Pune)`, `NH-44 (North-South Corridor)`).
2.  **Dynamic GeoJSON Loading:** Selecting a different highway simply fetches a new GeoJSON track and dynamically recenters the Leaflet map bounds.
3.  **Data Partitioning:** All backend APIs (e.g., `/zones`, `/checkpoints`) accept a `highway_id` parameter. The Redis streams and PostgreSQL tables are partitioned by this ID.

*For the demo, the selector is present in the UI to demonstrate product completeness, but only the `NH-275` option contains active data streams.*
