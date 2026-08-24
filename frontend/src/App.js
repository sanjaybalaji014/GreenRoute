import React, { useState, useRef, useEffect } from 'react';
import { MapContainer, TileLayer, Marker, Popup, Polyline, useMap } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import L from 'leaflet';
import './App.css';
 
// Fixes a known leaflet + webpack bundling issue where marker icons don't show up
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
  iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
  shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
});
 
const CAR_MAKES = [
  'Toyota', 'Honda', 'Ford', 'Chevrolet', 'Nissan',
  'BMW', 'Mercedes-Benz', 'Hyundai', 'Kia', 'Tesla', 'Subaru',
];
 
const GAS_TYPES = [
  { value: '87', label: '87 (Regular)' },
  { value: '89', label: '89 (Mid-Grade)' },
  { value: '91', label: '91 (Premium)' },
  { value: 'diesel', label: 'Diesel' },
];
 
// TODO: change this to your target city's coordinates
const CITY_CENTER = [37.7749, -122.4194];
 
// ---- Mock data generator ----
// Stand-in for your friend's backend so you can build/test the UI right now.
// Swap the body of handleGetRoutes() for a real fetch() once the API endpoint exists.
function generateMockRoutes(start, end, weights) {
  const count = 3 + Math.floor(Math.random() * 4); // 3-6 routes for demo purposes
  const routes = [];
 
  for (let i = 0; i < count; i++) {
    const distance = 2 + Math.random() * 6; // miles
    const travelTime = distance * (2 + Math.random() * 2); // minutes
    const congestionDelta = Math.random() * 6 - 1; // +/- minutes vs free-flow
    const fuelGallons = distance / (28 + Math.random() * 10);
    const fuelPrice = fuelGallons * 3.6;
    const emissions = distance * (0.3 + Math.random() * 0.15);
    const safetyScore = Math.random();
 
    const speedComponent = 1 - travelTime / 30;
    const ecoComponent = 1 - emissions / 3;
    const safetyComponent = safetyScore;
    const overall =
      (weights.speed / 100) * speedComponent +
      (weights.eco / 100) * ecoComponent +
      (weights.safety / 100) * safetyComponent;
 
    routes.push({
      id: i,
      name: `Route ${String.fromCharCode(65 + i)}`,
      path: [
        start,
        [
          start[0] + (end[0] - start[0]) * 0.5 + (Math.random() - 0.5) * 0.01,
          start[1] + (end[1] - start[1]) * 0.5 + (Math.random() - 0.5) * 0.01,
        ],
        end,
      ],
      metrics: {
        travelTime,
        congestionDelta,
        distance,
        fuelGallons,
        fuelPrice,
        emissions,
        safetyScore,
      },
      overall,
    });
  }
 
  return routes.sort((a, b) => b.overall - a.overall);
}
 
function FitBounds({ path }) {
  const map = useMap();
  React.useEffect(() => {
    if (path && path.length > 1) {
      map.invalidateSize();
      map.fitBounds(path, { padding: [12, 12] });
    }
  }, [path, map]);
  return null;
}
 
// Leaflet sometimes grabs the wrong container size when it mounts inside a
// CSS grid layout (before the grid has settled its final dimensions), or
// when a panel gets dragged wider/narrower — both show up as grey tiles
// until you drag/zoom. A ResizeObserver on the map's own container catches
// both cases (initial mount AND panel-resize-drag) automatically.
function MapResizeFix() {
  const map = useMap();
  React.useEffect(() => {
    const container = map.getContainer();
    const fix = () => map.invalidateSize();
    const t1 = setTimeout(fix, 150);
    const ro = new ResizeObserver(fix);
    ro.observe(container);
    return () => {
      clearTimeout(t1);
      ro.disconnect();
    };
  }, [map]);
  return null;
}
 
// Small preview showing the real map with this route's path drawn on top.
// Non-interactive (no drag/zoom/scroll) so it reads as a "picture," not a
// second map to fiddle with. Uses the same MapResizeFix as the main map so
// it doesn't grey out — that greying earlier was a container-sizing issue
// (mounting before the grid settled), not the tile server itself.
function RouteMiniMap({ route, active }) {
  const mid = route.path[Math.floor(route.path.length / 2)];
  return (
    <div className="route-card-map">
      <MapContainer
        className="mini-map"
        center={mid}
        zoom={13}
        dragging={false}
        zoomControl={false}
        scrollWheelZoom={false}
        doubleClickZoom={false}
        boxZoom={false}
        keyboard={false}
        touchZoom={false}
        attributionControl={false}
      >
        <TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
        <Polyline
          positions={route.path}
          pathOptions={{ color: active ? '#ff7a1a' : '#a8d5ba', weight: 4 }}
        />
        <FitBounds path={route.path} />
        <MapResizeFix />
      </MapContainer>
    </div>
  );
}
 
function RouteCard({ route, active, onSelect }) {
  const m = route.metrics;
  return (
    <div
      className={`route-card ${active ? 'route-card-active' : ''}`}
      onClick={() => onSelect(route.id)}
    >
      <div className="route-card-header">
        <span className="route-card-name">{route.name}</span>
        <span className="route-card-score">{(route.overall * 100).toFixed(0)}</span>
      </div>
 
      <RouteMiniMap route={route} active={active} />
 
      <div className="route-card-metrics">
        <div className="metric">
          <span className="metric-label">Travel time</span>
          <span className="metric-value">{m.travelTime.toFixed(1)} min</span>
        </div>
        <div className="metric">
          <span className="metric-label">Traffic delay</span>
          <span className={`metric-value ${m.congestionDelta >= 0 ? 'metric-bad' : 'metric-good'}`}>
            {m.congestionDelta >= 0 ? '+' : ''}
            {m.congestionDelta.toFixed(1)} min
          </span>
        </div>
        <div className="metric">
          <span className="metric-label">Distance</span>
          <span className="metric-value">{m.distance.toFixed(1)} mi</span>
        </div>
        <div className="metric">
          <span className="metric-label">Fuel</span>
          <span className="metric-value">
            {m.fuelGallons.toFixed(2)} gal (${m.fuelPrice.toFixed(2)})
          </span>
        </div>
        <div className="metric">
          <span className="metric-label">Emissions</span>
          <span className="metric-value metric-green">{m.emissions.toFixed(2)} kg CO2</span>
        </div>
        <div className="metric">
          <span className="metric-label">Safety score</span>
          <span className="metric-value">{(m.safetyScore * 100).toFixed(0)}/100</span>
        </div>
      </div>
    </div>
  );
}
 
function App() {
  const [startText, setStartText] = useState('');
  const [endText, setEndText] = useState('');
  const [carMake, setCarMake] = useState(CAR_MAKES[0]);
  const [gasType, setGasType] = useState(GAS_TYPES[0].value);
 
  const [weights, setWeights] = useState({ speed: 34, eco: 33, safety: 33 });
 
  const [routes, setRoutes] = useState([]);
  const [selectedRouteId, setSelectedRouteId] = useState(null);
  const [loading, setLoading] = useState(false);
 
  // Draggable panel widths — left is the inputs sidebar, right is the routes panel
  const [leftWidth, setLeftWidth] = useState(280);
  const [rightWidth, setRightWidth] = useState(460);
  const draggingRef = useRef(null); // 'left' | 'right' | null
 
  useEffect(() => {
    function handleMouseMove(e) {
      if (!draggingRef.current) return;
      if (draggingRef.current === 'left') {
        const next = Math.min(480, Math.max(220, e.clientX));
        setLeftWidth(next);
      } else if (draggingRef.current === 'right') {
        const next = Math.min(640, Math.max(300, window.innerWidth - e.clientX));
        setRightWidth(next);
      }
    }
    function handleMouseUp() {
      draggingRef.current = null;
      document.body.style.userSelect = '';
      document.body.style.cursor = '';
    }
    window.addEventListener('mousemove', handleMouseMove);
    window.addEventListener('mouseup', handleMouseUp);
    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseup', handleMouseUp);
    };
  }, []);
 
  function startDragging(side) {
    return (e) => {
      e.preventDefault();
      draggingRef.current = side;
      document.body.style.userSelect = 'none';
      document.body.style.cursor = 'col-resize';
    };
  }
 
  const selectedRoute = routes.find((r) => r.id === selectedRouteId);
 
  // Keeps the 3 sliders summing to 100 by scaling the other two proportionally
  function handleWeightChange(key, value) {
    value = Number(value);
    const others = Object.keys(weights).filter((k) => k !== key);
    const remaining = 100 - value;
    const othersSum = others.reduce((sum, k) => sum + weights[k], 0) || 1;
 
    const updated = { ...weights, [key]: value };
    others.forEach((k) => {
      updated[k] = Math.round((weights[k] / othersSum) * remaining);
    });
 
    const drift = 100 - (updated.speed + updated.eco + updated.safety);
    updated[others[0]] += drift;
 
    setWeights(updated);
  }
 
  // customWeights lets preset buttons pass their weights directly, instead of
  // waiting on setWeights() to finish updating state before firing the request.
  async function handleGetRoutes(customWeights) {
    const useWeights = customWeights || weights;
 
    // --- Replace this whole block once the backend endpoint is ready ---
    // const response = await fetch('http://localhost:5000/route', {
    //   method: 'POST',
    //   headers: { 'Content-Type': 'application/json' },
    //   body: JSON.stringify({ start, end, weights: useWeights, carMake, gasType }),
    // });
    // const data = await response.json();
    // setRoutes(data.routes);
    // ---------------------------------------------------------------
 
    setLoading(true);
    const start = CITY_CENTER;
    const end = [CITY_CENTER[0] + 0.02, CITY_CENTER[1] + 0.02];
 
    setTimeout(() => {
      const generated = generateMockRoutes(start, end, useWeights);
      setRoutes(generated);
      setSelectedRouteId(generated[0].id);
      setLoading(false);
    }, 400);
  }
 
  const PRESETS = {
    fastest: { speed: 100, eco: 0, safety: 0 },
    eco: { speed: 0, eco: 100, safety: 0 },
    safest: { speed: 0, eco: 0, safety: 100 },
  };
 
  function handlePreset(name) {
    const presetWeights = PRESETS[name];
    setWeights(presetWeights);
    handleGetRoutes(presetWeights);
  }
 
  return (
    <div className="app">
      <header className="app-header">
        <div className="logo">
          <div className="logo-badge">
            <svg viewBox="0 0 48 48" className="logo-icon">
              {/* large leaf outline */}
              <path
                d="M24 2 C8 8 2 24 10 35 C15 42 24 46 24 46 C24 46 33 42 38 35 C46 24 40 8 24 2 Z"
                fill="#a8d5ba"
                stroke="#ffffff"
                strokeWidth="1.5"
              />
              {/* central vein + branching route-veins, in white */}
              <path
                d="M24 42 L24 6 M24 33 L13 23 M24 33 L35 23 M24 20 L15 12 M24 20 L33 12"
                fill="none"
                stroke="#ffffff"
                strokeWidth="1.8"
                strokeLinecap="round"
              />
            </svg>
          </div>
          <div className="logo-text">
            <h1>
              <span className="accent-green">GREEN</span>
              <span className="accent-orange">ROUTE</span>
            </h1>
            <p className="logo-subtitle">Speed. Eco. Safety. Your route, your priorities.</p>
          </div>
        </div>
      </header>
 
      <div
        className="app-body"
        style={{ gridTemplateColumns: `${leftWidth}px 6px 1fr 6px ${rightWidth}px` }}
      >
        <aside className="panel panel-inputs">
          <section className="panel-section">
            <h2>Trip</h2>
            <label>Start location</label>
            <input
              type="text"
              placeholder="e.g. 123 Main St"
              value={startText}
              onChange={(e) => setStartText(e.target.value)}
            />
            <label>End location</label>
            <input
              type="text"
              placeholder="e.g. 456 Market St"
              value={endText}
              onChange={(e) => setEndText(e.target.value)}
            />
          </section>
 
          <section className="panel-section">
            <h2>Vehicle</h2>
            <label>Car make</label>
            <select value={carMake} onChange={(e) => setCarMake(e.target.value)}>
              {CAR_MAKES.map((make) => (
                <option key={make} value={make}>
                  {make}
                </option>
              ))}
            </select>
            <label>Gas type</label>
            <select value={gasType} onChange={(e) => setGasType(e.target.value)}>
              {GAS_TYPES.map((g) => (
                <option key={g.value} value={g.value}>
                  {g.label}
                </option>
              ))}
            </select>
          </section>
 
          <section className="panel-section">
            <h2>Presets</h2>
            <div className="preset-row">
              <button
                className="preset-btn preset-btn-orange"
                onClick={() => handlePreset('fastest')}
                disabled={loading}
              >
                Fastest
              </button>
              <button
                className="preset-btn preset-btn-green"
                onClick={() => handlePreset('eco')}
                disabled={loading}
              >
                Eco
              </button>
              <button
                className="preset-btn preset-btn-orange"
                onClick={() => handlePreset('safest')}
                disabled={loading}
              >
                Safest
              </button>
            </div>
          </section>
 
          <section className="panel-section">
            <h2>Priorities</h2>
            <div className="slider-row">
              <label>
                Speed <span>{weights.speed}%</span>
              </label>
              <input
                type="range"
                min="0"
                max="100"
                value={weights.speed}
                onChange={(e) => handleWeightChange('speed', e.target.value)}
                className="slider slider-orange"
              />
            </div>
            <div className="slider-row">
              <label>
                Eco <span>{weights.eco}%</span>
              </label>
              <input
                type="range"
                min="0"
                max="100"
                value={weights.eco}
                onChange={(e) => handleWeightChange('eco', e.target.value)}
                className="slider slider-green"
              />
            </div>
            <div className="slider-row">
              <label>
                Safety <span>{weights.safety}%</span>
              </label>
              <input
                type="range"
                min="0"
                max="100"
                value={weights.safety}
                onChange={(e) => handleWeightChange('safety', e.target.value)}
                className="slider slider-orange"
              />
            </div>
          </section>
 
          <button className="get-route-btn" onClick={handleGetRoutes} disabled={loading}>
            {loading ? 'Finding routes...' : 'Get Routes'}
          </button>
        </aside>
 
        <div className="resizer" onMouseDown={startDragging('left')} />
 
        <main className="panel-map">
          <MapContainer center={CITY_CENTER} zoom={13} className="map">
            <TileLayer
              url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
              attribution="&copy; OpenStreetMap contributors"
            />
            {routes.map((route) => (
              <Polyline
                key={route.id}
                positions={route.path}
                pathOptions={{
                  color: route.id === selectedRouteId ? '#ff7a1a' : '#4a4a4a',
                  weight: route.id === selectedRouteId ? 5 : 3,
                  opacity: route.id === selectedRouteId ? 1 : 0.5,
                }}
                eventHandlers={{ click: () => setSelectedRouteId(route.id) }}
              />
            ))}
            {selectedRoute && (
              <>
                <Marker position={selectedRoute.path[0]}>
                  <Popup>Start</Popup>
                </Marker>
                <Marker position={selectedRoute.path[selectedRoute.path.length - 1]}>
                  <Popup>End</Popup>
                </Marker>
                <FitBounds path={selectedRoute.path} />
              </>
            )}
            <MapResizeFix />
          </MapContainer>
        </main>
 
        <div className="resizer" onMouseDown={startDragging('right')} />
 
        <aside className="panel panel-results">
          <h2>Routes</h2>
          {routes.length === 0 && <p className="muted">Set your trip and hit "Get Routes."</p>}
 
          <div className="route-cards">
            {routes.map((route) => (
              <RouteCard
                key={route.id}
                route={route}
                active={route.id === selectedRouteId}
                onSelect={setSelectedRouteId}
              />
            ))}
          </div>
        </aside>
      </div>
    </div>
  );
}
 
export default App;