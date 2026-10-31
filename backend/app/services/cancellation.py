"""Cooperative cancellation: interrupt HTTP immediately, drain local work before cleanup."""
import asyncio
from contextlib import contextmanager, suppress
from contextvars import ContextVar
from dataclasses import dataclass, field
from uuid import UUID

from fastapi import HTTPException
from starlette.concurrency import run_in_threadpool as _threadpool


class RequestCancelled(asyncio.CancelledError):
    pass


@dataclass
class Operation:
    request_id: UUID
    stop: asyncio.Event = field(default_factory=asyncio.Event)
    task: asyncio.Task | None = None


current: ContextVar[Operation | None] = ContextVar("current_operation", default=None)
operations: dict[tuple, Operation] = {}
deleting: set[tuple] = set()


def checkpoint():
    operation = current.get()
    if operation is not None and operation.stop.is_set():
        raise RequestCancelled()


@contextmanager
def suspended():
    token = current.set(None)
    try:
        yield
    finally:
        current.reset(token)


async def run_in_threadpool(function, *args, **kwargs):
    checkpoint()
    # Do not abandon a worker that may still be writing files or a transaction.
    return await _threadpool(function, *args, **kwargs)


async def interruptible(awaitable):
    operation = current.get()
    if operation is None:
        return await awaitable
    work = asyncio.ensure_future(awaitable)
    if operation.stop.is_set():
        work.cancel()
        await asyncio.gather(work, return_exceptions=True)
        raise RequestCancelled()
    stopped = asyncio.create_task(operation.stop.wait())
    try:
        await asyncio.wait((work, stopped), return_when=asyncio.FIRST_COMPLETED)
        if operation.stop.is_set():
            work.cancel()
            await asyncio.gather(work, return_exceptions=True)
            raise RequestCancelled()
        return await work
    finally:
        stopped.cancel()
        if not work.done():
            work.cancel()
        await asyncio.gather(work, stopped, return_exceptions=True)


def bind(user_id, chat_id):
    operation = current.get()
    if operation:
        if (user_id, chat_id) in deleting:
            operation.stop.set()
            checkpoint()
        operations[user_id, chat_id] = operation


async def cancel(user_id, chat_id, request_id=None):
    operation = operations.get((user_id, chat_id))
    if operation is None or (request_id is not None and operation.request_id != request_id):
        return False
    operation.stop.set()
    if operation.task is not None:
        await asyncio.shield(asyncio.gather(operation.task, return_exceptions=True))
    for alias in [alias for alias, value in operations.items() if value is operation]:
        operations.pop(alias, None)
    return True


@contextmanager
def deletion(keys):
    if any(key in deleting for key in keys):
        raise HTTPException(409, "Удаление уже выполняется")
    deleting.update(keys)
    try:
        yield
    finally:
        deleting.difference_update(keys)


async def supervise(request, key, request_id, factory):
    if key in deleting:
        raise HTTPException(409, "Чат удаляется")
    if key in operations:
        raise HTTPException(409, detail={"code": "agent_busy", "message": "Агент ещё обрабатывает предыдущий запрос."})
    operation = Operation(request_id)
    async def execute():
        token = current.set(operation)
        try:
            return await factory()
        finally:
            current.reset(token)
    operation.task = asyncio.create_task(execute())
    operations[key] = operation
    async def watch():
        while not operation.task.done():
            if await request.is_disconnected():
                operation.stop.set()
                return
            await asyncio.sleep(0.2)
    watcher = asyncio.create_task(watch())
    try:
        return await asyncio.shield(operation.task)
    except asyncio.CancelledError:
        requested = operation.stop.is_set()
        operation.stop.set()
        with suppress(asyncio.CancelledError):
            await asyncio.shield(operation.task)
        if requested:
            raise HTTPException(409, detail={"code": "request_cancelled", "message": "Запрос отменён"}) from None
        raise
    finally:
        # Starlette's is_disconnected uses an AnyIO cancellation scope which can
        # consume Task.cancel(). Let the watcher exit on task.done() instead.
        await asyncio.gather(watcher, return_exceptions=True)
        for alias in [alias for alias, value in operations.items() if value is operation]:
            operations.pop(alias, None)
