from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict


class DocumentSource(BaseModel):
    """Metadata describing the origin file."""
    filename: str
    file_type: str


class RawTable(BaseModel):
    """Raw table extracted from document."""
    headers: List[str] = Field(default_factory=list)
    rows: List[List[Any]] = Field(default_factory=list)
    sheet_name: Optional[str] = None
    page_number: Optional[int] = None


class RawExtractionData(BaseModel):
    """Unified raw extraction format across PDF, Excel, and CSV."""
    source: DocumentSource
    tables: List[RawTable] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class CompanyInfo(BaseModel):
    """Company information."""
    name: Optional[str] = None


class PeriodInfo(BaseModel):
    """Financial reporting period."""
    start: Optional[str] = None
    end: Optional[str] = None
    fiscal_year: Optional[str] = None


class FinancialMetrics(BaseModel):
    """Extensible financial metrics schema."""
    revenue: Optional[float] = None
    assets: Optional[float] = None
    liabilities: Optional[float] = None
    equity: Optional[float] = None
    
    # Potential future financial line items
    operating_income: Optional[float] = None
    net_income: Optional[float] = None
    cash: Optional[float] = None
    inventory: Optional[float] = None
    accounts_receivable: Optional[float] = None
    accounts_payable: Optional[float] = None
    expenses: Optional[float] = None
    gross_profit: Optional[float] = None
    current_assets: Optional[float] = None
    current_liabilities: Optional[float] = None

    model_config = ConfigDict(extra="allow")


class NormalizedFinancialData(BaseModel):
    """Full normalized dataset representation."""
    document_id: str
    company: CompanyInfo = Field(default_factory=CompanyInfo)
    currency: Optional[str] = None
    period: PeriodInfo = Field(default_factory=PeriodInfo)
    financial_data: FinancialMetrics = Field(default_factory=FinancialMetrics)
    previous_period_data: Optional[Dict[str, Any]] = None
    source: DocumentSource
    normalization_warnings: List[str] = Field(default_factory=list)

    model_config = ConfigDict(extra="allow")


class NormalizedDocumentResponse(BaseModel):
    """API response model for GET /api/v1/documents/{document_id}/normalized."""
    document_id: str
    status: str
    company: CompanyInfo = Field(default_factory=CompanyInfo)
    currency: Optional[str] = None
    period: PeriodInfo = Field(default_factory=PeriodInfo)
    financial_data: FinancialMetrics = Field(default_factory=FinancialMetrics)
    previous_period_data: Optional[Dict[str, Any]] = None
    source: Optional[DocumentSource] = None
    normalization_warnings: List[str] = Field(default_factory=list)

    model_config = ConfigDict(extra="allow")
