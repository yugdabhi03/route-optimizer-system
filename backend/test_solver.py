from main import _validate_points
from solver import RouteSolver


def test_validate_points_accepts_valid_values():
    points = [[43.6532, -79.3832], [43.66, -79.39]]
    assert _validate_points(points) == points


def test_distance_returns_zero_for_none():
    solver = RouteSolver()
    assert solver._distance(None, [1, 2]) == 0


def test_distance_positive_for_two_points():
    solver = RouteSolver()
    assert solver._distance([43.65, -79.38], [43.66, -79.39]) > 0
