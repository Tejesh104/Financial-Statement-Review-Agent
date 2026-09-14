import uuid
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import get_optional_user
from app.database.database import get_db
from app.models.document import Document, DocumentStatus
from app.models.user import User
from app.schemas.upload import UploadResponse
from app.services.extraction.extractor_factory import ExtractorFactory

router = APIRouter()


@router.post(
    "/upload",
    response_model=UploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a financial document",
    description="Upload a PDF, Excel (.xlsx, .xls), or CSV financial statement for extraction and normalization."
)
async def upload_document(
    file: UploadFile = File(..., description="Financial document to upload (PDF, Excel, or CSV)"),
    db: Session = Depends(get_db),
    user: Optional[User] = Depends(get_optional_user)
):
    # 1. Validate file presence
    if not file or not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No file provided in the upload request."
        )

    # 2. Sanitize filename to prevent directory traversal attacks
    safe_filename = Path(file.filename).name
    extension = Path(safe_filename).suffix.lower()

    # 3. Validate supported extension
    if extension not in settings.ALLOWED_EXTENSIONS:
        allowed = ", ".join(sorted(settings.ALLOWED_EXTENSIONS))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file extension '{extension}'. Supported file extensions are: {allowed}"
        )

    # 4. Generate unique document ID and secure storage path
    document_id = str(uuid.uuid4())
    stored_filename = f"{document_id}_{safe_filename}"
    file_path = settings.upload_path / stored_filename

    # 5. Stream and save file while enforcing size limit
    total_bytes = 0
    try:
        with open(file_path, "wb") as buffer:
            while chunk := await file.read(1024 * 1024):  # 1MB chunks
                total_bytes += len(chunk)
                if total_bytes > settings.max_upload_size_bytes:
                    # Clean up partially written file
                    buffer.close()
                    if file_path.exists():
                        file_path.unlink()
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"File exceeds the maximum upload limit of {settings.MAX_UPLOAD_SIZE_MB}MB."
                    )
                buffer.write(chunk)
    except HTTPException:
        raise
    except Exception as err:
        if file_path.exists():
            file_path.unlink()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save uploaded file: {str(err)}"
        )

    # 6. Validate non-empty file
    if total_bytes == 0:
        if file_path.exists():
            file_path.unlink()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The uploaded file is empty (0 bytes)."
        )

    # 7. Identify canonical file type
    file_type = ExtractorFactory.get_file_type_name(extension)

    # 8. Record document in database
    doc_record = Document(
        id=document_id,
        user_id=user.id if user else None,
        filename=safe_filename,
        file_type=file_type,
        file_path=str(file_path.resolve()),
        status=DocumentStatus.UPLOADED.value
    )
    db.add(doc_record)
    db.commit()
    db.refresh(doc_record)

    return UploadResponse(
        document_id=doc_record.id,
        filename=doc_record.filename,
        file_type=doc_record.file_type,
        status=doc_record.status
    )
