from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.auth import routes as auth_routes
from app.chat import routes as chat_routes
from app.core.database import Base, engine
from app.websocket.app import create_socket_app

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Checkpoint API")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_routes.router)
app.include_router(chat_routes.router)

# Create the combined app with Socket.IO
socket_app = create_socket_app(app)