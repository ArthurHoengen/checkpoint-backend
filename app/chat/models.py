from sqlalchemy import Column, Integer, String, ForeignKey, Boolean, DateTime, func
from sqlalchemy.orm import relationship
from app.core.database import Base

class Conversation(Base):
    __tablename__ = "conversations"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=True)
    mode = Column(String, default="ollama")
    active = Column(Boolean, default=True)
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")

class Message(Base):
    __tablename__ = "messages"
    id = Column(Integer, primary_key=True, index=True)
    sender = Column(String, index=True)
    text = Column(String)
    conversation_id = Column(Integer, ForeignKey("conversations.id"))
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # flags for safety
    flagged = Column(Boolean, default=False)            # marcou como risco
    risk_level = Column(String, nullable=True)          # e.g. "low", "medium", "high"
    notified = Column(Boolean, default=False)           # já notificou alguém?

    conversation = relationship("Conversation", back_populates="messages")