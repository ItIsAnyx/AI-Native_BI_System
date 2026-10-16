from uuid import UUID

from pydantic import BaseModel, ConfigDict


class UserDto(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str
    login: str
