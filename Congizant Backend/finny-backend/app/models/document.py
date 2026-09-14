import uuid
from datetime import datetime, timezone
from enum import Enum
from sqlalchemy import Column, String, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from app.database.database import Base


class DocumentStatus(str, Enum):
    UPLOADED = "UPLOADED"
    EXTRACTING = "EXTRACTING"
    EXTRACTED = "EXTRACTED"
    NORMALIZING = "NORMALIZING"
    NORMALIZED = "NORMALIZED"
    EXTRACTION_FAILED = "EXTRACTION_FAILED"
    NORMALIZATION_FAILED = "NORMALIZATION_FAILED"
    REJECTED = "REJECTED"


class Document(Base):
    """SQLAlchemy model representing an uploaded document and its processing state."""
    
    __tablename__ = "documents"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=True, index=True)
    filename = Column(String(255), nullable=False)
    file_type = Column(String(50), nullable=False)
    file_path = Column(String(500), nullable=False)
    status = Column(String(50), nullable=False, default=DocumentStatus.UPLOADED.value)
    uploaded_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    processed_at = Column(DateTime(timezone=True), nullable=True)
    error_message = Column(Text, nullable=True)
    
    # Relationship to owner (nullable for backward compat with pre-existing documents)
    owner = relationship("User", back_populates="documents")
    
    # Relationship to financial data
    financial_records = relationship(
        "FinancialData",
        back_populates="document",
        cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Document(id='{self.id}', filename='{self.filename}', status='{self.status}')>"
