from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class MessageCreate(BaseModel):
    sender: str
    text: str

class MessageOut(BaseModel):
    id: int
    sender: str
    text: str
    created_at: datetime

    class Config:
        from_attributes = True  # ou orm_mode se ainda usar Pydantic V1


class ConversationCreate(BaseModel):
    title: Optional[str] = None

class ConversationOut(BaseModel):
    id: int
    title: Optional[str]
    mode: str
    active: bool
    messages: List[MessageOut] = []

    class Config:
        from_attributes = True