# app/auth/dependencies.py
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.auth import models
from app.core.security import decode_access_token


security = HTTPBearer()

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> models.User:
    try:
        token = credentials.credentials
        payload = decode_access_token(token)
        username = payload.get("sub")
        if username is None:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Token inválido")
        user = db.query(models.User).filter(models.User.username == username).first()
        if not user:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Usuário não encontrado")
        return user
    except Exception:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Token inválido")