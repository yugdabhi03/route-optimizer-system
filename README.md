# Route Optimizer

A small full-stack app for planning a driving route through several stops. You add points on a map (or search by address), the backend picks a sensible visit order and builds a path along real roads, and the frontend draws it on an interactive map.

## What it does

1. Add stops by clicking the map or searching an address.
2. Reorder, remove, or undo stops before you run the optimizer.
3. Optionally enable **round trip** so the route returns to the first stop.
4. The backend downloads a local OpenStreetMap road graph (via OSMnx), solves a TSP-style ordering problem, and computes turn-by-turn geometry with NetworkX.
5. The map shows the ordered stops, total distance, per-leg distances, and lets you export CSV (stops) or GPX (track).

Routing runs on your machine against OSM data. There is no Mapbox/Google routing API key.

## Screenshots

| Main view | After optimize |
|-----------|----------------|
| ![Main view](docs/screenshots/main-view.png) | ![Optimized route](docs/screenshots/optimized-itinerary.png) |

## Project layout

```
route-optimizer-system/
├── backend/          FastAPI, OSMnx routing, TSP solver
├── frontend/         React + Vite + Leaflet
├── docs/screenshots/
└── .github/workflows/ci.yml
```

## Requirements

- Python 3.11+
- Node.js 20+
- Internet on first run (OSM graph download is cached under `backend/cache/`)

## Run locally

### Backend

```bash
cd backend
python -m venv venv

# Windows
venv\Scripts\activate
# macOS / Linux
# source venv/bin/activate

pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

API docs: http://127.0.0.1:8000/docs

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open the URL Vite prints (usually http://localhost:5173).

For local development you can skip a frontend `.env` file — Vite proxies `/route` and `/geocode` to port 8000. To point at another host, copy `.env.example` to `.env` and set `VITE_API_BASE_URL`.

### Backend environment (optional)

Copy `backend/.env.example` to `backend/.env` if you need:

| Variable | Purpose |
|----------|---------|
| `CORS_ORIGINS` | Allowed browser origins (default `*`) |
| `NOMINATIM_USER_AGENT` | Contact string for address search (Nominatim requires this) |

## API

### `POST /route`

```json
{
  "points": [[43.6532, -79.3832], [43.66, -79.39]],
  "round_trip": false
}
```

| Field | Description |
|-------|-------------|
| `optimized_stops` | Stops in visit order `[lat, lng]` |
| `full_path` | Polyline for the map |
| `total_km` | Approximate driving distance |
| `leg_distances_km` | Distance per leg |
| `round_trip` | Whether the return leg was included |
| `solve_time_seconds` | Wall time for the request |

### `GET /geocode?q=toronto`

Returns up to five `{ display_name, lat, lon }` results. The backend calls Nominatim so the browser does not hit their API directly.

## Tests and CI

```bash
cd backend && python -m pytest -q
cd frontend && npm run lint && npm run build
```

GitHub Actions runs the same checks on push and pull requests.

## Limitations

- Map and routing quality depend on OpenStreetMap in the area you pick.
- Very large areas (>20 km spread) are rejected to keep graph downloads reasonable.
- Address search is subject to Nominatim usage limits; do not hammer it.
- Distances are estimates for planning, not for billing or compliance.

## Possible next steps

- Public deployment and a live demo link in this README
- Shareable URLs that encode a stop list
- Drag-and-drop reorder on the map
