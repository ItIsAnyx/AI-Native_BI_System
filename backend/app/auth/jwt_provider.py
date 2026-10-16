import base64
import binascii
from datetime import datetime, timedelta, timezone
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

import jwt
from jwt import ExpiredSignatureError, InvalidTokenError

from app.config import settings

class TokenType(StrEnum):
    ACCESS = "access"
    REFRESH = "refresh"


class TokenError(Exception):
    pass


class TokenExpiredError(TokenError):
    pass


class TokenTypeError(TokenError):
    pass


ALGORITHM = "HS256"
if settings.ALGORITHM != ALGORITHM:
    raise ValueError("Auth supports only HS256")

try:
    SECRET_KEY = base64.b64decode(settings.SECRET_KEY, validate=True)
except (ValueError, binascii.Error) as exc:
    raise ValueError("JWT secret must be valid base64") from exc
if len(SECRET_KEY) < 32:
    raise ValueError("JWT secret must be at least 32 bytes")
if settings.ACCESS_TOKEN_EXPIRE_MINUTES <= 0 or settings.REFRESH_TOKEN_EXPIRE_DAYS <= 0:
    raise ValueError("Token lifetimes must be positive")


def _user_id(subject: Any) -> UUID:
    if not isinstance(subject, str):
        raise TokenError("Invalid user ID")
    try:
        user_id = UUID(subject)
    except ValueError as exc:
        raise TokenError("Invalid user ID") from exc
    if user_id.int == 0 or str(user_id) != subject:
        raise TokenError("Invalid user ID")
    return user_id


def create_token(
    subject: str,
    token_type: TokenType,
    expires_delta: timedelta,
    **claims: Any,
) -> str:
    _user_id(subject)
    if expires_delta < timedelta(seconds=1):
        raise ValueError("Token lifetime must be at least one second")
    now = datetime.now(timezone.utc)
    payload = {
        **claims,
        "sub": subject,
        "type": TokenType(token_type).value,
        "iat": int(now.timestamp()),
        "exp": int((now + expires_delta).timestamp()),
        "jti": str(uuid4()),
    }
    if "role" in payload and (
        not isinstance(payload["role"], str) or not payload["role"].strip()
    ):
        raise ValueError("Invalid user role")
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def create_access_token(
    user_id: UUID,
    email: str | None = None,
    role: str = "user",
) -> str:
    claims: dict[str, Any] = {"role": role}
    if email is not None:
        claims["email"] = email
    return create_token(
        subject=str(user_id),
        token_type=TokenType.ACCESS,
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        **claims,
    )


def create_refresh_token(user_id: UUID) -> str:
    return create_token(
        subject=str(user_id),
        token_type=TokenType.REFRESH,
        expires_delta=timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    )


def decode_token(
    token: str,
    expected_type: TokenType | None = None,
) -> dict[str, Any]:
    if not isinstance(token, str) or not token:
        raise TokenError("Invalid token")
    try:
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM],
            options={"require": ["sub", "iat", "exp", "type", "jti"]},
        )
    except ExpiredSignatureError as exc:
        raise TokenExpiredError("Token expired") from exc
    except (InvalidTokenError, ValueError, TypeError, OverflowError) as exc:
        raise TokenError("Invalid token") from exc

    _user_id(payload["sub"])
    if type(payload["iat"]) is not int or type(payload["exp"]) is not int:
        raise TokenError("Invalid token timestamps")
    if payload["exp"] <= payload["iat"]:
        raise TokenError("Invalid token lifetime")
    try:
        UUID(payload["jti"])
        token_type = TokenType(payload["type"])
    except (ValueError, TypeError, AttributeError) as exc:
        raise TokenError("Invalid token claims") from exc
    if "role" in payload and (
        not isinstance(payload["role"], str) or not payload["role"].strip()
    ):
        raise TokenError("Invalid user role")
    if expected_type is not None and token_type != expected_type:
        raise TokenTypeError(f"Expected {expected_type.value} token")
    return payload


def get_token_subject(token: str) -> str:
    return decode_token(token)["sub"]


def get_token_user_id(token: str) -> UUID:
    return _user_id(verify_access_token(token)["sub"])


def get_token_role(token: str) -> str:
    role = verify_access_token(token).get("role")
    if role is None:
        raise TokenError("Token has no user role")
    return role


def get_token_type(token: str) -> TokenType:
    return TokenType(decode_token(token)["type"])


def verify_access_token(token: str) -> dict[str, Any]:
    return decode_token(token, TokenType.ACCESS)


def verify_refresh_token(token: str) -> dict[str, Any]:
    return decode_token(token, TokenType.REFRESH)

