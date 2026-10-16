from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth.service import hash_password, verify_password
from app.database.models import User
from app.exceptions.auth import InvalidCredentialsError, UserAlreadyExistsError
from app.repositories.user_repository import get_user_by_email, save_user


_DUMMY_PASSWORD_HASH = hash_password("dummy-password-for-timing-equalization")


def register_user(db: Session, email: str, login: str, password: str) -> User:
    if get_user_by_email(db, email) is not None:
        raise UserAlreadyExistsError()
    try:
        return save_user(db, email, login, hash_password(password))
    except IntegrityError as exc:
        # Unique violations, including concurrent registrations.
        if (
            getattr(exc.orig, "pgcode", None) == "23505"
            or getattr(exc.orig, "sqlstate", None) == "23505"
            or getattr(exc.orig, "sqlite_errorcode", None) == 2067
        ):
            raise UserAlreadyExistsError() from exc
        raise


def login_user(db: Session, email: str, password: str) -> User:
    user = get_user_by_email(db, email)
    valid = verify_password(password, user.password if user is not None else _DUMMY_PASSWORD_HASH)
    if user is None or not valid:
        raise InvalidCredentialsError()
    return user
