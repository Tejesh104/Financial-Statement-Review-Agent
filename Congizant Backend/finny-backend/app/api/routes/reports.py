"""Reports API routes exposing formal financial reviews and historical analysis."""

import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import get_optional_user
from app.database.database import get_db
from app.models.document import Document
from app.models.financial_data import FinancialData
from app.models.user import User
from app.api.dependencies import get_authorized_document
from app.api.routes.documents import get_dashboard_summary
from app.schemas.dashboard import DashboardSummaryResponse, DocumentListItem, DocumentListResponse

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get(
    "",
    response_model=DocumentListResponse,
    summary="List available reports for authenticated user",
    description="Retrieve listing of all financial reports available to the user."
)
def list_reports(db: Session = Depends(get_db), user: Optional[User] = Depends(get_optional_user)):
    """List financial statement reports, isolated to authenticated user."""
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
    "/{document_id}",
    response_model=DashboardSummaryResponse,
    summary="Get complete financial analysis report",
    description="Retrieve comprehensive report containing all verified math, YoY, ratio, ML, and AI findings."
)
def get_report_details(document_id: str, db: Session = Depends(get_db), user: Optional[User] = Depends(get_optional_user)):
    """Fetch complete report details with strict ownership verification."""
    return get_dashboard_summary(document_id=document_id, db=db, user=user)


@router.get(
    "/{document_id}/export",
    summary="Export financial report in PDF or CSV format",
    description="Generates and streams a formal executive PDF or tabular CSV report."
)
def export_report(
    document_id: str,
    format: str = "pdf",
    db: Session = Depends(get_db),
    user: Optional[User] = Depends(get_optional_user)
):
    """Generate and return downloadable financial review report."""
    from fastapi.responses import StreamingResponse
    import csv
    import io
    from app.services.reporting.pdf_report_builder import PDFReportBuilder

    summary = get_dashboard_summary(document_id=document_id, db=db, user=user)

    # Pipeline Completion Check: PDF and CSV reports can be exported
    # once document data has been extracted and normalized.
    p = summary.pipeline
    if not (p.uploaded and p.extracted and p.normalized):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Report cannot be generated yet. Document normalization is still pending."
        )

    data = summary.model_dump()

    # Ensure validation section exists with balance sheet check for reporting
    if not data.get("validation") or not data["validation"].get("balance_sheet_check"):
        from app.services.validation.math_validator import MathValidator
        fin = data.get("financial_data") or {}
        bs_res = MathValidator.validate_balance_sheet(
            assets=fin.get("assets"),
            liabilities=fin.get("liabilities"),
            equity=fin.get("equity")
        )
        data["validation"] = {"balance_sheet_check": bs_res}

    base_name = summary.filename.rsplit(".", 1)[0] if "." in summary.filename else summary.filename
    clean_name = "".join(c for c in base_name if c.isalnum() or c in ("-", "_")).strip() or "financial_report"

    fmt = format.lower().strip()


    if fmt == "csv":
        # Build CSV of financial data, ratios, and observations
        output = io.StringIO()
        writer = csv.writer(output)

        writer.writerow(["FINNY FINANCIAL STATEMENT REPORT"])
        writer.writerow(["Entity", summary.company_name or "N/A"])
        writer.writerow(["Fiscal Period", summary.period or "N/A"])
        writer.writerow(["Currency", summary.currency or "USD"])
        writer.writerow(["Risk Tier", summary.risk.tier])
        writer.writerow(["Balance Sheet Status", summary.risk.balance_sheet_status])
        writer.writerow([])

        # Financial Data
        writer.writerow(["CORE FINANCIAL METRICS"])
        writer.writerow(["Metric", "Value"])
        for k, v in (summary.financial_data or {}).items():
            writer.writerow([k, v if v is not None else "N/A"])
        writer.writerow([])

        # Ratios
        writer.writerow(["FINANCIAL RATIOS"])
        writer.writerow(["Category", "Ratio", "Value", "Status"])
        ratios = (summary.ratio_analysis or {}).get("ratios", {})
        for cat, cat_dict in ratios.items():
            if isinstance(cat_dict, dict):
                for r_name, r_info in cat_dict.items():
                    val = r_info.get("value") if isinstance(r_info, dict) else r_info
                    stat = r_info.get("status") if isinstance(r_info, dict) else "COMPLETED"
                    writer.writerow([cat, r_name, val if val is not None else "N/A", stat])
        writer.writerow([])

        # Observations
        writer.writerow(["AGENT 2 REVIEW OBSERVATIONS"])
        writer.writerow(["Severity", "Finding", "Explanation", "Recommendation"])
        obs_list = (summary.review_observations or {}).get("observations", [])
        for obs in obs_list:
            writer.writerow([
                obs.get("severity", "LOW"),
                obs.get("finding", ""),
                obs.get("explanation", ""),
                obs.get("recommendation", "")
            ])

        output.seek(0)
        bytes_io = io.BytesIO(output.getvalue().encode("utf-8-sig"))
        filename = f"{clean_name}_report.csv"
        return StreamingResponse(
            bytes_io,
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'}
        )

    # Default to PDF
    pdf_buffer = PDFReportBuilder.build_pdf(data)
    filename = f"{clean_name}_review_report.pdf"
    return StreamingResponse(
        pdf_buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )

