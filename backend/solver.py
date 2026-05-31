import math

import networkx as nx
import osmnx as ox
from shapely.geometry import Point
from shapely.ops import nearest_points

ox.settings.use_cache = True
ox.settings.log_console = False
ox.settings.timeout = 300
ox.settings.max_query_area_size = 1000 * 1000 * 1000


class RouteSolver:
    def __init__(self):
        self.graph = None
        self.graph_undirected = None
        self.last_center = None
        self.last_radius = None

    def load_graph_for_points(self, coords):
        avg_lat = sum(c[0] for c in coords) / len(coords)
        avg_lng = sum(c[1] for c in coords) / len(coords)
        center_point = (avg_lat, avg_lng)

        max_dist = max(self._distance(center_point, c) for c in coords)
        radius = (max_dist * 111000) + 1500

        if radius > 20000:
            raise Exception("Area too large! Please keep markers within 20km.")

        if (
            self.graph is None
            or self.last_center is None
            or self._distance(self.last_center, center_point) * 111000 > 1000
            or radius > (self.last_radius or 0) + 1000
        ):
            print(f"--- Downloading map: {radius:.0f}m radius ---")
            try:
                G = ox.graph_from_point(
                    center_point,
                    dist=radius,
                    network_type="drive",
                    simplify=True,
                )
                self.graph = ox.truncate.largest_component(G, strongly=True)
                self.graph_undirected = self.graph.to_undirected()
                self.last_center = center_point
                self.last_radius = radius
            except Exception:
                raise Exception("Could not find a connected road network in this area.")

    def get_path_with_distance(self, start_coords, end_coords):
        """Return a road-following path from start to end, including short connectors to the road network."""
        start_snap, start_node = self._snap_to_road(start_coords)
        end_snap, end_node = self._snap_to_road(end_coords)

        node_path, _, used_undirected = self._shortest_path_nodes(start_node, end_node)
        if not node_path or len(node_path) < 2:
            raise Exception("No drivable path found between stops.")

        road_coords = self._node_path_to_coords(node_path, used_undirected)
        if not road_coords:
            raise Exception("Could not build road geometry for this segment.")

        route_coords = self._concat_coords(
            [start_coords],
            [start_snap],
            road_coords,
            [end_snap],
            [end_coords],
        )
        return {
            "coords": route_coords,
            "distance": self._polyline_length_meters(route_coords),
        }

    def solve_tsp(self, coords_list, return_to_start=False):
        n = len(coords_list)
        if n <= 2:
            return coords_list

        dist_matrix = [[0] * n for _ in range(n)]
        nodes = []
        snaps = []

        for c in coords_list:
            try:
                snap_coords, node = self._snap_to_road(c)
                nodes.append(node)
                snaps.append(snap_coords)
            except Exception:
                nodes.append(None)
                snaps.append(None)

        for i in range(n):
            for j in range(n):
                if i == j:
                    dist_matrix[i][j] = 0
                elif nodes[i] is not None and nodes[j] is not None:
                    _, network_meters, _ = self._shortest_path_nodes(nodes[i], nodes[j])
                    connector = self._haversine_meters(coords_list[i], snaps[i]) + self._haversine_meters(
                        snaps[j], coords_list[j]
                    )
                    dist_matrix[i][j] = network_meters + connector
                else:
                    dist_matrix[i][j] = self._haversine_meters(coords_list[i], coords_list[j]) * 1.2

        def get_route_dist(route):
            total = sum(dist_matrix[route[k]][route[k + 1]] for k in range(n - 1))
            if return_to_start and len(route) > 1:
                total += dist_matrix[route[-1]][route[0]]
            return total

        if n <= 10:
            import itertools

            best_path = None
            best_dist = float("inf")
            for perm in itertools.permutations(range(1, n)):
                route = [0] + list(perm)
                d = get_route_dist(route)
                if d < best_dist:
                    best_dist = d
                    best_path = route
            path_indices = best_path
        else:
            unvisited = set(range(1, n))
            path_indices = [0]
            while unvisited:
                curr = path_indices[-1]
                next_node = min(unvisited, key=lambda x: dist_matrix[curr][x])
                path_indices.append(next_node)
                unvisited.remove(next_node)

            improved = True
            while improved:
                improved = False
                best_dist = get_route_dist(path_indices)
                for i in range(1, n):
                    for j in range(1, n):
                        if i == j:
                            continue
                        new_path = path_indices[:]
                        node = new_path.pop(i)
                        new_path.insert(j, node)
                        new_dist = get_route_dist(new_path)
                        if new_dist < best_dist - 0.1:
                            path_indices = new_path
                            best_dist = new_dist
                            improved = True

        return [coords_list[i] for i in path_indices]

    def _distance(self, p1, p2):
        if p1 is None or p2 is None:
            return 0
        return ((p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2) ** 0.5

    def _polyline_length_meters(self, coords):
        if not coords or len(coords) < 2:
            return 0.0
        return sum(self._haversine_meters(coords[i], coords[i + 1]) for i in range(len(coords) - 1))

    def _haversine_meters(self, p1, p2):
        lat1, lon1 = p1
        lat2, lon2 = p2
        r = 6371000.0
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        dphi = math.radians(lat2 - lat1)
        dlambda = math.radians(lon2 - lon1)
        a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return r * c

    def _node_to_coords(self, node):
        return [self.graph.nodes[node]["y"], self.graph.nodes[node]["x"]]

    def _snap_to_road(self, point):
        """Project a click onto the nearest road edge and pick the closer endpoint node for routing."""
        lng, lat = point[1], point[0]
        u, v, key = ox.nearest_edges(self.graph, X=lng, Y=lat)
        edge_data = self.graph.get_edge_data(u, v, key) or self.graph[u][v][key]

        u_coords = self._node_to_coords(u)
        v_coords = self._node_to_coords(v)
        geom = edge_data.get("geometry")

        if geom is not None:
            snapped, _ = nearest_points(geom, Point(lng, lat))
            snap_coords = [snapped.y, snapped.x]
        else:
            snap_coords = (
                u_coords
                if self._haversine_meters(point, u_coords) <= self._haversine_meters(point, v_coords)
                else v_coords
            )

        node = u if self._haversine_meters(snap_coords, u_coords) <= self._haversine_meters(snap_coords, v_coords) else v
        return snap_coords, node

    def _nearest_node_for_point(self, point):
        _, node = self._snap_to_road(point)
        return node

    def _shortest_path_nodes(self, start_node, end_node):
        try:
            path = nx.shortest_path(self.graph, start_node, end_node, weight="length")
            dist = nx.path_weight(self.graph, path, weight="length")
            return path, float(dist), False
        except nx.NetworkXNoPath:
            pass
        except Exception:
            pass

        path = nx.shortest_path(self.graph_undirected, start_node, end_node, weight="length")
        dist = nx.path_weight(self.graph_undirected, path, weight="length")
        return path, float(dist), True

    def _node_path_to_coords(self, node_path, used_undirected=False):
        if not node_path or len(node_path) < 2:
            return []

        if not used_undirected:
            try:
                route_gdf = ox.routing.route_to_gdf(self.graph, node_path, weight="length")
                return self._gdf_to_coords(route_gdf)
            except Exception:
                pass

        return self._node_path_to_coords_manual(node_path)

    def _gdf_to_coords(self, route_gdf):
        coords = []
        for geom in route_gdf.geometry:
            if geom is None or geom.is_empty:
                continue
            coords.extend(self._geometry_to_coords(geom))
        return self._dedupe_consecutive(coords)

    def _node_path_to_coords_manual(self, node_path):
        coords = []
        for i in range(len(node_path) - 1):
            u = node_path[i]
            v = node_path[i + 1]
            geom = self._lookup_edge_geometry(u, v)
            if geom is not None:
                segment = self._geometry_to_coords(geom, directed=(u, v))
                coords = self._concat_coords(coords, segment)
            else:
                u_point = self._node_to_coords(u)
                v_point = self._node_to_coords(v)
                coords = self._concat_coords(coords, [u_point, v_point])
        return coords

    def _lookup_edge_geometry(self, u, v):
        edge_data = self.graph.get_edge_data(u, v)
        if edge_data:
            best = self._best_edge_data(edge_data)
            if best and best.get("geometry") is not None:
                return best["geometry"]

        edge_data = self.graph.get_edge_data(v, u)
        if edge_data:
            best = self._best_edge_data(edge_data)
            if best and best.get("geometry") is not None:
                return best["geometry"]
        return None

    def _geometry_to_coords(self, geom, directed=None):
        coords = []
        x_vals, y_vals = geom.xy
        points = [[y, x] for x, y in zip(x_vals, y_vals)]

        if directed is not None:
            u, v = directed
            u_point = self._node_to_coords(u)
            if self._haversine_meters(points[0], u_point) > self._haversine_meters(points[-1], u_point):
                points = list(reversed(points))

        for point in points:
            if not coords or self._coords_differ(coords[-1], point):
                coords.append(point)
        return coords

    def _best_edge_data(self, edge_data):
        if edge_data is None:
            return None
        if isinstance(edge_data, dict) and "length" in edge_data:
            return edge_data
        if isinstance(edge_data, dict):
            candidates = list(edge_data.values())
            if not candidates:
                return None
            return min(candidates, key=lambda d: d.get("length", float("inf")))
        if isinstance(edge_data, list):
            if not edge_data:
                return None
            return min(edge_data, key=lambda d: d.get("length", float("inf")))
        return None

    def _concat_coords(self, *segments):
        coords = []
        for segment in segments:
            for point in segment:
                if point is None:
                    continue
                if not coords or self._coords_differ(coords[-1], point):
                    coords.append(point)
        return coords

    def _dedupe_consecutive(self, coords):
        if not coords:
            return []
        deduped = [coords[0]]
        for point in coords[1:]:
            if self._coords_differ(deduped[-1], point):
                deduped.append(point)
        return deduped

    def _coords_differ(self, a, b, eps=1e-7):
        return abs(a[0] - b[0]) > eps or abs(a[1] - b[1]) > eps
