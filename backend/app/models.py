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

