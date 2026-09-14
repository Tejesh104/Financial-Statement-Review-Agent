"""Review Observations Builder service (Step 4.2).

Consolidates verified Agent 1 Findings and Agent 2 Review into clean,
structured review observations:
  - finding
  - explanation
  - severity (LOW, MEDIUM, HIGH, CRITICAL)
  - evidence
  - recommendation
"""

import json
import logging
import math
import re
from typing import Dict, Any, List, Optional

from app.core.config import settings
from app.services.agent2.ollama_client import (
    OllamaClient,
    OllamaUnavailableException,
    OllamaTimeoutException,
    OllamaMalformedResponseException,
)
from app.schemas.review_observations import (
    ReviewObservation,
    ObservationEvidenceItem,
    ReviewObservationsResponse,
)

logger = logging.getLogger(__name__)

OBSERVATIONS_SYSTEM_PROMPT = """You are a Financial Review Explanation Agent.
You receive verified financial findings and deterministic severity ratings from backend accounting services.

Your job is to generate for each verified finding:
1. "finding": Brief, exact statement of the verified finding.
2. "explanation": 1-2 factual sentences explaining why this finding occurred based strictly on the provided evidence.
3. "recommendation": A factual, review-oriented, non-prescriptive recommendation (e.g., "Review the revenue movement against the underlying financial statements" or "Investigate the balance-sheet imbalance").

STRICT RULES:
- NEVER invent financial numbers, missing values, or new ratios.
- NEVER modify or recalculate any verified number.
- NEVER provide stock tips, investment advice, buy/sell recommendations, or portfolio suggestions.
- NEVER claim fraud, manipulation, insolvency, or misconduct without explicit verified mathematical proof.
- Return ONLY valid JSON matching this exact structure:
{
  "observations": [
    {
      "finding": "Exact finding statement",
      "explanation": "Clear factual explanation citing provided evidence.",
      "recommendation": "Review-oriented next step for the reviewer."
    }
  ],
  "summary": "Short high-level summary of the overall review."
}
"""


def _clean_json(obj: Any) -> Any:
    """Recursively clean dict/list of NaN and Inf."""
    if isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return None
        return obj
    elif isinstance(obj, dict):
        return {k: _clean_json(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_clean_json(v) for v in obj]
    return obj


class ReviewObservationsBuilder:
    """Builder for the Review Observations layer."""

    @classmethod
    def determine_severity(
        cls,
        category: str,
        status: str,
        extra_info: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Deterministic severity assignment based on verified finding characteristics.

        Rules:
          - Math validation INVALID -> CRITICAL (fundamental balance sheet imbalance)
          - Math validation INCOMPLETE -> MEDIUM
          - ML Anomaly -> HIGH (statistically unusual multi-metric distribution)
          - Negative YoY growth / contraction -> MEDIUM
          - Incomplete or undefined ratios -> MEDIUM
          - Valid math / Positive growth / Normal ML / Healthy ratio -> LOW
        """
        extra = extra_info or {}
        cat_upper = category.upper()
        status_upper = status.upper()

        if cat_upper == "VALIDATION":
            if status_upper == "INVALID":
                return "CRITICAL"
            elif status_upper == "INCOMPLETE":
                return "MEDIUM"
            return "LOW"

        if cat_upper == "ML_ANOMALY":
            if status_upper == "ANOMALY" or extra.get("is_anomaly") is True:
                return "HIGH"
            return "LOW"

        if cat_upper == "YOY":
            direction = str(extra.get("direction", "")).lower()
            if direction == "negative":
                return "MEDIUM"
            elif status_upper != "COMPLETED":
                return "MEDIUM"
            return "LOW"

        if cat_upper == "RATIO":
            if status_upper in ("UNDEFINED", "INCOMPLETE"):
                return "MEDIUM"
            return "LOW"

        return "LOW"

    @classmethod
    def generate_fallback_recommendation(cls, category: str, status: str, target: str) -> str:
        """Deterministic fallback recommendation if LLM is omitted or produces invalid text."""
        cat = category.upper()
        stat = status.upper()
        if cat == "VALIDATION":
            if stat == "INVALID":
                return "Review the balance-sheet inconsistency and verify underlying assets, liabilities, and equity line items."
            return "Retain balance sheet reconciliation records for standard accounting audit."
        elif cat == "YOY":
            if stat == "COMPLETED":
                return f"Review the {target} movement and monitor underlying operational drivers in subsequent periods."
            return f"Verify prior period reporting records to enable full multi-period comparison for {target}."
        elif cat == "ML_ANOMALY":
            if stat == "ANOMALY":
                return "Investigate the statistically unusual multi-ratio combination against industry norms and reporting context."
            return "Continue standard periodic monitoring of financial ratio profile."
        elif cat == "RATIO":
            if stat == "UNDEFINED":
                return f"Verify whether the zero denominator for {target} reflects operational inactivity or reporting omission."
            return f"Assess {target} against benchmark thresholds and review in subsequent reporting periods."
        return "Review the reported metric against the primary financial statement schedules."

    @classmethod
    def build_observations(
        cls,
        document_id: str,
        findings_data: Dict[str, Any],
        agent2_data: Optional[Dict[str, Any]] = None,
        ollama_client: Optional[OllamaClient] = None,
    ) -> Dict[str, Any]:
        """Compile final structured review observations.

        Args:
            document_id: UUID of document.
            findings_data: Agent 1 Findings dictionary (or normalized_data["analysis"]["agent1_findings"]).
            agent2_data: Agent 2 Review dictionary (or normalized_data["analysis"]["agent2"]).
            ollama_client: Injected OllamaClient.

        Returns:
            Dict conforming to ReviewObservationsResponse schema.
        """
        client = ollama_client or OllamaClient()
        findings = findings_data.get("findings", findings_data)
        warnings: List[str] = list(findings_data.get("warnings", []))
        if agent2_data and "warnings" in agent2_data:
            for w in agent2_data["warnings"]:
                if w not in warnings:
                    warnings.append(w)

        # 1. Gather Candidate Observations from Verified Findings
        candidates: List[Dict[str, Any]] = []

        # (a) Math Validation
        for val in findings.get("validations", []):
            v_status = val.get("status", "INCOMPLETE")
            is_valid = val.get("is_valid")
            diff = val.get("difference")
            tol = val.get("tolerance")
            diff_val = f"{diff:,.2f}" if diff is not None else "0.00"
            
            if v_status == "VALID":
                finding_str = f"Balance sheet equation balances (Assets = Liabilities + Equity) within tolerance {tol}."
                notes_str = f"Valid equation (difference: {diff_val})"
            elif v_status == "INVALID":
                finding_str = f"Balance sheet equation does not balance. Imbalance difference is {diff_val}."
                notes_str = f"Invalid equation (difference: {diff_val}, tolerance: {tol})"
            else:
                finding_str = "Balance sheet validation could not be completed due to missing values."
                notes_str = "Incomplete validation data"

            ev_item = {
                "field": "balance_sheet_check",
                "source": "validation",
                "value": diff,
                "current_value": None,
                "previous_value": None,
                "notes": notes_str,
            }
            severity = cls.determine_severity("VALIDATION", v_status)
            candidates.append({
                "category": "VALIDATION",
                "target": "balance_sheet",
                "finding": finding_str,
                "severity": severity,
                "status": v_status,
                "evidence": [ev_item],
            })

        # (b) YoY Variances
        for var in findings.get("variances", []):
            field = var.get("field", "metric")
            status = var.get("status", "COMPLETED")
            cur_val = var.get("current_value")
            prev_val = var.get("previous_value")
            pct_chg = var.get("percentage_change")
            direction = var.get("direction", "unchanged")
            field_name = field.replace("_", " ").title()

            if status == "COMPLETED":
                pct_str = f"{pct_chg:+.2f}%" if pct_chg is not None else "0.00%"
                finding_str = f"{field_name} changed by {pct_str} year-over-year ({direction} trend)."
            else:
                finding_str = f"Year-over-year analysis for {field_name} is {status}."

            ev_item = {
                "field": field,
                "source": "analysis.yoy",
                "value": cur_val,
                "current_value": cur_val,
                "previous_value": prev_val,
                "notes": f"Percentage change: {pct_chg}%, Direction: {direction}",
            }
            severity = cls.determine_severity("YOY", status, {"direction": direction})
            candidates.append({
                "category": "YOY",
                "target": field,
                "finding": finding_str,
                "severity": severity,
                "status": status,
                "evidence": [ev_item],
            })

        # (c) ML Anomaly Detection
        for anom in findings.get("anomalies", []):
            is_anom = anom.get("is_anomaly", False)
            score = anom.get("anomaly_score", 0.0)
            status = anom.get("status", "COMPLETED")
            cls_name = anom.get("classification", "NORMAL")

            if is_anom or cls_name == "ANOMALY":
                finding_str = f"Isolation Forest flagged statistical anomaly with score {score:.4f} (< 0 threshold)."
                notes_str = "Statistically unusual relative to training distribution"
            else:
                finding_str = f"Isolation Forest statistical normality confirmed with score {score:.4f} (>= 0 threshold)."
                notes_str = "Conforms to expected training distribution"

            ev_item = {
                "field": "isolation_forest",
                "source": "ml_anomaly",
                "value": score,
                "current_value": score,
                "previous_value": None,
                "notes": notes_str,
            }
            severity = cls.determine_severity("ML_ANOMALY", cls_name, {"is_anomaly": is_anom})
            candidates.append({
                "category": "ML_ANOMALY",
                "target": "statistical_anomaly",
                "finding": finding_str,
                "severity": severity,
                "status": cls_name,
                "evidence": [ev_item],
            })

        # (d) Key Ratios
        for r in findings.get("ratios", []):
            name = r.get("name", "ratio")
            cat = r.get("category", "general")
            val = r.get("value")
            status = r.get("status", "COMPLETED")
            ratio_name = name.replace("_", " ").title()

            if status == "COMPLETED" and val is not None:
                val_display = f"{val:.2f}%" if ("margin" in name or "return" in name) else f"{val:.2f}"
                finding_str = f"{ratio_name} ({cat}) is {val_display}."
                notes_str = f"Computed value: {val_display}"
            elif status == "UNDEFINED":
                finding_str = f"{ratio_name} ({cat}) is undefined due to zero denominator."
                notes_str = "Zero denominator encountered"
            else:
                finding_str = f"{ratio_name} ({cat}) could not be calculated due to missing inputs."
                notes_str = "Missing input data"

            ev_item = {
                "field": name,
                "source": "analysis.ratios",
                "value": val,
                "current_value": val,
                "previous_value": None,
                "notes": notes_str,
            }
            severity = cls.determine_severity("RATIO", status)
            candidates.append({
                "category": "RATIO",
                "target": name,
                "finding": finding_str,
                "severity": severity,
                "status": status,
                "evidence": [ev_item],
            })

        # 2. Prepare Context for Ollama Explanation Generation
        # Sort candidates to prioritize CRITICAL and HIGH severity first, taking top 3-6 items
        severity_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
        candidates.sort(key=lambda c: severity_order.get(c["severity"], 4))
        selected_candidates = candidates[:6] if candidates else []

        llm_input_items = []
        for c in selected_candidates:
            llm_input_items.append({
                "category": c["category"],
                "finding": c["finding"],
                "severity": c["severity"],
                "evidence_notes": [e.get("notes") for e in c["evidence"] if e.get("notes")],
            })

        prompt_context = {
            "document_id": document_id,
            "findings_for_review": llm_input_items,
        }

        user_prompt = (
            "Explain the verified findings below and provide a factual, review-oriented recommendation for each.\n\n"
            f"FINDINGS CONTEXT:\n{json.dumps(prompt_context, separators=(',', ':'))}\n"
        )

        # 3. Call Ollama for Explanations and Recommendations (or reuse agent2_data if available)
        llm_explanations: Dict[str, Dict[str, str]] = {}
        overall_summary = "Review observations compiled from verified analytical pipeline."

        has_agent2_obs = False
        if agent2_data and isinstance(agent2_data.get("observations"), list) and len(agent2_data["observations"]) > 0:
            has_agent2_obs = True
            overall_summary = agent2_data.get("summary") or overall_summary
            for idx, obs in enumerate(agent2_data["observations"]):
                rec_text = obs.get("recommendation", "") if isinstance(obs, dict) else getattr(obs, "recommendation", "") or ""
                expl_text = obs.get("explanation", "") if isinstance(obs, dict) else getattr(obs, "explanation", "") or ""
                finding_str = obs.get("finding", "") if isinstance(obs, dict) else getattr(obs, "finding", "") or ""
                llm_explanations[str(idx)] = {
                    "explanation": expl_text,
                    "recommendation": rec_text,
                }
                if finding_str:
                    llm_explanations[finding_str.strip().lower()] = {
                        "explanation": expl_text,
                        "recommendation": rec_text,
                    }

        if not has_agent2_obs:
            try:
                ollama_resp = client.generate_review(
                    system_prompt=OBSERVATIONS_SYSTEM_PROMPT,
                    context_prompt=user_prompt,
                )
                overall_summary = ollama_resp.summary or overall_summary
                # Map generated explanations by finding text or index
                for idx, obs in enumerate(ollama_resp.observations):
                    # Try matching by index or finding string
                    rec_text = getattr(obs, "recommendation", "") or ""
                    expl_text = obs.explanation or ""
                    f_title = obs.title or f"item_{idx}"
                    llm_explanations[str(idx)] = {
                        "explanation": expl_text,
                        "recommendation": rec_text,
                    }
                    if obs.finding:
                        llm_explanations[obs.finding.strip().lower()] = {
                            "explanation": expl_text,
                            "recommendation": rec_text,
                        }
            except (OllamaUnavailableException, OllamaTimeoutException, OllamaMalformedResponseException):
                raise  # Handled upstream by API router
            except Exception as exc:
                logger.warning("Ollama observation generation encountered unexpected error: %s. Proceeding with grounded defaults.", exc)
                warnings.append(f"Ollama review explanation error: {str(exc)}")

        # 4. Build Final Structured Observations with Strict Grounding Guardrails
        final_observations: List[Dict[str, Any]] = []
        forbidden_terms = [
            "buy this stock", "sell this stock", "strong buy", "strong sell",
            "investment advice", "guaranteed profit", "fraudulent scheme",
            "criminal fraud", "bankrupt company", "insolvent firm"
        ]

        for idx, c in enumerate(selected_candidates):
            # Fetch LLM explanation or fallback
            llm_match = (
                llm_explanations.get(c["finding"].strip().lower())
                or llm_explanations.get(str(idx))
            )

            raw_explanation = llm_match.get("explanation") if llm_match else None
            raw_rec = llm_match.get("recommendation") if llm_match else None

            # Grounding: neutralize forbidden advice or ungrounded fraud assertions
            if raw_explanation:
                if any(term in raw_explanation.lower() for term in forbidden_terms):
                    raw_explanation = "Content sanitized: Review observations do not provide investment advice or unverified allegations."
            else:
                raw_explanation = f"Observation grounded in verified {c['category'].lower()} findings."

            if raw_rec and str(raw_rec).strip():
                if any(term in raw_rec.lower() for term in forbidden_terms):
                    raw_rec = cls.generate_fallback_recommendation(c["category"], c["status"], c["target"])
            else:
                raw_rec = cls.generate_fallback_recommendation(c["category"], c["status"], c["target"])

            obs_obj = {
                "finding": c["finding"],
                "explanation": raw_explanation,
                "severity": c["severity"],  # Deterministic severity prevails
                "evidence": c["evidence"],  # Verified evidence strictly preserved
                "recommendation": raw_rec,
            }
            final_observations.append(obs_obj)

        # 5. Resolve Overall Status
        f_status = findings_data.get("status", "PARTIAL")
        overall_status = "COMPLETED" if f_status == "COMPLETED" and final_observations else "PARTIAL"
        reason = None if overall_status == "COMPLETED" else f"Observations compiled with partial findings (Agent 1 status: {f_status})."

        result_payload = {
            "document_id": document_id,
            "status": overall_status,
            "observations": final_observations,
            "summary": overall_summary,
            "warnings": warnings,
            "reason": reason,
            "model": client.model,
        }

        return _clean_json(result_payload)
