from typing import Optional
from pydantic import BaseModel, Field, ConfigDict
from app.services.validation.math_validator import DEFAULT_TOLERANCE


class BalanceSheetCheckResult(BaseModel):
    """Details of the Assets = Liabilities + Equity balance sheet check."""
    assets: Optional[float] = Field(None, description="Normalized total assets")
    liabilities: Optional[float] = Field(None, description="Normalized total liabilities")
    equity: Optional[float] = Field(None, description="Normalized shareholders'/owners' equity")
    liabilities_plus_equity: Optional[float] = Field(None, description="Sum of liabilities and equity")
    difference: Optional[float] = Field(None, description="Assets minus (Liabilities + Equity)")
    tolerance: float = Field(DEFAULT_TOLERANCE, description="Configured comparison tolerance")
    is_valid: Optional[bool] = Field(None, description="True if equation holds within tolerance, False otherwise, None if incomplete")
    status: str = Field(..., description="VALID, INVALID, or INCOMPLETE")
    reason: Optional[str] = Field(None, description="Explanatory message if invalid or incomplete")

    model_config = ConfigDict(extra="allow")


class MathValidationResponse(BaseModel):
    """API response schema for POST /api/v1/validation/{document_id}/math."""
    document_id: str = Field(..., description="Unique ID of the evaluated document")
    balance_sheet_check: BalanceSheetCheckResult

    model_config = ConfigDict(extra="allow")
