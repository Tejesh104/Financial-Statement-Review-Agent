"""Deterministic findings layer consolidating Agent 1 analytics and ML anomaly detection.

Consolidates:
  1. Validations: Balance Sheet check (Assets = Liabilities + Equity)
  2. Variances: YoY financial variances
  3. Anomalies: Isolation Forest ML anomaly detection findings
  4. Ratios: Canonical financial ratios (Liquidity, Profitability, Leverage)
  5. Evidence: Traceable references pointing to normalized financial data
"""

import logging
import math
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


def _clean_float(val: Any) -> Optional[float]:
    """Convert value to float, replacing NaN/Inf with None."""
    if val is None:
        return None
    try:
        f = float(val)
        if math.isnan(f) or math.isinf(f):
            return None
        return f
    except (ValueError, TypeError):
        return None


def _clean_json_values(obj: Any) -> Any:
    """Recursively clean dict/list of NaN and Inf."""
    if isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return None
        return obj
    elif isinstance(obj, dict):
        return {k: _clean_json_values(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_clean_json_values(v) for v in obj]
    return obj


CANONICAL_EVIDENCE_FIELDS = [
    "revenue",
    "assets",
    "liabilities",
    "equity",
    "current_assets",
    "current_liabilities",
    "inventory",
    "gross_profit",
    "net_profit",
]


class FindingsBuilder:
    """Consolidates existing analytical outputs into a deterministic findings response.

    No financial or ML calculations are performed here; existing outputs are extracted,
    restructured, and verified for consistency and traceability.
    """

    @classmethod
    def build_findings(
        cls,
        document_id: str,
        norm_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Extract and structure findings from normalized document data.

        Args:
            document_id: UUID of document.
            norm_data: Complete normalized_data dictionary from FinancialData.

        Returns:
            Dict matching Agent1FindingsResponse schema.
        """
        warnings: List[str] = []
        seen_warnings = set()

        def add_warning(msg: Optional[str]):
            if msg and str(msg).strip():
                clean_msg = str(msg).strip()
                if clean_msg not in seen_warnings:
                    seen_warnings.add(clean_msg)
                    warnings.append(clean_msg)

        # Retrieve analysis sections
        analysis = norm_data.get("analysis", {}) if isinstance(norm_data.get("analysis"), dict) else {}
        agent1 = analysis.get("agent1", {}) if isinstance(analysis.get("agent1"), dict) else {}
        a1_results = agent1.get("results", {}) if isinstance(agent1.get("results"), dict) else {}

        # -------------------------------------------------------------
        # 1. VALIDATIONS
        # -------------------------------------------------------------
        # Source: norm_data["validation"]["balance_sheet_check"] or a1_results["math_validation"]
        val_source = None
        if "validation" in norm_data and isinstance(norm_data["validation"], dict):
            val_source = norm_data["validation"].get("balance_sheet_check")
        if not val_source:
            val_source = a1_results.get("math_validation")
        if not val_source:
            val_source = analysis.get("validation", {}).get("balance_sheet_check") if isinstance(analysis.get("validation"), dict) else None

        validations: List[Dict[str, Any]] = []
        if val_source and isinstance(val_source, dict):
            status = val_source.get("status", "INCOMPLETE")
            is_valid = val_source.get("is_valid")
            diff = _clean_float(val_source.get("difference"))
            tol = _clean_float(val_source.get("tolerance"))
            reason = val_source.get("reason")
            validations.append({
                "type": "BALANCE_SHEET_VALIDATION",
                "status": status,
                "is_valid": is_valid,
                "difference": diff,
                "tolerance": tol,
                "reason": reason,
            })
            if status != "VALID" and reason:
                add_warning(f"validation: {reason}")
        else:
            validations.append({
                "type": "BALANCE_SHEET_VALIDATION",
                "status": "INCOMPLETE",
                "is_valid": None,
                "difference": None,
                "tolerance": None,
                "reason": "Math validation has not been performed for this document",
            })
            add_warning("validation: Math validation data not found")

        # -------------------------------------------------------------
        # 2. VARIANCES (YoY Analysis)
        # -------------------------------------------------------------
        # Source: analysis["yoy"] or a1_results["yoy_analysis"]
        yoy_source = analysis.get("yoy") or a1_results.get("yoy_analysis")
        variances: List[Dict[str, Any]] = []
        yoy_status = "INSUFFICIENT_DATA"

        if yoy_source and isinstance(yoy_source, dict):
            yoy_status = yoy_source.get("status", "INSUFFICIENT_DATA")
            periods_info = yoy_source.get("periods") if isinstance(yoy_source.get("periods"), dict) else {}
            cur_p = periods_info.get("current") or periods_info.get("current_period")
            prev_p = periods_info.get("previous") or periods_info.get("previous_period")
            if not cur_p and isinstance(norm_data.get("period"), dict):
                cur_p = norm_data["period"].get("fiscal_year") or norm_data["period"].get("end")
            if not prev_p and isinstance(norm_data.get("previous_period_data"), dict):
                prev_p = norm_data["previous_period_data"].get("period") or norm_data["previous_period_data"].get("fiscal_year")

            fin_data = yoy_source.get("financial_data", {})
            if isinstance(fin_data, dict) and fin_data:
                for field_name, f_data in fin_data.items():
                    if isinstance(f_data, dict):
                        variances.append({
                            "field": field_name,
                            "current_period": cur_p,
                            "previous_period": prev_p,
                            "current_value": _clean_float(f_data.get("current")),
                            "previous_value": _clean_float(f_data.get("previous")),
                            "absolute_change": _clean_float(f_data.get("absolute_change")),
                            "percentage_change": _clean_float(f_data.get("percentage_change")),
                            "direction": f_data.get("direction"),
                            "status": f_data.get("status", "COMPLETED"),
                            "reason": f_data.get("reason"),
                        })
            # Aggregate any YoY warnings
            for w in yoy_source.get("warnings", []):
                add_warning(w)
            if yoy_status != "COMPLETED" and yoy_source.get("reason"):
                add_warning(f"yoy_analysis: {yoy_source.get('reason')}")
        else:
            add_warning("yoy_analysis: YoY analysis data not found")

        # -------------------------------------------------------------
        # 3. ANOMALIES (ML Anomaly Detection)
        # -------------------------------------------------------------
        # Source: norm_data["ml_anomaly"]
        ml_source = norm_data.get("ml_anomaly")
        anomalies: List[Dict[str, Any]] = []
        ml_present = False

        if ml_source and isinstance(ml_source, dict):
            ml_present = True
            is_anomaly = bool(ml_source.get("is_anomaly", False))
            score = _clean_float(ml_source.get("score"))
            if score is None:
                score = _clean_float(ml_source.get("anomaly_score", 0.0))
            pred = int(ml_source.get("prediction", 1))
            classification = str(ml_source.get("label") or ml_source.get("classification") or ("ANOMALY" if is_anomaly else "NORMAL"))
            status = ml_source.get("status", "COMPLETED")
            model_info = ml_source.get("model", {}) if isinstance(ml_source.get("model"), dict) else {}
            model_type = model_info.get("type", "IsolationForest")
            ml_warnings = ml_source.get("warnings", [])
            anom_reason = ml_source.get("reason")

            anomalies.append({
                "type": "ML_ANOMALY",
                "classification": classification,
                "is_anomaly": is_anomaly,
                "anomaly_score": score if score is not None else 0.0,
                "prediction": pred,
                "status": status,
                "model_type": model_type,
                "warnings": ml_warnings if isinstance(ml_warnings, list) else [],
                "reason": anom_reason,
            })
            for w in ml_warnings:
                add_warning(f"ml_anomaly: {w}")
        else:
            add_warning("ml_anomaly: ML anomaly detection data not found")

        # -------------------------------------------------------------
        # 4. RATIOS (Financial Ratios)
        # -------------------------------------------------------------
        # Source: analysis["ratios"] or a1_results["financial_ratios"]
        ratio_source = analysis.get("ratios") or a1_results.get("financial_ratios")
        ratios: List[Dict[str, Any]] = []
        ratio_status = "INCOMPLETE"

        if ratio_source and isinstance(ratio_source, dict):
            ratio_status = ratio_source.get("status", "INCOMPLETE")
            raw_ratios = ratio_source.get("ratios", {})
            if isinstance(raw_ratios, dict):
                for cat_name, cat_dict in raw_ratios.items():
                    if isinstance(cat_dict, dict):
                        for ratio_name, r_info in cat_dict.items():
                            if isinstance(r_info, dict):
                                ratios.append({
                                    "name": ratio_name,
                                    "category": cat_name,
                                    "value": _clean_float(r_info.get("value")),
                                    "status": r_info.get("status", "INCOMPLETE"),
                                    "reason": r_info.get("reason"),
                                })
            for w in ratio_source.get("warnings", []):
                add_warning(w)
            if ratio_status != "COMPLETED" and ratio_source.get("reason"):
                add_warning(f"financial_ratios: {ratio_source.get('reason')}")
        else:
            add_warning("financial_ratios: Financial ratios data not found")

        # -------------------------------------------------------------
        # 5. EVIDENCE
        # -------------------------------------------------------------
        # Source: norm_data["financial_data"]
        raw_fin = norm_data.get("financial_data", {}) if isinstance(norm_data.get("financial_data"), dict) else {}
        evidence: List[Dict[str, Any]] = []

        for field in CANONICAL_EVIDENCE_FIELDS:
            has_val = field in raw_fin and raw_fin[field] is not None
            val_cleaned = _clean_float(raw_fin.get(field)) if has_val else None
            is_available = has_val and (val_cleaned is not None or str(raw_fin.get(field)).strip() != "")
            evidence.append({
                "field": field,
                "value": val_cleaned,
                "source": f"normalized_data.financial_data.{field}",
                "is_available": is_available,
            })

        # Also include any additional non-canonical fields present in raw_fin
        for field, raw_v in raw_fin.items():
            if field not in CANONICAL_EVIDENCE_FIELDS:
                val_cleaned = _clean_float(raw_v)
                evidence.append({
                    "field": field,
                    "value": val_cleaned,
                    "source": f"normalized_data.financial_data.{field}",
                    "is_available": raw_v is not None,
                })

        # -------------------------------------------------------------
        # 6. OVERALL STATUS DETERMINATION
        # -------------------------------------------------------------
        # Status is COMPLETED if:
        # - validations is present and status == "VALID"
        # - variances has items and yoy_status == "COMPLETED"
        # - anomalies has items (ML detected)
        # - ratios has items and ratio_status == "COMPLETED"
        # - evidence has items
        # If any section is missing or partially incomplete, overall status is PARTIAL.
        val_ok = any(v.get("status") == "VALID" for v in validations)
        yoy_ok = (yoy_status == "COMPLETED") and len(variances) > 0
        anom_ok = ml_present and len(anomalies) > 0
        ratios_ok = (ratio_status == "COMPLETED") and len(ratios) > 0
        evidence_ok = len(evidence) > 0

        partial_reasons = []
        if not val_ok:
            partial_reasons.append("Math validation is invalid or incomplete")
        if not yoy_ok:
            partial_reasons.append(f"YoY analysis is {yoy_status}")
        if not anom_ok:
            partial_reasons.append("ML anomaly detection not completed")
        if not ratios_ok:
            partial_reasons.append(f"Financial ratios is {ratio_status}")

        if val_ok and yoy_ok and anom_ok and ratios_ok and evidence_ok:
            overall_status = "COMPLETED"
            overall_reason = None
        else:
            overall_status = "PARTIAL"
            overall_reason = f"Partial findings: {', '.join(partial_reasons)}." if partial_reasons else None

        result_dict = {
            "document_id": document_id,
            "status": overall_status,
            "findings": {
                "validations": validations,
                "variances": variances,
                "anomalies": anomalies,
                "ratios": ratios,
                "evidence": evidence,
            },
            "warnings": warnings,
            "reason": overall_reason,
        }

        return _clean_json_values(result_dict)
