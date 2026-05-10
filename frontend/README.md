# Emergency Routing System Frontend

React + Vite dispatch console for the FastAPI emergency-routing backend.

## Features

- Leaflet/OpenStreetMap route visualization
- G-8 Islamabad boundary coordinates from `map_load/map.py`
- Click-to-select from/to points with road snapping through FastAPI
- Responder-to-incident and incident-to-hospital route legs
- Animated emergency vehicle movement trail
- Browser GPS tracking with accuracy circle
- Backend `/route/coordinates` routing from map-selected points

## Run

```bash
npm install
npm run dev
```

Start the backend separately on `http://127.0.0.1:8000`; Vite proxies `/route` to it.
