from sqlalchemy.orm import Session
from . import models, schemas
from app.core.ollama_client import OllamaClient

ollama_client = OllamaClient()

def create_conversation(db: Session, data: schemas.ConversationCreate):
    conversation = models.Conversation(title=data.title)
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    return conversation

def set_conversation_mode(db: Session, conversation_id: int, mode: str):
    conv = db.query(models.Conversation).get(conversation_id)
    if not conv:
        return None
    conv.mode = mode
    db.commit()
    db.refresh(conv)
    return conv

def add_message(db: Session, conversation_id: int, msg: schemas.MessageCreate):
    db_msg = models.Message(**msg.dict(), conversation_id=conversation_id)
    db.add(db_msg)
    db.commit()
    db.refresh(db_msg)
    return db_msg

def get_response(db: Session, conversation_id: int, msg: schemas.MessageCreate):
    conv = db.get(models.Conversation, conversation_id)
    if not conv:
        return None

    add_message(db, conversation_id, msg)

    if conv.mode == "ollama":
        response_text = ollama_client.ask(msg.text, "llama3.2:1b")
        return add_message(
            db,
            conversation_id,
            schemas.MessageCreate(sender="ollama", text=response_text),
        )

    return None

def get_last_messages(db: Session, conversation_id: int, limit: int = 10):
    return (
        db.query(models.Message)
        .filter(models.Message.conversation_id == conversation_id)
        .order_by(models.Message.created_at.desc())
        .limit(limit)
        .all()
    )
    

def add_user_message(db: Session, conversation_id: int, user_id: int, msg: schemas.MessageCreate):
    db_msg = models.Message(
        **msg.dict(),
        conversation_id=conversation_id,
        user_id=user_id 
    )
    db.add(db_msg)
    db.commit()
    db.refresh(db_msg)
    return db_msg