from solver import RouteSolver
solver = RouteSolver()

points = [
    [43.66, -79.39],
    [43.6601, -79.3901] # Very close point
]

solver.load_graph_for_points(points)
result = solver.get_path_with_distance(points[0], points[1])
print("Result distance:", result["distance"])
