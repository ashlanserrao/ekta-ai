"""Live-data tools the LLM can call against the SQLite digital twin.

Each tool returns plain dicts/lists that are JSON-serializable so results can be
fed straight back to the model (or rendered deterministically by the orchestrator).
Errors are returned as {"error": ...} payloads rather than raised, so a failed
tool never aborts a chat turn.
"""
import logging
import sqlite3

from backend.app.database import db_connection
from backend.app.routing import find_path

logger = logging.getLogger("tools")

AVAILABLE_ZONES = "Zone-A, Zone-B, Zone-C, Zone-D, Zone-VIP"


def _normalize(s: str) -> str:
    return "".join(c for c in s.lower() if c.isalnum())


def get_crowd_density(zone: str) -> dict:
    """
    Gets the current crowd density and capacity information for a specific stadium zone or concourse.
    :param zone: The zone ID (e.g. 'Zone-A', 'Zone-B', 'Zone-C') or zone name.
    """
    if not zone:
        return {"error": f"Zone name or ID must be provided. Available: {AVAILABLE_ZONES}"}

    try:
        with db_connection() as conn:
            row = conn.execute(
                "SELECT id, name, type, capacity, current_crowd, density FROM zones WHERE id = ? OR name LIKE ?",
                (zone, f"%{zone}%"),
            ).fetchone()
        if row:
            return dict(row)
        return {"error": f"Zone '{zone}' not found. Available: {AVAILABLE_ZONES}"}
    except sqlite3.Error as e:
        logger.error(f"Database error in get_crowd_density: {e}")
        return {"error": "Unable to retrieve zone details at this time."}


def get_gate_status() -> list:
    """
    Gets the status (open/closed) and congestion level of all stadium gates.
    """
    try:
        with db_connection() as conn:
            rows = conn.execute(
                "SELECT id, name, status, congestion_level, zone_id FROM gates"
            ).fetchall()
        return [dict(row) for row in rows]
    except sqlite3.Error as e:
        logger.error(f"Database error in get_gate_status: {e}")
        return []


def _resolve_node_name(query: str) -> str:
    """Map a free-text location ('gate 2', 'Section 204') onto a routing-graph node id.

    Falls back to the raw query if no node matches, so find_path can still report
    an honest 'no route found' for unknown locations.
    """
    q_norm = _normalize(query)
    if not q_norm:
        return query

    try:
        with db_connection() as conn:
            nodes = [r["id"] for r in conn.execute("SELECT id FROM nodes").fetchall()]
    except sqlite3.Error as e:
        logger.error(f"Database error in _resolve_node_name: {e}")
        return query

    # Prefer an exact normalized match, then fall back to substring containment.
    for node in nodes:
        if _normalize(node) == q_norm:
            return node
    for node in nodes:
        n_norm = _normalize(node)
        if q_norm in n_norm or n_norm in q_norm:
            return node
    return query


def get_route(from_location: str, to_location: str, accessibility_required: bool = False) -> dict:
    """
    Retrieves the routing path between two locations, filtering for wheelchair accessibility if required.
    :param from_location: Start point (e.g., 'Gate 1', 'Gate 2')
    :param to_location: Destination point (e.g., 'Section 102', 'Section 204')
    :param accessibility_required: True if step-free accessible route is needed.
    """
    if not from_location or not to_location:
        return {"error": "Both start location (from_location) and destination (to_location) must be provided."}

    resolved_from = _resolve_node_name(from_location)
    resolved_to = _resolve_node_name(to_location)

    try:
        path = find_path(resolved_from, resolved_to, accessibility_required)
    except sqlite3.Error as e:
        logger.error(f"Error computing path in find_path: {e}")
        return {"error": "Unable to calculate route path at this time."}

    if not path:
        return {"error": f"No route found from {from_location} to {to_location}."}

    return {
        "id": f"route_{resolved_from.replace(' ', '_')}_{resolved_to.replace(' ', '_')}_{'acc' if accessibility_required else 'std'}",
        "from_location": resolved_from,
        "to_location": resolved_to,
        "path_nodes": path,
        "is_accessible": 1 if accessibility_required else 0,
    }
