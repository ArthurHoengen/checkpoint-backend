from sqlalchemy.orm import Session
from app.core import security
from . import models, schemas


def authenticate_user(db: Session, username: str, password: str):
    user = db.query(models.User).filter(models.User.username == username).first()
    if not user or not security.verify_password(password, user.hashed_password):
        return None
    return user