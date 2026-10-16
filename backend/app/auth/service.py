from typing import Annotated

from fastapi import Depends, HTTPException, Request, Response, status
from pwdlib import PasswordHash
from sqlalchemy.orm import Session

from app.auth.cookie_manager import ACCESS_COOKIE_NAME, add_auth_cookie
from app.auth.jwt_provider import TokenError, get_token_user_id
from app.auth.token_manager import create_token_pair
from app.database.db import get_db
from app.database.models import User


password_hash = PasswordHash.recommended()


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    return password_hash.verify(password, hashed_password)


def get_current_user(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
) -> User:
    token = request.cookies.get(ACCESS_COOKIE_NAME)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )
    try:
        user_id = get_token_user_id(token)
    except TokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        ) from exc
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
        )
    return user


def set_access_refresh_tokens_to_cookie(
    response: Response,
    access_token: str,
    refresh_token: str,
) -> Response:
    add_auth_cookie(response, access_token, refresh_token)
    response.headers["Cache-Control"] = "no-store"
    return response


def create_access_refresh_tokens_to_cookie(
    response: Response,
    user: User,
) -> Response:
    tokens = create_token_pair(user.id, user.email)
    return set_access_refresh_tokens_to_cookie(response, **tokens)
