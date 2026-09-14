import logging
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.security import get_optional_user
from app.database.database import get_db
from app.models.document import Document, DocumentStatus
from app.models.financial_data import FinancialData
from app.models.user import User
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
from app.schemas.agent1 import Agent1Response
from app.services.analytics.yoy_analyzer import YoYAnalyzer
from app.services.analytics.ratio_analyzer import RatioAnalyzer
from app.api.common import get_normalized_document_and_record, persist_analysis_section

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
def analyze_yoy(document_id: str, db: Session = Depends(get_db), user: Optional[User] = Depends(get_optional_user)):
    # 1. Validate UUID, document state, and retrieve records with authorization check
    doc, fin_record = get_normalized_document_and_record(document_id, db, user)

    norm_data = dict(fin_record.normalized_data or {})
    period_dict = norm_data.get("period", {}) if isinstance(norm_data.get("period"), dict) else {}
    current_period_str = fin_record.fiscal_year or fin_record.period_end or period_dict.get("fiscal_year") or period_dict.get("end") or "Current"
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
            cand_list = []
            for rec in other_records:
                rec_period = rec.fiscal_year or rec.period_end
                if rec_period:
                    cand_list.append((YoYAnalyzer.parse_period_sort_key(rec_period), rec_period, rec))

            cur_key = YoYAnalyzer.parse_period_sort_key(current_period_str)
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
                later_cands = [c for c in cand_list if c[0] > cur_key and c[0] != (0, 0)]
                if later_cands:
                    later_cands.sort(key=lambda x: x[0])
                    _, next_period_str, next_rec = later_cands[0]
                    previous_period_str = current_period_str
                    previous_metrics = current_metrics
                    current_period_str = next_period_str
                    current_metrics = {
                        "revenue": next_rec.revenue,
                        "assets": next_rec.assets,
                        "liabilities": next_rec.liabilities,
                        "equity": next_rec.equity,
                    }

    # 2. Check if we have two comparable periods
    if not previous_metrics or not previous_period_str:
        insufficient_res = {
            "status": "INSUFFICIENT_DATA",
            "periods": None,
            "financial_data": {},
            "warnings": ["At least two financial periods are required for YoY analysis"],
            "reason": "At least two financial periods are required for YoY analysis"
        }
        persist_analysis_section(
            fin_record=fin_record,
            db=db,
            section_key="yoy",
            section_data=insufficient_res,
            document_id=doc.id
        )
        return YoYAnalysisResponse(
            document_id=doc.id,
            yoy_analysis=YoYAnalysisData(**insufficient_res)
        )

    # 3. Perform YoY Analysis
    yoy_result = YoYAnalyzer.analyze_periods(
        previous_period=previous_period_str,
        current_period=current_period_str,
        previous_metrics=previous_metrics,
        current_metrics=current_metrics,
    )

    # 4. Safely and atomically persist YoY outcome
    persist_analysis_section(
        fin_record=fin_record,
        db=db,
        section_key="yoy",
        section_data=yoy_result,
        document_id=doc.id
    )

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
def compute_ratios(document_id: str, db: Session = Depends(get_db), user: Optional[User] = Depends(get_optional_user)):
    # 1. Validate UUID, document state, and retrieve records with authorization check
    doc, fin_record = get_normalized_document_and_record(document_id, db, user)

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

    # 2. Compute ratios
    ratio_result = RatioAnalyzer.analyze_ratios(metrics)

    # 3. Safely and atomically persist ratios outcome
    persist_analysis_section(
        fin_record=fin_record,
        db=db,
        section_key="ratios",
        section_data=ratio_result,
        document_id=doc.id
    )

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


@router.post(
    "/{document_id}/agent1",
    response_model=Agent1Response,
    summary="Execute Agent 1 Financial Validation & Analytics (Analysis namespace alias)",
    description=(
        "Orchestrates financial validation, YoY analysis, and financial ratios "
        "into a single consolidated Agent 1 response for a normalized document."
    )
)
def execute_agent1_alias(document_id: str, db: Session = Depends(get_db), user: Optional[User] = Depends(get_optional_user)):
    from app.api.routes.agent1 import execute_agent1
    return execute_agent1(document_id=document_id, db=db, user=user)
