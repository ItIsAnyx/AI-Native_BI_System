from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import case, select, update

from app.database.db import SessionLocal
from app.services.cancellation import checkpoint
from app.database.models import Artifact, ChatHistory, Source, ProjectChat


def _owned_chat(db, chat_id: UUID, user_id: UUID) -> ChatHistory:
    chat = db.scalar(select(ChatHistory).where(ChatHistory.id == chat_id, ChatHistory.user_id == user_id))
    if chat is None:
        raise HTTPException(status_code=404, detail="Chat not found")
    return chat


def _source_data(source: Source) -> dict:
    return {
        "id": str(source.id), "name": source.name, "description": source.description,
        "type": source.type, "file_path": source.file_path,
    }


def create_chat(user_id: UUID, title: str = "Новый чат") -> UUID:
    with SessionLocal() as db:
        chat = ChatHistory(user_id=user_id, title=title[:80])
        db.add(chat)
        checkpoint()
        db.commit()
        return chat.id


def list_chats(user_id: UUID) -> list[dict]:
    with SessionLocal() as db:
        rows = db.execute(select(
            ChatHistory.id, ChatHistory.title, ChatHistory.created_at, ChatHistory.updated_at, ProjectChat.project_id,
        ).outerjoin(ProjectChat, ProjectChat.chat_id == ChatHistory.id)
          .where(ChatHistory.user_id == user_id).order_by(ChatHistory.updated_at.desc())).mappings()
        return [dict(row) for row in rows]


def get_chat_history(chat_id: UUID, user_id: UUID) -> list[dict]:
    with SessionLocal() as db:
        history = db.scalar(select(ChatHistory.chat_history).where(ChatHistory.id == chat_id, ChatHistory.user_id == user_id))
        if history is None:
            raise HTTPException(status_code=404, detail="Chat not found")
        return history


def get_active_context(chat_id: UUID, user_id: UUID) -> list[dict]:
    with SessionLocal() as db:
        context = db.scalar(select(ChatHistory.active_context).where(ChatHistory.id == chat_id, ChatHistory.user_id == user_id))
        if context is None:
            raise HTTPException(status_code=404, detail="Chat not found")
        return context


def get_chat_state(chat_id: UUID, user_id: UUID) -> dict:
    with SessionLocal() as db:
        chat = _owned_chat(db, chat_id, user_id)
        sources = db.scalars(select(Source).where(Source.chat_id == chat_id).order_by(Source.created_at, Source.id)).all()
        return {
            "chat_history": chat.chat_history, "active_context": chat.active_context,
            "active_source_id": str(chat.active_source_id) if chat.active_source_id else None,
            "version": chat.version, "sources": [_source_data(source) for source in sources],
        }


def get_chat_sources(chat_id: UUID, user_id: UUID) -> list[dict]:
    with SessionLocal() as db:
        if db.scalar(select(ChatHistory.id).where(ChatHistory.id == chat_id, ChatHistory.user_id == user_id)) is None:
            raise HTTPException(status_code=404, detail="Chat not found")
        return [_source_data(source) for source in db.scalars(select(Source).where(
            Source.chat_id == chat_id,
        ).order_by(Source.created_at, Source.id))]


def save_chat_state(
    chat_id: UUID, user_id: UUID, version: int,
    chat_history: list[dict], active_context: list[dict], active_source_id: str | None,
    new_source: dict | None = None, artifacts: list[dict] | None = None,
    new_sources: list[dict] | None = None,
) -> None:
    with SessionLocal() as db:
        first_question = next((m["content"] for m in chat_history if m["role"] == "user"), "Новый чат")
        result = db.execute(update(ChatHistory).where(
            ChatHistory.id == chat_id, ChatHistory.user_id == user_id, ChatHistory.version == version,
        ).values(
            chat_history=chat_history, active_context=active_context,
            active_source_id=UUID(active_source_id) if active_source_id else None,
            version=version + 1,
            title=case((ChatHistory.title == "Новый чат", first_question[:80]), else_=ChatHistory.title),
        ))
        if result.rowcount != 1:
            raise HTTPException(status_code=409, detail="Chat changed during this request. Reload it and retry")
        if new_source:
            db.add(Source(chat_id=chat_id, **new_source))
        for source in new_sources or []:
            db.add(Source(chat_id=chat_id, **source))
        for artifact in artifacts or []:
            db.add(Artifact(chat_id=chat_id, **artifact))
        checkpoint()
        db.commit()


def get_source_file(source_id: UUID, user_id: UUID) -> dict:
    with SessionLocal() as db:
        source = db.scalar(select(Source).join(ChatHistory).where(
            Source.id == source_id, ChatHistory.user_id == user_id,
        ))
        if source is None:
            raise HTTPException(status_code=404, detail="Source not found")
        return _source_data(source)


def get_artifact(artifact_id: UUID, user_id: UUID) -> dict:
    with SessionLocal() as db:
        artifact = db.scalar(select(Artifact).join(ChatHistory).where(
            Artifact.id == artifact_id, ChatHistory.user_id == user_id,
        ))
        if artifact is None:
            raise HTTPException(status_code=404, detail="Artifact not found")
        return {"file_path": artifact.file_path, "mime_type": artifact.mime_type}
