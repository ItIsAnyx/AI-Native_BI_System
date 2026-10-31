"""Authenticated project management, dashboard library and live analytical sources."""
import json
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, Field
from sqlalchemy import delete, select

from app.api.chat import get_agent_user_id, running_chats
from app.config import settings
from app.database.db import SessionLocal
from app.database.models import Artifact, ChatHistory, Project, ProjectChat, Source
from app.repositories.chat_repository import _owned_chat, get_chat_state, save_chat_state
from app.services import chat_storage, cancellation
from starlette.concurrency import run_in_threadpool
from app.data.postgres_source import list_tables, read_table

router = APIRouter()


class ProjectRequest(BaseModel):
    name: str = Field(min_length=1, max_length=40)


class MoveRequest(BaseModel):
    project_id: UUID | None = None


class DatabaseSourceRequest(BaseModel):
    connection_id: str = Field(min_length=1, max_length=100)
    schema_name: str = Field(default="public", alias="schema", min_length=1, max_length=128)
    table: str = Field(min_length=1, max_length=128)


def owned_project(db, project_id, user_id):
    row = db.scalar(select(Project).where(Project.id == project_id, Project.user_id == user_id))
    if row is None:
        raise HTTPException(404, "Project not found")
    return row


def require_idle(chat_id, user_id):
    if (user_id, chat_id) in running_chats:
        raise HTTPException(409, "Дождитесь завершения обработки в чате")


def delete_chat_records(db, chat_id, user_id):
    _owned_chat(db, chat_id, user_id)
    require_idle(chat_id, user_id)
    paths = list(db.scalars(select(Source.file_path).where(Source.chat_id == chat_id)))
    paths += list(db.scalars(select(Artifact.file_path).where(Artifact.chat_id == chat_id)))
    for model in (ProjectChat, Artifact, Source):
        db.execute(delete(model).where(model.chat_id == chat_id))
    db.execute(delete(ChatHistory).where(ChatHistory.id == chat_id))
    return paths


def cleanup(paths):
    for path in paths:
        chat_storage.remove_file(path)


@router.delete("/agent/chats/{chat_id}", status_code=204)
async def delete_chat(chat_id: UUID, user_id: UUID = Depends(get_agent_user_id)):
    await run_in_threadpool(get_chat_state, chat_id, user_id)
    with cancellation.deletion([(user_id, chat_id)]):
        await cancellation.cancel(user_id, chat_id)
        def remove():
            with SessionLocal() as db:
                paths = delete_chat_records(db, chat_id, user_id)
                db.commit()
            cleanup(paths)
        await run_in_threadpool(remove)
    return Response(status_code=204)


@router.get("/agent/projects")
def projects(user_id: UUID = Depends(get_agent_user_id)):
    with SessionLocal() as db:
        return [{"id": p.id, "name": p.name, "open": True} for p in
                db.scalars(select(Project).where(Project.user_id == user_id).order_by(Project.name))]


@router.post("/agent/projects", status_code=201)
def create_project(body: ProjectRequest, user_id: UUID = Depends(get_agent_user_id)):
    name = " ".join(body.name.split())
    if not name:
        raise HTTPException(422, "Введите название проекта")
    with SessionLocal() as db:
        existing = db.scalars(select(Project.name).where(Project.user_id == user_id))
        if name.casefold() in {n.casefold() for n in existing}:
            raise HTTPException(409, "Проект с таким названием уже существует")
        project = Project(user_id=user_id, name=name)
        db.add(project)
        db.commit()
        return {"id": project.id, "name": project.name, "open": True}


@router.put("/agent/chats/{chat_id}/project")
def move_chat(chat_id: UUID, body: MoveRequest, user_id: UUID = Depends(get_agent_user_id)):
    with SessionLocal() as db:
        _owned_chat(db, chat_id, user_id)
        if body.project_id:
            owned_project(db, body.project_id, user_id)
        db.execute(delete(ProjectChat).where(ProjectChat.chat_id == chat_id))
        if body.project_id:
            db.add(ProjectChat(chat_id=chat_id, project_id=body.project_id))
        db.commit()
    return {"chatId": chat_id, "projectId": body.project_id}


@router.delete("/agent/projects/{project_id}", status_code=204)
async def delete_project(project_id: UUID, delete_chats: bool = False, user_id: UUID = Depends(get_agent_user_id)):
    def find_chats():
        with SessionLocal() as db:
            owned_project(db, project_id, user_id)
            return list(db.scalars(select(ProjectChat.chat_id).where(ProjectChat.project_id == project_id))) if delete_chats else []
    ids = await run_in_threadpool(find_chats)
    with cancellation.deletion([(user_id, chat_id) for chat_id in ids]):
        for chat_id in ids:
            await cancellation.cancel(user_id, chat_id)
        await run_in_threadpool(_delete_project, project_id, delete_chats, user_id)
    return Response(status_code=204)


def _delete_project(project_id, delete_chats, user_id):
    paths = []
    with SessionLocal() as db:
        owned_project(db, project_id, user_id)
        if delete_chats:
            ids = list(db.scalars(select(ProjectChat.chat_id).where(ProjectChat.project_id == project_id)))
            for chat_id in ids:
                paths += delete_chat_records(db, chat_id, user_id)
        db.execute(delete(ProjectChat).where(ProjectChat.project_id == project_id))
        db.execute(delete(Project).where(Project.id == project_id))
        db.commit()
    cleanup(paths)
    return Response(status_code=204)


@router.get("/agent/dashboards")
def dashboards(user_id: UUID = Depends(get_agent_user_id)):
    with SessionLocal() as db:
        rows = db.execute(select(Artifact, ChatHistory.title).join(ChatHistory).where(
            ChatHistory.user_id == user_id).order_by(Artifact.created_at.desc()))
        return [{**a.details, "id": str(a.id), "chat_id": str(a.chat_id), "chat_title": title,
                 "url": f"/agent/artifacts/{a.id}", "created_at": a.created_at}
                for a, title in rows if a.details.get("chart_type") == "dashboard"]


@router.get("/agent/database-connections")
def connections(user_id: UUID = Depends(get_agent_user_id)):
    return [{"id": name, "name": name, "type": "postgresql"} for name in settings.ANALYTICS_CONNECTIONS]


@router.get("/agent/database-connections/{connection_id}/tables")
def tables(connection_id: str, user_id: UUID = Depends(get_agent_user_id)):
    try:
        return list_tables(connection_id)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.post("/agent/chats/{chat_id}/database-sources", status_code=201)
def attach_database(chat_id: UUID, body: DatabaseSourceRequest, user_id: UUID = Depends(get_agent_user_id)):
    require_idle(chat_id, user_id)
    state = get_chat_state(chat_id, user_id)
    descriptor = body.model_dump(by_alias=True)
    try:
        read_table(descriptor)  # Validate access and size; no CSV export or preprocessing.
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    source_id = uuid4()
    relative = f"sources/{chat_id}/{source_id}.json"
    path = chat_storage.storage_path(relative)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(descriptor, ensure_ascii=False), encoding="utf-8")
    source = {"id": source_id, "name": f"{body.schema_name}.{body.table}", "description": "Прямое подключение PostgreSQL",
              "type": "postgresql", "file_path": relative}
    try:
        save_chat_state(chat_id, user_id, state["version"], state["chat_history"], state["active_context"],
                        str(source_id), new_source=source)
    except Exception:
        path.unlink(missing_ok=True)
        raise
    return {key: str(value) if isinstance(value, UUID) else value for key, value in source.items() if key != "file_path"}
