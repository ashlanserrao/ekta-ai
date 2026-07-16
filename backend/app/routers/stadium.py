import time
import logging
import json
import asyncio
from typing import List
from fastapi import APIRouter, HTTPException, Request
from sse_starlette.sse import EventSourceResponse

from backend.app.database import get_db_connection
from backend.app.models import GateStatus, ZoneStatus, StadiumStatus

logger = logging.getLogger("routers.stadium")

router = APIRouter(prefix="/api/v1/stadium", tags=["stadium"])

@router.get("/gates", response_model=List[GateStatus])
def get_gates():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, status, congestion_level, zone_id FROM gates")
        gates = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return gates
    except Exception as e:
        logger.error(f"Error in get_gates: {e}")
        raise HTTPException(status_code=500, detail="Database connection error while retrieving gates.")

@router.get("/zones", response_model=List[ZoneStatus])
def get_zones():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, type, capacity, current_crowd, density FROM zones")
        zones = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return zones
    except Exception as e:
        logger.error(f"Error in get_zones: {e}")
        raise HTTPException(status_code=500, detail="Database connection error while retrieving zones.")


@router.get("/status", response_model=StadiumStatus)
def get_stadium_status():
    gates = get_gates()
    zones = get_zones()
    return {
        "gates": gates,
        "zones": zones,
        "timestamp": time.time()
    }

@router.get("/stream")
async def stream_stadium_status(request: Request):
    async def event_generator():
        while True:
            if await request.is_disconnected():
                break
            try:
                gates = get_gates()
                zones = get_zones()
                data = {
                    "gates": gates,
                    "zones": zones,
                    "timestamp": time.time()
                }
                yield {
                    "event": "message",
                    "data": json.dumps(data)
                }
            except Exception as e:
                logger.error(f"Error yielding stream status: {e}")
            await asyncio.sleep(3.0)
    return EventSourceResponse(event_generator())
