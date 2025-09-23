# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Running the Application
```bash
# Development server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Production server (as per Dockerfile)
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Docker
```bash
# Build image
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
- `app/chat/`: Chat/conversation management
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