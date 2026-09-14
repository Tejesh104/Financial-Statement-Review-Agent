import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime
from sqlalchemy.orm import relationship
from app.database.database import Base


class User(Base):
    """SQLAlchemy model representing an authenticated user."""

    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    google_id = Column(String(255), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=True)
    picture_url = Column(String(1000), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    last_login_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    documents = relationship("Document", back_populates="owner", lazy="dynamic")
    chat_messages = relationship("ChatMessage", back_populates="user", cascade="all, delete-orphan", lazy="dynamic")

    def __repr__(self) -> str:
        return f"<User(id='{self.id}', email='{self.email}', name='{self.name}')>"
