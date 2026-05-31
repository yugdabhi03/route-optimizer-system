import os
import time
from typing import List

import httpx
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from solver import RouteSolver
import uvicorn

app = FastAPI()

cors_origins = os.getenv("CORS_ORIGINS", "*")
allow_origins = ["*"] if cors_origins.strip() == "*" else [o.strip() for o in cors_origins.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

solver = RouteSolver()
NOMINATIM_USER_AGENT = os.getenv(
    "NOMINATIM_USER_AGENT",
    "route-optimizer-system/1.0 (local development; contact via repository)",
)


class RouteRequest(BaseModel):
    points: List[List[float]] = Field(..., min_length=2)
    round_trip: bool = False


class RouteResponse(BaseModel):
    status: str
    optimized_stops: List[List[float]]
    full_path: List[List[float]]
    total_km: float
    solve_time_seconds: float
    leg_distances_km: List[float]
    round_trip: bool


class GeocodeResult(BaseModel):
    display_name: str
    lat: float
    lon: float


def _validate_points(points: List[List[float]]) -> List[List[float]]:
    cleaned: List[List[float]] = []
    for idx, point in enumerate(points):
        if len(point) != 2:
            raise HTTPException(status_code=422, detail=f"Point at index {idx} must contain exactly [lat, lng].")
        lat, lng = point
        if not (-90 <= lat <= 90):
            raise HTTPException(status_code=422, detail=f"Latitude out of range at index {idx}.")
        if not (-180 <= lng <= 180):
            raise HTTPException(status_code=422, detail=f"Longitude out of range at index {idx}.")
        cleaned.append([float(lat), float(lng)])
    return cleaned


def _append_segment(full_path: List[List[float]], segment_coords: List[List[float]]) -> None:
    if not segment_coords:
        return
    if full_path and (
        full_path[-1][0] == segment_coords[0][0] and full_path[-1][1] == segment_coords[0][1]
    ):
        segment_coords = segment_coords[1:]
    full_path.extend(segment_coords)


def _compute_route(raw_coords: List[List[float]], round_trip: bool = False) -> RouteResponse:
    start_time = time.time()
    solver.load_graph_for_points(raw_coords)
    optimized_stops = solver.solve_tsp(raw_coords, return_to_start=round_trip)

    full_path: List[List[float]] = []
    total_meters = 0.0
    leg_distances_km: List[float] = []

    legs: List[tuple] = []
    for i in range(len(optimized_stops) - 1):
        legs.append((optimized_stops[i], optimized_stops[i + 1]))
    if round_trip and len(optimized_stops) >= 2:
        legs.append((optimized_stops[-1], optimized_stops[0]))

    for start, end in legs:
        result = solver.get_path_with_distance(start, end)
        _append_segment(full_path, result["coords"])
        segment_meters = float(result["distance"])
        total_meters += segment_meters
        leg_distances_km.append(round(segment_meters / 1000, 3))

    solve_duration = round(time.time() - start_time, 3)
    return RouteResponse(
        status="success",
        optimized_stops=optimized_stops,
        full_path=full_path,
        total_km=round(total_meters / 1000, 2),
        solve_time_seconds=solve_duration,
        leg_distances_km=leg_distances_km,
        round_trip=round_trip,
    )


@app.post("/route", response_model=RouteResponse)
async def post_route(payload: RouteRequest):
    try:
        points = _validate_points(payload.points)
        return _compute_route(points, round_trip=payload.round_trip)
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Route optimization failed: {exc}") from exc


@app.get("/route")
async def get_route(points: str, round_trip: bool = False):
    try:
        parsed = [list(map(float, p.split(","))) for p in points.split(";") if p]
        return _compute_route(_validate_points(parsed), round_trip=round_trip)
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=f"Invalid points format: {exc}") from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Route optimization failed: {exc}") from exc


@app.get("/geocode", response_model=List[GeocodeResult])
async def geocode_search(q: str = Query(..., min_length=3, max_length=200)):
    query = q.strip()
    if not query:
        raise HTTPException(status_code=422, detail="Search query cannot be empty.")

    headers = {
        "User-Agent": NOMINATIM_USER_AGENT,
        "Accept": "application/json",
        "Accept-Language": "en",
    }
    params = {
        "q": query,
        "format": "jsonv2",
        "limit": 5,
        "addressdetails": 0,
    }

    try:
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            response = await client.get(
                "https://nominatim.openstreetmap.org/search",
                params=params,
                headers=headers,
            )
            if response.status_code == 429:
                raise HTTPException(
                    status_code=502,
                    detail="Too many searches. Wait a few seconds and try again.",
                )
            response.raise_for_status()
            payload = response.json()
    except HTTPException:
        raise
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=502,
            detail="Address search is temporarily unavailable. Check your internet connection.",
        ) from exc
    except ValueError as exc:
        raise HTTPException(status_code=502, detail="Address search returned invalid data.") from exc

    results: List[GeocodeResult] = []
    for item in payload:
        try:
            results.append(
                GeocodeResult(
                    display_name=item["display_name"],
                    lat=float(item["lat"]),
                    lon=float(item["lon"]),
                )
            )
        except (KeyError, TypeError, ValueError):
            continue
    return results


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
