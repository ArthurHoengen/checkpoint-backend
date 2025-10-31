# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Running the Application
```bash
# Development server with WebSocket support (RECOMMENDED)
python run_with_socketio.py

# Or manually with uvicorn
uvicorn app.main:socket_app --reload --host 0.0.0.0 --port 8000

# Legacy server without WebSocket (NOT RECOMMENDED)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Docker

#### Development with Docker Compose (RECOMMENDED)
```bash
# Full stack with PostgreSQL and Ollama
docker-compose up -d

# Rebuild after adding WebSocket dependencies
./rebuild_docker.sh

# View logs
docker-compose logs -f api
```

#### Manual Docker Build
```bash
# Build image with WebSocket support
docker build -t checkpoint-backend .

# Run container
docker run -p 8000:8000 checkpoint-backend
```

### Dependencies
```bash
# Install dependencies
pip install -r requirements.txt
```

## Architecture Overview

This is a FastAPI backend application for a chat system called "Checkpoint" with user authentication and conversation management.

### Core Structure
- **FastAPI Application**: Entry point at `app/main.py`
- **WebSocket Support**: Real-time communication via Socket.IO at `app/websocket/`
- **Database**: PostgreSQL with SQLAlchemy ORM
- **Authentication**: JWT-based with bcrypt password hashing
- **External Services**: Ollama integration for AI chat functionality

### Key Components

#### Database Models (`app/*/models.py`)
- **User**: Basic user management with username/password authentication
- **Conversation**: Chat conversations with mode settings (default: "ollama")
- **Message**: Individual messages with safety flags (flagged, risk_level, notified)

#### Module Organization
- `app/core/`: Core functionality (database, config, security, ollama client)
- `app/auth/`: User authentication system (JWT, bcrypt)
- `app/chat/`: Chat/conversation management with crisis detection
- `app/websocket/`: Real-time WebSocket communication (Socket.IO)
- `app/logs/`: Logging services
- `app/utils/`: Utility functions (anonymizer)

#### Configuration
- Environment variables loaded via `pydantic-settings`
- Required vars: `DATABASE_URL`, `JWT_SECRET`, `JWT_ALGORITHM`, `OLLAMA_BASE_URL`
- Config class in `app/core/config.py`

#### Safety Features
The chat system includes content moderation with:
- Message flagging capabilities
- Risk level assessment (low/medium/high)
- Notification tracking for flagged content

### Database
- Uses SQLAlchemy with PostgreSQL
- Auto-creates tables on startup via `Base.metadata.create_all()`
- Database dependency injection through `get_db()` in `app/core/database.py`

### External Dependencies
- **Ollama**: AI model backend (configurable base URL)
- **PostgreSQL**: Primary database
- **JWT**: Authentication tokens
- **bcrypt**: Password hashing
- **Socket.IO**: Real-time bidirectional communication
- **python-socketio**: Python Socket.IO server implementation

## WebSocket Features

### Real-Time Communication
- **Chat Messages**: Instant message delivery between users and monitors
- **Crisis Alerts**: Immediate notifications to monitors when crisis is detected
- **Presence Indicators**: Monitor online/offline status and typing indicators
- **Room Management**: Automatic room joining/leaving for conversations

### WebSocket Events
- `connect/disconnect`: Connection management
- `join_conversation`: Join specific conversation room
- `join_monitor`: Join monitor broadcast room
- `send_message`: Send real-time messages
- `typing`: Typing indicators
- `new_message`: Receive new messages
- `crisis_alert`: Crisis detection notifications
- `monitor_joined`: Monitor presence notifications

### Socket.IO Endpoints
- WebSocket available at: `ws://localhost:8000/socket.io/`
- Supports WebSocket and HTTP long-polling fallback
- CORS enabled for frontend integration