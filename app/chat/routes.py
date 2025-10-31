from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from fastapi.responses import Response
from sqlalchemy.orm import Session
from typing import List
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



# Novas rotas com detecção de crise
@router.post("/conversations/{conversation_id}/ask-with-crisis-detection")
async def ask_with_crisis_detection(
    conversation_id: int,
    msg: schemas.MessageWithCrisisCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Endpoint principal com detecção de crise integrada."""

    ai_response, crisis_analysis = await services.get_response_with_crisis_detection(
        db, conversation_id, msg
    )

    # Se requer atenção humana, adicionar task de notificação
    if crisis_analysis and crisis_analysis.requires_human:
        background_tasks.add_task(
            _notify_monitors_of_crisis,
            conversation_id,
            crisis_analysis
        )

    # Retornar resposta
    if ai_response is None:
        conv = db.get(Conversation, conversation_id)
        if conv is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Conversation not found")

        # Se foi escalado, retornar info sobre escalação
        if conv.status.value == "escalated":
            return {
                "message": "Conversa foi escalada para um monitor humano",
                "escalated": True,
                "crisis_analysis": crisis_analysis
            }

        return Response(status_code=status.HTTP_204_NO_CONTENT)

    # Converter ai_response para schema se existir
    ai_response_schema = None
    if ai_response:
        ai_response_schema = schemas.MessageOut.model_validate(ai_response)

    return {
        "ai_response": ai_response_schema,
        "crisis_analysis": crisis_analysis,
        "escalated": crisis_analysis.emergency_contact if crisis_analysis else False
    }

# Rotas para monitores
@router.get("/monitor/dashboard", response_model=List[schemas.ConversationOut])
def get_monitor_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Dashboard para monitores verem conversas que precisam de atenção."""
    conversations = services.get_conversations_needing_attention(db)
    return conversations

@router.post("/monitor/take-control/{conversation_id}")
async def monitor_take_control(
    conversation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Monitor assume controle de uma conversa."""
    success = services.monitor_take_control(db, conversation_id, current_user.id)
    if not success:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Conversation not found")

    # Notify via WebSocket that monitor joined
    try:
        from app.websocket.manager import socket_manager
        await socket_manager.notify_monitor_joined(conversation_id, current_user.username)
    except Exception as e:
        print(f"Erro ao notificar entrada do monitor via WebSocket: {e}")

    return {"message": "Monitor assumiu controle da conversa", "conversation_id": conversation_id}

@router.post("/monitor/escalate/{conversation_id}")
async def escalate_conversation(
    conversation_id: int,
    escalation: schemas.EscalationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Escala manualmente uma conversa para monitor."""
    success = services.escalate_to_monitor(
        db,
        conversation_id,
        current_user.id,
        escalation.reason
    )
    if not success:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Conversation not found")

    # Notify via WebSocket that conversation was escalated
    try:
        from app.websocket.manager import socket_manager
        await socket_manager.broadcast_conversation_escalated(
            conversation_id,
            current_user.username,
            escalation.reason
        )
    except Exception as e:
        print(f"Erro ao notificar escalação via WebSocket: {e}")

    return {"message": "Conversa escalada com sucesso", "reason": escalation.reason}

@router.get("/monitor/flagged-messages", response_model=List[schemas.MessageOut])
def get_flagged_messages(
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Lista mensagens flagadas para revisão."""
    messages = services.get_flagged_messages(db, limit)
    return messages

@router.get("/monitor/debug/connected")
def get_connected_monitors():
    """Debug endpoint - mostra monitores conectados via WebSocket."""
    from app.websocket.manager import socket_manager
    return {
        "total_monitors": len(socket_manager.monitor_rooms),
        "monitor_ids": list(socket_manager.monitor_rooms.keys()),
        "monitor_details": {
            monitor_id: len(sessions)
            for monitor_id, sessions in socket_manager.monitor_rooms.items()
        },
        "total_sessions": sum(len(sessions) for sessions in socket_manager.monitor_rooms.values())
    }

# Função auxiliar para notificações (executada em background)
async def _notify_monitors_of_crisis(conversation_id: int, crisis_analysis: schemas.CrisisAnalysisOut):
    """
    Notifica monitores sobre crise detectada.
    Esta função será executada em background.
    """
    from app.websocket.manager import socket_manager

    print(f"🚨 ALERTA DE CRISE - Conversa {conversation_id}")
    print(f"Nível de risco: {crisis_analysis.risk_level}")
    print(f"Confiança: {crisis_analysis.confidence:.2f}")
    print(f"Requer humano: {crisis_analysis.requires_human}")
    print(f"Emergência: {crisis_analysis.emergency_contact}")

    if crisis_analysis.emergency_contact:
        print("⚠️  EMERGÊNCIA - CONTATO IMEDIATO NECESSÁRIO")

    # Broadcast crisis alert via WebSocket
    try:
        await socket_manager.broadcast_crisis_alert(
            conversation_id,
            crisis_analysis,
            "Alerta de crise detectado"
        )
    except Exception as e:
        print(f"Erro ao enviar alerta via WebSocket: {e}")

    # TODO: Adicionar outros canais de notificação:
    # - await email_service.send_crisis_alert(crisis_analysis)
    # - await sms_service.send_emergency_alert(crisis_analysis)