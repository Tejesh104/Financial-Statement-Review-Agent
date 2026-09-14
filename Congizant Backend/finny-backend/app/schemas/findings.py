"""Pydantic schemas for Agent 1 Findings layer.

Consolidates validations, variances (YoY), anomalies (ML), ratios, and evidence
into a unified, deterministic findings contract.
"""

from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field


class ValidationFinding(BaseModel):
    """Mathematical validation finding."""
    type: str = Field(default="BALANCE_SHEET_VALIDATION", description="Validation category")
    status: str = Field(..., description="VALID, INVALID, or INCOMPLETE")
    is_valid: Optional[bool] = Field(None, description="True if equation holds, False if imbalanced, None if incomplete")
    difference: Optional[float] = Field(None, description="Assets - (Liabilities + Equity)")
    tolerance: Optional[float] = Field(None, description="Numerical comparison tolerance")
    reason: Optional[str] = Field(None, description="Explanatory notice if imbalanced or incomplete")


class VarianceFinding(BaseModel):
    """Year-over-Year financial change finding."""
    field: str = Field(..., description="Financial metric name (e.g., revenue, assets)")
    current_period: Optional[str] = Field(None, description="Current reporting period")
    previous_period: Optional[str] = Field(None, description="Previous reporting period")
    current_value: Optional[float] = Field(None, description="Metric value in current period")
    previous_value: Optional[float] = Field(None, description="Metric value in previous period")
    absolute_change: Optional[float] = Field(None, description="Current - Previous")
    percentage_change: Optional[float] = Field(None, description="Percentage delta")
    direction: Optional[str] = Field(None, description="positive, negative, or unchanged")
    status: str = Field(..., description="COMPLETED, INCOMPLETE, or INSUFFICIENT_DATA")
    reason: Optional[str] = Field(None, description="Notice for zero denominator or missing periods")


class AnomalyFinding(BaseModel):
    """ML anomaly detection finding."""
    type: str = Field(default="ML_ANOMALY", description="Anomaly category")
    classification: str = Field(..., description="NORMAL or ANOMALY")
    is_anomaly: bool = Field(..., description="True if statistical anomaly, False otherwise")
    anomaly_score: float = Field(..., description="Isolation Forest decision score (<0 indicates anomaly)")
    prediction: int = Field(..., description="Raw model prediction: 1 = normal, -1 = anomaly")
    status: str = Field(default="COMPLETED", description="COMPLETED or INCOMPLETE")
    model_type: Optional[str] = Field("IsolationForest", description="Model algorithm")
    warnings: List[str] = Field(default_factory=list, description="Model or feature warnings")
    reason: Optional[str] = Field(None, description="Notice if features were imputed")


class RatioItemFinding(BaseModel):
    """Single financial ratio finding."""
    name: str = Field(..., description="Canonical ratio key")
    category: str = Field(..., description="liquidity, profitability, or leverage")
    value: Optional[float] = Field(None, description="Computed numerical ratio or percentage")
    status: str = Field(..., description="COMPLETED, INCOMPLETE, or UNDEFINED")
    reason: Optional[str] = Field(None, description="Reason if undefined or incomplete")


class EvidenceFinding(BaseModel):
    """Deterministic, traceable data evidence."""
    field: str = Field(..., description="Canonical field name")
    value: Optional[float] = Field(None, description="Extracted numerical value")
    source: str = Field(..., description="JSON path within normalized_data")
    is_available: bool = Field(..., description="True if present, False if missing in statement")


class FindingsContainer(BaseModel):
    """Container holding all structured finding collections."""
    validations: List[ValidationFinding] = Field(default_factory=list, description="Mathematical validation checks")
    variances: List[VarianceFinding] = Field(default_factory=list, description="YoY financial variances")
    anomalies: List[AnomalyFinding] = Field(default_factory=list, description="Statistical ML anomaly findings")
    ratios: List[RatioItemFinding] = Field(default_factory=list, description="Core financial ratios")
    evidence: List[EvidenceFinding] = Field(default_factory=list, description="Traceable normalized evidence")


class Agent1FindingsResponse(BaseModel):
    """Canonical Agent 1 Findings response contract."""
    document_id: str = Field(..., description="Document UUID")
    status: str = Field(..., description="Overall findings status: COMPLETED, PARTIAL, or FAILED")
    findings: FindingsContainer = Field(..., description="Consolidated findings sections")
    warnings: List[str] = Field(default_factory=list, description="Aggregated deduplicated diagnostic warnings")
    reason: Optional[str] = Field(None, description="Explanatory summary when status is PARTIAL or FAILED")
