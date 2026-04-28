import os
import time
from typing import List

from fastapi import FastAPI, HTTPException
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

class RouteRequest(BaseModel):
    points: List[List[float]] = Field(..., min_length=2)


class RouteResponse(BaseModel):
    status: str
    optimized_stops: List[List[float]]
    full_path: List[List[float]]
    total_km: float
    solve_time_seconds: float
    leg_distances_km: List[float]


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


def _compute_route(raw_coords: List[List[float]]) -> RouteResponse:
    start_time = time.time()
    solver.load_graph_for_points(raw_coords)
    optimized_stops = solver.solve_tsp(raw_coords)

    full_path = []
    total_meters = 0.0
    leg_distances_km: List[float] = []
    for i in range(len(optimized_stops) - 1):
        result = solver.get_path_with_distance(optimized_stops[i], optimized_stops[i + 1])
        full_path.extend(result["coords"])
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
    )


@app.post("/route", response_model=RouteResponse)
async def post_route(payload: RouteRequest):
    try:
        points = _validate_points(payload.points)
        return _compute_route(points)
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Route optimization failed: {exc}") from exc


@app.get("/route")
async def get_route(points: str):
    try:
        parsed = [list(map(float, p.split(","))) for p in points.split(";") if p]
        return _compute_route(_validate_points(parsed))
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=f"Invalid points format: {exc}") from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Route optimization failed: {exc}") from exc

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)