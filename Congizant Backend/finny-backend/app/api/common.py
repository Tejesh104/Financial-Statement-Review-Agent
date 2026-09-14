import uuid
import copy
import logging
from typing import Tuple, Dict, Any, Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from app.models.document import Document, DocumentStatus
from app.models.financial_data import FinancialData

logger = logging.getLogger(__name__)


def validate_uuid(document_id: str) -> str:
    """Validate that document_id is a valid UUID string (or preloaded demo document ID).
    
    Raises:
        HTTPException: HTTP 400 Bad Request if document_id is not a valid UUID.
    """
    clean_id = str(document_id).strip()
    if clean_id.startswith("doc-demo-"):
        return clean_id
    try:
        uuid.UUID(clean_id)
        return clean_id
    except (ValueError, AttributeError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid document ID format '{document_id}'. Expected a valid UUID."
        )


def get_normalized_document_and_record(
    document_id: str,
    db: Session,
    user: Optional[Any] = None
) -> Tuple[Document, FinancialData]:
    """Validate UUID format, verify document exists and is in NORMALIZED state, and fetch financial record.
    If user is provided, verifies user owns the document (or document has no owner).
    
    Returns:
        Tuple[Document, FinancialData]: The verified document and financial data record.
        
    Raises:
        HTTPException: 
            - HTTP 400 if document_id is not a valid UUID.
            - HTTP 404 if document does not exist or unauthorized.
            - HTTP 400 if document is not in NORMALIZED status.
            - HTTP 404 if normalized FinancialData record does not exist.
    """
    # 1. Validate UUID format
    clean_id = validate_uuid(document_id)

    # 2. Fetch document record
    doc = db.query(Document).filter(Document.id == clean_id).first()
    if not doc and clean_id.startswith("doc-demo-"):
        from app.database.demo_seeder import ensure_demo_documents
        ensure_demo_documents(db)
        doc = db.query(Document).filter(Document.id == clean_id).first()

    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with ID '{clean_id}' not found."
        )

    # 2b. Authorization check: if authenticated user is provided, must own the document or document is legacy (user_id is None)
    if user is not None and doc.user_id is not None and doc.user_id != getattr(user, "id", None):
        logger.warning("User %s attempted unauthorized access to document %s", getattr(user, "id", None), clean_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with ID '{clean_id}' not found."
        )

    # 3. Document must be in NORMALIZED status
    if doc.status != DocumentStatus.NORMALIZED.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Document '{clean_id}' is in '{doc.status}' state and has not been normalized yet."
        )

    # 4. Retrieve normalized financial data
    fin_record = db.query(FinancialData).filter(FinancialData.document_id == doc.id).first()
    if not fin_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Normalized financial record for document '{clean_id}' was not found."
        )

    return doc, fin_record


def persist_analysis_section(
    fin_record: FinancialData,
    db: Session,
    section_key: str,
    section_data: Dict[str, Any],
    document_id: str
) -> None:
    """Safely and atomically persist an analytical result under normalized_data['analysis'][section_key].
    
    Guarantees:
    - Never overwrites underlying normalized financial data
    - Preserves all other analysis sections (yoy, ratios, agent1)
    - Re-running updates only its own analysis section cleanly
    - Commits atomically and rolls back on failure without leaving dirty session
    """
    try:
        # Re-fetch active record from DB session to avoid stale identity map issues
        active_record = db.query(FinancialData).filter(FinancialData.document_id == document_id).first()
        target = active_record or fin_record
        norm_data = copy.deepcopy(target.normalized_data) if target.normalized_data else {}
        if "analysis" not in norm_data or not isinstance(norm_data["analysis"], dict):
            norm_data["analysis"] = {}
        norm_data["analysis"][section_key] = section_data
        target.normalized_data = norm_data
        flag_modified(target, "normalized_data")
        db.commit()
    except Exception as db_err:
        logger.error("Failed to persist %s analysis for doc %s: %s", section_key, document_id, db_err)
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to persist {section_key} analysis in database: {str(db_err)}"
        )


def persist_validation_section(
    fin_record: FinancialData,
    db: Session,
    validation_data: Dict[str, Any],
    document_id: str
) -> None:
    """Safely and atomically persist mathematical validation under normalized_data['validation'].
    
    Guarantees:
    - Preserves all normalized financial data and analysis blocks
    - Commits atomically and rolls back on failure
    """
    try:
        active_record = db.query(FinancialData).filter(FinancialData.document_id == document_id).first()
        target = active_record or fin_record
        norm_data = copy.deepcopy(target.normalized_data) if target.normalized_data else {}
        norm_data["validation"] = {"balance_sheet_check": validation_data}
        target.normalized_data = norm_data
        flag_modified(target, "normalized_data")
        db.commit()
    except Exception as db_err:
        logger.error("Failed to persist validation for doc %s: %s", document_id, db_err)
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to persist validation in database: {str(db_err)}"
        )


def persist_ml_section(
    fin_record: FinancialData,
    db: Session,
    ml_data: Dict[str, Any],
    document_id: str
) -> None:
    """Safely and atomically persist ML anomaly detection under normalized_data['ml_anomaly'].
    
    Guarantees:
    - Never deletes validation, analysis (yoy, ratios, agent1), or normalized financial data
    - Repeated execution updates only 'ml_anomaly' in place
    - Commits atomically and rolls back on failure
    """
    try:
        active_record = db.query(FinancialData).filter(FinancialData.document_id == document_id).first()
        target = active_record or fin_record
        norm_data = copy.deepcopy(target.normalized_data) if target.normalized_data else {}
        norm_data["ml_anomaly"] = ml_data
        target.normalized_data = norm_data
        flag_modified(target, "normalized_data")
        db.commit()
    except Exception as db_err:
        logger.error("Failed to persist ML anomaly for doc %s: %s", document_id, db_err)
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to persist ML anomaly in database: {str(db_err)}"
        )


def persist_review_observations_section(
    fin_record: FinancialData,
    db: Session,
    observations_data: Dict[str, Any],
    document_id: str
) -> None:
    """Safely and atomically persist Review Observations under normalized_data['review_observations'].

    Guarantees:
    - Preserves all underlying normalized financial data and sibling sections (validation, analysis.*, ml_anomaly)
    - Repeated execution updates only 'review_observations' in place
    - Commits atomically and rolls back on failure without leaving dirty session
    """
    try:
        active_record = db.query(FinancialData).filter(FinancialData.document_id == document_id).first()
        target = active_record or fin_record
        norm_data = copy.deepcopy(target.normalized_data) if target.normalized_data else {}
        norm_data["review_observations"] = observations_data
        target.normalized_data = norm_data
        flag_modified(target, "normalized_data")
        db.commit()
    except Exception as db_err:
        logger.error("Failed to persist review observations for doc %s: %s", document_id, db_err)
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to persist review observations in database: {str(db_err)}"
        )

