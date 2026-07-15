import heapq
import logging
from backend.app.database import get_db_connection

logger = logging.getLogger("routing")

def find_path(from_node: str, to_node: str, accessible_only: bool = False) -> list:
    """
    Computes the shortest path between from_node and to_node.
    If accessible_only is True, non-accessible edges (stairs) are excluded.
    Returns a list of node names/IDs in traversal order, or an empty list if unreachable.
    """
    logger.info(f"Routing query: from_node='{from_node}', to_node='{to_node}', accessible_only={accessible_only}")
    
    if from_node == to_node:
        return [from_node]
        
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 1. Fetch edges matching accessibility constraints
    if accessible_only:
        cursor.execute("SELECT from_node, to_node, distance_or_weight FROM edges WHERE is_accessible = 1")
    else:
        cursor.execute("SELECT from_node, to_node, distance_or_weight FROM edges")
        
    rows = cursor.fetchall()
    conn.close()
    
    # 2. Build adjacency list representation (undirected graph)
    graph = {}
    for row in rows:
        u, v, w = row["from_node"], row["to_node"], row["distance_or_weight"]
        if u not in graph:
            graph[u] = []
        if v not in graph:
            graph[v] = []
        graph[u].append((v, w))
        graph[v].append((u, w))
        
    # Check if endpoints exist in graph
    if from_node not in graph or to_node not in graph:
        logger.warning(f"Nodes not found in edges graph: from='{from_node}', to='{to_node}'")
        return []
        
    # 3. Dijkstra's shortest path algorithm
    # Priority Queue elements format: (cumulative_distance, current_node, path_list)
    pq = [(0.0, from_node, [from_node])]
    visited = set()
    
    while pq:
        dist, current, path = heapq.heappop(pq)
        
        if current in visited:
            continue
        visited.add(current)
        
        if current == to_node:
            logger.info(f"Shortest path found: {path} (distance: {dist})")
            return path
            
        for neighbor, weight in graph.get(current, []):
            if neighbor not in visited:
                heapq.heappush(pq, (dist + weight, neighbor, path + [neighbor]))
                
    logger.warning(f"No path found between '{from_node}' and '{to_node}' under accessibility constraints.")
    return []
