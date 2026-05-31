export function createStop(coords, label = "") {
    return {
        id: crypto.randomUUID(),
        coords,
        label,
    };
}

export function formatCoords(coords) {
    return `${coords[0].toFixed(5)}, ${coords[1].toFixed(5)}`;
}

export function stopsToPoints(stops) {
    return stops.map((stop) => stop.coords);
}
