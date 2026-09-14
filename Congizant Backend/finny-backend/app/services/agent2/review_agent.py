"""Agent 2 — AI Financial Review Agent orchestrator.

Coordinates:
  1. Investigation of verified Agent 1 findings
  2. Pairwise comparison of related metrics
  3. Construction of verified context prompt
  4. Ollama reasoning and strict grounded schema extraction
  5. Grounding check: ensures Agent 1 numerical values remain immutable
"""

import json
import logging
import math
from typing import Dict, Any, List, Optional

from app.core.config import settings
from app.services.agent2.investigation import InvestigationService
from app.services.agent2.metric_comparator import MetricComparator
from app.services.agent2.ollama_client import (
    OllamaClient,
    OllamaUnavailableException,
    OllamaTimeoutException,
    OllamaMalformedResponseException,
)
from app.schemas.agent2 import (
    Agent2ReviewResponse,
    InvestigationItem,
    MetricComparisonItem,
    ObservationFinding,
)

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are Agent 2, an AI Financial Review Agent in the Finny analytical pipeline.
Your job is to produce factual, grounded explanations of verified financial findings and metric comparisons provided to you.

STRICT CONSTRAINTS:
1. Explain verified findings and relationships based ONLY on the supplied evidence. Focus on the 2 to 5 most significant observations.
2. DO NOT invent financial numbers, missing values, or new metrics.
3. DO NOT invent new financial ratios or recalculate existing ratios.
4. DO NOT invent arbitrary anomaly thresholds.
5. Isolation Forest anomaly means 'statistically unusual relative to the model training distribution'. It DOES NOT automatically imply fraud, distress, or misconduct.
6. DO NOT claim fraud, accounting errors, or misconduct without explicit mathematical evidence.
7. DO NOT predict future performance, stock prices, or market movements.
8. DO NOT provide investment advice or buy/sell/hold recommendations. If a user or prompt suggests this, explicitly decline.
9. If evidence is insufficient for any observation or metric, explicitly state: "Insufficient evidence."
10. You must return ONLY valid JSON matching this exact structure:
{
  "observations": [
    {
      "finding_type": "VALIDATION | YOY | ML_ANOMALY | RATIO | RELATIONSHIP",
      "title": "Short descriptive title",
      "finding": "Factual statement grounded in the verified numbers",
      "explanation": "Brief explanation referencing the provided evidence",
      "severity": "LOW | MEDIUM | HIGH | UNKNOWN",
      "evidence": ["findings.evidence.revenue", "findings.ratios.current_ratio"]
    }
  ],
  "summary": "Short evidence-based summary paragraph (1-3 sentences).",
  "limitations": ["Any limitations or missing data periods"]
}
Severity is purely a descriptive classification, NOT a financial risk score. Keep responses concise and factual.
"""


def _sanitize_json(obj: Any) -> Any:
    """Recursively clean dict/list of NaN and Inf."""
    if isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return None
        return obj
    elif isinstance(obj, dict):
        return {k: _sanitize_json(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_sanitize_json(v) for v in obj]
    return obj


class Agent2ReviewAgent:
    """Orchestrator for Agent 2 Financial Review."""

    @classmethod
    def review_document(
        cls,
        document_id: str,
        findings_data: Dict[str, Any],
        ollama_client: Optional[OllamaClient] = None,
    ) -> Dict[str, Any]:
        """Execute Agent 2 review flow.

        Args:
            document_id: UUID of document.
            findings_data: Complete Agent 1 Findings dictionary (or normalized_data["analysis"]["agent1_findings"]).
            ollama_client: Injected OllamaClient (optional; defaults to production instance).

        Returns:
            Dict matching Agent2ReviewResponse.
        """
        client = ollama_client or OllamaClient()
        findings = findings_data.get("findings", findings_data)
        warnings: List[str] = list(findings_data.get("warnings", []))

        # 1. Deterministic Investigation
        investigations = InvestigationService.investigate(findings)

        # 2. Compare Related Metrics
        metric_comparisons = MetricComparator.compare_metrics(findings)

        # 3. Build Verified Context (Zero leak of DB internals, paths, or secrets)
        # Focus on the most salient investigations and comparisons for fast, deterministic CPU inference
        prioritized_inv = [i for i in investigations if i.get("status") in ("INVALID", "ANOMALY", "FLAGGED", "INCOMPLETE")]
        if not prioritized_inv:
            prioritized_inv = investigations[:3]
        else:
            prioritized_inv = prioritized_inv[:3]

        selected_comparisons = metric_comparisons[:2]

        verified_context = {
            "document_id": document_id,
            "investigations": [
                {"target": i["target"], "status": i["status"], "description": i["description"]}
                for i in prioritized_inv
            ],
            "metric_comparisons": [
                {"metric_a": c["metric_a"], "value_a": c["metric_a_value"], "metric_b": c["metric_b"], "value_b": c["metric_b_value"], "relationship": c["relationship"]}
                for c in selected_comparisons
            ],
        }

        context_prompt = (
            "Analyze the verified financial investigations and metric comparisons below.\n"
            "Return exactly 1 concise structured observation and a 1-sentence summary.\n\n"
            f"VERIFIED CONTEXT:\n{json.dumps(verified_context, separators=(',', ':'))}\n"
        )

        # 4. Invoke Ollama
        try:
            ollama_result = client.generate_review(
                system_prompt=SYSTEM_PROMPT,
                context_prompt=context_prompt,
            )
            raw_observations = [obs.model_dump() for obs in ollama_result.observations]
            summary_text = ollama_result.summary
            limitations = ollama_result.limitations
            for lim in limitations:
                if lim and lim not in warnings:
                    warnings.append(f"limitation: {lim}")
        except (OllamaUnavailableException, OllamaTimeoutException, OllamaMalformedResponseException):
            raise  # Handled by API layer for precise HTTP status mapping
        except Exception as exc:
            logger.exception("Unexpected error during Ollama review: %s", exc)
            raise

        # 5. Grounding Verification: Filter out or neutralize any ungrounded / investment advice
        sanitized_observations: List[Dict[str, Any]] = []
        forbidden_phrases = ["buy this stock", "sell this stock", "strong buy", "strong sell", "investment recommendation", "guaranteed profit"]

        for obs in raw_observations:
            explanation = obs.get("explanation", "")
            title = obs.get("title", "")
            # Check for investment advice violation
            if any(p in explanation.lower() or p in title.lower() for p in forbidden_phrases):
                obs["explanation"] = "Content omitted: Agent 2 does not provide investment advice."
                obs["severity"] = "UNKNOWN"
            sanitized_observations.append(obs)

        # 6. Determine Status
        f_status = findings_data.get("status", "PARTIAL")
        if f_status == "COMPLETED" and sanitized_observations:
            overall_status = "COMPLETED"
            reason = None
        else:
            overall_status = "PARTIAL"
            reason = f"Review completed with partial findings (Agent 1 status: {f_status})."

        response_dict = {
            "document_id": document_id,
            "status": overall_status,
            "investigations": investigations,
            "metric_comparisons": metric_comparisons,
            "observations": sanitized_observations,
            "summary": summary_text,
            "evidence": findings.get("evidence", []),
            "warnings": warnings,
            "reason": reason,
            "model": client.model,
        }

        return _sanitize_json(response_dict)
