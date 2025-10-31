import asyncio
from datetime import datetime
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import desc
from . import models, schemas
from .crisis_detector import crisis_detector, RiskLevel
from .models import ConversationStatus, EscalationLevel
from app.core.ollama_client import OllamaClient

ollama_client = OllamaClient()

def create_conversation(db: Session, data: schemas.ConversationCreate):
    conversation = models.Conversation(
        title=data.title,
        status=models.ConversationStatus.ACTIVE
    )
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


async def get_response_with_crisis_detection(
    db: Session,
    conversation_id: int,
    msg: schemas.MessageWithCrisisCreate
) -> tuple[Optional[models.Message], Optional[schemas.CrisisAnalysisOut]]:
    """
    Processa mensagem com detecção de crise integrada.
    Retorna (resposta_da_ia, análise_de_crise)
    """
    conv = db.get(models.Conversation, conversation_id)
    if not conv:
        return None, None

    # 1. Analisar mensagem para crise ANTES de salvá-la
    session_context = get_recent_session_messages(db, conversation_id, msg.session_id)
    crisis_analysis = await crisis_detector.analyze_message(
        msg.text,
        [m.text for m in session_context]
    )

    # Debug log
    print(f"🔍 CRISIS ANALYSIS - Conversa {conversation_id}")
    print(f"   Mensagem: '{msg.text}'")
    print(f"   Risco: {crisis_analysis.risk_level}")
    print(f"   Confiança: {crisis_analysis.confidence}")
    print(f"   Requer humano: {crisis_analysis.requires_human}")
    print(f"   Emergência: {crisis_analysis.emergency_contact}")

    # 2. Salvar mensagem do usuário com dados de crise
    user_message = models.Message(
        sender=msg.sender,
        text=msg.text,
        conversation_id=conversation_id,
        session_id=msg.session_id,
        flagged=crisis_analysis.requires_human,
        risk_level=crisis_analysis.risk_level.value,
        escalation_level=_map_risk_to_escalation(crisis_analysis.risk_level),
        extra_data={
            "crisis_analysis": {
                "confidence": crisis_analysis.confidence,
                "keywords_found": crisis_analysis.keywords_found,
                "analysis_timestamp": datetime.now().isoformat()
            }
        }
    )
    db.add(user_message)

    # 3. Se crítico, escalar automaticamente
    if crisis_analysis.risk_level == RiskLevel.CRITICAL:
        conv.status = ConversationStatus.ESCALATED
        user_message.notified = True

    # 4. Gerar resposta da IA (apenas se não foi assumido por monitor)
    ai_response = None

    # Se monitor assumiu a conversa, NÃO gerar resposta da IA
    if conv.mode == "monitor":
        print(f"⚠️  Monitor assumiu conversa {conversation_id} - IA não vai responder")
    elif conv.status != ConversationStatus.ESCALATED and conv.mode == "ollama":
        # Adaptar resposta baseada no nível de risco
        ai_prompt = _build_crisis_aware_prompt(msg.text, crisis_analysis.risk_level)
        response_text = await ollama_client.ask(ai_prompt, "llama3.2:3b")

        ai_response = models.Message(
            sender="ai",
            text=response_text,
            conversation_id=conversation_id,
            session_id=msg.session_id
        )
        db.add(ai_response)

    db.commit()

    # 5. Retornar análise para notificação
    crisis_schema = schemas.CrisisAnalysisOut(
        risk_level=crisis_analysis.risk_level.value,
        confidence=crisis_analysis.confidence,
        keywords_found=crisis_analysis.keywords_found,
        requires_human=crisis_analysis.requires_human,
        emergency_contact=crisis_analysis.emergency_contact,
        analysis_details=crisis_analysis.analysis_details
    )

    return ai_response, crisis_schema


async def analyze_and_respond(
    db: Session,
    conversation_id: int,
    user_message_id: int
) -> tuple[Optional[models.Message], Optional[schemas.CrisisAnalysisOut]]:
    """
    Analisa mensagem já salva e gera resposta da IA.
    NÃO salva a mensagem do usuário novamente.
    """
    # Buscar mensagem do usuário
    user_message = db.query(models.Message).get(user_message_id)
    if not user_message:
        return None, None

    conv = db.get(models.Conversation, conversation_id)
    if not conv:
        return None, None

    # 1. Analisar mensagem para crise
    session_context = get_recent_session_messages(db, conversation_id, user_message.session_id)
    crisis_analysis = await crisis_detector.analyze_message(
        user_message.text,
        [m.text for m in session_context if m.id != user_message_id]
    )

    # Debug log
    print(f"🔍 CRISIS ANALYSIS - Conversa {conversation_id}")
    print(f"   Mensagem: '{user_message.text}'")
    print(f"   Risco: {crisis_analysis.risk_level}")
    print(f"   Confiança: {crisis_analysis.confidence}")
    print(f"   Requer humano: {crisis_analysis.requires_human}")
    print(f"   Emergência: {crisis_analysis.emergency_contact}")

    # 2. Atualizar mensagem do usuário com dados de crise
    user_message.flagged = crisis_analysis.requires_human
    user_message.risk_level = crisis_analysis.risk_level.value
    user_message.escalation_level = _map_risk_to_escalation(crisis_analysis.risk_level)
    user_message.extra_data = {
        "crisis_analysis": {
            "confidence": crisis_analysis.confidence,
            "keywords_found": crisis_analysis.keywords_found,
            "analysis_timestamp": datetime.now().isoformat()
        }
    }

    # 3. Se crítico, escalar automaticamente
    if crisis_analysis.risk_level == RiskLevel.CRITICAL:
        conv.status = ConversationStatus.ESCALATED
        user_message.notified = True

    # 4. Gerar resposta da IA (apenas se não foi assumido por monitor)
    ai_response = None

    # Se monitor assumiu a conversa, NÃO gerar resposta da IA
    if conv.mode == "monitor":
        print(f"⚠️  Monitor assumiu conversa {conversation_id} - IA não vai responder")
    elif conv.status == ConversationStatus.ESCALATED and crisis_analysis.risk_level == RiskLevel.CRITICAL:
        # Se foi escalado para CRITICAL, enviar mensagem de apoio imediato
        ai_response = models.Message(
            sender="ai",
            text="Percebo que você está passando por um momento muito difícil. Um profissional será notificado imediatamente para ajudá-lo. Por favor, ligue para o CVV no 188 se precisar de apoio urgente. Você não está sozinho.",
            conversation_id=conversation_id,
            session_id=user_message.session_id
        )
        db.add(ai_response)
    elif conv.mode == "ollama":
        # Adaptar resposta baseada no nível de risco
        ai_prompt = _build_crisis_aware_prompt(user_message.text, crisis_analysis.risk_level)
        response_text = await ollama_client.ask(ai_prompt, "llama3.2:3b")

        ai_response = models.Message(
            sender="ai",
            text=response_text,
            conversation_id=conversation_id,
            session_id=user_message.session_id
        )
        db.add(ai_response)

    db.commit()

    # 5. Retornar análise para notificação
    crisis_schema = schemas.CrisisAnalysisOut(
        risk_level=crisis_analysis.risk_level.value,
        confidence=crisis_analysis.confidence,
        keywords_found=crisis_analysis.keywords_found,
        requires_human=crisis_analysis.requires_human,
        emergency_contact=crisis_analysis.emergency_contact,
        analysis_details=crisis_analysis.analysis_details
    )

    return ai_response, crisis_schema


def get_last_messages(db: Session, conversation_id: int, limit: int = 10):
    return (
        db.query(models.Message)
        .filter(models.Message.conversation_id == conversation_id)
        .order_by(models.Message.created_at.desc())
        .limit(limit)
        .all()
    )
    


# Funções auxiliares para detecção de crise
def get_recent_session_messages(db: Session, conversation_id: int, session_id: Optional[str], limit: int = 5) -> List[models.Message]:
    """Busca mensagens recentes da sessão para contexto."""
    query = db.query(models.Message).filter(
        models.Message.conversation_id == conversation_id
    )

    if session_id:
        query = query.filter(models.Message.session_id == session_id)

    return query.order_by(desc(models.Message.created_at)).limit(limit).all()

def _map_risk_to_escalation(risk_level: RiskLevel) -> EscalationLevel:
    """Mapeia nível de risco para nível de escalação."""
    mapping = {
        RiskLevel.NONE: EscalationLevel.NONE,
        RiskLevel.LOW: EscalationLevel.LOW,
        RiskLevel.MEDIUM: EscalationLevel.MEDIUM,
        RiskLevel.HIGH: EscalationLevel.HIGH,
        RiskLevel.CRITICAL: EscalationLevel.CRITICAL
    }
    return mapping.get(risk_level, EscalationLevel.NONE)

def _build_crisis_aware_prompt(user_message: str, risk_level: RiskLevel) -> str:
    """Constrói prompt para IA baseado no nível de risco detectado."""

    base_context = """Você é um conselheiro de apoio emocional. Fale em português claro e natural.
Seja empático, acolhedor e profissional. Responda com 2-3 parágrafos curtos."""

    if risk_level == RiskLevel.HIGH:
        return f"""{base_context}

IMPORTANTE: Esta pessoa pode estar em risco emocional.
- Valide os sentimentos
- Ofereça esperança
- Mencione o CVV (Centro de Valorização da Vida): 188
- Mantenha tom calmo e acolhedor

Pessoa disse: "{user_message}"

Resposta empática em português:"""

    elif risk_level == RiskLevel.MEDIUM:
        return f"""{base_context}

Esta pessoa está passando por dificuldades.
- Seja empático
- Faça perguntas para entender melhor
- Valide os sentimentos
- Ofereça apoio prático

Pessoa disse: "{user_message}"

Resposta em português:"""

    else:
        return f"""{base_context}

Pessoa disse: "{user_message}"

Resposta acolhedora em português:"""

# Funções para sistema de monitores
def escalate_to_monitor(db: Session, conversation_id: int, monitor_id: Optional[int] = None, reason: str = "Crisis detected") -> bool:
    """Escala conversa para monitor humano."""
    conv = db.get(models.Conversation, conversation_id)
    if not conv:
        return False

    # Mudar status da conversa
    conv.status = ConversationStatus.ESCALATED

    # Registrar intervenção
    intervention_msg = models.Message(
        conversation_id=conversation_id,
        user_id=monitor_id,
        sender="system",
        text=f"🚨 Conversa escalada para monitor humano. Motivo: {reason}",
        intervention_timestamp=datetime.now(),
        escalation_level=EscalationLevel.HIGH
    )
    db.add(intervention_msg)

    db.commit()
    return True

def monitor_take_control(db: Session, conversation_id: int, monitor_id: int) -> bool:
    """Monitor assume controle da conversa."""
    conv = db.get(models.Conversation, conversation_id)
    if not conv:
        return False

    # Atualizar conversa
    conv.mode = "monitor"
    conv.status = ConversationStatus.ESCALATED

    # Registrar takeover
    takeover_msg = models.Message(
        conversation_id=conversation_id,
        user_id=monitor_id,
        sender="system",
        text="👨‍⚕️ Monitor assumiu a conversa. Você agora está falando com um profissional.",
        intervention_timestamp=datetime.now()
    )
    db.add(takeover_msg)

    db.commit()
    return True

def get_conversations_needing_attention(db: Session) -> List[models.Conversation]:
    """Busca conversas que precisam de atenção humana."""
    return db.query(models.Conversation).filter(
        models.Conversation.status.in_([
            ConversationStatus.ACTIVE,
            ConversationStatus.ESCALATED
        ])
    ).order_by(desc(models.Conversation.updated_at)).all()

def get_flagged_messages(db: Session, limit: int = 50) -> List[models.Message]:
    """Busca mensagens flagadas para revisão."""
    return db.query(models.Message).filter(
        models.Message.flagged == True,
        models.Message.notified == False
    ).order_by(desc(models.Message.created_at)).limit(limit).all()