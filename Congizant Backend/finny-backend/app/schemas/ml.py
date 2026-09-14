"""Pydantic response and data schemas for ML anomaly detection."""

from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field


class ModelInfo(BaseModel):
    """Metadata regarding the ML model used for inference."""
    type: str = Field(..., description="Type of model (e.g., IsolationForest)")
    version: str = Field(..., description="Scikit-Learn library version")
    training_dataset: str = Field(..., description="Dataset name used during training")
    feature_count: int = Field(..., description="Number of canonical features used")


class AnomalyDetectionResult(BaseModel):
    """Core anomaly classification and score."""
    prediction: int = Field(..., description="Raw model prediction: 1 = normal, -1 = anomaly")
    label: str = Field(..., description="Normalized label: 'normal' or 'anomaly'")
    classification: Optional[str] = Field(None, description="Standardized classification: 'NORMAL' or 'ANOMALY'")
    is_anomaly: bool = Field(..., description="True if statistically unusual / anomaly, False otherwise")
    score: float = Field(..., description="Anomaly decision function score (higher is more normal, <0 is unusual)")
    anomaly_score: Optional[float] = Field(None, description="Alias for decision function anomaly score")


class MLAnomalyResponse(BaseModel):
    """Top-level response schema for POST /api/v1/ml/{document_id}/anomaly."""
    document_id: str = Field(..., description="UUID of the analyzed document")
    status: str = Field(..., description="Execution status: COMPLETED, INCOMPLETE, or ERROR")
    classification: Optional[str] = Field(None, description="Standardized classification: 'NORMAL' or 'ANOMALY'")
    anomaly_score: Optional[float] = Field(None, description="Direct anomaly decision function score")
    prediction: Optional[int] = Field(None, description="Raw model prediction: 1 or -1")
    is_anomaly: Optional[bool] = Field(None, description="True if anomaly, False if normal")
    model: ModelInfo = Field(..., description="Model metadata")
    features: Dict[str, Optional[float]] = Field(..., description="Canonical 6-feature values extracted from Agent 1")
    anomaly_detection: AnomalyDetectionResult = Field(..., description="Anomaly classification outcome")
    warnings: List[str] = Field(default_factory=list, description="Diagnostic notices or warnings")
    reason: Optional[str] = Field(None, description="Explanation if status is INCOMPLETE or warnings exist")
