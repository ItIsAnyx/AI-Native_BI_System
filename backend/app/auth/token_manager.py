from typing import TypedDict
from uuid import UUID

from sqlalchemy.orm import Session

from app.auth.jwt_provider import (
    TokenError,
    create_access_token,
    create_refresh_token,
    verify_refresh_token,
)
from app.database.models import User


class TokenPair(TypedDict):
    access_token: str
    refresh_token: str


def create_token_pair(user_id: UUID, email: str) -> TokenPair:
    return {
        "access_token": create_access_token(user_id, email=email),
        "refresh_token": create_refresh_token(user_id),    }


def refresh_access_token(refresh_token: str, db: Session) -> TokenPair | None:
    try:
        payload = verify_refresh_token(refresh_token)
    except TokenError:
        return None

    user = db.get(User, UUID(payload["sub"]))
    return create_token_pair(user.id, user.email) if user else None

