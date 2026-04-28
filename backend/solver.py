import osmnx as ox
import networkx as nx
import math

# Industry settings for OSMnx v2.0
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

        max_dist = max([self._distance(center_point, c) for c in coords])
        radius = (max_dist * 111000) + 1500 

        # --- SAFETY CAP ---
        if radius > 20000:
            raise Exception("Area too large! Please keep markers within 20km for urban optimization.")

        if (self.graph is None or 
            self.last_center is None or 
            self._distance(self.last_center, center_point) * 111000 > 1000 or
            radius > (self.last_radius or 0) + 1000):
            
            print(f"--- Downloading map: {radius:.0f}m radius ---")
            try:
                G = ox.graph_from_point(center_point, dist=radius, network_type="drive", simplify=True)
                self.graph = ox.truncate.largest_component(G, strongly=True)
                self.graph_undirected = self.graph.to_undirected()
                self.last_center = center_point
                self.last_radius = radius
            except Exception as e:
                raise Exception("Could not find a connected road network in this area.")

    def get_path_with_distance(self, start_coords, end_coords):
        """Return road-following path and robust distance between two clicked points."""
        try:
            start_node = self._nearest_node_for_point(start_coords)
            end_node = self._nearest_node_for_point(end_coords)
            node_path, path_meters, used_undirected = self._shortest_path_nodes(start_node, end_node)
            if not node_path:
                raise Exception("No drivable path found between stops.")

            graph_for_geom = self.graph_undirected if used_undirected else self.graph
            route_coords = self._node_path_to_coords(graph_for_geom, node_path)
            if not route_coords:
                route_coords = [start_coords, end_coords]

            connector_meters = self._haversine_meters(start_coords, route_coords[0]) + self._haversine_meters(route_coords[-1], end_coords)
            total_meters = max(0.0, path_meters + connector_meters)
            return {"coords": route_coords, "distance": total_meters}
        except Exception as e:
            import traceback
            print(f"Pathfinding Error: {e}")
            traceback.print_exc()
            # Avoid silently returning misleading near-zero distances.
            raise Exception("Could not compute a valid drivable path for this segment.")

    def solve_tsp(self, coords_list):
        n = len(coords_list)
        if n <= 2:
            return coords_list

        # 1. Map each coordinate to its nearest graph node to compute accurate distances.
        dist_matrix = [[0] * n for _ in range(n)]
        
        nodes = []
        for c in coords_list:
            try:
                node = self._nearest_node_for_point(c)
                nodes.append(node)
            except Exception:
                nodes.append(None)
                
        for i in range(n):
            for j in range(n):
                if i == j:
                    dist_matrix[i][j] = 0
                elif nodes[i] is not None and nodes[j] is not None:
                    _, network_meters, _ = self._shortest_path_nodes(nodes[i], nodes[j])
                    connector = self._haversine_meters(coords_list[i], self._node_to_coords(nodes[i])) + self._haversine_meters(self._node_to_coords(nodes[j]), coords_list[j])
                    dist_matrix[i][j] = network_meters + connector
                else:
                    # Fallback to straight line distance
                    dist_matrix[i][j] = self._haversine_meters(coords_list[i], coords_list[j]) * 1.2

        # Helper to calculate total distance of a route
        def get_route_dist(route):
            return sum(dist_matrix[route[k]][route[k+1]] for k in range(n-1))

        if n <= 10:
            # For small N, find the absolute mathematically optimal path
            import itertools
            best_path = None
            best_dist = float('inf')
            
            # Start node is always 0
            for perm in itertools.permutations(range(1, n)):
                route = [0] + list(perm)
                d = get_route_dist(route)
                if d < best_dist:
                    best_dist = d
                    best_path = route
                    
            path_indices = best_path
        else:
            # For large N, use Nearest-Neighbor followed by Node Relocation (not reversal)
            # Reversal (standard 2-opt) fails on asymmetric directed graphs (one-way streets)
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
                
                # Node Relocation: Try moving node at index i to position j
                for i in range(1, n):
                    for j in range(1, n):
                        if i == j: continue
                        
                        new_path = path_indices[:]
                        node = new_path.pop(i)
                        new_path.insert(j, node)
                        
                        new_dist = get_route_dist(new_path)
                        if new_dist < best_dist - 0.1:
                            path_indices = new_path
                            best_dist = new_dist
                            improved = True

        # 4. Map indices back to original coordinates
        return [coords_list[i] for i in path_indices]

    def _distance(self, p1, p2):
        if p1 is None or p2 is None: return 0
        return ((p1[0]-p2[0])**2 + (p1[1]-p2[1])**2)**0.5

    def _polyline_length_meters(self, coords):
        if not coords or len(coords) < 2:
            return 0.0
        total = 0.0
        for i in range(len(coords) - 1):
            total += self._haversine_meters(coords[i], coords[i + 1])
        return total

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

    def _nearest_node_for_point(self, point):
        edge = ox.nearest_edges(self.graph, X=point[1], Y=point[0])
        u, v, _ = edge
        u_coords = self._node_to_coords(u)
        v_coords = self._node_to_coords(v)
        if self._haversine_meters(point, u_coords) <= self._haversine_meters(point, v_coords):
            return u
        return v

    def _shortest_path_nodes(self, start_node, end_node):
        try:
            path = nx.shortest_path(self.graph, start_node, end_node, weight="length")
            dist = nx.path_weight(self.graph, path, weight="length")
            return path, float(dist), False
        except Exception:
            path = nx.shortest_path(self.graph_undirected, start_node, end_node, weight="length")
            dist = nx.path_weight(self.graph_undirected, path, weight="length")
            return path, float(dist), True

    def _node_path_to_coords(self, graph_obj, node_path):
        if not node_path:
            return []
        coords = []
        for i in range(len(node_path) - 1):
            u = node_path[i]
            v = node_path[i + 1]
            edge_data = graph_obj.get_edge_data(u, v)
            best = self._best_edge_data(edge_data)
            if best and "geometry" in best and best["geometry"] is not None:
                x_vals, y_vals = best["geometry"].xy
                for x, y in zip(x_vals, y_vals):
                    point = [y, x]
                    if not coords or coords[-1] != point:
                        coords.append(point)
            else:
                u_point = [graph_obj.nodes[u]["y"], graph_obj.nodes[u]["x"]]
                v_point = [graph_obj.nodes[v]["y"], graph_obj.nodes[v]["x"]]
                if not coords or coords[-1] != u_point:
                    coords.append(u_point)
                if coords[-1] != v_point:
                    coords.append(v_point)
        return coords

    def _best_edge_data(self, edge_data):
        if edge_data is None:
            return None
        if isinstance(edge_data, dict):
            if "length" in edge_data:
                return edge_data
            candidates = list(edge_data.values())
            if not candidates:
                return None
            return min(candidates, key=lambda d: d.get("length", float("inf")))
        if isinstance(edge_data, list):
            if not edge_data:
                return None
            return min(edge_data, key=lambda d: d.get("length", float("inf")))
        return None