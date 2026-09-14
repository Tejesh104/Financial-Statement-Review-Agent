import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Float, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from app.database.database import Base


class FinancialData(Base):
    """SQLAlchemy model representing normalized financial metrics extracted from a document."""
    
    __tablename__ = "financial_data"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id = Column(String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    
    company_name = Column(String(255), nullable=True)
    currency = Column(String(10), nullable=True)
    period_start = Column(String(50), nullable=True)
    period_end = Column(String(50), nullable=True)
    fiscal_year = Column(String(50), nullable=True)
    
    # Core normalized financial indicators
    revenue = Column(Float, nullable=True)
    assets = Column(Float, nullable=True)
    liabilities = Column(Float, nullable=True)
    equity = Column(Float, nullable=True)
    
    # Complete normalized JSON document containing all extracted data, warnings, and source info
    normalized_data = Column(JSON, nullable=False)
    
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    
    # Back-reference to document
    document = relationship("Document", back_populates="financial_records")

    def __repr__(self) -> str:
        return f"<FinancialData(id='{self.id}', document_id='{self.document_id}', revenue={self.revenue})>"
