from typing import Dict, Any, List, Optional
from datetime import datetime
from pydantic import BaseModel, Field


class DocumentListItem(BaseModel):
    """Document summary item in document list."""
    document_id: str = Field(..., description="Document UUID")
    filename: str = Field(..., description="Uploaded file name")
    file_type: str = Field(..., description="Detected file type")
    status: str = Field(..., description="Document processing status")
    uploaded_at: datetime = Field(..., description="Upload timestamp")
    processed_at: Optional[datetime] = Field(None, description="Processing completion timestamp")
    company_name: Optional[str] = Field(None, description="Company name")
    fiscal_year: Optional[str] = Field(None, description="Fiscal year")
    has_analysis: bool = Field(default=False, description="True if analytics exist")


class DocumentListResponse(BaseModel):
    """Response containing list of available documents."""
    total: int = Field(..., description="Total count")
    documents: List[DocumentListItem] = Field(default_factory=list, description="Documents list")


class RiskAssessment(BaseModel):
    """Documented composite risk assessment derived deterministically from verified outputs."""
    tier: str = Field(..., description="LOW, MEDIUM, or HIGH")
    score: Optional[float] = Field(None, description="ISO Forest score")
    classification: str = Field(default="NORMAL", description="NORMAL or ANOMALY")
    balance_sheet_status: str = Field(default="UNKNOWN", description="VALID, INVALID, or INCOMPLETE")
    critical_count: int = Field(default=0)
    high_count: int = Field(default=0)
    medium_count: int = Field(default=0)
    low_count: int = Field(default=0)
    derivation_notes: List[str] = Field(default_factory=list)


class PipelineStages(BaseModel):
    """Pipeline completion flags."""
    uploaded: bool = Field(default=False)
    extracted: bool = Field(default=False)
    normalized: bool = Field(default=False)
    validated: bool = Field(default=False)
    yoy_analyzed: bool = Field(default=False)
    ratios_computed: bool = Field(default=False)
    agent1_completed: bool = Field(default=False)
    ml_evaluated: bool = Field(default=False)
    agent1_findings_ready: bool = Field(default=False)
    agent2_reviewed: bool = Field(default=False)
    observations_ready: bool = Field(default=False)


class DashboardSummaryResponse(BaseModel):
    """Consolidated read-only dashboard response for a document."""
    document_id: str = Field(...)
    status: str = Field(...)
    filename: str = Field(...)
    file_type: str = Field(...)
    uploaded_at: datetime = Field(...)
    processed_at: Optional[datetime] = Field(None)
    pipeline: PipelineStages = Field(default_factory=PipelineStages)
    company_name: Optional[str] = Field(None)
    currency: Optional[str] = Field(None)
    period: Optional[str] = Field(None)
    financial_data: Dict[str, Optional[float]] = Field(default_factory=dict)
    previous_period_data: Optional[Dict[str, Any]] = Field(None)
    normalization_warnings: List[str] = Field(default_factory=list)
    risk: RiskAssessment = Field(...)
    validation: Optional[Dict[str, Any]] = Field(None)
    yoy_analysis: Optional[Dict[str, Any]] = Field(None)
    ratio_analysis: Optional[Dict[str, Any]] = Field(None)
    ml_anomaly: Optional[Dict[str, Any]] = Field(None)
    agent1_findings: Optional[Dict[str, Any]] = Field(None)
    agent2_review: Optional[Dict[str, Any]] = Field(None)
    review_observations: Optional[Dict[str, Any]] = Field(None)

