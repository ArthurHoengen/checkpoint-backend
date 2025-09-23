from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from sqlalchemy.orm import Session
from app.core.database import get_db
from . import schemas, services
from .models import Conversation
from app.auth.dependencies import get_current_user
from app.auth.models import User

router = APIRouter(prefix="/chat", tags=["chat"])

@router.post("/conversations", response_model=schemas.ConversationOut)
def create_conversation(data: schemas.ConversationCreate, db: Session = Depends(get_db)):
    return services.create_conversation(db, data)

@router.post("/conversations/{conversation_id}/mode")
def set_mode(conversation_id: int, mode: str, db: Session = Depends(get_db)):
    conv = services.set_conversation_mode(db, conversation_id, mode)
    if not conv:
        raise HTTPException(404, "Conversation not found")
    return conv

@router.post("/conversations/{conversation_id}/ask", response_model=schemas.MessageOut)
def ask(conversation_id: int, msg: schemas.MessageCreate, db: Session = Depends(get_db)):
    response = services.get_response(db, conversation_id, msg)

    if response is None:
        conv = db.get(Conversation, conversation_id)
        if conv is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Conversation not found")
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    return response

@router.get(
    "/conversations/{conversation_id}/messages",
    response_model=list[schemas.MessageOut],
)
def get_last_messages(conversation_id: int, db: Session = Depends(get_db)):
    conv = db.get(Conversation, conversation_id)
    if not conv:
        raise HTTPException(404, "Conversation not found")

    messages = services.get_last_messages(db, conversation_id, limit=10)
    # Retorna do mais antigo para o mais novo
    return list(reversed(messages))


@router.post("/conversations/{conversation_id}/reply", response_model=schemas.MessageOut)
def reply_as_user(
    conversation_id: int,
    msg: schemas.MessageCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    response = services.add_user_message(db, conversation_id, current_user.id, msg)
    return response