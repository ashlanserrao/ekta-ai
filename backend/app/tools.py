import logging
from backend.app.database import get_db_connection

logger = logging.getLogger("tools")

def get_crowd_density(zone: str) -> dict:
    """
    Gets the current crowd density and capacity information for a specific stadium zone or concourse.
    :param zone: The zone ID (e.g. 'Zone-A', 'Zone-B', 'Zone-C') or zone name.
    """
    if not zone:
        return {"error": "Zone name or ID must be provided. Available: Zone-A, Zone-B, Zone-C, Zone-D, Zone-VIP"}
        
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, name, capacity, current_crowd, density FROM zones WHERE id = ? OR name LIKE ?",
            (zone, f"%{zone}%")
        )
        row = cursor.fetchone()
        conn.close()
        if row:
            return dict(row)
        return {"error": f"Zone '{zone}' not found. Available: Zone-A, Zone-B, Zone-C, Zone-D, Zone-VIP"}
    except Exception as e:
        logger.error(f"Database error in get_crowd_density: {e}")
        return {"error": "Unable to retrieve zone details at this time."}

def get_gate_status() -> list:
    """
    Gets the status (open/closed) and congestion level of all stadium gates.
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, status, congestion_level, zone_id FROM gates")
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]
    except Exception as e:
        logger.error(f"Database error in get_gate_status: {e}")
        return []

def get_route(from_location: str, to_location: str, accessibility_required: bool = False) -> dict:
    """
    Retrieves the routing path between two locations, filtering for wheelchair accessibility if required.
    :param from_location: Start point (e.g., 'Gate 1', 'Gate 2')
    :param to_location: Destination point (e.g., 'Section 102', 'Section 204')
    :param accessibility_required: True if step-free accessible route is needed.
    """
    if not from_location or not to_location:
        return {"error": "Both start location (from_location) and destination (to_location) must be provided."}
        
    from backend.app.routing import find_path
    
    def resolve_node_name(query: str) -> str:
        if not query:
            return ""
        
        def normalize(s: str) -> str:
            return "".join(c for c in s.lower() if c.isalnum())
            
        q_norm = normalize(query)
        if not q_norm:
            return query
            
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM nodes")
            nodes = [r["id"] for r in cursor.fetchall()]
            conn.close()
        except Exception as e:
            logger.error(f"Database error in resolve_node_name: {e}")
            return query
            
        # 1. Check exact normalized match
        for node in nodes:
            if normalize(node) == q_norm:
                return node
                
        # 2. Check substring normalized match
        for node in nodes:
            n_norm = normalize(node)
            if q_norm in n_norm or n_norm in q_norm:
                return node
                
        return query
        
    resolved_from = resolve_node_name(from_location)
    resolved_to = resolve_node_name(to_location)
    
    try:
        path = find_path(resolved_from, resolved_to, accessibility_required)
    except Exception as e:
        logger.error(f"Error computing path in find_path: {e}")
        return {"error": "Unable to calculate route path at this time."}
        
    if not path:
        return {"error": f"No route found from {from_location} to {to_location}."}
        
    return {
        "id": f"route_{resolved_from.replace(' ', '_')}_{resolved_to.replace(' ', '_')}_{'acc' if accessibility_required else 'std'}",
        "from_location": resolved_from,
        "to_location": resolved_to,
        "path_nodes": path,
        "is_accessible": 1 if accessibility_required else 0
    }
