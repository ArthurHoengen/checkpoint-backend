from sqlalchemy import Column, Integer, String, ForeignKey, Boolean, DateTime, func, JSON, Enum
from sqlalchemy.orm import relationship
from app.core.database import Base
import enum

class ConversationStatus(enum.Enum):
    ACTIVE = "active"
    ESCALATED = "escalated"
    RESOLVED = "resolved"
    CLOSED = "closed"

class EscalationLevel(enum.Enum):
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class Conversation(Base):
    __tablename__ = "conversations"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=True)
    mode = Column(String, default="ollama")
    active = Column(Boolean, default=True)
    status = Column(Enum(ConversationStatus), default=ConversationStatus.ACTIVE)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")

class Message(Base):
    __tablename__ = "messages"
    id = Column(Integer, primary_key=True, index=True)
    sender = Column(String, index=True)  # "user", "ai", "monitor"
    text = Column(String)
    conversation_id = Column(Integer, ForeignKey("conversations.id"))
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # NULL para anônimos e IA
    session_id = Column(String, index=True, nullable=True)  # Para rastrear usuários anônimos
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Sistema de segurança e escalação
    flagged = Column(Boolean, default=False)            # marcou como risco
    risk_level = Column(String, nullable=True)          # "low", "medium", "high"
    escalation_level = Column(Enum(EscalationLevel), default=EscalationLevel.NONE)
    notified = Column(Boolean, default=False)           # já notificou alguém?
    intervention_timestamp = Column(DateTime(timezone=True), nullable=True)  # quando monitor assumiu

    # Metadados adicionais (sem dados pessoais)
    extra_data = Column(JSON, nullable=True)  # contexto adicional, configurações, etc.

    conversation = relationship("Conversation", back_populates="messages")