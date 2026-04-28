from solver import RouteSolver
solver = RouteSolver()

points = [
    [43.66, -79.39],
    [43.64, -79.38]
]

solver.load_graph_for_points(points)
result = solver.get_path_with_distance(points[0], points[1])
print("Num coords:", len(result["coords"]))
print("Distance:", result["distance"])
