import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import get_optional_user
from app.database.database import get_db
from app.models.user import User
from app.schemas.agent1 import Agent1Response, Agent1Results
from app.schemas.findings import Agent1FindingsResponse
from app.schemas.validation import BalanceSheetCheckResult
from app.schemas.analysis import (
    YoYAnalysisData,
    FieldYoYResult,
    PeriodsInfo,
    RatioAnalysisData,
    RatiosData,
    LiquidityRatios,
    ProfitabilityRatios,
    LeverageRatios,
    RatioResult,
)
from app.services.agent1.result_builder import Agent1ResultBuilder
from app.services.agent1.findings_builder import FindingsBuilder
from app.services.ml.anomaly_detector import AnomalyDetector
from app.services.ml.anomaly_result_builder import AnomalyResultBuilder
from app.api.common import (
    get_normalized_document_and_record,
    persist_analysis_section,
    persist_ml_section,
)

router = APIRouter()
logger = logging.getLogger(__name__)
anomaly_detector = AnomalyDetector()


def build_agent1_response(doc_id: str, agent1_dict: dict) -> Agent1Response:
    res = agent1_dict.get("results", {})
    math_dict = res.get("math_validation") or agent1_dict.get("validation", {}).get("balance_sheet_check", {})
    y = res.get("yoy_analysis") or agent1_dict.get("yoy_analysis", {})
    ratios_dict = res.get("financial_ratios") or agent1_dict.get("financial_ratios", {})

    math_model = BalanceSheetCheckResult(**math_dict)

    formatted_fin_data = {
        k: FieldYoYResult(**v_item) for k, v_item in y.get("financial_data", {}).items()
    }
    periods_data = PeriodsInfo(**y["periods"]) if y.get("periods") else None

    yoy_model = YoYAnalysisData(
        status=y["status"],
        periods=periods_data,
        financial_data=formatted_fin_data,
        warnings=y.get("warnings", []),
        reason=y.get("reason"),
    )

    r = ratios_dict.get("ratios", {})
    ratio_model = RatioAnalysisData(
        status=ratios_dict.get("status", "INCOMPLETE"),
        ratios=RatiosData(
            liquidity=LiquidityRatios(
                current_ratio=RatioResult(**r["liquidity"]["current_ratio"]) if "liquidity" in r and "current_ratio" in r["liquidity"] else None,
                quick_ratio=RatioResult(**r["liquidity"]["quick_ratio"]) if "liquidity" in r and "quick_ratio" in r["liquidity"] else None,
            ),
            profitability=ProfitabilityRatios(
                gross_profit_margin=RatioResult(**r["profitability"]["gross_profit_margin"]) if "profitability" in r and "gross_profit_margin" in r["profitability"] else None,
                net_profit_margin=RatioResult(**r["profitability"]["net_profit_margin"]) if "profitability" in r and "net_profit_margin" in r["profitability"] else None,
                return_on_assets=RatioResult(**r["profitability"]["return_on_assets"]) if "profitability" in r and "return_on_assets" in r["profitability"] else None,
                return_on_equity=RatioResult(**r["profitability"]["return_on_equity"]) if "profitability" in r and "return_on_equity" in r["profitability"] else None,
            ),
            leverage=LeverageRatios(
                debt_to_equity=RatioResult(**r["leverage"]["debt_to_equity"]) if "leverage" in r and "debt_to_equity" in r["leverage"] else None,
                debt_ratio=RatioResult(**r["leverage"]["debt_ratio"]) if "leverage" in r and "debt_ratio" in r["leverage"] else None,
            ),
        ),
        warnings=ratios_dict.get("warnings", []),
        reason=ratios_dict.get("reason"),
    )

    return Agent1Response(
        document_id=doc_id,
        agent=agent1_dict.get("agent", "Agent 1"),
        status=agent1_dict.get("status", "COMPLETED"),
        results=Agent1Results(
            math_validation=math_model,
            yoy_analysis=yoy_model,
            financial_ratios=ratio_model,
        ),
        warnings=agent1_dict.get("warnings", []),
        reason=agent1_dict.get("reason"),
    )


@router.post(
    "/{document_id}",
    response_model=Agent1Response,
    summary="Execute Agent 1 Financial Validation & Analytics",
    description=(
        "Orchestrates financial validation, YoY analysis, and financial ratios "
        "into a single consolidated Agent 1 response for a normalized document."
    )
)
def execute_agent1(document_id: str, db: Session = Depends(get_db), user: Optional[User] = Depends(get_optional_user)):
    # 1. Validate UUID, document state, and retrieve records with authorization check
    doc, fin_record = get_normalized_document_and_record(document_id, db, user)

    # 2. Orchestrate Agent 1 results using existing services
    agent1_result = Agent1ResultBuilder.build_from_record(
        document_id=doc.id,
        fin_record=fin_record,
        db=db,
    )

    # 3. Safely and atomically persist Agent 1 outcome
    persist_analysis_section(
        fin_record=fin_record,
        db=db,
        section_key="agent1",
        section_data=agent1_result,
        document_id=doc.id
    )

    return build_agent1_response(doc.id, agent1_result)


@router.post(
    "/{document_id}/findings",
    response_model=Agent1FindingsResponse,
    summary="Consolidate Agent 1 Findings & ML Anomaly Detection",
    description=(
        "Produces consolidated, deterministic Agent 1 findings (validations, variances, "
        "anomalies, ratios, evidence) without recalculation. If prerequisites are not yet "
        "present, triggers prerequisite generation automatically."
    )
)
def execute_agent1_findings(document_id: str, db: Session = Depends(get_db), user: Optional[User] = Depends(get_optional_user)):
    # 1. Validate UUID, document existence, and NORMALIZED status with authorization check
    doc, fin_record = get_normalized_document_and_record(document_id, db, user)

    norm_data = dict(fin_record.normalized_data or {})
    analysis = dict(norm_data.get("analysis", {}) or {})
    agent1_data = analysis.get("agent1")

    # 2. Ensure Agent 1 analytics exist
    if not agent1_data:
        try:
            agent1_data = Agent1ResultBuilder.build_from_record(
                document_id=doc.id,
                fin_record=fin_record,
                db=db,
            )
            persist_analysis_section(
                fin_record=fin_record,
                db=db,
                section_key="agent1",
                section_data=agent1_data,
                document_id=doc.id
            )
            norm_data = dict(fin_record.normalized_data or {})
            analysis = dict(norm_data.get("analysis", {}) or {})
        except Exception as a1_err:
            logger.error("Failed to build prerequisite Agent 1 data for doc %s: %s", doc.id, a1_err)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to generate prerequisite Agent 1 analytics: {str(a1_err)}"
            )

    # 3. Ensure ML anomaly detection exists
    ml_data = norm_data.get("ml_anomaly")
    if not ml_data:
        try:
            raw_ml_result = anomaly_detector.detect_anomalies(
                agent1_data=agent1_data,
                document_id=doc.id
            )
            ml_data = AnomalyResultBuilder.build_result(
                document_id=doc.id,
                inference_output=raw_ml_result
            )
            persist_ml_section(
                fin_record=fin_record,
                db=db,
                ml_data=ml_data,
                document_id=doc.id
            )
            norm_data = dict(fin_record.normalized_data or {})
        except Exception as ml_err:
            logger.warning("Could not auto-generate ML anomaly for doc %s: %s", doc.id, ml_err)
            # Do not fail findings if ML fails; findings builder will mark ML as missing/incomplete

    # 4. Build consolidated deterministic findings
    try:
        findings_result = FindingsBuilder.build_findings(
            document_id=doc.id,
            norm_data=norm_data,
        )
    except Exception as f_err:
        logger.exception("Failed to build findings for doc %s: %s", doc.id, f_err)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to build findings: {str(f_err)}"
        )

    # 5. Atomically persist findings under normalized_data['analysis']['agent1_findings']
    persist_analysis_section(
        fin_record=fin_record,
        db=db,
        section_key="agent1_findings",
        section_data=findings_result,
        document_id=doc.id
    )

    return Agent1FindingsResponse(**findings_result)
