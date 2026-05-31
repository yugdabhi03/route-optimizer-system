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


def test_concat_coords_deduplicates_join_points():
    solver = RouteSolver()
    merged = solver._concat_coords([[43.65, -79.38], [43.66, -79.39]], [[43.66, -79.39], [43.67, -79.40]])
    assert merged == [[43.65, -79.38], [43.66, -79.39], [43.67, -79.40]]


def test_polyline_length_for_two_points():
    solver = RouteSolver()
    length = solver._polyline_length_meters([[43.65, -79.38], [43.66, -79.39]])
    assert length > 0


def test_return_leg_increases_tour_cost():
    dist_matrix = [[0, 10, 12], [10, 0, 4], [12, 4, 0]]
    route = [0, 1, 2]
    open_dist = sum(dist_matrix[route[k]][route[k + 1]] for k in range(2))
    round_dist = open_dist + dist_matrix[route[-1]][route[0]]
    assert round_dist > open_dist
