"""Public transit endpoint for the Fan Portal's "Getting Here" view.

Serves the live transit-line state from the digital twin plus a GenAI departure
advisory (cached, deterministic fallback). Public like the other stadium
telemetry endpoints — fans need this before they authenticate anywhere.
"""
import logging
import sqlite3
import time

from fastapi import APIRouter, HTTPException

from backend.app.models import TransitStatus
from backend.app.services.transit_service import (
    egress_capacity_per_minute,
    generate_transit_advisory,
    get_transit_lines,
)

logger = logging.getLogger("routers.transit")

router = APIRouter(prefix="/api/v1/transit", tags=["transit"])


@router.get("", response_model=TransitStatus)
def read_transit_status():
    try:
        lines = get_transit_lines()
    except sqlite3.Error as e:
        logger.error(f"Error reading transit lines: {e}")
        raise HTTPException(status_code=500, detail="Database connection error while retrieving transit status.")

    return {
        "lines": lines,
        "advisory": generate_transit_advisory(lines),
        "egress_capacity_per_minute": egress_capacity_per_minute(lines),
        "timestamp": time.time(),
    }
