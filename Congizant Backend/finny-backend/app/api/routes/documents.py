import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import get_optional_user
from app.database.database import get_db
from app.models.document import Document, DocumentStatus
from app.models.financial_data import FinancialData
from app.models.chat import ChatMessage
from app.models.user import User
from app.api.dependencies import get_authorized_document
from app.schemas.upload import DocumentStatusResponse
from app.schemas.financial import (
    NormalizedDocumentResponse,
    NormalizedFinancialData,
    CompanyInfo,
    PeriodInfo,
    FinancialMetrics,
    DocumentSource,
)
from app.schemas.dashboard import (
    DocumentListItem,
    DocumentListResponse,
    DashboardSummaryResponse,
    RiskAssessment,
    PipelineStages,
)
from app.services.extraction.extractor_factory import ExtractorFactory
from app.services.normalization.normalizer import Normalizer
from app.services.validation.statement_classifier import FinancialStatementClassifier

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post(
    "/{document_id}/process",
    response_model=NormalizedDocumentResponse,
    summary="Process document through extraction and normalization pipeline",
    description="Extracts tabular financial data from the document and normalizes fields, metrics, currency, and periods."
)
def process_document(document_id: str, db: Session = Depends(get_db), user: Optional[User] = Depends(get_optional_user)):
    # 1. Fetch document record with authorization check
    doc = get_authorized_document(document_id, db, user)

    file_path = Path(doc.file_path)
    if not file_path.exists():
        doc.status = DocumentStatus.EXTRACTION_FAILED.value
        doc.error_message = f"File not found on server: {doc.filename}"
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document physical file is missing on the server."
        )

    # 2. Status: EXTRACTING
    doc.status = DocumentStatus.EXTRACTING.value
    doc.error_message = None
    db.commit()

    # 3. Resolve Extractor & Extract Raw Data
    try:
        extractor = ExtractorFactory.get_extractor(file_path)
        raw_data = extractor.extract(file_path)
    except Exception as extract_err:
        logger.exception("Extraction failed for document %s", document_id)
        doc.status = DocumentStatus.EXTRACTION_FAILED.value
        doc.error_message = str(extract_err)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Document extraction failed: {str(extract_err)}"
        )

    # 3b. Verify Document is a Valid Financial Statement
    classifier = FinancialStatementClassifier()
    is_valid, reject_reason, detected_metrics = classifier.classify(raw_data)
    if not is_valid:
        logger.warning("Document %s rejected: %s", document_id, reject_reason)
        doc.status = DocumentStatus.REJECTED.value
        doc.error_message = reject_reason
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=reject_reason
        )

    # 4. Status: EXTRACTED -> NORMALIZING
    doc.status = DocumentStatus.EXTRACTED.value
    db.commit()

    doc.status = DocumentStatus.NORMALIZING.value
    db.commit()

    # 5. Normalization
    try:
        normalizer = Normalizer()
        normalized_result: NormalizedFinancialData = normalizer.normalize(raw_data, document_id=doc.id)
        normalized_result.source.filename = doc.filename
    except Exception as norm_err:
        logger.exception("Normalization failed for document %s", document_id)
        doc.status = DocumentStatus.NORMALIZATION_FAILED.value
        doc.error_message = str(norm_err)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Data normalization failed: {str(norm_err)}"
        )

    # 6. Persist Normalized Data in DB
    # Remove any existing financial records for this document to avoid duplicates
    db.query(FinancialData).filter(FinancialData.document_id == doc.id).delete()

    fin_record = FinancialData(
        document_id=doc.id,
        company_name=normalized_result.company.name,
        currency=normalized_result.currency,
        period_start=normalized_result.period.start,
        period_end=normalized_result.period.end,
        fiscal_year=normalized_result.period.fiscal_year,
        revenue=normalized_result.financial_data.revenue,
        assets=normalized_result.financial_data.assets,
        liabilities=normalized_result.financial_data.liabilities,
        equity=normalized_result.financial_data.equity,
        normalized_data=normalized_result.model_dump(),
    )
    db.add(fin_record)

    # 7. Update Document Status to NORMALIZED
    doc.status = DocumentStatus.NORMALIZED.value
    doc.processed_at = datetime.now(timezone.utc)
    doc.error_message = None
    db.commit()

    return NormalizedDocumentResponse(
        document_id=doc.id,
        status=doc.status,
        company=normalized_result.company,
        currency=normalized_result.currency,
        period=normalized_result.period,
        financial_data=normalized_result.financial_data,
        source=normalized_result.source,
        normalization_warnings=normalized_result.normalization_warnings
    )


@router.get(
    "/history",
    response_model=DocumentListResponse,
    summary="User document upload history",
    description="Returns only the authenticated user's own uploaded documents in reverse chronological order. Does not include shared or anonymous documents."
)
def get_document_history(db: Session = Depends(get_db), user: Optional[User] = Depends(get_optional_user)):
    """Return strictly user-owned documents for the audit history view."""
    if user is None:
        docs = (
            db.query(Document)
            .filter(Document.user_id.is_(None))
            .order_by(Document.uploaded_at.desc())
            .all()
        )
    elif user.id == "00000000-0000-0000-0000-000000000000":
        docs = (
            db.query(Document)
            .filter((Document.user_id == user.id) | (Document.user_id.is_(None)))
            .order_by(Document.uploaded_at.desc())
            .all()
        )
    else:
        docs = (
            db.query(Document)
            .filter(Document.user_id == user.id)
            .order_by(Document.uploaded_at.desc())
            .all()
        )
    items = []
    for d in docs:
        fin = db.query(FinancialData).filter(FinancialData.document_id == d.id).first()
        company = fin.company_name if fin else None
        fy = fin.fiscal_year if fin else None
        nd = (fin.normalized_data or {}) if fin else {}
        has_an = bool(nd.get("analysis") or nd.get("validation") or nd.get("ml_anomaly") or nd.get("review_observations"))
        items.append(
            DocumentListItem(
                document_id=d.id,
                filename=d.filename,
                file_type=d.file_type,
                status=d.status,
                uploaded_at=d.uploaded_at,
                processed_at=d.processed_at,
                company_name=company,
                fiscal_year=fy,
                has_analysis=has_an,
            )
        )
    return DocumentListResponse(total=len(items), documents=items)


@router.get(
    "/{document_id}",
    response_model=DocumentStatusResponse,
    summary="Get document status",
    description="Retrieve processing status and file metadata for an uploaded document."
)
def get_document_status(document_id: str, db: Session = Depends(get_db), user: Optional[User] = Depends(get_optional_user)):
    doc = get_authorized_document(document_id, db, user)

    return DocumentStatusResponse(
        document_id=doc.id,
        filename=doc.filename,
        file_type=doc.file_type,
        status=doc.status,
        uploaded_at=doc.uploaded_at,
        processed_at=doc.processed_at,
        error_message=doc.error_message
    )


@router.get(
    "/{document_id}/normalized",
    response_model=NormalizedDocumentResponse,
    summary="Get normalized financial data",
    description="Retrieve canonical normalized financial metrics and metadata for a processed document."
)
def get_normalized_data(document_id: str, db: Session = Depends(get_db), user: Optional[User] = Depends(get_optional_user)):
    doc = get_authorized_document(document_id, db, user)

    if doc.status != DocumentStatus.NORMALIZED.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Document '{document_id}' is in '{doc.status}' state and has not been normalized yet."
        )

    fin_record = db.query(FinancialData).filter(FinancialData.document_id == doc.id).first()
    if not fin_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Normalized financial record for document '{document_id}' was not found."
        )

    norm_data = fin_record.normalized_data or {}
    company_dict = norm_data.get("company", {})
    period_dict = norm_data.get("period", {})
    fin_dict = norm_data.get("financial_data", {})
    source_dict = norm_data.get("source")
    warnings = norm_data.get("normalization_warnings", [])

    return NormalizedDocumentResponse(
        document_id=doc.id,
        status=doc.status,
        company=CompanyInfo(**company_dict),
        currency=fin_record.currency,
        period=PeriodInfo(**period_dict),
        financial_data=FinancialMetrics(**fin_dict),
        source=DocumentSource(**source_dict) if source_dict else None,
        normalization_warnings=warnings
    )


@router.get(
    "",
    response_model=DocumentListResponse,
    summary="List all uploaded documents",
    description="Retrieve list of documents with metadata, status, and company information for dashboard selection."
)
def list_documents(db: Session = Depends(get_db), user: Optional[User] = Depends(get_optional_user)):
    query = db.query(Document)
    if user is not None:
        query = query.filter((Document.user_id == user.id) | (Document.user_id.is_(None)))
    docs = query.order_by(Document.uploaded_at.desc()).all()
    items = []
    for d in docs:
        fin = db.query(FinancialData).filter(FinancialData.document_id == d.id).first()
        company = fin.company_name if fin else None
        fy = fin.fiscal_year if fin else None
        nd = (fin.normalized_data or {}) if fin else {}
        has_an = bool(nd.get("analysis") or nd.get("validation") or nd.get("ml_anomaly") or nd.get("review_observations"))
        items.append(
            DocumentListItem(
                document_id=d.id,
                filename=d.filename,
                file_type=d.file_type,
                status=d.status,
                uploaded_at=d.uploaded_at,
                processed_at=d.processed_at,
                company_name=company,
                fiscal_year=fy,
                has_analysis=has_an,
            )
        )
    return DocumentListResponse(total=len(items), documents=items)


@router.get(
    "/{document_id}/dashboard",
    response_model=DashboardSummaryResponse,
    summary="Get consolidated dashboard data for document",
    description="Returns all verified analytical layers (financials, math validation, YoY, ratios, ML, findings, AI review, observations) in a single fast, read-only payload."
)
def get_dashboard_summary(document_id: str, db: Session = Depends(get_db), user: Optional[User] = Depends(get_optional_user)):
    doc = get_authorized_document(document_id, db, user)

    fin_record = db.query(FinancialData).filter(FinancialData.document_id == doc.id).first()
    norm_data = (fin_record.normalized_data or {}) if fin_record else {}
    analysis = norm_data.get("analysis", {}) if isinstance(norm_data.get("analysis"), dict) else {}

    # 1. Pipeline progression
    pipeline = PipelineStages(
        uploaded=True,
        extracted=(doc.status in (DocumentStatus.EXTRACTED.value, DocumentStatus.NORMALIZING.value, DocumentStatus.NORMALIZED.value)),
        normalized=(doc.status == DocumentStatus.NORMALIZED.value),
        validated=bool(norm_data.get("validation")),
        yoy_analyzed=bool(analysis.get("yoy")),
        ratios_computed=bool(analysis.get("ratios")),
        agent1_completed=bool(analysis.get("agent1")),
        ml_evaluated=bool(norm_data.get("ml_anomaly")),
        agent1_findings_ready=bool(analysis.get("agent1_findings")),
        agent2_reviewed=bool(analysis.get("agent2")),
        observations_ready=bool(norm_data.get("review_observations")),
    )

    # 2. Extract sections
    validation = norm_data.get("validation")
    yoy_analysis = analysis.get("yoy")
    ratio_analysis = analysis.get("ratios")
    ml_anomaly = norm_data.get("ml_anomaly")
    agent1_findings = analysis.get("agent1_findings")
    agent2_review = analysis.get("agent2")
    review_observations = norm_data.get("review_observations")

    # 3. Transparent, documented risk score derivation
    # ML Component:
    iso_score = None
    iso_classification = "NORMAL"
    if ml_anomaly and isinstance(ml_anomaly, dict):
        iso_score = ml_anomaly.get("anomaly_score")
        if iso_score is None and "anomaly_detection" in ml_anomaly:
            iso_score = ml_anomaly["anomaly_detection"].get("score")
        iso_classification = ml_anomaly.get("classification") or ("ANOMALY" if ml_anomaly.get("is_anomaly") else "NORMAL")

    # Validation Component:
    bs_status = "UNKNOWN"
    if validation and isinstance(validation, dict):
        bs_check = validation.get("balance_sheet_check", {})
        bs_status = bs_check.get("status", "UNKNOWN")

    # Observation Severity Counts:
    crit_count = 0
    high_count = 0
    med_count = 0
    low_count = 0
    if review_observations and isinstance(review_observations, dict):
        for obs in review_observations.get("observations", []):
            sev = str(obs.get("severity", "")).upper()
            if sev == "CRITICAL":
                crit_count += 1
            elif sev == "HIGH":
                high_count += 1
            elif sev == "MEDIUM":
                med_count += 1
            elif sev == "LOW":
                low_count += 1

    # Derivation rules:
    derivation_notes = []
    if bs_status == "INVALID":
        tier = "HIGH"
        derivation_notes.append("High Risk: Fundamental balance sheet accounting equation does not balance.")
    elif iso_classification == "ANOMALY" or (iso_score is not None and iso_score < 0):
        tier = "HIGH"
        derivation_notes.append(f"Elevated Risk: Isolation Forest model flagged statistical anomaly with score {iso_score:.4f}.")
    elif crit_count > 0:
        tier = "HIGH"
        derivation_notes.append(f"High Risk: Document contains {crit_count} CRITICAL review observation(s).")
    elif high_count > 0:
        tier = "HIGH"
        derivation_notes.append(f"Elevated Risk: Document contains {high_count} HIGH severity observation(s).")
    elif med_count > 0 or bs_status == "INCOMPLETE":
        tier = "MEDIUM"
        derivation_notes.append(f"Moderate Risk: Contains {med_count} MEDIUM observation(s) (e.g. YoY contraction or undefined ratios).")
    else:
        tier = "LOW"
        derivation_notes.append("Low Risk: Balance sheet verified, statistical normality confirmed, and zero critical issues flagged.")

    risk = RiskAssessment(
        tier=tier,
        score=iso_score,
        classification=iso_classification,
        balance_sheet_status=bs_status,
        critical_count=crit_count,
        high_count=high_count,
        medium_count=med_count,
        low_count=low_count,
        derivation_notes=derivation_notes,
    )

    company_name = fin_record.company_name if fin_record else None
    currency = fin_record.currency if fin_record else None
    period = fin_record.fiscal_year or fin_record.period_end if fin_record else None
    fin_dict = norm_data.get("financial_data", {}) if isinstance(norm_data.get("financial_data"), dict) else {}
    prev_dict = norm_data.get("previous_period_data")
    warnings = norm_data.get("normalization_warnings", [])

    return DashboardSummaryResponse(
        document_id=doc.id,
        status=doc.status,
        filename=doc.filename,
        file_type=doc.file_type,
        uploaded_at=doc.uploaded_at,
        processed_at=doc.processed_at,
        pipeline=pipeline,
        company_name=company_name,
        currency=currency,
        period=period,
        financial_data=fin_dict,
        previous_period_data=prev_dict,
        normalization_warnings=warnings,
        risk=risk,
        validation=validation,
        yoy_analysis=yoy_analysis,
        ratio_analysis=ratio_analysis,
        ml_anomaly=ml_anomaly,
        agent1_findings=agent1_findings,
        agent2_review=agent2_review,
        review_observations=review_observations,
    )


@router.delete(
    "/{document_id}",
    summary="Delete a document",
    description="Permanently delete an uploaded document, its associated financial data, chat messages, and stored file."
)
def delete_document(
    document_id: str,
    db: Session = Depends(get_db),
    user: Optional[User] = Depends(get_optional_user)
):
    """Delete document and all cascaded artifacts."""
    if str(document_id).startswith("doc-demo-"):
        return {
            "status": "deleted",
            "document_id": document_id,
            "message": f"Demo document '{document_id}' cleared successfully."
        }
    doc = get_authorized_document(document_id, db, user)

    # 1. Delete associated chat messages
    db.query(ChatMessage).filter(ChatMessage.document_id == doc.id).delete()

    # 2. Delete associated financial data records
    db.query(FinancialData).filter(FinancialData.document_id == doc.id).delete()

    # 3. Clean up physical file on disk if present
    if doc.file_path:
        try:
            file_p = Path(doc.file_path)
            if file_p.exists():
                file_p.unlink(missing_ok=True)
        except Exception as f_err:
            logger.warning("Could not unlink physical file for doc %s: %s", doc.id, f_err)

    # 4. Delete document record
    db.delete(doc)
    db.commit()

    logger.info("Document %s deleted successfully.", document_id)
    return {
        "status": "deleted",
        "document_id": document_id,
        "message": f"Document '{doc.filename}' deleted successfully."
    }


