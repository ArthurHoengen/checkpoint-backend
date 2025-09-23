from fastapi import FastAPI
from app.auth import routes as auth_routes
from app.chat import routes as chat_routes
from app.core.database import Base, engine

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Checkpoint API")

app.include_router(auth_routes.router)
app.include_router(chat_routes.router)