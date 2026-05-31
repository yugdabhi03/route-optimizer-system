import { useEffect } from "react";
import { useMap } from "react-leaflet";
import L from "leaflet";

export default function MapFitBounds({ points, enabled }) {
    const map = useMap();

    useEffect(() => {
        if (!enabled || !points?.length) {
            return;
        }
        const bounds = L.latLngBounds(points.map(([lat, lng]) => [lat, lng]));
        map.fitBounds(bounds, { padding: [72, 72], maxZoom: 16 });
    }, [map, points, enabled]);

    return null;
}
