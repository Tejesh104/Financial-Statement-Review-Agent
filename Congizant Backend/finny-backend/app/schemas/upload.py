from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class UploadResponse(BaseModel):
    """Response returned immediately after file upload."""
    document_id: str = Field(..., description="Unique UUID identifying the uploaded document")
    filename: str = Field(..., description="Original filename of the uploaded file")
    file_type: str = Field(..., description="Detected file type extension (pdf, excel, csv)")
    status: str = Field(..., description="Initial document processing status: UPLOADED")


class DocumentStatusResponse(BaseModel):
    """Status metadata for an uploaded document."""
    document_id: str
    filename: str
    file_type: str
    status: str
    uploaded_at: datetime
    processed_at: Optional[datetime] = None
    error_message: Optional[str] = None
