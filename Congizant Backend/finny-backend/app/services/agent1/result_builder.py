import logging
import math
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session

from app.models.financial_data import FinancialData
from app.models.document import Document, DocumentStatus
from app.services.validation.math_validator import MathValidator
from app.services.analytics.yoy_analyzer import YoYAnalyzer
from app.services.analytics.ratio_analyzer import RatioAnalyzer

logger = logging.getLogger(__name__)


def _sanitize_json(obj: Any) -> Any:
    """Recursively clean dictionary / list to ensure standard JSON compliance (no NaN/inf)."""
    if isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return None
        return obj
    elif isinstance(obj, dict):
        return {k: _sanitize_json(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_sanitize_json(x) for x in obj]
    return obj


class Agent1ResultBuilder:
    """Orchestration service for Agent 1 — Financial Validation & Analytics.
    
    Consolidates:
      1. Mathematical Validation (Balance sheet equation)
      2. YoY Growth Analysis
      3. Financial Ratios (Liquidity, Profitability, Leverage)
      
    This orchestrator delegates to existing services without duplicating
    any mathematical or accounting calculation logic.
    """

    @classmethod
    def build_from_data(
        cls,
        document_id: str,
        current_metrics: Dict[str, Any],
        previous_metrics: Optional[Dict[str, Any]] = None,
        current_period: Optional[str] = None,
        previous_period: Optional[str] = None,
        tolerance: float = 0.01,
    ) -> Dict[str, Any]:
        """Build consolidated Agent 1 analytical results from in-memory metrics.
        
        Args:
            document_id: Unique document identifier
            current_metrics: Financial fields for the current period
            previous_metrics: Financial fields for the previous period (optional)
            current_period: Label for current reporting period (e.g. '2024-25')
            previous_period: Label for previous reporting period (e.g. '2023-24')
            tolerance: Comparison tolerance for balance sheet validation
            
        Returns:
            Dict[str, Any] matching the Agent1Response structure.
        """
        try:
            # Helper to extract clean float or None
            def get_val(m: Dict[str, Any], key: str, alt_key: Optional[str] = None) -> Optional[float]:
                v = m.get(key)
                if (v is None or str(v).strip() == "") and alt_key:
                    v = m.get(alt_key)
                if v is not None and str(v).strip() != "":
                    try:
                        return float(v)
                    except (ValueError, TypeError):
                        return None
                return None

            assets = get_val(current_metrics, "assets")
            liabilities = get_val(current_metrics, "liabilities")
            equity = get_val(current_metrics, "equity")

            # 1. Delegate to MathValidator (Step 2.1)
            math_result = MathValidator.validate_balance_sheet(
                assets=assets,
                liabilities=liabilities,
                equity=equity,
                tolerance=tolerance,
            )

            # 2. Delegate to YoYAnalyzer (Step 2.2)
            if previous_period and current_period and previous_metrics:
                yoy_result = YoYAnalyzer.analyze_periods(
                    previous_period=previous_period,
                    current_period=current_period,
                    previous_metrics=previous_metrics,
                    current_metrics=current_metrics,
                )
            else:
                yoy_result = {
                    "status": "INSUFFICIENT_DATA",
                    "periods": None,
                    "financial_data": {},
                    "warnings": ["At least two financial periods are required for YoY analysis"],
                    "reason": "At least two financial periods are required for YoY analysis",
                }

            # 3. Delegate to RatioAnalyzer (Step 2.3)
            ratio_result = RatioAnalyzer.analyze_ratios(current_metrics)

            # 4. Aggregate Warnings & Notices (Deduplicated, order-preserving)
            warnings: List[str] = []
            seen_warnings = set()

            def add_warning(w: Optional[str]):
                if w and str(w).strip():
                    msg = str(w).strip()
                    if msg not in seen_warnings:
                        seen_warnings.add(msg)
                        warnings.append(msg)

            # Math warnings
            if math_result.get("status") in ("INVALID", "INCOMPLETE") and math_result.get("reason"):
                add_warning(f"math_validation: {math_result['reason']}")

            # YoY warnings
            for yw in yoy_result.get("warnings", []):
                add_warning(yw)
            if yoy_result.get("status") != "COMPLETED" and yoy_result.get("reason"):
                add_warning(f"yoy_analysis: {yoy_result['reason']}")

            # Ratio warnings
            for rw in ratio_result.get("warnings", []):
                add_warning(rw)
            if ratio_result.get("status") != "COMPLETED" and ratio_result.get("reason"):
                add_warning(f"financial_ratios: {ratio_result['reason']}")

            # 5. Determine Overall Agent 1 Status
            math_ok = (math_result.get("status") == "VALID")
            yoy_ok = (yoy_result.get("status") == "COMPLETED")
            ratios_ok = (ratio_result.get("status") == "COMPLETED")

            if math_ok and yoy_ok and ratios_ok:
                overall_status = "COMPLETED"
                overall_reason = None
            else:
                overall_status = "PARTIAL"
                reasons_list = []
                if not math_ok:
                    reasons_list.append(f"Math validation is {math_result.get('status', 'INCOMPLETE')}")
                if not yoy_ok:
                    reasons_list.append(f"YoY analysis is {yoy_result.get('status', 'INCOMPLETE')}")
                if not ratios_ok:
                    reasons_list.append(f"Financial ratios is {ratio_result.get('status', 'INCOMPLETE')}")
                overall_reason = f"Partial analysis completed: {', '.join(reasons_list)}."

            payload = {
                "document_id": document_id,
                "agent": "Agent 1",
                "status": overall_status,
                "results": {
                    "math_validation": math_result,
                    "yoy_analysis": yoy_result,
                    "financial_ratios": ratio_result,
                },
                "warnings": warnings,
                "reason": overall_reason,
            }

            return _sanitize_json(payload)

        except Exception as exc:
            logger.exception("Agent 1 Result Builder execution failed for doc %s: %s", document_id, exc)
            return {
                "document_id": document_id,
                "agent": "Agent 1",
                "status": "FAILED",
                "results": {
                    "math_validation": {
                        "assets": None, "liabilities": None, "equity": None,
                        "liabilities_plus_equity": None, "difference": None,
                        "tolerance": tolerance, "is_valid": None,
                        "status": "INCOMPLETE", "reason": "Execution failed"
                    },
                    "yoy_analysis": {
                        "status": "INSUFFICIENT_DATA", "periods": None,
                        "financial_data": {}, "warnings": [], "reason": "Execution failed"
                    },
                    "financial_ratios": {
                        "status": "INCOMPLETE", "ratios": {
                            "liquidity": {"current_ratio": {"value": None, "status": "INCOMPLETE", "reason": None}, "quick_ratio": {"value": None, "status": "INCOMPLETE", "reason": None}},
                            "profitability": {
                                "gross_profit_margin": {"value": None, "status": "INCOMPLETE", "reason": None},
                                "net_profit_margin": {"value": None, "status": "INCOMPLETE", "reason": None},
                                "return_on_assets": {"value": None, "status": "INCOMPLETE", "reason": None},
                                "return_on_equity": {"value": None, "status": "INCOMPLETE", "reason": None},
                            },
                            "leverage": {"debt_to_equity": {"value": None, "status": "INCOMPLETE", "reason": None}, "debt_ratio": {"value": None, "status": "INCOMPLETE", "reason": None}},
                        },
                        "warnings": [], "reason": "Execution failed"
                    },
                },
                "warnings": [f"System error during analysis: {str(exc)}"],
                "reason": f"Agent 1 processing failed: {str(exc)}",
            }

    @classmethod
    def build_from_record(
        cls,
        document_id: str,
        fin_record: FinancialData,
        db: Optional[Session] = None,
    ) -> Dict[str, Any]:
        """Build Agent 1 result from a FinancialData database record, resolving periods dynamically."""
        norm_data = dict(fin_record.normalized_data or {})
        period_dict = norm_data.get("period", {}) if isinstance(norm_data.get("period"), dict) else {}
        current_period_str = fin_record.fiscal_year or fin_record.period_end or period_dict.get("fiscal_year") or period_dict.get("end") or "Current"

        current_metrics: Dict[str, Any] = {
            "revenue": fin_record.revenue,
            "assets": fin_record.assets,
            "liabilities": fin_record.liabilities,
            "equity": fin_record.equity,
        }
        if "financial_data" in norm_data and isinstance(norm_data["financial_data"], dict):
            for k, v in norm_data["financial_data"].items():
                if k not in current_metrics or current_metrics[k] is None:
                    current_metrics[k] = v

        previous_period_str = None
        previous_metrics = None

        # 1. Check embedded previous period data
        if "previous_period_data" in norm_data and isinstance(norm_data["previous_period_data"], dict):
            prev_dict = norm_data["previous_period_data"]
            previous_period_str = prev_dict.get("period") or prev_dict.get("fiscal_year") or "Previous"
            previous_metrics = prev_dict.get("financial_data") or prev_dict

        # 2. Check DB for multi-period records of the same company
        if (not previous_metrics or not previous_period_str) and fin_record.company_name and db is not None:
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

        return cls.build_from_data(
            document_id=document_id,
            current_metrics=current_metrics,
            previous_metrics=previous_metrics,
            current_period=current_period_str,
            previous_period=previous_period_str,
        )
