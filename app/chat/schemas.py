from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime


class MessageOut(BaseModel):
    id: int
    sender: str
    text: str
    created_at: datetime
    session_id: Optional[str] = None
    flagged: bool = False
    risk_level: Optional[str] = None
    escalation_level: Optional[str] = None
    notified: bool = False
    intervention_timestamp: Optional[datetime] = None
    extra_data: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True


class ConversationCreate(BaseModel):
    title: Optional[str] = None

class ConversationOut(BaseModel):
    id: int
    title: Optional[str]
    mode: str
    active: bool
    status: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    messages: List[MessageOut] = []

    class Config:
        from_attributes = True

# Schemas para sistema de crise
class CrisisAnalysisOut(BaseModel):
    risk_level: str
    confidence: float
    keywords_found: List[str]
    requires_human: bool
    emergency_contact: bool
    analysis_details: Dict[str, Any]

class MessageWithCrisisCreate(BaseModel):
    sender: str
    text: str
    session_id: Optional[str] = None

class EscalationRequest(BaseModel):
    conversation_id: int
    reason: str
    monitor_id: Optional[int] = None