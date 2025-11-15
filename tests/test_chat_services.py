"""
Testes para serviços de chat.
"""
import pytest
from sqlalchemy.orm import Session

from app.chat import services, schemas
from app.chat.models import Conversation, Message, ConversationStatus
from app.auth.models import User


class TestConversationServices:
    """Testes para serviços de gerenciamento de conversas."""

    def test_create_conversation(self, db_session: Session):
        """Teste criação de conversa."""
        data = schemas.ConversationCreate(title="Test Chat")
        conversation = services.create_conversation(db_session, data)

        assert conversation.id is not None
        assert conversation.title == "Test Chat"
        assert conversation.status == ConversationStatus.ACTIVE
        # Mode padrão é "ollama"
        assert conversation.mode == "ollama"

    def test_get_conversation(self, db_session: Session, test_conversation: Conversation):
        """Teste busca de conversa por ID."""
        conv = db_session.get(Conversation, test_conversation.id)

        assert conv is not None
        assert conv.id == test_conversation.id
        assert conv.title == test_conversation.title

    def test_set_conversation_mode(self, db_session: Session, test_conversation: Conversation):
        """Teste mudança de modo da conversa."""
        conv = services.set_conversation_mode(db_session, test_conversation.id, "monitor")

        assert conv is not None
        assert conv.mode == "monitor"

    def test_set_conversation_mode_invalid_id(self, db_session: Session):
        """Teste mudança de modo com ID inválido."""
        conv = services.set_conversation_mode(db_session, 99999, "monitor")

        assert conv is None

    def test_get_conversations_needing_attention(self, db_session: Session):
        """Teste busca de conversas que precisam de atenção."""
        # Criar conversa escalada
        escalated_conv = Conversation(
            title="Escalated",
            status=ConversationStatus.ESCALATED,
            user_connected=False
        )
        db_session.add(escalated_conv)

        # Criar conversa ativa com usuário conectado
        active_conv = Conversation(
            title="Active",
            status=ConversationStatus.ACTIVE,
            user_connected=True
        )
        db_session.add(active_conv)

        # Criar conversa ativa sem usuário conectado (não deve aparecer)
        inactive_conv = Conversation(
            title="Inactive",
            status=ConversationStatus.ACTIVE,
            user_connected=False
        )
        db_session.add(inactive_conv)

        db_session.commit()

        conversations = services.get_conversations_needing_attention(db_session)

        # Deve retornar apenas escalada e ativa com usuário conectado
        assert len(conversations) == 2
        conv_ids = [c.id for c in conversations]
        assert escalated_conv.id in conv_ids
        assert active_conv.id in conv_ids
        assert inactive_conv.id not in conv_ids


class TestMessageServices:
    """Testes para serviços de mensagens."""

    def test_get_last_messages(self, db_session: Session, test_conversation: Conversation):
        """Teste busca de últimas mensagens."""
        import time
        # Criar várias mensagens com pequeno delay para garantir ordem temporal
        messages_created = []
        for i in range(5):
            msg = Message(
                sender="user",
                text=f"Message {i}",
                conversation_id=test_conversation.id
            )
            db_session.add(msg)
            db_session.flush()  # Flush para garantir created_at
            messages_created.append(msg)
            time.sleep(0.01)  # Pequeno delay entre mensagens
        db_session.commit()

        messages = services.get_last_messages(db_session, test_conversation.id, limit=3)

        assert len(messages) == 3
        # Deve retornar as 3 mais recentes em ordem DESC (mais nova primeiro)
        # Verifica que são mensagens da conversa certa
        for msg in messages:
            assert msg.conversation_id == test_conversation.id
            assert msg.sender == "user"

    def test_get_flagged_messages(self, db_session: Session, test_conversation: Conversation):
        """Teste busca de mensagens flagadas."""
        # Criar mensagem flagada
        flagged_msg = Message(
            sender="user",
            text="Flagged message",
            conversation_id=test_conversation.id,
            flagged=True,
            notified=False
        )
        db_session.add(flagged_msg)

        # Criar mensagem normal
        normal_msg = Message(
            sender="user",
            text="Normal message",
            conversation_id=test_conversation.id,
            flagged=False
        )
        db_session.add(normal_msg)

        db_session.commit()

        flagged = services.get_flagged_messages(db_session)

        assert len(flagged) == 1
        assert flagged[0].id == flagged_msg.id
        assert flagged[0].flagged is True


class TestMonitorServices:
    """Testes para serviços de monitor."""

    def test_monitor_take_control(self, db_session: Session, test_conversation: Conversation, test_user: User):
        """Teste monitor assumindo controle da conversa."""
        success = services.monitor_take_control(db_session, test_conversation.id, test_user.id)

        assert success is True

        # Verificar mudanças na conversa
        db_session.refresh(test_conversation)
        assert test_conversation.mode == "monitor"
        assert test_conversation.status == ConversationStatus.ESCALATED

    def test_monitor_take_control_invalid_conversation(self, db_session: Session, test_user: User):
        """Teste monitor tentando assumir conversa inexistente."""
        success = services.monitor_take_control(db_session, 99999, test_user.id)

        assert success is False

    def test_escalate_to_monitor(self, db_session: Session, test_conversation: Conversation, test_user: User):
        """Teste escalação de conversa para monitor."""
        reason = "User mentioned suicide"
        success = services.escalate_to_monitor(
            db_session,
            test_conversation.id,
            test_user.id,
            reason
        )

        assert success is True

        # Verificar mudanças na conversa
        db_session.refresh(test_conversation)
        assert test_conversation.status == ConversationStatus.ESCALATED

    def test_escalate_to_monitor_invalid_conversation(self, db_session: Session, test_user: User):
        """Teste escalação de conversa inexistente."""
        success = services.escalate_to_monitor(db_session, 99999, test_user.id, "reason")

        assert success is False


class TestConversationActivity:
    """Testes para rastreamento de atividade de conversas."""

    def test_user_connected_tracking(self, db_session: Session, test_conversation: Conversation):
        """Teste rastreamento de usuário conectado."""
        # user_connected default é True
        assert test_conversation.user_connected is True

        # Simular usuário desconectando
        test_conversation.user_connected = False
        db_session.commit()
        db_session.refresh(test_conversation)

        assert test_conversation.user_connected is False

    def test_last_activity_update(self, db_session: Session, test_conversation: Conversation):
        """Teste atualização de última atividade."""
        import time
        from datetime import datetime, timezone

        # Pegar tempo inicial
        initial_time = test_conversation.last_activity
        assert initial_time is not None

        # Esperar um pouco
        time.sleep(0.15)

        # Atualizar com datetime timezone-aware
        new_time = datetime.now(timezone.utc)
        test_conversation.last_activity = new_time
        db_session.commit()
        db_session.refresh(test_conversation)

        # Deve ter um valor atualizado
        assert test_conversation.last_activity is not None
        # A atividade foi atualizada (comparando com o inicial)
        assert test_conversation.last_activity != initial_time
