import React, { useCallback, useMemo, useState } from 'react';
import { MapContainer, TileLayer, Marker, Polyline, useMapEvents, Popup, ZoomControl } from 'react-leaflet';
import axios from 'axios';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import './index.css';
import AddressSearch from './components/AddressSearch';
import MapFitBounds from './components/MapFitBounds';
import { exportRouteGpx, exportStopsCsv } from './utils/exportRoute';
import { createStop, formatCoords, stopsToPoints } from './utils/stops';

const DEFAULT_CENTER = [43.6532, -79.3832];

const createNumberedIcon = (number, isLast, isFirst) => {
    let variant = 'marker-waypoint';
    if (isFirst) variant = 'marker-start';
    else if (isLast) variant = 'marker-end';

    return L.divIcon({
        html: `<div class="route-marker ${variant}">${number}</div>`,
        className: '',
        iconSize: [28, 28],
        iconAnchor: [14, 14],
    });
};

function MapClickHandler({ onAddMarker, disabled }) {
    useMapEvents({
        click: (e) => {
            if (!disabled) {
                onAddMarker([e.latlng.lat, e.latlng.lng]);
            }
        },
    });
    return null;
}

function labelForOptimizedStop(stops, coords, index, total, roundTrip) {
    const match = stops.find(
        (s) => Math.abs(s.coords[0] - coords[0]) < 1e-6 && Math.abs(s.coords[1] - coords[1]) < 1e-6,
    );
    if (match?.label) return match.label;
    if (index === 0) return 'Start';
    if (roundTrip && index === total - 1) return 'Return to start';
    if (!roundTrip && index === total - 1) return 'End';
    return `Stop ${index + 1}`;
}

function App() {
    const [stops, setStops] = useState([]);
    const [undoStack, setUndoStack] = useState([]);
    const [orderedStops, setOrderedStops] = useState([]);
    const [route, setRoute] = useState([]);
    const [loading, setLoading] = useState(false);
    const [routeStats, setRouteStats] = useState(null);
    const [errorMessage, setErrorMessage] = useState('');
    const [validationMessage, setValidationMessage] = useState('');
    const [roundTrip, setRoundTrip] = useState(false);
    const [fitMap, setFitMap] = useState(false);
    const [routeHighlight, setRouteHighlight] = useState(false);
    const [mobilePanelOpen, setMobilePanelOpen] = useState(true);

    // In dev, use Vite proxy (same origin) when VITE_API_BASE_URL is unset.
    const apiUrl =
        import.meta.env.VITE_API_BASE_URL ??
        (import.meta.env.DEV ? '' : 'http://localhost:8000');

    const pushUndo = useCallback((snapshot) => {
        setUndoStack((prev) => [...prev.slice(-19), snapshot]);
    }, []);

    const resetRoute = useCallback(() => {
        setOrderedStops([]);
        setRoute([]);
        setRouteStats(null);
        setFitMap(false);
        setRouteHighlight(false);
    }, []);

    const mutateStops = useCallback(
        (updater) => {
            setStops((prev) => {
                pushUndo(prev);
                const next = typeof updater === 'function' ? updater(prev) : updater;
                return next;
            });
            resetRoute();
            setErrorMessage('');
            setValidationMessage('');
        },
        [pushUndo, resetRoute],
    );

    const addStop = useCallback(
        (coords, label = '') => {
            mutateStops((prev) => [...prev, createStop(coords, label)]);
        },
        [mutateStops],
    );

    const removeStop = (id) => mutateStops((prev) => prev.filter((s) => s.id !== id));

    const moveStop = (index, direction) => {
        mutateStops((prev) => {
            const next = [...prev];
            const target = index + direction;
            if (target < 0 || target >= next.length) return prev;
            [next[index], next[target]] = [next[target], next[index]];
            return next;
        });
    };

    const undo = () => {
        setUndoStack((prev) => {
            if (!prev.length) return prev;
            const snapshot = prev[prev.length - 1];
            setStops(snapshot);
            resetRoute();
            setErrorMessage('');
            return prev.slice(0, -1);
        });
    };

    const clearAll = () => {
        setStops([]);
        setUndoStack([]);
        resetRoute();
        setErrorMessage('');
        setValidationMessage('');
    };

    const handleOptimize = async () => {
        if (stops.length < 2) {
            setValidationMessage('Add at least 2 stops on the map or via search.');
            return;
        }
        setLoading(true);
        setErrorMessage('');
        setValidationMessage('');
        try {
            const response = await axios.post(`${apiUrl}/route`, {
                points: stopsToPoints(stops),
                round_trip: roundTrip,
            });

            setOrderedStops(response.data.optimized_stops);
            setRoute(response.data.full_path);
            setRouteStats({
                solveTimeSeconds: response.data.solve_time_seconds,
                totalKm: response.data.total_km,
                legDistancesKm: response.data.leg_distances_km,
                roundTrip: response.data.round_trip,
            });
            setFitMap(true);
            setRouteHighlight(true);
            setTimeout(() => setRouteHighlight(false), 2500);
        } catch (error) {
            console.error(error);
            setRouteStats(null);
            const apiError = error?.response?.data?.detail;
            setErrorMessage(apiError || 'Could not calculate route. Is the backend running?');
        }
        setLoading(false);
    };

    const displayStops = useMemo(() => {
        if (!orderedStops.length) return stops;
        return orderedStops.map((coords, index) => ({
            id: `opt-${index}`,
            coords,
            label: labelForOptimizedStop(stops, coords, index, orderedStops.length, routeStats?.roundTrip ?? roundTrip),
        }));
    }, [stops, orderedStops, routeStats?.roundTrip, roundTrip]);

    const mapPoints = route.length ? route : displayStops.map((s) => s.coords);
    const canExport = orderedStops.length > 0 || stops.length > 0;
    const isOptimized = orderedStops.length > 0;

    return (
        <div className="app-shell">
            <MapContainer center={DEFAULT_CENTER} zoom={13} className="map-layer" zoomControl={false}>
                <TileLayer
                    url="https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png"
                    attribution='&copy; OpenStreetMap &copy; CARTO'
                />
                <ZoomControl position="bottomright" />
                <MapFitBounds points={mapPoints} enabled={fitMap} />
                <MapClickHandler onAddMarker={(coords) => addStop(coords)} disabled={loading} />

                {displayStops.map((stop, idx) => {
                    const total = displayStops.length;
                    const isFirst = idx === 0;
                    const isLast = idx === total - 1;

                    return (
                        <Marker
                            key={stop.id}
                            position={stop.coords}
                            icon={createNumberedIcon(idx + 1, isLast, isFirst)}
                        >
                            <Popup>
                                <div className="text-sm font-medium text-slate-800">
                                    {stop.label || `Stop ${idx + 1}`}
                                </div>
                                <div className="text-xs text-slate-500">{formatCoords(stop.coords)}</div>
                            </Popup>
                        </Marker>
                    );
                })}

                {route.length > 0 && (
                    <Polyline
                        positions={route}
                        pathOptions={{
                            color: '#0f766e',
                            weight: 5,
                            opacity: 0.92,
                            lineCap: 'round',
                            lineJoin: 'round',
                            className: routeHighlight ? 'route-line route-line-new' : 'route-line',
                        }}
                    />
                )}
            </MapContainer>

            <button
                type="button"
                className="mobile-panel-toggle md:hidden"
                onClick={() => setMobilePanelOpen((v) => !v)}
                aria-expanded={mobilePanelOpen}
            >
                {mobilePanelOpen ? 'Hide panel' : 'Show route controls'}
            </button>

            <aside className={`control-panel ${mobilePanelOpen ? 'panel-open' : 'panel-closed'}`}>
                <header className="panel-header">
                    <div>
                        <h1 className="panel-title">Route Optimizer</h1>
                        <p className="panel-subtitle">Add stops, optimize order, export your route</p>
                    </div>
                </header>

                <AddressSearch apiUrl={apiUrl} onSelect={addStop} disabled={loading} />

                <label className="round-trip-toggle">
                    <input
                        type="checkbox"
                        checked={roundTrip}
                        onChange={(e) => {
                            setRoundTrip(e.target.checked);
                            resetRoute();
                        }}
                        disabled={loading}
                    />
                    <span>Round trip (return to start)</span>
                </label>

                <div className="action-row">
                    <button
                        type="button"
                        className="btn btn-primary"
                        onClick={handleOptimize}
                        disabled={loading || stops.length < 2}
                    >
                        {loading ? 'Calculating…' : 'Optimize route'}
                    </button>
                    <button type="button" className="btn btn-secondary" onClick={undo} disabled={!undoStack.length || loading}>
                        Undo
                    </button>
                </div>

                <button type="button" className="btn btn-ghost" onClick={clearAll} disabled={!stops.length && !route.length}>
                    Clear all
                </button>

                {validationMessage && <p className="message message-warn">{validationMessage}</p>}
                {errorMessage && <p className="message message-error">{errorMessage}</p>}

                {routeStats && (
                    <div className="stats-card">
                        <p className="stats-title">Route summary</p>
                        <p>{routeStats.totalKm} km total</p>
                        {routeStats.legDistancesKm?.length > 0 && (
                            <p className="stats-detail">
                                {routeStats.legDistancesKm.map((km, i) => `Leg ${i + 1}: ${km} km`).join(' · ')}
                            </p>
                        )}
                        <p className="stats-detail">
                            {routeStats.roundTrip ? 'Round trip' : 'One-way'} · {routeStats.solveTimeSeconds}s
                        </p>
                    </div>
                )}

                {canExport && (
                    <div className="export-row">
                        <button
                            type="button"
                            className="btn btn-secondary"
                            onClick={() =>
                                exportStopsCsv({
                                    stops,
                                    orderedStops,
                                    legDistancesKm: routeStats?.legDistancesKm,
                                    totalKm: routeStats?.totalKm,
                                    roundTrip: routeStats?.roundTrip ?? roundTrip,
                                })
                            }
                        >
                            Export CSV
                        </button>
                        <button
                            type="button"
                            className="btn btn-secondary"
                            onClick={() =>
                                exportRouteGpx({
                                    fullPath: route,
                                    orderedStops,
                                    stops,
                                    roundTrip: routeStats?.roundTrip ?? roundTrip,
                                })
                            }
                        >
                            Export GPX
                        </button>
                    </div>
                )}

                <section className="stops-section">
                    <div className="stops-header">
                        <h2>Stops ({stops.length})</h2>
                        {!isOptimized && <span className="stops-hint">Click map to add</span>}
                        {isOptimized && <span className="stops-hint">Optimized order</span>}
                    </div>

                    {stops.length === 0 ? (
                        <p className="stops-empty">No stops yet. Search an address or click the map.</p>
                    ) : (
                        <ul className="stops-list">
                            {(isOptimized ? displayStops : stops).map((stop, index) => (
                                <li key={stop.id} className="stop-item">
                                    <span className="stop-index">{index + 1}</span>
                                    <div className="stop-body">
                                        <span className="stop-label">{stop.label || `Stop ${index + 1}`}</span>
                                        <span className="stop-coords">{formatCoords(stop.coords)}</span>
                                    </div>
                                    {!isOptimized && (
                                        <div className="stop-actions">
                                            <button
                                                type="button"
                                                className="icon-btn"
                                                onClick={() => moveStop(index, -1)}
                                                disabled={index === 0}
                                                aria-label="Move up"
                                            >
                                                ↑
                                            </button>
                                            <button
                                                type="button"
                                                className="icon-btn"
                                                onClick={() => moveStop(index, 1)}
                                                disabled={index === stops.length - 1}
                                                aria-label="Move down"
                                            >
                                                ↓
                                            </button>
                                            <button
                                                type="button"
                                                className="icon-btn icon-btn-danger"
                                                onClick={() => removeStop(stop.id)}
                                                aria-label="Remove stop"
                                            >
                                                ×
                                            </button>
                                        </div>
                                    )}
                                </li>
                            ))}
                        </ul>
                    )}
                </section>
            </aside>
        </div>
    );
}

export default App;
