from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

class FanChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=500, description="Chat message from the fan")
    language: Optional[str] = Field("en", description="ISO 639-1 language code")

class StaffChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=500, description="Operations query from the staff")

class RouteInfo(BaseModel):
    id: str
    from_location: str
    to_location: str
    path_nodes: List[str]
    is_accessible: int

class ChatResponse(BaseModel):
    reply: str
    tool_called: Optional[str] = None
    route: Optional[RouteInfo] = None
    rag_used: bool = False
    provider: Optional[str] = None

class GateStatus(BaseModel):
    id: str
    name: str
    status: str
    congestion_level: str
    zone_id: Optional[str] = None

class ZoneStatus(BaseModel):
    id: str
    name: str
    type: str
    capacity: int
    current_crowd: int
    density: float

class StadiumStatus(BaseModel):
    gates: List[GateStatus]
    zones: List[ZoneStatus]
    timestamp: float

class PlainLanguageAlert(BaseModel):
    id: str
    severity: str  # info, warning, critical
    message: str
    recommended_action: str
