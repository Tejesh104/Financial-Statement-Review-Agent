import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship
from app.database.database import Base


class ChatMessage(Base):
    """SQLAlchemy model representing a chat message in a document-scoped conversation."""

    __tablename__ = "chat_messages"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    document_id = Column(String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(String(20), nullable=False)  # 'user' or 'assistant'
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    user = relationship("User", back_populates="chat_messages")

    # Composite index for efficient conversation queries
    __table_args__ = (
        Index("ix_chat_user_doc_time", "user_id", "document_id", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<ChatMessage(id='{self.id}', role='{self.role}', user_id='{self.user_id}')>"
