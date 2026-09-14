import logging
from typing import Optional
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.security import get_optional_user
from app.database.database import get_db
from app.models.user import User
from app.schemas.validation import MathValidationResponse, BalanceSheetCheckResult
from app.services.validation.math_validator import MathValidator
from app.api.common import get_normalized_document_and_record, persist_validation_section

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post(
    "/{document_id}/math",
    response_model=MathValidationResponse,
    summary="Perform mathematical validation on normalized financial data",
    description=(
        "Evaluates the fundamental balance sheet accounting equation (Assets = Liabilities + Equity) "
        "on a previously normalized document."
    )
)
def validate_math(document_id: str, db: Session = Depends(get_db), user: Optional[User] = Depends(get_optional_user)):
    # 1. Validate UUID, document state, and retrieve records with authorization check
    doc, fin_record = get_normalized_document_and_record(document_id, db, user)

    # 2. Extract metrics (columns take precedence, fallback to normalized_data)
    norm_data = fin_record.normalized_data or {}
    fin_dict = norm_data.get("financial_data", {}) if isinstance(norm_data.get("financial_data"), dict) else {}
    assets = fin_record.assets if fin_record.assets is not None else fin_dict.get("assets")
    liabilities = fin_record.liabilities if fin_record.liabilities is not None else fin_dict.get("liabilities")
    equity = fin_record.equity if fin_record.equity is not None else fin_dict.get("equity")

    # 3. Perform balance sheet mathematical validation
    check_result = MathValidator.validate_balance_sheet(
        assets=assets,
        liabilities=liabilities,
        equity=equity
    )

    # 4. Safely and atomically persist validation outcome
    persist_validation_section(
        fin_record=fin_record,
        db=db,
        validation_data=check_result,
        document_id=doc.id
    )

    return MathValidationResponse(
        document_id=doc.id,
        balance_sheet_check=BalanceSheetCheckResult(**check_result)
    )
