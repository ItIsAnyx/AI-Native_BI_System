from uuid import uuid4

from sqlalchemy import Column, DateTime, ForeignKey, Integer, JSON, String, Uuid, func
from sqlalchemy.dialects.postgresql import JSONB
from app.database.db import Base

class User(Base):
    __tablename__ = "users"
    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid4, nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    login = Column(String(255), unique=True, nullable=False)
    password = Column(String(255), nullable=False)


class ChatHistory(Base):
    __tablename__ = "chat_history"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(80), nullable=False, default="Новый чат")
    chat_history = Column(JSON().with_variant(JSONB, "postgresql"), nullable=False, default=list)
    active_context = Column(JSON().with_variant(JSONB, "postgresql"), nullable=False, default=list)
    active_source_id = Column(Uuid(as_uuid=True), nullable=True)
    version = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())


class Source(Base):
    __tablename__ = "sources"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    chat_id = Column(Uuid(as_uuid=True), ForeignKey("chat_history.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(String(1000), nullable=False, default="")
    type = Column(String(20), nullable=False, default="csv")
    file_path = Column(String(500), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class Artifact(Base):
    __tablename__ = "artifacts"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    chat_id = Column(Uuid(as_uuid=True), ForeignKey("chat_history.id", ondelete="CASCADE"), nullable=False, index=True)
    message_id = Column(Uuid(as_uuid=True), nullable=False)
    file_path = Column(String(500), nullable=False)
    mime_type = Column(String(100), nullable=False, default="image/png")
    details = Column(JSON().with_variant(JSONB, "postgresql"), nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
