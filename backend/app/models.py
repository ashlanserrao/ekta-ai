from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Literal

class ChatMessage(BaseModel):
    role: str = Field(..., description="Role of the sender: user or assistant")
    content: str = Field(..., description="Message text")

class FanChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=500, description="Chat message from the fan")
    language: Optional[str] = Field("en", description="ISO 639-1 language code")
    history: Optional[List[ChatMessage]] = Field(default_factory=list, description="Recent conversation history")

class StaffChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=500, description="Operations query from the staff")
    history: Optional[List[ChatMessage]] = Field(default_factory=list, description="Recent conversation history")

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
    severity: Literal["info", "warning", "critical"]
    message: str
    recommended_action: str

class TransitLine(BaseModel):
    id: str
    name: str
    mode: Literal["metro", "rail", "shuttle", "bus"]
    destination: str
    headway_minutes: float
    capacity_per_departure: int
    current_load: float
    status: Literal["on_time", "delayed"]
    minutes_to_next: float
    crowding: Literal["low", "medium", "high"]
    co2_saved_kg_per_trip: float

class TransitAdvisory(BaseModel):
    generated_at: float
    provider: str
    summary: str
    tips: List[str]

class TransitStatus(BaseModel):
    lines: List[TransitLine]
    advisory: TransitAdvisory
    egress_capacity_per_minute: int
    timestamp: float

class InteractionEventCreate(BaseModel):
    session_id: str = Field(..., min_length=1, max_length=64, description="Random per-browser-session id, not tied to any personal identifier")
    role: Literal["fan", "staff"]
    event_type: Literal["login", "logout", "chat_message", "page_view"]
    view: Optional[str] = Field(None, max_length=64, description="Screen/view name, e.g. 'stats', 'schedule'")
    meta: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Small non-sensitive counters only (e.g. message length, language) - never raw text or PII")

class InteractionEvent(BaseModel):
    id: int
    ts: str
    session_id: str
    role: str
    event_type: str
    view: Optional[str] = None
    meta: Dict[str, Any] = Field(default_factory=dict)

class InteractionSummary(BaseModel):
    events: List[InteractionEvent]
    counts_by_type: Dict[str, int]
    total: int

