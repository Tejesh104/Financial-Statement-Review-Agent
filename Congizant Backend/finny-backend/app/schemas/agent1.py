from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict
from app.schemas.validation import BalanceSheetCheckResult
from app.schemas.analysis import YoYAnalysisData, RatioAnalysisData


class Agent1Results(BaseModel):
    """Consolidated results of all Agent 1 analytical components."""
    math_validation: BalanceSheetCheckResult = Field(..., description="Balance sheet accounting equation validation result")
    yoy_analysis: YoYAnalysisData = Field(..., description="Year-Over-Year growth and comparison analysis")
    financial_ratios: RatioAnalysisData = Field(..., description="Liquidity, profitability, and leverage financial ratios")

    model_config = ConfigDict(extra="allow")


class Agent1Response(BaseModel):
    """API response schema for Agent 1 Result Builder."""
    document_id: str = Field(..., description="Unique ID of the evaluated document")
    agent: str = Field("Agent 1", description="Identifier of the executing orchestrator")
    status: str = Field(..., description="Overall Agent 1 status: 'COMPLETED', 'PARTIAL', or 'FAILED'")
    results: Agent1Results = Field(..., description="Consolidated analytical components")
    warnings: List[str] = Field(default_factory=list, description="Deduplicated non-fatal notices and missing indicators")
    reason: Optional[str] = Field(None, description="Summary reason when status is PARTIAL or FAILED")

    model_config = ConfigDict(extra="allow")
