from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from app.auth.cookie_manager import REFRESH_COOKIE_NAME, clear_auth_cookie
from app.auth.service import (
    create_access_refresh_tokens_to_cookie,
    get_current_user,
    set_access_refresh_tokens_to_cookie,
)
from app.auth.token_manager import refresh_access_token
from app.database.db import get_db
from app.database.models import User
from app.exceptions.auth import InvalidCredentialsError, UserAlreadyExistsError
from app.schemas.auth import LoginUserRequest, RegisterUserRequest
from app.schemas.user import UserDto
from app.services.user_service import login_user, register_user


router = APIRouter()
Database = Annotated[Session, Depends(get_db)]


@router.post("/login", response_model=UserDto)
def login(payload: LoginUserRequest, response: Response, db: Database) -> UserDto:
    try:
        user = login_user(db, payload.email, payload.password)
    except InvalidCredentialsError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        ) from exc
    create_access_refresh_tokens_to_cookie(response, user)
    return UserDto.model_validate(user)


@router.post("/register", response_model=UserDto, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterUserRequest, response: Response, db: Database) -> UserDto:
    try:
        user = register_user(db, payload.email, payload.login, payload.password)
    except UserAlreadyExistsError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email or login already registered",
        ) from exc
    create_access_refresh_tokens_to_cookie(response, user)
    return UserDto.model_validate(user)


@router.post("/refresh")
def refresh(request: Request, response: Response, db: Database) -> dict[str, str]:
    refresh_token = request.cookies.get(REFRESH_COOKIE_NAME)
    tokens = refresh_access_token(refresh_token, db) if refresh_token else None
    if tokens is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )
    set_access_refresh_tokens_to_cookie(response, **tokens)
    return {"message": "token refreshed"}


@router.post("/logout")
def logout(response: Response) -> dict[str, str]:
    clear_auth_cookie(response)
    return {"message": "logout"}


@router.get("/me", response_model=UserDto)
def me(response: Response, user: Annotated[User, Depends(get_current_user)]) -> UserDto:
    response.headers["Cache-Control"] = "no-store"
    return UserDto.model_validate(user)
