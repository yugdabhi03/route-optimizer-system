function escapeXml(value) {
    return String(value)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;");
}

function downloadFile(filename, content, mimeType) {
    const blob = new Blob([content], { type: mimeType });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = filename;
    link.click();
    URL.revokeObjectURL(url);
}

function findStopLabel(stops, coords) {
    const match = stops.find(
        (s) => Math.abs(s.coords[0] - coords[0]) < 1e-6 && Math.abs(s.coords[1] - coords[1]) < 1e-6,
    );
    return match?.label || "";
}

export function exportStopsCsv({ stops, orderedStops, legDistancesKm, totalKm, roundTrip }) {
    const rows = [["order", "label", "lat", "lng"]];
    const usingOptimized = orderedStops?.length > 0;

    if (usingOptimized) {
        orderedStops.forEach((coords, index) => {
            rows.push([
                String(index + 1),
                findStopLabel(stops, coords),
                coords[0].toFixed(6),
                coords[1].toFixed(6),
            ]);
        });
    } else {
        stops.forEach((stop, index) => {
            rows.push([
                String(index + 1),
                stop.label || "",
                stop.coords[0].toFixed(6),
                stop.coords[1].toFixed(6),
            ]);
        });
    }

    if (totalKm != null) {
        rows.push([]);
        rows.push(["total_km", String(totalKm)]);
        rows.push(["round_trip", roundTrip ? "yes" : "no"]);
        if (legDistancesKm?.length) {
            rows.push(["leg_km", legDistancesKm.join("|")]);
        }
    }

    const csv = rows.map((row) => row.map((cell) => `"${String(cell).replace(/"/g, '""')}"`).join(",")).join("\n");
    downloadFile("route-stops.csv", csv, "text/csv;charset=utf-8");
}

export function exportRouteGpx({ fullPath, orderedStops, stops, roundTrip }) {
    const points = fullPath?.length
        ? fullPath
        : (orderedStops?.length ? orderedStops : stops.map((s) => s.coords));

    const waypoints = orderedStops?.length ? orderedStops : stops.map((s) => s.coords);
    const wptXml = waypoints
        .map((coords, index) => {
            const name = findStopLabel(stops, coords) || `Stop ${index + 1}`;
            return `<wpt lat="${coords[0]}" lon="${coords[1]}"><name>${escapeXml(name)}</name></wpt>`;
        })
        .join("");

    const trkptXml = points
        .map((coords) => `<trkpt lat="${coords[0]}" lon="${coords[1]}"></trkpt>`)
        .join("");

    const gpx = `<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1" creator="Route Optimizer" xmlns="http://www.topografix.com/GPX/1/1">
  <metadata><name>Route Optimizer Export</name></metadata>
  ${wptXml}
  <trk>
    <name>${roundTrip ? "Round trip route" : "Optimized route"}</name>
    <trkseg>${trkptXml}</trkseg>
  </trk>
</gpx>`;

    downloadFile("route.gpx", gpx, "application/gpx+xml;charset=utf-8");
}
