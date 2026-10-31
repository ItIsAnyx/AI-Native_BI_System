from typing import Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from app.config import settings


class ContextMessage(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str


class MessageRequest(BaseModel):
    message: str = Field(min_length=1, max_length=settings.MAX_REQUEST_LENGTH)
    chat_id: UUID | None = None
    source_id: UUID | None = None
    request_id: UUID = Field(default_factory=uuid4)


class ChartArtifact(BaseModel):
    id: UUID
    url: str
    source_id: str | None = None
    chart_type: str
    x_column: str
    y_column: str
    aggregation: str
    total_rows: int
    valid_rows: int
    excluded_rows: int
    available_points: int
    plotted_points: int
    truncated: bool
    mime_type: Literal["image/png"]
    title: str = ""
    panels: list[dict] = Field(default_factory=list)


class MessageResponse(BaseModel):
    chat_id: UUID
    message_id: UUID
    message: str
    context: list[ContextMessage]
    sources: list[dict] = Field(default_factory=list)
    charts: list[ChartArtifact] = Field(default_factory=list)
