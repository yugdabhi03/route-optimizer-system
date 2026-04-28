from solver import RouteSolver
solver = RouteSolver()

points = [
    [43.6532, -79.3832],
    [43.66, -79.39],
    [43.64, -79.38]
]

solver.load_graph_for_points(points)

nodes = []
for c in points:
    try:
        import osmnx as ox
        edge = ox.nearest_edges(solver.graph, X=c[1], Y=c[0])
        print("Edge is:", edge)
    except Exception as e:
        print("Exception:", e)
