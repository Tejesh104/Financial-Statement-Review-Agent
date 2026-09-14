import os
from pathlib import Path

# 1. Create app/services/analytics/ratio_analyzer.py
ratio_analyzer_code = '''from typing import Dict, Any, Optional, List


class RatioAnalyzer:
    """Service for computing Financial Ratios (Liquidity, Profitability, Leverage) from normalized financial data."""

    @staticmethod
    def _calc_ratio(
        numerator: Optional[float],
        denominator: Optional[float],
        as_percentage: bool = False,
        num_name: str = "Numerator",
        den_name: str = "Denominator",
    ) -> Dict[str, Any]:
        """Safely calculate a financial ratio with zero-denominator and missing-field protection.
        
        Args:
            numerator: The dividend (top)
            denominator: The divisor (bottom)
            as_percentage: If True, multiplies ratio by 100
            num_name: Field name of numerator for error messaging
            den_name: Field name of denominator for error messaging
            
        Returns:
            Dict[str, Any] with 'value', 'status', and 'reason'.
        """
        # 1. Missing field check
        if numerator is None and denominator is None:
            return {
                "value": None,
                "status": "INCOMPLETE",
                "reason": f"Both {num_name.lower()} and {den_name.lower()} are missing.",
            }
        if numerator is None:
            return {
                "value": None,
                "status": "INCOMPLETE",
                "reason": f"{num_name} is missing.",
            }
        if denominator is None:
            return {
                "value": None,
                "status": "INCOMPLETE",
                "reason": f"{den_name} is missing.",
            }

        # 2. Zero-denominator check
        if denominator == 0:
            return {
                "value": None,
                "status": "UNDEFINED",
                "reason": f"Ratio cannot be calculated because {den_name.lower()} is zero.",
            }

        # 3. Calculate ratio
        val = (numerator / denominator) * (100.0 if as_percentage else 1.0)
        # Consistent precision: percentage up to 2 decimal places, raw ratio up to 4 decimal places
        rounded_val = round(val, 2 if as_percentage else 4)

        return {
            "value": rounded_val,
            "status": "COMPLETED",
            "reason": None,
        }

    @classmethod
    def calculate_current_ratio(cls, current_assets: Optional[float], current_liabilities: Optional[float]) -> Dict[str, Any]:
        """Current Ratio = Current Assets / Current Liabilities"""
        return cls._calc_ratio(
            numerator=current_assets,
            denominator=current_liabilities,
            as_percentage=False,
            num_name="Current assets",
            den_name="Current liabilities",
        )

    @classmethod
    def calculate_quick_ratio(
        cls,
        current_assets: Optional[float],
        inventory: Optional[float],
        current_liabilities: Optional[float]
    ) -> Dict[str, Any]:
        """Quick Ratio = (Current Assets - Inventory) / Current Liabilities"""
        if current_assets is None or inventory is None or current_liabilities is None:
            missing = []
            if current_assets is None:
                missing.append("current assets")
            if inventory is None:
                missing.append("inventory")
            if current_liabilities is None:
                missing.append("current liabilities")
            return {
                "value": None,
                "status": "INCOMPLETE",
                "reason": f"{', '.join(missing).capitalize()} {'is' if len(missing) == 1 else 'are'} missing.",
            }

        quick_assets = current_assets - inventory
        return cls._calc_ratio(
            numerator=quick_assets,
            denominator=current_liabilities,
            as_percentage=False,
            num_name="Quick assets (Current assets - Inventory)",
            den_name="Current liabilities",
        )

    @classmethod
    def calculate_gross_profit_margin(cls, gross_profit: Optional[float], revenue: Optional[float]) -> Dict[str, Any]:
        """Gross Profit Margin = (Gross Profit / Revenue) * 100"""
        return cls._calc_ratio(
            numerator=gross_profit,
            denominator=revenue,
            as_percentage=True,
            num_name="Gross profit",
            den_name="Revenue",
        )

    @classmethod
    def calculate_net_profit_margin(cls, net_profit: Optional[float], revenue: Optional[float]) -> Dict[str, Any]:
        """Net Profit Margin = (Net Profit / Revenue) * 100"""
        return cls._calc_ratio(
            numerator=net_profit,
            denominator=revenue,
            as_percentage=True,
            num_name="Net profit",
            den_name="Revenue",
        )

    @classmethod
    def calculate_return_on_assets(cls, net_profit: Optional[float], assets: Optional[float]) -> Dict[str, Any]:
        """Return on Assets (ROA) = (Net Profit / Total Assets) * 100"""
        return cls._calc_ratio(
            numerator=net_profit,
            denominator=assets,
            as_percentage=True,
            num_name="Net profit",
            den_name="Total assets",
        )

    @classmethod
    def calculate_return_on_equity(cls, net_profit: Optional[float], equity: Optional[float]) -> Dict[str, Any]:
        """Return on Equity (ROE) = (Net Profit / Equity) * 100"""
        return cls._calc_ratio(
            numerator=net_profit,
            denominator=equity,
            as_percentage=True,
            num_name="Net profit",
            den_name="Equity",
        )

    @classmethod
    def calculate_debt_to_equity(cls, debt: Optional[float], equity: Optional[float]) -> Dict[str, Any]:
        """Debt-to-Equity = Total Debt / Equity"""
        return cls._calc_ratio(
            numerator=debt,
            denominator=equity,
            as_percentage=False,
            num_name="Total debt",
            den_name="Equity",
        )

    @classmethod
    def calculate_debt_ratio(cls, debt: Optional[float], assets: Optional[float]) -> Dict[str, Any]:
        """Debt Ratio = Total Debt / Total Assets"""
        return cls._calc_ratio(
            numerator=debt,
            denominator=assets,
            as_percentage=False,
            num_name="Total debt",
            den_name="Total assets",
        )

    @classmethod
    def analyze_ratios(cls, metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Compute all supported financial ratios across Liquidity, Profitability, and Leverage.
        
        Args:
            metrics: Dictionary containing available normalized financial fields.
            
        Returns:
            Structured dictionary matching the RatioAnalysisData schema.
        """
        # Resolve fields from metrics dictionary
        def get_num(key: str, alt_key: Optional[str] = None) -> Optional[float]:
            val = metrics.get(key)
            if (val is None or str(val).strip() == "") and alt_key:
                val = metrics.get(alt_key)
            if val is not None and str(val).strip() != "":
                try:
                    return float(val)
                except (ValueError, TypeError):
                    return None
            return None

        current_assets = get_num("current_assets")
        current_liabilities = get_num("current_liabilities")
        inventory = get_num("inventory")
        revenue = get_num("revenue")
        gross_profit = get_num("gross_profit")
        net_profit = get_num("net_profit", "net_income")
        assets = get_num("assets")
        equity = get_num("equity")
        # Debt: resolve explicit debt if present; else fall back to liabilities
        debt = get_num("debt", "liabilities")

        # 1. Liquidity
        current_ratio = cls.calculate_current_ratio(current_assets, current_liabilities)
        quick_ratio = cls.calculate_quick_ratio(current_assets, inventory, current_liabilities)
        liquidity = {
            "current_ratio": current_ratio,
            "quick_ratio": quick_ratio,
        }

        # 2. Profitability
        gpm = cls.calculate_gross_profit_margin(gross_profit, revenue)
        npm = cls.calculate_net_profit_margin(net_profit, revenue)
        roa = cls.calculate_return_on_assets(net_profit, assets)
        roe = cls.calculate_return_on_equity(net_profit, equity)
        profitability = {
            "gross_profit_margin": gpm,
            "net_profit_margin": npm,
            "return_on_assets": roa,
            "return_on_equity": roe,
        }

        # 3. Leverage
        dte = cls.calculate_debt_to_equity(debt, equity)
        dr = cls.calculate_debt_ratio(debt, assets)
        leverage = {
            "debt_to_equity": dte,
            "debt_ratio": dr,
        }

        all_ratios = [
            ("current_ratio", current_ratio),
            ("quick_ratio", quick_ratio),
            ("gross_profit_margin", gpm),
            ("net_profit_margin", npm),
            ("return_on_assets", roa),
            ("return_on_equity", roe),
            ("debt_to_equity", dte),
            ("debt_ratio", dr),
        ]

        warnings: List[str] = []
        has_completed = False
        has_incomplete = False
        has_undefined = False

        for name, r in all_ratios:
            if r["status"] == "COMPLETED":
                has_completed = True
            elif r["status"] == "UNDEFINED":
                has_undefined = True
                warnings.append(f"{name}: {r['reason']}")
            else:
                has_incomplete = True
                warnings.append(f"{name}: {r['reason']}")

        if has_completed and not has_incomplete and not has_undefined:
            overall_status = "COMPLETED"
            overall_reason = None
        elif has_completed or has_undefined:
            overall_status = "INCOMPLETE" if has_incomplete else ("UNDEFINED" if has_undefined else "COMPLETED")
            overall_reason = "One or more financial ratios could not be calculated."
        else:
            overall_status = "INCOMPLETE"
            overall_reason = "All required inputs for financial ratios are missing."

        return {
            "status": overall_status,
            "ratios": {
                "liquidity": liquidity,
                "profitability": profitability,
                "leverage": leverage,
            },
            "warnings": warnings,
            "reason": overall_reason,
        }
'''

Path("app/services/analytics/ratio_analyzer.py").write_text(ratio_analyzer_code, encoding="utf-8")
Path("app/services/analytics/__init__.py").write_text(
    'from app.services.analytics.yoy_analyzer import YoYAnalyzer\n'
    'from app.services.analytics.ratio_analyzer import RatioAnalyzer\n\n'
    '__all__ = ["YoYAnalyzer", "RatioAnalyzer"]\n',
    encoding="utf-8"
)
print("RatioAnalyzer service created successfully.")

yoy_analyzer_code = '''import re
from typing import Dict, Any, Optional, Tuple, List


class YoYAnalyzer:
    """Service for performing Year-Over-Year (YoY) financial analysis on normalized datasets."""

    CORE_FINANCIAL_FIELDS = [
        "revenue",
        "assets",
        "liabilities",
        "equity",
        "operating_income",
        "net_income",
        "cash",
        "inventory",
        "accounts_receivable",
        "accounts_payable",
        "expenses",
        "gross_profit",
        "current_assets",
        "current_liabilities",
    ]

    @staticmethod
    def parse_period_sort_key(period_str: Optional[str]) -> Tuple[int, int]:
        """Convert a period/fiscal year string into a sortable tuple of integers."""
        if not period_str:
            return (0, 0)

        clean = str(period_str).strip()

        fy_match = re.search(r"(?:FY\s*)?((?:19|20)\d{2})[-/](\d{2,4})", clean, re.IGNORECASE)
        if fy_match:
            start_yr = int(fy_match.group(1))
            end_part = fy_match.group(2)
            if len(end_part) == 2:
                end_yr = int(str(start_yr)[:2] + end_part)
            else:
                end_yr = int(end_part)
            return (start_yr, end_yr)

        # Check ISO date YYYY-MM-DD
        date_match = re.search(r"((?:19|20)\d{2})-(\d{2})-(\d{2})", clean)
        if date_match:
            return (int(date_match.group(1)), int(date_match.group(2)))

        # Check single 4-digit year e.g. 2024
        yr_match = re.search(r"\b((?:19|20)\d{2})\b", clean)
        if yr_match:
            yr = int(yr_match.group(1))
            return (yr, yr)

        return (0, 0)

    @staticmethod
    def calculate_field_yoy(previous: Optional[float], current: Optional[float]) -> Dict[str, Any]:
        """Calculate YoY metrics for a single financial field.
        
        Formulas:
            Absolute Change = Current Year - Previous Year
            Percentage Change = ((Current Year - Previous Year) / Previous Year) * 100
        
        Args:
            previous: Value from the earlier / previous period
            current: Value from the later / current period
            
        Returns:
            Dict[str, Any] matching the FieldYoYResult schema.
        """
        # 1. Missing value handling
        if previous is None and current is None:
            return {
                "previous": None,
                "current": None,
                "absolute_change": None,
                "percentage_change": None,
                "direction": None,
                "status": "INCOMPLETE",
                "reason": "Both previous and current period values are missing",
            }
        if previous is None:
            return {
                "previous": None,
                "current": current,
                "absolute_change": None,
                "percentage_change": None,
                "direction": None,
                "status": "INCOMPLETE",
                "reason": "Previous period value is missing",
            }
        if current is None:
            return {
                "previous": previous,
                "current": None,
                "absolute_change": None,
                "percentage_change": None,
                "direction": None,
                "status": "INCOMPLETE",
                "reason": "Current period value is missing",
            }

        # 2. Numerical calculations
        absolute_change = current - previous

        # Determine mathematical direction of change
        if absolute_change > 0:
            direction = "positive"
        elif absolute_change < 0:
            direction = "negative"
        else:
            direction = "unchanged"

        # 3. Handle zero previous value
        if previous == 0:
            return {
                "previous": previous,
                "current": current,
                "absolute_change": absolute_change,
                "percentage_change": None,
                "direction": direction,
                "status": "COMPLETED",
                "reason": "Percentage change cannot be calculated because previous value is zero.",
            }

        # 4. Standard percentage change
        percentage_change = (absolute_change / abs(previous)) * 100.0

        return {
            "previous": previous,
            "current": current,
            "absolute_change": absolute_change,
            "percentage_change": percentage_change,
            "direction": direction,
            "status": "COMPLETED",
            "reason": None,
        }

    @classmethod
    def analyze_periods(
        cls,
        previous_period: Optional[str],
        current_period: Optional[str],
        previous_metrics: Dict[str, Any],
        current_metrics: Dict[str, Any],
        fields_to_analyze: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Perform full YoY analysis across multiple financial fields between two periods."""
        if not previous_period or not current_period or previous_metrics is None or current_metrics is None:
            return {
                "status": "INSUFFICIENT_DATA",
                "periods": None,
                "financial_data": {},
                "warnings": ["At least two financial periods are required for YoY analysis"],
                "reason": "At least two financial periods are required for YoY analysis",
            }

        # Check if periods need chronological ordering
        key_prev = cls.parse_period_sort_key(previous_period)
        key_curr = cls.parse_period_sort_key(current_period)
        if key_prev > key_curr and key_prev != (0, 0) and key_curr != (0, 0):
            previous_period, current_period = current_period, previous_period
            previous_metrics, current_metrics = current_metrics, previous_metrics

        # If fields_to_analyze is explicitly provided, use it.
        # Otherwise, dynamically evaluate fields present in either previous or current metrics.
        if fields_to_analyze:
            active_fields = fields_to_analyze
        else:
            present_fields = [f for f in cls.CORE_FINANCIAL_FIELDS if f in previous_metrics or f in current_metrics]
            active_fields = present_fields if present_fields else ["revenue", "assets", "liabilities", "equity"]

        financial_results: Dict[str, Any] = {}
        warnings: List[str] = []
        has_completed = False
        has_incomplete = False

        for field in active_fields:
            p_val = previous_metrics.get(field)
            c_val = current_metrics.get(field)

            p_num = float(p_val) if p_val is not None and str(p_val).strip() != "" else None
            c_num = float(c_val) if c_val is not None and str(c_val).strip() != "" else None

            res = cls.calculate_field_yoy(p_num, c_num)
            financial_results[field] = res

            if res["status"] == "COMPLETED":
                has_completed = True
                if res.get("reason"):
                    warnings.append(f"{field}: {res['reason']}")
            else:
                has_incomplete = True
                if res.get("reason"):
                    warnings.append(f"{field}: {res['reason']}")

        overall_status = "COMPLETED" if (has_completed and not has_incomplete) else ("INCOMPLETE" if has_completed else "INSUFFICIENT_DATA")

        return {
            "status": overall_status,
            "periods": {
                "previous": previous_period,
                "current": current_period,
            },
            "financial_data": financial_results,
            "warnings": warnings,
            "reason": None if overall_status == "COMPLETED" else "One or more financial fields are incomplete or missing",
        }
'''

Path("app/services/analytics").mkdir(parents=True, exist_ok=True)
Path("app/services/analytics/yoy_analyzer.py").write_text(yoy_analyzer_code, encoding="utf-8")
Path("app/services/analytics/__init__.py").write_text(
    'from app.services.analytics.yoy_analyzer import YoYAnalyzer\n\n__all__ = ["YoYAnalyzer"]\n',
    encoding="utf-8"
)

# 2. Create app/schemas/analysis.py
analysis_schema_code = '''from typing import Optional, Dict, List, Any
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
'''

Path("app/schemas/analysis.py").write_text(analysis_schema_code, encoding="utf-8")

# Update app/schemas/__init__.py
schemas_init = '''from app.schemas.upload import UploadResponse, DocumentStatusResponse
from app.schemas.financial import (
    RawExtractionData,
    NormalizedFinancialData,
    NormalizedDocumentResponse,
    CompanyInfo,
    PeriodInfo,
    FinancialMetrics,
    DocumentSource,
    RawTable,
)
from app.schemas.validation import BalanceSheetCheckResult, MathValidationResponse
from app.schemas.analysis import (
    FieldYoYResult,
    PeriodsInfo,
    YoYAnalysisData,
    YoYAnalysisResponse,
    RatioResult,
    LiquidityRatios,
    ProfitabilityRatios,
    LeverageRatios,
    RatiosData,
    RatioAnalysisData,
    RatioAnalysisResponse,
)

__all__ = [
    "UploadResponse",
    "DocumentStatusResponse",
    "RawExtractionData",
    "NormalizedFinancialData",
    "NormalizedDocumentResponse",
    "CompanyInfo",
    "PeriodInfo",
    "FinancialMetrics",
    "DocumentSource",
    "RawTable",
    "BalanceSheetCheckResult",
    "MathValidationResponse",
    "FieldYoYResult",
    "PeriodsInfo",
    "YoYAnalysisData",
    "YoYAnalysisResponse",
    "RatioResult",
    "LiquidityRatios",
    "ProfitabilityRatios",
    "LeverageRatios",
    "RatiosData",
    "RatioAnalysisData",
    "RatioAnalysisResponse",
]
'''
Path("app/schemas/__init__.py").write_text(schemas_init, encoding="utf-8")

# 3. Create app/api/routes/analysis.py
route_code = '''import logging
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from app.database.database import get_db
from app.models.document import Document, DocumentStatus
from app.models.financial_data import FinancialData
from app.schemas.analysis import (
    YoYAnalysisResponse,
    YoYAnalysisData,
    FieldYoYResult,
    PeriodsInfo,
    RatioAnalysisResponse,
    RatioAnalysisData,
    RatiosData,
    LiquidityRatios,
    ProfitabilityRatios,
    LeverageRatios,
    RatioResult,
)
from app.services.analytics.yoy_analyzer import YoYAnalyzer
from app.services.analytics.ratio_analyzer import RatioAnalyzer

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post(
    "/{document_id}/yoy",
    response_model=YoYAnalysisResponse,
    summary="Perform Year-Over-Year (YoY) financial analysis on normalized data",
    description=(
        "Compares financial metrics between the current and previous financial periods "
        "for a normalized document."
    )
)
def analyze_yoy(document_id: str, db: Session = Depends(get_db)):
    # 1. Fetch document record
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with ID '{document_id}' not found."
        )

    # 2. Document must be in NORMALIZED status
    if doc.status != DocumentStatus.NORMALIZED.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Document '{document_id}' is in '{doc.status}' state and has not been normalized yet."
        )

    # 3. Retrieve normalized financial data for this document
    fin_record = db.query(FinancialData).filter(FinancialData.document_id == doc.id).first()
    if not fin_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Normalized financial record for document '{document_id}' was not found."
        )

    norm_data = dict(fin_record.normalized_data or {})
    current_period_str = fin_record.fiscal_year or fin_record.period_end or "Current"
    current_metrics = {
        "revenue": fin_record.revenue,
        "assets": fin_record.assets,
        "liabilities": fin_record.liabilities,
        "equity": fin_record.equity,
    }
    # Add any extra metrics from norm_data.financial_data
    if "financial_data" in norm_data and isinstance(norm_data["financial_data"], dict):
        for k, v in norm_data["financial_data"].items():
            if k not in current_metrics or current_metrics[k] is None:
                current_metrics[k] = v

    previous_period_str = None
    previous_metrics = None

    # Option A: Check if previous period data was embedded in normalized_data
    # e.g., in norm_data["previous_period_data"] or norm_data["historical_periods"]
    if "previous_period_data" in norm_data and isinstance(norm_data["previous_period_data"], dict):
        prev_dict = norm_data["previous_period_data"]
        previous_period_str = prev_dict.get("period") or prev_dict.get("fiscal_year") or "Previous"
        previous_metrics = prev_dict.get("financial_data") or prev_dict

    # Option B: Look for previous period record in DB for the same company
    if (not previous_metrics or not previous_period_str) and fin_record.company_name:
        other_records = (
            db.query(FinancialData)
            .join(Document, Document.id == FinancialData.document_id)
            .filter(
                FinancialData.company_name == fin_record.company_name,
                FinancialData.document_id != fin_record.document_id,
                Document.status == DocumentStatus.NORMALIZED.value,
            )
            .all()
        )
        if other_records:
            # Sort chronologically alongside current record
            cand_list = []
            for rec in other_records:
                rec_period = rec.fiscal_year or rec.period_end
                if rec_period:
                    cand_list.append((YoYAnalyzer.parse_period_sort_key(rec_period), rec_period, rec))

            cur_key = YoYAnalyzer.parse_period_sort_key(current_period_str)
            # Find closest earlier period
            earlier_cands = [c for c in cand_list if c[0] < cur_key and c[0] != (0, 0)]
            if earlier_cands:
                earlier_cands.sort(key=lambda x: x[0], reverse=True)
                _, previous_period_str, prev_rec = earlier_cands[0]
                previous_metrics = {
                    "revenue": prev_rec.revenue,
                    "assets": prev_rec.assets,
                    "liabilities": prev_rec.liabilities,
                    "equity": prev_rec.equity,
                }
                prev_norm = dict(prev_rec.normalized_data or {})
                if "financial_data" in prev_norm and isinstance(prev_norm["financial_data"], dict):
                    for k, v in prev_norm["financial_data"].items():
                        if k not in previous_metrics or previous_metrics[k] is None:
                            previous_metrics[k] = v
            elif not earlier_cands and cand_list:
                # If current is earlier than other record, compare adjacent
                later_cands = [c for c in cand_list if c[0] > cur_key and c[0] != (0, 0)]
                if later_cands:
                    later_cands.sort(key=lambda x: x[0])
                    _, next_period_str, next_rec = later_cands[0]
                    # Treat current as previous and next as current
                    previous_period_str = current_period_str
                    previous_metrics = current_metrics
                    current_period_str = next_period_str
                    current_metrics = {
                        "revenue": next_rec.revenue,
                        "assets": next_rec.assets,
                        "liabilities": next_rec.liabilities,
                        "equity": next_rec.equity,
                    }

    # 4. Check if we have two comparable periods
    if not previous_metrics or not previous_period_str:
        insufficient_res = {
            "status": "INSUFFICIENT_DATA",
            "periods": None,
            "financial_data": {},
            "warnings": ["At least two financial periods are required for YoY analysis"],
            "reason": "At least two financial periods are required for YoY analysis"
        }
        # Persist insufficient data status
        try:
            norm_data["analysis"] = norm_data.get("analysis", {})
            norm_data["analysis"]["yoy"] = insufficient_res
            fin_record.normalized_data = norm_data
            flag_modified(fin_record, "normalized_data")
            db.commit()
        except Exception as db_err:
            logger.error("Failed to persist YoY analysis: %s", db_err)
            db.rollback()

        return YoYAnalysisResponse(
            document_id=doc.id,
            yoy_analysis=YoYAnalysisData(**insufficient_res)
        )

    # 5. Perform YoY Analysis
    yoy_result = YoYAnalyzer.analyze_periods(
        previous_period=previous_period_str,
        current_period=current_period_str,
        previous_metrics=previous_metrics,
        current_metrics=current_metrics,
    )

    # 6. Persist YoY analysis into normalized_data JSON
    try:
        norm_data["analysis"] = norm_data.get("analysis", {})
        norm_data["analysis"]["yoy"] = yoy_result
        fin_record.normalized_data = norm_data
        flag_modified(fin_record, "normalized_data")
        db.commit()
    except Exception as db_err:
        logger.error("Failed to persist YoY analysis result for doc %s: %s", document_id, db_err)
        db.rollback()

    # Convert financial_data dict into FieldYoYResult models
    formatted_fin_data = {
        k: FieldYoYResult(**v) for k, v in yoy_result.get("financial_data", {}).items()
    }
    periods_data = PeriodsInfo(**yoy_result["periods"]) if yoy_result.get("periods") else None

        return YoYAnalysisResponse(
            document_id=doc.id,
            yoy_analysis=YoYAnalysisData(
                status=yoy_result["status"],
                periods=periods_data,
                financial_data=formatted_fin_data,
                warnings=yoy_result.get("warnings", []),
                reason=yoy_result.get("reason"),
            )
        )


@router.post(
    "/{document_id}/ratios",
    response_model=RatioAnalysisResponse,
    summary="Compute Financial Ratios (Liquidity, Profitability, Leverage) on normalized data",
    description=(
        "Computes key financial ratios for a normalized document: Current Ratio, Quick Ratio, "
        "Gross Profit Margin, Net Profit Margin, Return on Assets, Return on Equity, Debt-to-Equity, "
        "and Debt Ratio."
    )
)
def compute_ratios(document_id: str, db: Session = Depends(get_db)):
    # 1. Fetch document record
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with ID '{document_id}' not found."
        )

    # 2. Document must be in NORMALIZED status
    if doc.status != DocumentStatus.NORMALIZED.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Document '{document_id}' is in '{doc.status}' state and has not been normalized yet."
        )

    # 3. Retrieve normalized financial data
    fin_record = db.query(FinancialData).filter(FinancialData.document_id == doc.id).first()
    if not fin_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Normalized financial record for document '{document_id}' was not found."
        )

    norm_data = dict(fin_record.normalized_data or {})
    metrics = {
        "revenue": fin_record.revenue,
        "assets": fin_record.assets,
        "liabilities": fin_record.liabilities,
        "equity": fin_record.equity,
    }
    if "financial_data" in norm_data and isinstance(norm_data["financial_data"], dict):
        for k, v in norm_data["financial_data"].items():
            if k not in metrics or metrics[k] is None:
                metrics[k] = v

    # 4. Compute ratios
    ratio_result = RatioAnalyzer.analyze_ratios(metrics)

    # 5. Persist ratios result in normalized_data JSON
    try:
        norm_data["analysis"] = norm_data.get("analysis", {})
        norm_data["analysis"]["ratios"] = ratio_result
        fin_record.normalized_data = norm_data
        flag_modified(fin_record, "normalized_data")
        db.commit()
    except Exception as db_err:
        logger.error("Failed to persist ratio analysis for doc %s: %s", document_id, db_err)
        db.rollback()

    # Format into Pydantic models
    r = ratio_result["ratios"]
    ratios_model = RatiosData(
        liquidity=LiquidityRatios(
            current_ratio=RatioResult(**r["liquidity"]["current_ratio"]),
            quick_ratio=RatioResult(**r["liquidity"]["quick_ratio"]),
        ),
        profitability=ProfitabilityRatios(
            gross_profit_margin=RatioResult(**r["profitability"]["gross_profit_margin"]),
            net_profit_margin=RatioResult(**r["profitability"]["net_profit_margin"]),
            return_on_assets=RatioResult(**r["profitability"]["return_on_assets"]),
            return_on_equity=RatioResult(**r["profitability"]["return_on_equity"]),
        ),
        leverage=LeverageRatios(
            debt_to_equity=RatioResult(**r["leverage"]["debt_to_equity"]),
            debt_ratio=RatioResult(**r["leverage"]["debt_ratio"]),
        ),
    )

    return RatioAnalysisResponse(
        document_id=doc.id,
        ratio_analysis=RatioAnalysisData(
            status=ratio_result["status"],
            ratios=ratios_model,
            warnings=ratio_result.get("warnings", []),
            reason=ratio_result.get("reason"),
        )
    )
'''

Path("app/api/routes/analysis.py").write_text(route_code, encoding="utf-8")

# Update app/api/routes/__init__.py
routes_init = '''from fastapi import APIRouter
from app.api.routes.upload import router as upload_router
from app.api.routes.documents import router as documents_router
from app.api.routes.validation import router as validation_router
from app.api.routes.analysis import router as analysis_router

api_router = APIRouter()
api_router.include_router(upload_router, prefix="/documents", tags=["Upload"])
api_router.include_router(documents_router, prefix="/documents", tags=["Documents"])
api_router.include_router(validation_router, prefix="/validation", tags=["Validation"])
api_router.include_router(analysis_router, prefix="/analysis", tags=["Analysis"])
'''
Path("app/api/routes/__init__.py").write_text(routes_init, encoding="utf-8")

# 4. Create tests/test_yoy_analysis.py
test_code = '''import uuid
from pathlib import Path
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.services.analytics.yoy_analyzer import YoYAnalyzer
from app.models.document import Document, DocumentStatus
from app.models.financial_data import FinancialData


# ==============================================================================
# UNIT TESTS: YoYAnalyzer
# ==============================================================================

def test_unit_normal_growth():
    """TEST 1: Normal growth (Prev: 10M, Curr: 12.5M -> +2.5M, +25%, positive)."""
    res = YoYAnalyzer.calculate_field_yoy(previous=10_000_000.0, current=12_500_000.0)
    assert res["status"] == "COMPLETED"
    assert res["absolute_change"] == 2_500_000.0
    assert res["percentage_change"] == 25.0
    assert res["direction"] == "positive"
    assert res["reason"] is None


def test_unit_decline():
    """TEST 2: Decline (Prev: 12.5M, Curr: 10M -> -2.5M, -20%, negative)."""
    res = YoYAnalyzer.calculate_field_yoy(previous=12_500_000.0, current=10_000_000.0)
    assert res["status"] == "COMPLETED"
    assert res["absolute_change"] == -2_500_000.0
    assert res["percentage_change"] == -20.0
    assert res["direction"] == "negative"


def test_unit_no_change():
    """TEST 3: No change (Prev: 10M, Curr: 10M -> 0, 0%, unchanged)."""
    res = YoYAnalyzer.calculate_field_yoy(previous=10_000_000.0, current=10_000_000.0)
    assert res["status"] == "COMPLETED"
    assert res["absolute_change"] == 0.0
    assert res["percentage_change"] == 0.0
    assert res["direction"] == "unchanged"


def test_unit_previous_zero():
    """TEST 4: Previous zero (Prev: 0, Curr: 500K -> abs: 500K, pct: None, no crash)."""
    res = YoYAnalyzer.calculate_field_yoy(previous=0.0, current=500_000.0)
    assert res["status"] == "COMPLETED"
    assert res["absolute_change"] == 500_000.0
    assert res["percentage_change"] is None
    assert res["direction"] == "positive"
    assert "zero" in res["reason"].lower()


def test_unit_current_zero():
    """TEST 5: Current zero (Prev: 500K, Curr: 0 -> abs: -500K, pct: -100%, negative)."""
    res = YoYAnalyzer.calculate_field_yoy(previous=500_000.0, current=0.0)
    assert res["status"] == "COMPLETED"
    assert res["absolute_change"] == -500_000.0
    assert res["percentage_change"] == -100.0
    assert res["direction"] == "negative"


def test_unit_missing_previous():
    """TEST 6: Missing previous (Prev: None, Curr: 500K -> status INCOMPLETE)."""
    res = YoYAnalyzer.calculate_field_yoy(previous=None, current=500_000.0)
    assert res["status"] == "INCOMPLETE"
    assert res["absolute_change"] is None
    assert res["percentage_change"] is None
    assert "previous" in res["reason"].lower()


def test_unit_missing_current():
    """TEST 7: Missing current (Prev: 500K, Curr: None -> status INCOMPLETE)."""
    res = YoYAnalyzer.calculate_field_yoy(previous=500_000.0, current=None)
    assert res["status"] == "INCOMPLETE"
    assert res["absolute_change"] is None
    assert res["percentage_change"] is None
    assert "current" in res["reason"].lower()


def test_unit_only_one_period():
    """TEST 8: Only one period provided to analyze_periods returns INSUFFICIENT_DATA."""
    res = YoYAnalyzer.analyze_periods(
        previous_period="2024-25",
        current_period=None,
        previous_metrics={"revenue": 10_000_000.0},
        current_metrics=None,
    )
    assert res["status"] == "INSUFFICIENT_DATA"
    assert "two financial periods" in res["reason"].lower()


def test_unit_negative_values():
    """TEST 9: Negative values calculated mathematically (Prev: -10M, Curr: -5M -> diff: +5M, pct: +50%)."""
    res = YoYAnalyzer.calculate_field_yoy(previous=-10_000_000.0, current=-5_000_000.0)
    assert res["status"] == "COMPLETED"
    assert res["absolute_change"] == 5_000_000.0
    assert res["percentage_change"] == 50.0
    assert res["direction"] == "positive"


def test_unit_large_values():
    """TEST 10: Large financial values (Prev: 1 Trillion, Curr: 1.25 Trillion -> +250 Billion, +25%)."""
    prev_val = 1_000_000_000_000.0
    curr_val = 1_250_000_000_000.0
    res = YoYAnalyzer.calculate_field_yoy(previous=prev_val, current=curr_val)
    assert res["status"] == "COMPLETED"
    assert res["absolute_change"] == 250_000_000_000.0
    assert res["percentage_change"] == 25.0
    assert res["direction"] == "positive"


def test_unit_multiple_financial_fields():
    """TEST 11: Multiple financial fields analyzed concurrently."""
    prev_data = {
        "revenue": 10_000_000.0,
        "assets": 40_000_000.0,
        "liabilities": 15_000_000.0,
        "equity": 25_000_000.0,
    }
    curr_data = {
        "revenue": 12_500_000.0,
        "assets": 45_000_000.0,
        "liabilities": 18_000_000.0,
        "equity": 27_000_000.0,
    }
    res = YoYAnalyzer.analyze_periods(
        previous_period="2023-24",
        current_period="2024-25",
        previous_metrics=prev_data,
        current_metrics=curr_data,
    )
    assert res["status"] == "COMPLETED"
    fin = res["financial_data"]
    assert "revenue" in fin and fin["revenue"]["percentage_change"] == 25.0
    assert "assets" in fin and fin["assets"]["percentage_change"] == 12.5
    assert "liabilities" in fin and fin["liabilities"]["percentage_change"] == 20.0
    assert "equity" in fin and fin["equity"]["percentage_change"] == 8.0


def test_unit_period_ordering():
    """TEST 12: Chronological ordering ensures earlier period is previous, later is current."""
    # Pass 2024-25 as first arg and 2023-24 as second arg
    m_24_25 = {"revenue": 12_500_000.0}
    m_23_24 = {"revenue": 10_000_000.0}
    res = YoYAnalyzer.analyze_periods(
        previous_period="2024-25",
        current_period="2023-24",
        previous_metrics=m_24_25,
        current_metrics=m_23_24,
    )
    assert res["status"] == "COMPLETED"
    assert res["periods"]["previous"] == "2023-24"
    assert res["periods"]["current"] == "2024-25"
    assert res["financial_data"]["revenue"]["previous"] == 10_000_000.0
    assert res["financial_data"]["revenue"]["current"] == 12_500_000.0
    assert res["financial_data"]["revenue"]["percentage_change"] == 25.0


# ==============================================================================
# INTEGRATION TESTS: API POST /api/v1/analysis/{document_id}/yoy
# ==============================================================================

def test_api_valid_normalized_data_two_periods(client: TestClient, db_session: Session):
    """API TEST 1: Valid normalized data with two periods (embedded previous period)."""
    doc_id = str(uuid.uuid4())
    doc = Document(
        id=doc_id,
        filename="balance_sheet_fy25.pdf",
        file_type="pdf",
        file_path=str(Path("uploads") / "test_fy25.pdf"),
        status=DocumentStatus.NORMALIZED.value
    )
    fin_record = FinancialData(
        id=str(uuid.uuid4()),
        document_id=doc_id,
        company_name="Apex Global Ltd",
        currency="INR",
        fiscal_year="2024-25",
        revenue=12500000.0,
        assets=45000000.0,
        liabilities=18000000.0,
        equity=27000000.0,
        normalized_data={
            "document_id": doc_id,
            "company": {"name": "Apex Global Ltd"},
            "currency": "INR",
            "period": {"fiscal_year": "2024-25"},
            "financial_data": {
                "revenue": 12500000.0,
                "assets": 45000000.0,
                "liabilities": 18000000.0,
                "equity": 27000000.0
            },
            "previous_period_data": {
                "fiscal_year": "2023-24",
                "financial_data": {
                    "revenue": 10000000.0,
                    "assets": 40000000.0,
                    "liabilities": 15000000.0,
                    "equity": 25000000.0
                }
            }
        }
    )
    db_session.add(doc)
    db_session.add(fin_record)
    db_session.commit()

    response = client.post(f"/api/v1/analysis/{doc_id}/yoy")
    assert response.status_code == 200
    data = response.json()
    assert data["document_id"] == doc_id
    yoy = data["yoy_analysis"]
    assert yoy["status"] == "COMPLETED"
    assert yoy["periods"]["previous"] == "2023-24"
    assert yoy["periods"]["current"] == "2024-25"
    assert yoy["financial_data"]["revenue"]["absolute_change"] == 2500000.0
    assert yoy["financial_data"]["revenue"]["percentage_change"] == 25.0
    assert yoy["financial_data"]["revenue"]["direction"] == "positive"


def test_api_one_period_only(client: TestClient, db_session: Session):
    """API TEST 2: Only one period available returns INSUFFICIENT_DATA."""
    doc_id = str(uuid.uuid4())
    doc = Document(
        id=doc_id,
        filename="single_year.csv",
        file_type="csv",
        file_path=str(Path("uploads") / "single_year.csv"),
        status=DocumentStatus.NORMALIZED.value
    )
    fin_record = FinancialData(
        id=str(uuid.uuid4()),
        document_id=doc_id,
        company_name="Unique Startup Inc",
        currency="USD",
        fiscal_year="2024-25",
        revenue=5000000.0,
        assets=10000000.0,
        liabilities=4000000.0,
        equity=6000000.0,
        normalized_data={
            "document_id": doc_id,
            "company": {"name": "Unique Startup Inc"},
            "period": {"fiscal_year": "2024-25"},
            "financial_data": {
                "revenue": 5000000.0,
                "assets": 10000000.0,
                "liabilities": 4000000.0,
                "equity": 6000000.0
            }
        }
    )
    db_session.add(doc)
    db_session.add(fin_record)
    db_session.commit()

    response = client.post(f"/api/v1/analysis/{doc_id}/yoy")
    assert response.status_code == 200
    data = response.json()
    assert data["yoy_analysis"]["status"] == "INSUFFICIENT_DATA"
    assert "at least two financial periods" in data["yoy_analysis"]["reason"].lower()


def test_api_missing_financial_field(client: TestClient, db_session: Session):
    """API TEST 3: Missing financial field produces INCOMPLETE field status."""
    doc_id = str(uuid.uuid4())
    doc = Document(
        id=doc_id,
        filename="partial_data.xlsx",
        file_type="xlsx",
        file_path=str(Path("uploads") / "partial_data.xlsx"),
        status=DocumentStatus.NORMALIZED.value
    )
    fin_record = FinancialData(
        id=str(uuid.uuid4()),
        document_id=doc_id,
        company_name="Partial Corp",
        currency="INR",
        fiscal_year="2024-25",
        revenue=12000000.0,
        assets=40000000.0,
        liabilities=None,
        equity=None,
        normalized_data={
            "document_id": doc_id,
            "company": {"name": "Partial Corp"},
            "period": {"fiscal_year": "2024-25"},
            "financial_data": {
                "revenue": 12000000.0,
                "assets": 40000000.0,
            },
            "previous_period_data": {
                "fiscal_year": "2023-24",
                "financial_data": {
                    "revenue": 10000000.0,
                    "assets": 35000000.0,
                }
            }
        }
    )
    db_session.add(doc)
    db_session.add(fin_record)
    db_session.commit()

    response = client.post(f"/api/v1/analysis/{doc_id}/yoy")
    assert response.status_code == 200
    data = response.json()
    yoy = data["yoy_analysis"]
    assert yoy["financial_data"]["revenue"]["status"] == "COMPLETED"
    assert yoy["financial_data"]["revenue"]["percentage_change"] == 20.0
    assert yoy["financial_data"]["liabilities"]["status"] == "INCOMPLETE"
    assert yoy["status"] == "INCOMPLETE"


def test_api_zero_previous_value(client: TestClient, db_session: Session):
    """API TEST 4: Zero previous value returns null percentage_change with reason."""
    doc_id = str(uuid.uuid4())
    doc = Document(
        id=doc_id,
        filename="zero_prev.csv",
        file_type="csv",
        file_path=str(Path("uploads") / "zero_prev.csv"),
        status=DocumentStatus.NORMALIZED.value
    )
    fin_record = FinancialData(
        id=str(uuid.uuid4()),
        document_id=doc_id,
        company_name="New Venture Ltd",
        currency="USD",
        fiscal_year="2024-25",
        revenue=500000.0,
        assets=1000000.0,
        liabilities=400000.0,
        equity=600000.0,
        normalized_data={
            "document_id": doc_id,
            "company": {"name": "New Venture Ltd"},
            "period": {"fiscal_year": "2024-25"},
            "financial_data": {
                "revenue": 500000.0,
                "assets": 1000000.0,
                "liabilities": 400000.0,
                "equity": 600000.0
            },
            "previous_period_data": {
                "fiscal_year": "2023-24",
                "financial_data": {
                    "revenue": 0.0,
                    "assets": 1000000.0,
                    "liabilities": 400000.0,
                    "equity": 600000.0
                }
            }
        }
    )
    db_session.add(doc)
    db_session.add(fin_record)
    db_session.commit()

    response = client.post(f"/api/v1/analysis/{doc_id}/yoy")
    assert response.status_code == 200
    data = response.json()
    rev_result = data["yoy_analysis"]["financial_data"]["revenue"]
    assert rev_result["previous"] == 0.0
    assert rev_result["current"] == 500000.0
    assert rev_result["absolute_change"] == 500000.0
    assert rev_result["percentage_change"] is None
    assert "zero" in rev_result["reason"].lower()


def test_api_nonexistent_document(client: TestClient):
    """API TEST 5: Nonexistent document ID returns 404."""
    nonexistent_id = str(uuid.uuid4())
    response = client.post(f"/api/v1/analysis/{nonexistent_id}/yoy")
    assert response.status_code == 404
    assert f"Document with ID '{nonexistent_id}' not found." in response.json()["detail"]


def test_api_document_not_normalized(client: TestClient, db_session: Session):
    """API TEST 6: Document not in NORMALIZED state returns 400."""
    doc_id = str(uuid.uuid4())
    doc = Document(
        id=doc_id,
        filename="unprocessed.pdf",
        file_type="pdf",
        file_path=str(Path("uploads") / "unprocessed.pdf"),
        status=DocumentStatus.UPLOADED.value
    )
    db_session.add(doc)
    db_session.commit()

    response = client.post(f"/api/v1/analysis/{doc_id}/yoy")
    assert response.status_code == 400
    assert "has not been normalized yet" in response.json()["detail"]
'''

Path("tests/test_yoy_analysis.py").write_text(test_code, encoding="utf-8")

# 5. Create verify_yoy_cases.py
cases_script = '''import sys
from app.services.analytics.yoy_analyzer import YoYAnalyzer

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

print("=== YoY TEST CASES VERIFICATION ===")

# TEST 1 - NORMAL GROWTH
t1 = YoYAnalyzer.calculate_field_yoy(previous=10_000_000.0, current=12_500_000.0)
print(f"TEST 1 - NORMAL GROWTH: status={t1['status']}, abs={t1['absolute_change']}, pct={t1['percentage_change']}%, dir={t1['direction']}")

# TEST 2 - DECLINE
t2 = YoYAnalyzer.calculate_field_yoy(previous=12_500_000.0, current=10_000_000.0)
print(f"TEST 2 - DECLINE: status={t2['status']}, abs={t2['absolute_change']}, pct={t2['percentage_change']}%, dir={t2['direction']}")

# TEST 3 - NO CHANGE
t3 = YoYAnalyzer.calculate_field_yoy(previous=10_000_000.0, current=10_000_000.0)
print(f"TEST 3 - NO CHANGE: status={t3['status']}, abs={t3['absolute_change']}, pct={t3['percentage_change']}%, dir={t3['direction']}")

# TEST 4 - PREVIOUS VALUE ZERO
t4 = YoYAnalyzer.calculate_field_yoy(previous=0.0, current=500_000.0)
print(f"TEST 4 - PREVIOUS VALUE ZERO: status={t4['status']}, abs={t4['absolute_change']}, pct={t4['percentage_change']}, reason={t4['reason']}")

# TEST 5 - CURRENT VALUE ZERO
t5 = YoYAnalyzer.calculate_field_yoy(previous=500_000.0, current=0.0)
print(f"TEST 5 - CURRENT VALUE ZERO: status={t5['status']}, abs={t5['absolute_change']}, pct={t5['percentage_change']}%, dir={t5['direction']}")

# TEST 6 - MISSING PREVIOUS
t6 = YoYAnalyzer.calculate_field_yoy(previous=None, current=500_000.0)
print(f"TEST 6 - MISSING PREVIOUS: status={t6['status']}, abs={t6['absolute_change']}, pct={t6['percentage_change']}, reason={t6['reason']}")

# TEST 7 - MISSING CURRENT
t7 = YoYAnalyzer.calculate_field_yoy(previous=500_000.0, current=None)
print(f"TEST 7 - MISSING CURRENT: status={t7['status']}, abs={t7['absolute_change']}, pct={t7['percentage_change']}, reason={t7['reason']}")

# TEST 8 - ONLY ONE PERIOD
t8 = YoYAnalyzer.analyze_periods(
    previous_period="2024-25",
    current_period=None,
    previous_metrics={"revenue": 10_000_000.0},
    current_metrics=None,
)
print(f"TEST 8 - ONLY ONE PERIOD: status={t8['status']}, reason={t8['reason']}")

# TEST 9 - NEGATIVE VALUES
t9 = YoYAnalyzer.calculate_field_yoy(previous=-10_000_000.0, current=-5_000_000.0)
print(f"TEST 9 - NEGATIVE VALUES: status={t9['status']}, abs={t9['absolute_change']}, pct={t9['percentage_change']}%, dir={t9['direction']}")

# TEST 10 - LARGE VALUES
t10 = YoYAnalyzer.calculate_field_yoy(previous=1_000_000_000_000.0, current=1_250_000_000_000.0)
print(f"TEST 10 - LARGE VALUES: status={t10['status']}, abs={t10['absolute_change']}, pct={t10['percentage_change']}%, dir={t10['direction']}")

# TEST 11 - MULTIPLE FINANCIAL FIELDS
t11 = YoYAnalyzer.analyze_periods(
    previous_period="2023-24",
    current_period="2024-25",
    previous_metrics={"revenue": 10_000_000.0, "assets": 40_000_000.0, "liabilities": 15_000_000.0, "equity": 25_000_000.0},
    current_metrics={"revenue": 12_500_000.0, "assets": 45_000_000.0, "liabilities": 18_000_000.0, "equity": 27_000_000.0},
)
print(f"TEST 11 - MULTIPLE FIELDS: status={t11['status']}, fields={list(t11['financial_data'].keys())}")

# TEST 12 - PERIOD ORDERING
t12 = YoYAnalyzer.analyze_periods(
    previous_period="2024-25",
    current_period="2023-24",
    previous_metrics={"revenue": 12_500_000.0},
    current_metrics={"revenue": 10_000_000.0},
)
print(f"TEST 12 - PERIOD ORDERING: prev={t12['periods']['previous']}, curr={t12['periods']['current']}, pct={t12['financial_data']['revenue']['percentage_change']}%")
'''
Path("verify_yoy_cases.py").write_text(cases_script, encoding="utf-8")

# 6. Create verify_yoy_api.py
api_script = '''import sys
import json
import uuid
from pathlib import Path
from fastapi.testclient import TestClient

from app.main import app
from app.database.database import SessionLocal
from app.models.document import Document, DocumentStatus
from app.models.financial_data import FinancialData

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

client = TestClient(app)
db = SessionLocal()

print("==================================================")
print("SECTION 1: HEALTH CHECK")
print("==================================================")
r_health = client.get("/api/health")
print("GET /api/health Status:", r_health.status_code)
print("Health Response:", r_health.json())

print("\\n==================================================")
print("SECTION 2: POST /api/v1/analysis/{document_id}/yoy WITH REAL NORMALIZED DATA")
print("==================================================")
doc_id = str(uuid.uuid4())
doc = Document(
    id=doc_id,
    filename="annual_report_2025.csv",
    file_type="csv",
    file_path=str(Path("uploads") / "annual_report_2025.csv"),
    status=DocumentStatus.NORMALIZED.value
)
fin = FinancialData(
    id=str(uuid.uuid4()),
    document_id=doc_id,
    company_name="Reliance Retail Ventures Ltd",
    currency="INR",
    fiscal_year="2024-25",
    revenue=12500000.0,
    assets=45000000.0,
    liabilities=18000000.0,
    equity=27000000.0,
    normalized_data={
        "document_id": doc_id,
        "company": {"name": "Reliance Retail Ventures Ltd"},
        "currency": "INR",
        "period": {"fiscal_year": "2024-25"},
        "financial_data": {
            "revenue": 12500000.0,
            "assets": 45000000.0,
            "liabilities": 18000000.0,
            "equity": 27000000.0
        },
        "previous_period_data": {
            "fiscal_year": "2023-24",
            "financial_data": {
                "revenue": 10000000.0,
                "assets": 40000000.0,
                "liabilities": 15000000.0,
                "equity": 25000000.0
            }
        }
    }
)
db.add(doc)
db.add(fin)
db.commit()

resp = client.post(f"/api/v1/analysis/{doc_id}/yoy")
print("POST /api/v1/analysis/{document_id}/yoy Status:", resp.status_code)
print("COMPLETE HTTP RESPONSE BODY:")
print(json.dumps(resp.json(), indent=2))

print("\\n==================================================")
print("SECTION 3: ERROR & EDGE CASES")
print("==================================================")
# Nonexistent doc
r_404 = client.post(f"/api/v1/analysis/{uuid.uuid4()}/yoy")
print("A. Nonexistent Document Status:", r_404.status_code, "Body:", r_404.json())

# Unnormalized doc
unnorm_id = str(uuid.uuid4())
unnorm_doc = Document(
    id=unnorm_id,
    filename="raw_upload.pdf",
    file_type="pdf",
    file_path="uploads/raw_upload.pdf",
    status=DocumentStatus.UPLOADED.value
)
db.add(unnorm_doc)
db.commit()
r_400 = client.post(f"/api/v1/analysis/{unnorm_id}/yoy")
print("B. Unnormalized Document Status:", r_400.status_code, "Body:", r_400.json())

# One period only
single_id = str(uuid.uuid4())
single_doc = Document(
    id=single_id,
    filename="single_period.csv",
    file_type="csv",
    file_path="uploads/single_period.csv",
    status=DocumentStatus.NORMALIZED.value
)
single_fin = FinancialData(
    id=str(uuid.uuid4()),
    document_id=single_id,
    company_name="Single Year Corp",
    currency="INR",
    fiscal_year="2024-25",
    revenue=10000000.0,
    assets=30000000.0,
    liabilities=10000000.0,
    equity=20000000.0,
    normalized_data={
        "document_id": single_id,
        "company": {"name": "Single Year Corp"},
        "period": {"fiscal_year": "2024-25"},
        "financial_data": {
            "revenue": 10000000.0,
            "assets": 30000000.0,
            "liabilities": 10000000.0,
            "equity": 20000000.0
        }
    }
)
db.add(single_doc)
db.add(single_fin)
db.commit()
r_single = client.post(f"/api/v1/analysis/{single_id}/yoy")
print("C. Single Period Status:", r_single.status_code, "Body:", r_single.json())

# Zero previous
zero_id = str(uuid.uuid4())
zero_doc = Document(
    id=zero_id,
    filename="zero_prev.csv",
    file_type="csv",
    file_path="uploads/zero_prev.csv",
    status=DocumentStatus.NORMALIZED.value
)
zero_fin = FinancialData(
    id=str(uuid.uuid4()),
    document_id=zero_id,
    company_name="Zero Previous Inc",
    currency="USD",
    fiscal_year="2024-25",
    revenue=500000.0,
    assets=1000000.0,
    liabilities=400000.0,
    equity=600000.0,
    normalized_data={
        "document_id": zero_id,
        "company": {"name": "Zero Previous Inc"},
        "period": {"fiscal_year": "2024-25"},
        "financial_data": {"revenue": 500000.0, "assets": 1000000.0, "liabilities": 400000.0, "equity": 600000.0},
        "previous_period_data": {
            "fiscal_year": "2023-24",
            "financial_data": {"revenue": 0.0, "assets": 1000000.0, "liabilities": 400000.0, "equity": 600000.0}
        }
    }
)
db.add(zero_doc)
db.add(zero_fin)
db.commit()
r_zero = client.post(f"/api/v1/analysis/{zero_id}/yoy")
print("D. Zero Previous Status:", r_zero.status_code, "Revenue YoY:", r_zero.json()["yoy_analysis"]["financial_data"]["revenue"])

print("\\n==================================================")
print("SECTION 4: SWAGGER & OPENAPI DOCUMENTATION")
print("==================================================")
r_docs = client.get("/docs")
r_openapi = client.get("/openapi.json")
print("GET /docs Status:", r_docs.status_code)
print("GET /openapi.json Status:", r_openapi.status_code)
paths = r_openapi.json().get("paths", {})
has_yoy = "/api/v1/analysis/{document_id}/yoy" in paths
print("YoY Endpoint in OpenAPI:", has_yoy)

print("\\n==================================================")
print("SECTION 5: DATABASE PERSISTENCE VERIFICATION")
print("==================================================")
db.refresh(fin)
stored_norm = fin.normalized_data or {}
yoy_block = stored_norm.get("analysis", {}).get("yoy")
print("Persisted in financial_data.normalized_data['analysis']['yoy']:")
print(json.dumps(yoy_block, indent=2))

print("\\nALL VERIFICATION STEPS COMPLETED!")
'''
Path("verify_yoy_api.py").write_text(api_script, encoding="utf-8")
print("verify_yoy_cases.py and verify_yoy_api.py created successfully.")

# 7. Create tests/test_ratio_analysis.py
ratio_test_code = '''import uuid
from pathlib import Path
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.services.analytics.ratio_analyzer import RatioAnalyzer
from app.models.document import Document, DocumentStatus
from app.models.financial_data import FinancialData


# ==============================================================================
# UNIT TESTS: RatioAnalyzer
# ==============================================================================

def test_unit_current_ratio():
    """TEST 1: Current Ratio = Current Assets (200) / Current Liabilities (100) = 2.0"""
    res = RatioAnalyzer.calculate_current_ratio(current_assets=200.0, current_liabilities=100.0)
    assert res["status"] == "COMPLETED"
    assert res["value"] == 2.0
    assert res["reason"] is None


def test_unit_quick_ratio():
    """TEST 2: Quick Ratio = (Current Assets (200) - Inventory (50)) / Current Liabilities (100) = 1.5"""
    res = RatioAnalyzer.calculate_quick_ratio(current_assets=200.0, inventory=50.0, current_liabilities=100.0)
    assert res["status"] == "COMPLETED"
    assert res["value"] == 1.5
    assert res["reason"] is None


def test_unit_gross_profit_margin():
    """TEST 3: Gross Profit Margin = (Gross Profit (400) / Revenue (1000)) * 100 = 40.0%"""
    res = RatioAnalyzer.calculate_gross_profit_margin(gross_profit=400.0, revenue=1000.0)
    assert res["status"] == "COMPLETED"
    assert res["value"] == 40.0
    assert res["reason"] is None


def test_unit_net_profit_margin():
    """TEST 4: Net Profit Margin = (Net Profit (100) / Revenue (1000)) * 100 = 10.0%"""
    res = RatioAnalyzer.calculate_net_profit_margin(net_profit=100.0, revenue=1000.0)
    assert res["status"] == "COMPLETED"
    assert res["value"] == 10.0
    assert res["reason"] is None


def test_unit_return_on_assets():
    """TEST 5: ROA = (Net Profit (100) / Assets (2000)) * 100 = 5.0%"""
    res = RatioAnalyzer.calculate_return_on_assets(net_profit=100.0, assets=2000.0)
    assert res["status"] == "COMPLETED"
    assert res["value"] == 5.0
    assert res["reason"] is None


def test_unit_return_on_equity():
    """TEST 6: ROE = (Net Profit (100) / Equity (500)) * 100 = 20.0%"""
    res = RatioAnalyzer.calculate_return_on_equity(net_profit=100.0, equity=500.0)
    assert res["status"] == "COMPLETED"
    assert res["value"] == 20.0
    assert res["reason"] is None


def test_unit_debt_to_equity():
    """TEST 7: Debt-to-Equity = Debt (300) / Equity (600) = 0.5"""
    res = RatioAnalyzer.calculate_debt_to_equity(debt=300.0, equity=600.0)
    assert res["status"] == "COMPLETED"
    assert res["value"] == 0.5
    assert res["reason"] is None


def test_unit_debt_ratio():
    """TEST 8: Debt Ratio = Debt (300) / Assets (1000) = 0.3"""
    res = RatioAnalyzer.calculate_debt_ratio(debt=300.0, assets=1000.0)
    assert res["status"] == "COMPLETED"
    assert res["value"] == 0.3
    assert res["reason"] is None


def test_unit_missing_current_liabilities():
    """TEST 9: Missing Current Liabilities -> Current Ratio = null, status = INCOMPLETE"""
    res = RatioAnalyzer.calculate_current_ratio(current_assets=200.0, current_liabilities=None)
    assert res["status"] == "INCOMPLETE"
    assert res["value"] is None
    assert "current liabilities" in res["reason"].lower()


def test_unit_missing_revenue():
    """TEST 10: Missing Revenue -> Gross Profit Margin and Net Profit Margin = null, status = INCOMPLETE"""
    gpm = RatioAnalyzer.calculate_gross_profit_margin(gross_profit=400.0, revenue=None)
    assert gpm["status"] == "INCOMPLETE"
    assert gpm["value"] is None
    assert "revenue" in gpm["reason"].lower()

    npm = RatioAnalyzer.calculate_net_profit_margin(net_profit=100.0, revenue=None)
    assert npm["status"] == "INCOMPLETE"
    assert npm["value"] is None
    assert "revenue" in npm["reason"].lower()


def test_unit_missing_equity():
    """TEST 11: Missing Equity -> ROE and Debt-to-Equity = null, status = INCOMPLETE"""
    roe = RatioAnalyzer.calculate_return_on_equity(net_profit=100.0, equity=None)
    assert roe["status"] == "INCOMPLETE"
    assert roe["value"] is None
    assert "equity" in roe["reason"].lower()

    dte = RatioAnalyzer.calculate_debt_to_equity(debt=300.0, equity=None)
    assert dte["status"] == "INCOMPLETE"
    assert dte["value"] is None
    assert "equity" in dte["reason"].lower()


def test_unit_zero_revenue():
    """TEST 12: Zero Revenue -> value = null, status = UNDEFINED, no crash"""
    gpm = RatioAnalyzer.calculate_gross_profit_margin(gross_profit=400.0, revenue=0.0)
    assert gpm["status"] == "UNDEFINED"
    assert gpm["value"] is None
    assert "zero" in gpm["reason"].lower()

    npm = RatioAnalyzer.calculate_net_profit_margin(net_profit=100.0, revenue=0.0)
    assert npm["status"] == "UNDEFINED"
    assert npm["value"] is None
    assert "zero" in npm["reason"].lower()


def test_unit_zero_assets():
    """TEST 13: Zero Assets -> ROA and Debt Ratio = null, status = UNDEFINED, no crash"""
    roa = RatioAnalyzer.calculate_return_on_assets(net_profit=100.0, assets=0.0)
    assert roa["status"] == "UNDEFINED"
    assert roa["value"] is None
    assert "zero" in roa["reason"].lower()

    dr = RatioAnalyzer.calculate_debt_ratio(debt=300.0, assets=0.0)
    assert dr["status"] == "UNDEFINED"
    assert dr["value"] is None
    assert "zero" in dr["reason"].lower()


def test_unit_zero_equity():
    """TEST 14: Zero Equity -> ROE and Debt-to-Equity = null, status = UNDEFINED, no crash"""
    roe = RatioAnalyzer.calculate_return_on_equity(net_profit=100.0, equity=0.0)
    assert roe["status"] == "UNDEFINED"
    assert roe["value"] is None
    assert "zero" in roe["reason"].lower()

    dte = RatioAnalyzer.calculate_debt_to_equity(debt=300.0, equity=0.0)
    assert dte["status"] == "UNDEFINED"
    assert dte["value"] is None
    assert "zero" in dte["reason"].lower()


def test_unit_negative_net_profit():
    """TEST 15: Negative Net Profit (-100 / 1000 * 100 = -10%) calculates normally without rejection"""
    npm = RatioAnalyzer.calculate_net_profit_margin(net_profit=-100.0, revenue=1000.0)
    assert npm["status"] == "COMPLETED"
    assert npm["value"] == -10.0
    assert npm["reason"] is None


def test_unit_zero_debt():
    """TEST 16: Zero Debt (0 / 500 = 0.0) treats 0 as valid numerator, not missing"""
    dte = RatioAnalyzer.calculate_debt_to_equity(debt=0.0, equity=500.0)
    assert dte["status"] == "COMPLETED"
    assert dte["value"] == 0.0

    dr = RatioAnalyzer.calculate_debt_ratio(debt=0.0, assets=1000.0)
    assert dr["status"] == "COMPLETED"
    assert dr["value"] == 0.0


def test_unit_large_values():
    """TEST 17: Large values in trillions maintain numerical precision"""
    net_profit = 250_000_000_000.0
    equity = 1_000_000_000_000.0
    roe = RatioAnalyzer.calculate_return_on_equity(net_profit=net_profit, equity=equity)
    assert roe["status"] == "COMPLETED"
    assert roe["value"] == 25.0


def test_unit_multiple_ratios():
    """TEST 18: Provide complete normalized dataset and verify all applicable ratios compute"""
    metrics = {
        "current_assets": 200.0,
        "current_liabilities": 100.0,
        "inventory": 50.0,
        "revenue": 1000.0,
        "gross_profit": 400.0,
        "net_profit": 100.0,
        "assets": 2000.0,
        "equity": 500.0,
        "debt": 300.0,
    }
    res = RatioAnalyzer.analyze_ratios(metrics)
    assert res["status"] == "COMPLETED"
    r = res["ratios"]
    assert r["liquidity"]["current_ratio"]["value"] == 2.0
    assert r["liquidity"]["quick_ratio"]["value"] == 1.5
    assert r["profitability"]["gross_profit_margin"]["value"] == 40.0
    assert r["profitability"]["net_profit_margin"]["value"] == 10.0
    assert r["profitability"]["return_on_assets"]["value"] == 5.0
    assert r["profitability"]["return_on_equity"]["value"] == 20.0
    assert r["leverage"]["debt_to_equity"]["value"] == 0.6
    assert r["leverage"]["debt_ratio"]["value"] == 0.15


def test_unit_missing_inventory():
    """TEST 19: Missing inventory -> Current ratio calculates, Quick ratio is INCOMPLETE"""
    metrics = {
        "current_assets": 200.0,
        "current_liabilities": 100.0,
        "inventory": None,
    }
    res = RatioAnalyzer.analyze_ratios(metrics)
    r = res["ratios"]
    assert r["liquidity"]["current_ratio"]["status"] == "COMPLETED"
    assert r["liquidity"]["current_ratio"]["value"] == 2.0
    assert r["liquidity"]["quick_ratio"]["status"] == "INCOMPLETE"
    assert r["liquidity"]["quick_ratio"]["value"] is None


def test_unit_partial_dataset():
    """TEST 20: Partial dataset computes available ratios and flags unavailable without fabricating data"""
    metrics = {
        "revenue": 1000.0,
        "gross_profit": 400.0,
        "assets": 2000.0,
    }
    res = RatioAnalyzer.analyze_ratios(metrics)
    r = res["ratios"]
    assert r["profitability"]["gross_profit_margin"]["status"] == "COMPLETED"
    assert r["profitability"]["gross_profit_margin"]["value"] == 40.0
    assert r["liquidity"]["current_ratio"]["status"] == "INCOMPLETE"
    assert r["profitability"]["net_profit_margin"]["status"] == "INCOMPLETE"


# ==============================================================================
# INTEGRATION TESTS: API POST /api/v1/analysis/{document_id}/ratios
# ==============================================================================

def test_api_valid_document_complete_ratios(client: TestClient, db_session: Session):
    """API TEST 1 & 2: Valid normalized document with complete metrics -> 200 and all ratios computed"""
    doc_id = str(uuid.uuid4())
    doc = Document(
        id=doc_id,
        filename="complete_report.csv",
        file_type="csv",
        file_path=str(Path("uploads") / "complete_report.csv"),
        status=DocumentStatus.NORMALIZED.value
    )
    fin_record = FinancialData(
        id=str(uuid.uuid4()),
        document_id=doc_id,
        company_name="Apex Global Ltd",
        currency="INR",
        fiscal_year="2024-25",
        revenue=10000000.0,
        assets=20000000.0,
        liabilities=8000000.0,
        equity=12000000.0,
        normalized_data={
            "document_id": doc_id,
            "company": {"name": "Apex Global Ltd"},
            "period": {"fiscal_year": "2024-25"},
            "financial_data": {
                "revenue": 10000000.0,
                "gross_profit": 4000000.0,
                "net_profit": 1500000.0,
                "assets": 20000000.0,
                "equity": 12000000.0,
                "liabilities": 8000000.0,
                "current_assets": 6000000.0,
                "current_liabilities": 3000000.0,
                "inventory": 1500000.0,
            }
        }
    )
    db_session.add(doc)
    db_session.add(fin_record)
    db_session.commit()

    response = client.post(f"/api/v1/analysis/{doc_id}/ratios")
    assert response.status_code == 200
    data = response.json()
    assert data["document_id"] == doc_id
    ratios = data["ratio_analysis"]["ratios"]
    assert ratios["liquidity"]["current_ratio"]["value"] == 2.0
    assert ratios["liquidity"]["quick_ratio"]["value"] == 1.5
    assert ratios["profitability"]["gross_profit_margin"]["value"] == 40.0
    assert ratios["profitability"]["net_profit_margin"]["value"] == 15.0
    assert ratios["profitability"]["return_on_assets"]["value"] == 7.5
    assert ratios["profitability"]["return_on_equity"]["value"] == 12.5
    assert ratios["leverage"]["debt_to_equity"]["value"] == 0.6667
    assert ratios["leverage"]["debt_ratio"]["value"] == 0.4


def test_api_missing_fields(client: TestClient, db_session: Session):
    """API TEST 3: Normalized document missing some fields returns 200 with INCOMPLETE individual statuses"""
    doc_id = str(uuid.uuid4())
    doc = Document(
        id=doc_id,
        filename="partial_fields.csv",
        file_type="csv",
        file_path=str(Path("uploads") / "partial_fields.csv"),
        status=DocumentStatus.NORMALIZED.value
    )
    fin_record = FinancialData(
        id=str(uuid.uuid4()),
        document_id=doc_id,
        company_name="Partial Ltd",
        currency="USD",
        revenue=5000000.0,
        assets=10000000.0,
        liabilities=4000000.0,
        equity=6000000.0,
        normalized_data={
            "document_id": doc_id,
            "company": {"name": "Partial Ltd"},
            "financial_data": {
                "revenue": 5000000.0,
                "assets": 10000000.0,
                "equity": 6000000.0,
                "liabilities": 4000000.0,
            }
        }
    )
    db_session.add(doc)
    db_session.add(fin_record)
    db_session.commit()

    response = client.post(f"/api/v1/analysis/{doc_id}/ratios")
    assert response.status_code == 200
    data = response.json()
    r = data["ratio_analysis"]["ratios"]
    assert r["liquidity"]["current_ratio"]["status"] == "INCOMPLETE"
    assert r["liquidity"]["quick_ratio"]["status"] == "INCOMPLETE"
    assert r["leverage"]["debt_to_equity"]["status"] == "COMPLETED"
    assert r["leverage"]["debt_ratio"]["status"] == "COMPLETED"


def test_api_zero_denominator(client: TestClient, db_session: Session):
    """API TEST 4: Zero denominator returns 200 with UNDEFINED status and value null"""
    doc_id = str(uuid.uuid4())
    doc = Document(
        id=doc_id,
        filename="zero_rev.csv",
        file_type="csv",
        file_path=str(Path("uploads") / "zero_rev.csv"),
        status=DocumentStatus.NORMALIZED.value
    )
    fin_record = FinancialData(
        id=str(uuid.uuid4()),
        document_id=doc_id,
        company_name="Zero Rev Corp",
        currency="USD",
        revenue=0.0,
        assets=10000000.0,
        liabilities=4000000.0,
        equity=6000000.0,
        normalized_data={
            "document_id": doc_id,
            "financial_data": {
                "revenue": 0.0,
                "gross_profit": 500000.0,
                "net_profit": 100000.0,
                "assets": 10000000.0,
                "equity": 6000000.0,
            }
        }
    )
    db_session.add(doc)
    db_session.add(fin_record)
    db_session.commit()

    response = client.post(f"/api/v1/analysis/{doc_id}/ratios")
    assert response.status_code == 200
    data = response.json()
    prof = data["ratio_analysis"]["ratios"]["profitability"]
    assert prof["gross_profit_margin"]["status"] == "UNDEFINED"
    assert prof["gross_profit_margin"]["value"] is None
    assert "zero" in prof["gross_profit_margin"]["reason"].lower()


def test_api_nonexistent_document(client: TestClient):
    """API TEST 5: Nonexistent document returns 404"""
    nonexistent_id = str(uuid.uuid4())
    response = client.post(f"/api/v1/analysis/{nonexistent_id}/ratios")
    assert response.status_code == 404
    assert f"Document with ID '{nonexistent_id}' not found." in response.json()["detail"]


def test_api_unnormalized_document(client: TestClient, db_session: Session):
    """API TEST 6: Unnormalized document returns 400"""
    doc_id = str(uuid.uuid4())
    doc = Document(
        id=doc_id,
        filename="pending.pdf",
        file_type="pdf",
        file_path="uploads/pending.pdf",
        status=DocumentStatus.UPLOADED.value
    )
    db_session.add(doc)
    db_session.commit()

    response = client.post(f"/api/v1/analysis/{doc_id}/ratios")
    assert response.status_code == 400
    assert "has not been normalized yet" in response.json()["detail"]


def test_api_db_persistence(client: TestClient, db_session: Session):
    """API TEST 8: Verify ratio result is persisted in financial_data.normalized_data['analysis']['ratios']"""
    doc_id = str(uuid.uuid4())
    doc = Document(
        id=doc_id,
        filename="persist_test.csv",
        file_type="csv",
        file_path="uploads/persist_test.csv",
        status=DocumentStatus.NORMALIZED.value
    )
    fin_record = FinancialData(
        id=str(uuid.uuid4()),
        document_id=doc_id,
        company_name="Persist Corp",
        currency="USD",
        revenue=1000.0,
        assets=2000.0,
        equity=500.0,
        normalized_data={
            "document_id": doc_id,
            "financial_data": {
                "revenue": 1000.0,
                "gross_profit": 400.0,
                "net_profit": 100.0,
                "assets": 2000.0,
                "equity": 500.0,
            }
        }
    )
    db_session.add(doc)
    db_session.add(fin_record)
    db_session.commit()

    response = client.post(f"/api/v1/analysis/{doc_id}/ratios")
    assert response.status_code == 200

    # Refresh record from database
    db_session.refresh(fin_record)
    stored_norm = fin_record.normalized_data or {}
    assert "analysis" in stored_norm
    assert "ratios" in stored_norm["analysis"]
    persisted_ratios = stored_norm["analysis"]["ratios"]
    assert persisted_ratios["ratios"]["profitability"]["gross_profit_margin"]["value"] == 40.0
'''

Path("tests/test_ratio_analysis.py").write_text(ratio_test_code, encoding="utf-8")
print("tests/test_ratio_analysis.py created successfully.")

# 8. Create verify_ratio_cases.py
ratio_cases_script = '''import sys
from app.services.analytics.ratio_analyzer import RatioAnalyzer

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

print("=== FINANCIAL RATIOS TEST CASES VERIFICATION ===")

t1 = RatioAnalyzer.calculate_current_ratio(200.0, 100.0)
print(f"TEST 1 - Current Ratio (200/100): val={t1['value']}, status={t1['status']}")

t2 = RatioAnalyzer.calculate_quick_ratio(200.0, 50.0, 100.0)
print(f"TEST 2 - Quick Ratio ((200-50)/100): val={t2['value']}, status={t2['status']}")

t3 = RatioAnalyzer.calculate_gross_profit_margin(400.0, 1000.0)
print(f"TEST 3 - Gross Profit Margin (400/1000): val={t3['value']}%, status={t3['status']}")

t4 = RatioAnalyzer.calculate_net_profit_margin(100.0, 1000.0)
print(f"TEST 4 - Net Profit Margin (100/1000): val={t4['value']}%, status={t4['status']}")

t5 = RatioAnalyzer.calculate_return_on_assets(100.0, 2000.0)
print(f"TEST 5 - ROA (100/2000): val={t5['value']}%, status={t5['status']}")

t6 = RatioAnalyzer.calculate_return_on_equity(100.0, 500.0)
print(f"TEST 6 - ROE (100/500): val={t6['value']}%, status={t6['status']}")

t7 = RatioAnalyzer.calculate_debt_to_equity(300.0, 600.0)
print(f"TEST 7 - Debt-to-Equity (300/600): val={t7['value']}, status={t7['status']}")

t8 = RatioAnalyzer.calculate_debt_ratio(300.0, 1000.0)
print(f"TEST 8 - Debt Ratio (300/1000): val={t8['value']}, status={t8['status']}")

t9 = RatioAnalyzer.calculate_current_ratio(200.0, None)
print(f"TEST 9 - Missing Current Liabilities: val={t9['value']}, status={t9['status']}, reason={t9['reason']}")

t10 = RatioAnalyzer.calculate_gross_profit_margin(400.0, None)
print(f"TEST 10 - Missing Revenue: val={t10['value']}, status={t10['status']}, reason={t10['reason']}")

t11 = RatioAnalyzer.calculate_return_on_equity(100.0, None)
print(f"TEST 11 - Missing Equity: val={t11['value']}, status={t11['status']}, reason={t11['reason']}")

t12 = RatioAnalyzer.calculate_gross_profit_margin(400.0, 0.0)
print(f"TEST 12 - Zero Revenue: val={t12['value']}, status={t12['status']}, reason={t12['reason']}")

t13 = RatioAnalyzer.calculate_return_on_assets(100.0, 0.0)
print(f"TEST 13 - Zero Assets: val={t13['value']}, status={t13['status']}, reason={t13['reason']}")

t14 = RatioAnalyzer.calculate_return_on_equity(100.0, 0.0)
print(f"TEST 14 - Zero Equity: val={t14['value']}, status={t14['status']}, reason={t14['reason']}")

t15 = RatioAnalyzer.calculate_net_profit_margin(-100.0, 1000.0)
print(f"TEST 15 - Negative Net Profit: val={t15['value']}%, status={t15['status']}")

t16 = RatioAnalyzer.calculate_debt_to_equity(0.0, 500.0)
print(f"TEST 16 - Zero Debt: val={t16['value']}, status={t16['status']}")

t17 = RatioAnalyzer.calculate_return_on_equity(250_000_000_000.0, 1_000_000_000_000.0)
print(f"TEST 17 - Large Values (Trillions): val={t17['value']}%, status={t17['status']}")

t18 = RatioAnalyzer.analyze_ratios({
    'current_assets': 200.0, 'current_liabilities': 100.0, 'inventory': 50.0,
    'revenue': 1000.0, 'gross_profit': 400.0, 'net_profit': 100.0,
    'assets': 2000.0, 'equity': 500.0, 'debt': 300.0
})
print(f"TEST 18 - Complete Dataset: status={t18['status']}, CR={t18['ratios']['liquidity']['current_ratio']['value']}, GPM={t18['ratios']['profitability']['gross_profit_margin']['value']}%")

t19 = RatioAnalyzer.analyze_ratios({'current_assets': 200.0, 'current_liabilities': 100.0, 'inventory': None})
print(f"TEST 19 - Missing Inventory: CR={t19['ratios']['liquidity']['current_ratio']['value']}, QR status={t19['ratios']['liquidity']['quick_ratio']['status']}")

t20 = RatioAnalyzer.analyze_ratios({'revenue': 1000.0, 'gross_profit': 400.0})
print(f"TEST 20 - Partial Dataset: GPM status={t20['ratios']['profitability']['gross_profit_margin']['status']}, CR status={t20['ratios']['liquidity']['current_ratio']['status']}")
'''
Path("verify_ratio_cases.py").write_text(ratio_cases_script, encoding="utf-8")
print("verify_ratio_cases.py created successfully.")

# 9. Create verify_ratio_api.py
ratio_api_script = '''import sys
import json
import uuid
from pathlib import Path
from fastapi.testclient import TestClient

from app.main import app
from app.database.database import SessionLocal
from app.models.document import Document, DocumentStatus
from app.models.financial_data import FinancialData

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

client = TestClient(app)
db = SessionLocal()

print("==================================================")
print("SECTION 1: HEALTH CHECK")
print("==================================================")
r_health = client.get("/api/health")
print("GET /api/health Status:", r_health.status_code)
print("Health Response:", r_health.json())

print("\\n==================================================")
print("SECTION 2: POST /api/v1/analysis/{document_id}/ratios WITH COMPLETE NORMALIZED DATA")
print("==================================================")
doc_id = str(uuid.uuid4())
doc = Document(
    id=doc_id,
    filename="comprehensive_financials.csv",
    file_type="csv",
    file_path=str(Path("uploads") / "comprehensive_financials.csv"),
    status=DocumentStatus.NORMALIZED.value
)
fin = FinancialData(
    id=str(uuid.uuid4()),
    document_id=doc_id,
    company_name="Reliance Retail Ventures Ltd",
    currency="INR",
    fiscal_year="2024-25",
    revenue=10000000.0,
    assets=20000000.0,
    liabilities=8000000.0,
    equity=12000000.0,
    normalized_data={
        "document_id": doc_id,
        "company": {"name": "Reliance Retail Ventures Ltd"},
        "currency": "INR",
        "period": {"fiscal_year": "2024-25"},
        "financial_data": {
            "revenue": 10000000.0,
            "gross_profit": 4000000.0,
            "net_profit": 1500000.0,
            "assets": 20000000.0,
            "equity": 12000000.0,
            "liabilities": 8000000.0,
            "current_assets": 6000000.0,
            "current_liabilities": 3000000.0,
            "inventory": 1500000.0,
        }
    }
)
db.add(doc)
db.add(fin)
db.commit()

resp = client.post(f"/api/v1/analysis/{doc_id}/ratios")
print("POST /api/v1/analysis/{document_id}/ratios Status:", resp.status_code)
print("COMPLETE HTTP RESPONSE BODY:")
print(json.dumps(resp.json(), indent=2))

print("\\n==================================================")
print("SECTION 3: ERROR & EDGE CASES")
print("==================================================")
r_404 = client.post(f"/api/v1/analysis/{uuid.uuid4()}/ratios")
print("A. Nonexistent Document Status:", r_404.status_code, "Body:", r_404.json())

unnorm_id = str(uuid.uuid4())
unnorm_doc = Document(
    id=unnorm_id,
    filename="raw_ratio.pdf",
    file_type="pdf",
    file_path="uploads/raw_ratio.pdf",
    status=DocumentStatus.UPLOADED.value
)
db.add(unnorm_doc)
db.commit()
r_400 = client.post(f"/api/v1/analysis/{unnorm_id}/ratios")
print("B. Unnormalized Document Status:", r_400.status_code, "Body:", r_400.json())

# Zero denominator
zero_id = str(uuid.uuid4())
zero_doc = Document(
    id=zero_id,
    filename="zero_rev_ratio.csv",
    file_type="csv",
    file_path="uploads/zero_rev_ratio.csv",
    status=DocumentStatus.NORMALIZED.value
)
zero_fin = FinancialData(
    id=str(uuid.uuid4()),
    document_id=zero_id,
    company_name="Zero Rev Ltd",
    currency="USD",
    revenue=0.0,
    assets=10000000.0,
    liabilities=4000000.0,
    equity=6000000.0,
    normalized_data={
        "document_id": zero_id,
        "financial_data": {
            "revenue": 0.0,
            "gross_profit": 500000.0,
            "assets": 10000000.0,
            "equity": 6000000.0,
        }
    }
)
db.add(zero_doc)
db.add(zero_fin)
db.commit()
r_zero = client.post(f"/api/v1/analysis/{zero_id}/ratios")
print("C. Zero Revenue GPM Status:", r_zero.status_code, "GPM:", r_zero.json()["ratio_analysis"]["ratios"]["profitability"]["gross_profit_margin"])

print("\\n==================================================")
print("SECTION 4: SWAGGER & OPENAPI DOCUMENTATION")
print("==================================================")
r_docs = client.get("/docs")
r_openapi = client.get("/openapi.json")
print("GET /docs Status:", r_docs.status_code)
print("GET /openapi.json Status:", r_openapi.status_code)
paths = r_openapi.json().get("paths", {})
has_ratios = "/api/v1/analysis/{document_id}/ratios" in paths
print("Ratios Endpoint in OpenAPI:", has_ratios)

print("\\n==================================================")
print("SECTION 5: DATABASE PERSISTENCE VERIFICATION")
print("==================================================")
db.refresh(fin)
stored_norm = fin.normalized_data or {}
ratios_block = stored_norm.get("analysis", {}).get("ratios")
print("Persisted in financial_data.normalized_data['analysis']['ratios']:")
print(json.dumps(ratios_block, indent=2))

print("\\nALL RATIOS VERIFICATION STEPS COMPLETED!")
'''
Path("verify_ratio_api.py").write_text(ratio_api_script, encoding="utf-8")
print("verify_ratio_api.py created successfully.")
