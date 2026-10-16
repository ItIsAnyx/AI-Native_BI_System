from uuid import uuid4

from sqlalchemy import Column, String, Uuid
from app.database.db import Base

class User(Base):
    __tablename__ = "users"
    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid4, nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    login = Column(String(255), unique=True, nullable=False)
    password = Column(String(255), nullable=False)
