from sqlalchemy.orm import Session
from app.database.models import User

def get_user_by_email(db: Session, email: str):
    return db.query(User).filter(User.email == email).first()

def save_user(db: Session, email: str, login: str, password: str):
    user = User(email=email, login=login, password=password)
    db.add(user)
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise
    db.refresh(user)
    return user
