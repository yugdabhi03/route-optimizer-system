from fastapi.testclient import TestClient

from main import app
import main as main_module


client = TestClient(app)


def test_post_route_success(monkeypatch):
    points = [[43.6532, -79.3832], [43.66, -79.39]]

    monkeypatch.setattr(main_module.solver, "load_graph_for_points", lambda _: None)
    monkeypatch.setattr(main_module.solver, "solve_tsp", lambda _: points)
    monkeypatch.setattr(
        main_module.solver,
        "get_path_with_distance",
        lambda start, end: {"coords": [start, end], "distance": 1250},
    )

    response = client.post("/route", json={"points": points})
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "success"
    assert payload["optimized_stops"] == points
    assert payload["total_km"] == 1.25
    assert payload["leg_distances_km"] == [1.25]
    assert "solve_time_seconds" in payload


def test_post_route_validation_error():
    response = client.post("/route", json={"points": [[120.0, -79.3], [43.6, -79.2]]})
    assert response.status_code == 422
    assert "Latitude out of range" in response.json()["detail"]

