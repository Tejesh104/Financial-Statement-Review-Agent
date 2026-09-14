"""Authorization dependencies for verifying document ownership and access control."""

import logging
from typing import Optional, Tuple

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.document import Document
from app.models.financial_data import FinancialData
from app.models.user import User

logger = logging.getLogger(__name__)


def get_authorized_document(
    document_id: str,
    db: Session,
    user: Optional[User] = None,
) -> Document:
    """Fetch a document and verify the requesting user is authorized to access it.

    Authorization rules:
    - If user is None (unauthenticated backward-compat mode): allow access to any document
    - If user is authenticated: document must have user_id == user.id OR user_id is NULL (legacy)

    Returns 404 (not 403) for unauthorized documents to prevent IDOR information leakage.

    Raises:
        HTTPException 404: document not found or not authorized.
    """
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc and str(document_id).startswith("doc-demo-"):
        from app.database.demo_seeder import ensure_demo_documents
        ensure_demo_documents(db)
        doc = db.query(Document).filter(Document.id == document_id).first()

    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with ID '{document_id}' not found."
        )

    # Authorization check: authenticated users can only access their own documents
    # or legacy documents with no owner (user_id is NULL)
    if user is not None and doc.user_id is not None and doc.user_id != user.id:
        # Return 404 instead of 403 to prevent IDOR leakage
        logger.warning(
            "User %s attempted to access document %s owned by user %s",
            user.id, document_id, doc.user_id
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with ID '{document_id}' not found."
        )

    return doc


def get_authorized_document_and_record(
    document_id: str,
    db: Session,
    user: Optional[User] = None,
) -> Tuple[Document, FinancialData]:
    """Fetch a normalized document + financial record with authorization check.

    Combines document authorization with the normalized-state and financial-record checks
    from the existing common.get_normalized_document_and_record.

    Raises:
        HTTPException 404: document or financial record not found / not authorized.
        HTTPException 400: document not in NORMALIZED state.
    """
    from app.api.common import validate_uuid
    from app.models.document import DocumentStatus

    clean_id = validate_uuid(document_id)
    doc = get_authorized_document(clean_id, db, user)

    if doc.status != DocumentStatus.NORMALIZED.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Document '{clean_id}' is in '{doc.status}' state and has not been normalized yet."
        )

    fin_record = db.query(FinancialData).filter(FinancialData.document_id == doc.id).first()
    if not fin_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Normalized financial record for document '{clean_id}' was not found."
        )

    return doc, fin_record
