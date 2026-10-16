from typing import Generator

from sqlalchemy import create_engine, URL
from sqlalchemy.orm import Session, sessionmaker, DeclarativeBase
from app.config import settings

DATABASE_URL = URL.create(
    drivername="postgresql+psycopg2",
    username=settings.DB_USERNAME,
    password=settings.DB_PASSWORD,
    host=settings.DB_HOST,
    port=settings.DB_PORT,
    database=settings.DB_DATABASE
)

engine = create_engine(DATABASE_URL, echo=False, pool_pre_ping=True)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

class Base(DeclarativeBase):
    pass

def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try: 
        yield db
    finally:
        db.close()
