from typing import Literal

from fastapi import Response

from app.config import settings


ACCESS_COOKIE_NAME = "access_token"
REFRESH_COOKIE_NAME = "refresh_token"
AUTH_COOKIE_PATH = "/"

ACCESS_MAX_AGE = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
REFRESH_MAX_AGE = settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60


def _same_site() -> Literal["lax", "strict", "none"]:
    value = settings.COOKIE_SAMESITE.lower()
    if value not in ("lax", "strict", "none"):
        raise ValueError("COOKIE_SAMESITE must be lax, strict or none")
    if value == "none" and not settings.COOKIE_SECURE:
        raise ValueError("SameSite=None requires secure cookies")
    return value


def create_cookie(
    response: Response,
    name: str,
    value: str,
    max_age: int,
    path: str = AUTH_COOKIE_PATH,
) -> None:
    if not isinstance(value, str) or not value:
        raise ValueError("Cookie token must be a non-empty string")
    if max_age <= 0:
        raise ValueError("Cookie lifetime must be positive")
    response.set_cookie(
        key=name,
        value=value,
        max_age=max_age,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite=_same_site(),
        path=path,
    )


def create_empty_cookie(
    response: Response,
    name: str,
    path: str = AUTH_COOKIE_PATH,
) -> None:
    response.delete_cookie(
        key=name,
        path=path,
        secure=settings.COOKIE_SECURE,
        httponly=True,
        samesite=_same_site(),
    )


def add_auth_cookie(response: Response, access_token: str, refresh_token: str) -> None:
    if not all(isinstance(token, str) and token for token in (access_token, refresh_token)):
        raise ValueError("Both auth tokens must be non-empty strings")
    create_cookie(response, ACCESS_COOKIE_NAME, access_token, ACCESS_MAX_AGE)
    create_cookie(response, REFRESH_COOKIE_NAME, refresh_token, REFRESH_MAX_AGE)


def clear_auth_cookie(response: Response) -> None:
    create_empty_cookie(response, ACCESS_COOKIE_NAME)
    create_empty_cookie(response, REFRESH_COOKIE_NAME)
    response.headers["Cache-Control"] = "no-store"
