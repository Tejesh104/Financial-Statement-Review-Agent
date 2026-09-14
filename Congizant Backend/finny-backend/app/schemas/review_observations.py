"""Pydantic schemas for the Review Observations layer (Step 4.2).

Represents structured, final review observations:
- finding
- explanation
- severity (LOW, MEDIUM, HIGH, CRITICAL)
- evidence (traceable data pointers)
- recommendation (factual, review-oriented)
"""

from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field


class ObservationEvidenceItem(BaseModel):
    """Structured evidence item referencing verified financial data."""
    field: str = Field(..., description="Canonical financial metric or validation check name")
    source: str = Field(..., description="Traceable path within normalized_data (e.g. analysis.yoy, validation)")
    value: Optional[float] = Field(None, description="Current or single reported numerical value")
    current_value: Optional[float] = Field(None, description="Current period value if comparative")
    previous_value: Optional[float] = Field(None, description="Previous period value if comparative")
    notes: Optional[str] = Field(None, description="Contextual note or status")


class ReviewObservation(BaseModel):
    """Single review observation contract."""
    finding: str = Field(..., description="Verified finding statement")
    explanation: str = Field(..., description="Factual explanation based on verified evidence")
    severity: str = Field(..., description="Deterministic classification: LOW, MEDIUM, HIGH, or CRITICAL")
    evidence: List[ObservationEvidenceItem] = Field(default_factory=list, description="Traceable evidence items")
    recommendation: str = Field(..., description="Review-oriented, non-prescriptive recommendation")


class ReviewObservationsResponse(BaseModel):
    """Canonical API response contract for Review Observations."""
    document_id: str = Field(..., description="Document UUID")
    status: str = Field(..., description="COMPLETED, PARTIAL, or FAILED")
    observations: List[ReviewObservation] = Field(default_factory=list, description="List of final review observations")
    summary: str = Field(default="Review observations compiled.", description="Narrative review summary")
    warnings: List[str] = Field(default_factory=list, description="Aggregated diagnostic warnings")
    reason: Optional[str] = Field(None, description="Explanation if status is PARTIAL or FAILED")
    model: str = Field(..., description="Ollama model identifier used for explanations")
