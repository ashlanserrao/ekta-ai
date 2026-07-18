import json
import logging
import sqlite3
from datetime import datetime, timezone

from fastapi import APIRouter, Request, Depends, HTTPException, status

from backend.app.database import get_db_connection
from backend.app.models import InteractionEventCreate, InteractionEvent, InteractionSummary
from backend.app.auth import get_current_staff_user
from backend.app.middleware.rate_limit import interaction_limiter

logger = logging.getLogger("routers.interactions")

router = APIRouter(prefix="/api/v1/interactions", tags=["interactions"])

MAX_META_CHARS = 500

@router.post("", status_code=status.HTTP_204_NO_CONTENT)
def log_interaction(event: InteractionEventCreate, req: Request):
    client_ip = req.client.host if req.client else "unknown"
    if interaction_limiter.is_rate_limited(client_ip):
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Too many requests.")

    meta_json = json.dumps(event.meta or {})[:MAX_META_CHARS]

    try:
        conn = get_db_connection()
        conn.execute(
            "INSERT INTO interaction_events (ts, session_id, role, event_type, view, meta) VALUES (?, ?, ?, ?, ?, ?)",
            (
                datetime.now(timezone.utc).isoformat(),
                event.session_id,
                event.role,
                event.event_type,
                event.view,
                meta_json,
            ),
        )
        conn.commit()
        conn.close()
    except sqlite3.Error as e:
        # Analytics logging must never break the caller's actual action.
        logger.warning(f"Failed to record interaction event: {e}")

@router.get("", response_model=InteractionSummary)
def read_interactions(
    limit: int = 200,
    current_user: dict = Depends(get_current_staff_user),
):
    capped_limit = max(1, min(limit, 500))
    try:
        conn = get_db_connection()
        rows = conn.execute(
            "SELECT id, ts, session_id, role, event_type, view, meta FROM interaction_events ORDER BY id DESC LIMIT ?",
            (capped_limit,),
        ).fetchall()
        count_rows = conn.execute(
            "SELECT event_type, COUNT(*) as n FROM interaction_events GROUP BY event_type"
        ).fetchall()
        total = conn.execute("SELECT COUNT(*) as n FROM interaction_events").fetchone()["n"]
        conn.close()
    except sqlite3.Error as e:
        logger.error(f"Error reading interaction events: {e}")
        raise HTTPException(status_code=500, detail="Database connection error while retrieving interaction history.")

    events = [
        InteractionEvent(
            id=r["id"], ts=r["ts"], session_id=r["session_id"], role=r["role"],
            event_type=r["event_type"], view=r["view"],
            meta=json.loads(r["meta"]) if r["meta"] else {},
        )
        for r in rows
    ]
    return InteractionSummary(
        events=events,
        counts_by_type={r["event_type"]: r["n"] for r in count_rows},
        total=total,
    )
