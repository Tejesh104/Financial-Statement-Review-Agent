from typing import Optional, Dict, List, Any
from pydantic import BaseModel, Field, ConfigDict


class FieldYoYResult(BaseModel):
    """Year-Over-Year comparative result for a single financial line item."""
    previous: Optional[float] = Field(None, description="Financial metric value in the previous period")
    current: Optional[float] = Field(None, description="Financial metric value in the current period")
    absolute_change: Optional[float] = Field(None, description="Current period minus previous period")
    percentage_change: Optional[float] = Field(None, description="Percentage change ((Current - Previous) / |Previous|) * 100")
    direction: Optional[str] = Field(None, description="'positive', 'negative', or 'unchanged'")
    status: str = Field(..., description="'COMPLETED' or 'INCOMPLETE'")
    reason: Optional[str] = Field(None, description="Explanatory warning or reason if incomplete or zero-previous")

    model_config = ConfigDict(extra="allow")


class PeriodsInfo(BaseModel):
    """Identifies the compared financial periods."""
    previous: Optional[str] = Field(None, description="Earlier fiscal period / date")
    current: Optional[str] = Field(None, description="Later fiscal period / date")

    model_config = ConfigDict(extra="allow")


class YoYAnalysisData(BaseModel):
    """Detailed YoY analysis payload."""
    status: str = Field(..., description="'COMPLETED', 'INCOMPLETE', or 'INSUFFICIENT_DATA'")
    periods: Optional[PeriodsInfo] = Field(None, description="Compared reporting periods")
    financial_data: Dict[str, FieldYoYResult] = Field(default_factory=dict, description="YoY results per financial field")
    warnings: List[str] = Field(default_factory=list, description="Non-fatal notices or missing indicators")
    reason: Optional[str] = Field(None, description="Reason if status is not COMPLETED")

    model_config = ConfigDict(extra="allow")


class YoYAnalysisResponse(BaseModel):
    """API response schema for POST /api/v1/analysis/{document_id}/yoy."""
    document_id: str = Field(..., description="Unique ID of the evaluated document")
    yoy_analysis: YoYAnalysisData

    model_config = ConfigDict(extra="allow")


# Financial Ratio Schemas
class RatioResult(BaseModel):
    """Outcome of a single financial ratio calculation."""
    value: Optional[float] = Field(None, description="Calculated ratio value, null if undefined or incomplete")
    status: str = Field(..., description="'COMPLETED', 'INCOMPLETE', or 'UNDEFINED'")
    reason: Optional[str] = Field(None, description="Explanatory message if incomplete or undefined")

    model_config = ConfigDict(extra="allow")


class LiquidityRatios(BaseModel):
    """Liquidity ratio group."""
    current_ratio: RatioResult
    quick_ratio: RatioResult

    model_config = ConfigDict(extra="allow")


class ProfitabilityRatios(BaseModel):
    """Profitability ratio group."""
    gross_profit_margin: RatioResult
    net_profit_margin: RatioResult
    return_on_assets: RatioResult
    return_on_equity: RatioResult

    model_config = ConfigDict(extra="allow")


class LeverageRatios(BaseModel):
    """Leverage ratio group."""
    debt_to_equity: RatioResult
    debt_ratio: RatioResult

    model_config = ConfigDict(extra="allow")


class RatiosData(BaseModel):
    """Container for all ratio categories."""
    liquidity: LiquidityRatios
    profitability: ProfitabilityRatios
    leverage: LeverageRatios

    model_config = ConfigDict(extra="allow")


class RatioAnalysisData(BaseModel):
    """Structured ratio analysis payload."""
    status: str = Field(..., description="'COMPLETED', 'INCOMPLETE', or 'UNDEFINED'")
    ratios: RatiosData
    warnings: List[str] = Field(default_factory=list, description="Non-fatal warnings or undefined ratio notices")
    reason: Optional[str] = Field(None, description="Explanatory summary reason")

    model_config = ConfigDict(extra="allow")


class RatioAnalysisResponse(BaseModel):
    """API response schema for POST /api/v1/analysis/{document_id}/ratios."""
    document_id: str = Field(..., description="Unique ID of the evaluated document")
    ratio_analysis: RatioAnalysisData

    model_config = ConfigDict(extra="allow")
