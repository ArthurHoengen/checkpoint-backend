"""
Configuração global de fixtures para testes.
"""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient
from fastapi import FastAPI

from app.core.database import Base, get_db
from app.auth.models import User
from app.chat.models import Conversation, Message, ConversationStatus
from app.core.security import get_password_hash


# Database fixture - usa SQLite em memória para testes
@pytest.fixture(scope="function")
def db_session():
    """
    Cria uma sessão de banco de dados em memória para testes.
    Cada teste recebe uma nova sessão limpa.
    """
    # Cria engine em memória
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    # Cria todas as tabelas
    Base.metadata.create_all(bind=engine)

    # Cria sessão
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()

    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def app():
    """
    Cria uma aplicação FastAPI para testes.
    """
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware
    from app.auth import routes as auth_routes
    from app.chat import routes as chat_routes

    test_app = FastAPI(title="Checkpoint API - Test")

    # Add CORS middleware
    test_app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    test_app.include_router(auth_routes.router)
    test_app.include_router(chat_routes.router)

    return test_app


@pytest.fixture(scope="function")
def client(db_session, app):
    """
    Cliente de teste para fazer requisições à API.
    """
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


@pytest.fixture
def test_user(db_session: Session):
    """
    Cria um usuário de teste no banco.
    """
    user = User(
        username="testuser",
        hashed_password=get_password_hash("testpassword123")
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def auth_token(client, test_user):
    """
    Gera um token de autenticação válido para o usuário de teste.
    """
    response = client.post(
        "/auth/login",
        json={"username": "testuser", "password": "testpassword123"}
    )
    assert response.status_code == 200
    return response.json()["access_token"]


@pytest.fixture
def authenticated_client(client, auth_token):
    """
    Cliente de teste com autenticação configurada.
    """
    client.headers = {
        **client.headers,
        "Authorization": f"Bearer {auth_token}"
    }
    return client


@pytest.fixture
def test_conversation(db_session: Session):
    """
    Cria uma conversa de teste.
    """
    conversation = Conversation(
        title="Test Conversation",
        status=ConversationStatus.ACTIVE,
        mode="user"
    )
    db_session.add(conversation)
    db_session.commit()
    db_session.refresh(conversation)
    return conversation


@pytest.fixture
def test_message(db_session: Session, test_conversation: Conversation):
    """
    Cria uma mensagem de teste.
    """
    message = Message(
        sender="user",
        text="Hello, I need help",
        conversation_id=test_conversation.id,
        flagged=False
    )
    db_session.add(message)
    db_session.commit()
    db_session.refresh(message)
    return message


@pytest.fixture
def crisis_message(db_session: Session, test_conversation: Conversation):
    """
    Cria uma mensagem com conteúdo de crise para testes.
    """
    message = Message(
        sender="user",
        text="Eu quero me matar, não aguento mais",
        conversation_id=test_conversation.id,
        flagged=True,
        risk_level="critical"
    )
    db_session.add(message)
    db_session.commit()
    db_session.refresh(message)
    return message
