import React, { useState } from 'react';
import { MapContainer, TileLayer, Marker, Polyline, useMapEvents, Popup, ZoomControl } from 'react-leaflet';
import axios from 'axios';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import './index.css';

// Function to create a numbered icon
const createNumberedIcon = (number, isLast, isFirst) => {
    let bg = "bg-blue-600";
    if (isFirst) bg = "bg-emerald-500";
    if (isLast && !isFirst) bg = "bg-rose-500";

    return L.divIcon({
        html: `<div class="w-8 h-8 rounded-full ${bg} text-white flex items-center justify-center font-bold border-2 border-white shadow-[0_4px_10px_rgba(0,0,0,0.3)] transform hover:scale-110 transition-transform">
            ${number}
        </div>`,
        className: "",
        iconSize: [32, 32],
        iconAnchor: [16, 16]
    });
};

function MapClickHandler({ onAddMarker }) {
    useMapEvents({
        click: (e) => onAddMarker([e.latlng.lat, e.latlng.lng]),
    });
    return null;
}

function App() {
    const [markers, setMarkers] = useState([]); // User clicks
    const [orderedMarkers, setOrderedMarkers] = useState([]); // Markers after backend optimization
    const [route, setRoute] = useState([]);
    const [loading, setLoading] = useState(false);
    const [routeStats, setRouteStats] = useState(null);
    const [errorMessage, setErrorMessage] = useState("");

    const handleOptimize = async () => {
        if (markers.length < 2) {
            alert("Please add at least 2 points!");
            return;
        }
        setLoading(true);
        setErrorMessage("");
        try {
            const apiUrl = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
            const response = await axios.post(`${apiUrl}/route`, { points: markers });

            setOrderedMarkers(response.data.optimized_stops);
            setRoute(response.data.full_path);
            setRouteStats({
                solveTimeSeconds: response.data.solve_time_seconds
            });
        } catch (error) {
            console.error("Error:", error);
            setRouteStats(null);
            const apiError = error?.response?.data?.detail;
            setErrorMessage(apiError || "Optimization failed. Check backend console.");
        }
        setLoading(false);
    };

    const clearMap = () => {
        setMarkers([]);
        setOrderedMarkers([]);
        setRoute([]);
        setRouteStats(null);
        setErrorMessage("");
    };

    return (
        <div className="h-screen w-screen relative bg-slate-100 overflow-hidden text-slate-800">
            {/* Control Panel */}
            <div className="absolute top-6 left-6 z-[1000] w-[340px] max-h-[calc(100vh-3rem)] overflow-y-auto custom-scrollbar glass-panel rounded-2xl p-6 flex flex-col gap-5">
                <div className="flex items-center gap-4 border-b border-slate-200/50 pb-4">
                    <div className="bg-gradient-to-br from-blue-500 to-indigo-600 p-2.5 rounded-xl shadow-lg shadow-blue-500/30">
                        <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2.5" d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7" /></svg>
                    </div>
                    <div>
                        <h3 className="text-xl font-bold tracking-tight m-0">Route Optimizer</h3>
                        <p className="text-xs text-blue-600 font-semibold uppercase tracking-widest mt-0.5">Professional</p>
                    </div>
                </div>

                <div className="flex flex-col gap-3">
                    <button 
                        onClick={handleOptimize} 
                        disabled={loading || markers.length < 2} 
                        className={`w-full py-3.5 px-4 rounded-xl font-semibold text-white transition-all duration-300 flex items-center justify-center gap-2 outline-none border-none
                            ${loading || markers.length < 2 ? 'bg-slate-300 text-slate-500 cursor-not-allowed' : 'bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 hover:shadow-[0_8px_20px_-6px_rgba(79,70,229,0.5)] hover:-translate-y-0.5 active:translate-y-0 cursor-pointer'}`}
                    >
                        {loading ? (
                            <><svg className="animate-spin -ml-1 mr-2 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg> Calculating Optimal Path...</>
                        ) : (
                            <><svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 10V3L4 14h7v7l9-11h-7z" /></svg> Optimize Route</>
                        )}
                    </button>
                    
                    <button 
                        onClick={clearMap} 
                        className="w-full py-2.5 px-4 rounded-xl font-medium text-slate-600 bg-white/60 hover:bg-white border border-slate-200 transition-all hover:shadow-sm flex items-center justify-center gap-2 cursor-pointer outline-none"
                    >
                        <svg className="w-4 h-4 text-rose-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" /></svg>
                        Clear Map
                    </button>
                </div>
                
                <div className="text-sm text-slate-600 bg-blue-50/70 p-3.5 rounded-xl border border-blue-100 shadow-inner">
                    <p className="flex items-start gap-2.5 m-0 leading-relaxed">
                        <span className="text-blue-500 font-bold mt-0.5 text-base">ℹ</span> 
                        Click anywhere on the map to add destinations. Add at least 2 points to start optimizing.
                    </p>
                </div>

                {routeStats && (
                    <div className="bg-emerald-50/80 border border-emerald-100 rounded-xl p-3.5 text-sm text-emerald-900">
                        <p className="m-0 font-semibold">Optimization complete</p>
                        <p className="m-0">Solve time: {routeStats.solveTimeSeconds}s</p>
                    </div>
                )}

                {errorMessage && (
                    <div className="bg-rose-50/90 border border-rose-200 rounded-xl p-3.5 text-sm text-rose-900">
                        {errorMessage}
                    </div>
                )}

                {orderedMarkers.length > 0 && (
                    <div className="mt-1 flex flex-col h-full max-h-[40vh]">
                        <div className="text-xs font-bold text-slate-400 uppercase tracking-widest mb-3 px-1">Optimized Itinerary</div>
                        <div className="flex flex-col gap-2.5 overflow-y-auto pr-2 pb-2 custom-scrollbar">
                            {orderedMarkers.map((_, i) => (
                                <div key={i} className="flex items-center gap-3 bg-white/70 p-3 rounded-xl border border-slate-100 shadow-sm transition-all hover:bg-white hover:shadow-md hover:-translate-y-0.5">
                                    <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold text-white shadow-sm
                                        ${i === 0 ? 'bg-emerald-500' : i === orderedMarkers.length - 1 ? 'bg-rose-500' : 'bg-blue-500'}`}>
                                        {i + 1}
                                    </div>
                                    <div className="flex flex-col">
                                        <span className="text-sm font-bold text-slate-700">
                                            {i === 0 ? "Start Location" : i === orderedMarkers.length - 1 ? "Final Destination" : `Waypoint ${i}`}
                                        </span>
                                        <span className="text-xs font-medium text-slate-400">
                                            Stop #{i + 1}
                                        </span>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>
                )}
            </div>

            <MapContainer center={[43.6532, -79.3832]} zoom={13} className="h-full w-full z-0" zoomControl={false}>
                {/* Modern CartoDB Base Map */}
                <TileLayer 
                    url="https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png" 
                    attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>'
                />
                
                <ZoomControl position="topright" />
                
                <MapClickHandler onAddMarker={(newLoc) => setMarkers([...markers, newLoc])} />

                {(orderedMarkers.length > 0 ? orderedMarkers : markers).map((pos, idx) => (
                    <Marker 
                        key={idx} 
                        position={pos} 
                        icon={createNumberedIcon(
                            idx + 1, 
                            idx === (orderedMarkers.length || markers.length) - 1,
                            idx === 0
                        )}
                    >
                        <Popup className="font-outfit rounded-xl">
                            <div className="font-bold text-slate-800 text-center px-2 py-1">
                                {idx === 0 ? "Start Location" : idx === (orderedMarkers.length || markers.length) - 1 ? "End Location" : `Stop ${idx + 1}`}
                            </div>
                        </Popup>
                    </Marker>
                ))}

                {route.length > 0 && (
                    <Polyline 
                        positions={route} 
                        pathOptions={{ 
                            color: "#3b82f6", 
                            weight: 6, 
                            opacity: 0.9,
                            lineCap: "round",
                            lineJoin: "round",
                            className: 'path-animation'
                        }} 
                    />
                )}
            </MapContainer>
        </div>
    );
}

export default App;