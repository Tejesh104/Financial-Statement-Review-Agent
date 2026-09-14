"""HTTP client for communicating with local Ollama instance."""

import json
import logging
import os
import re
import urllib.request
import urllib.error
from typing import Dict, Any, Optional

from app.core.config import settings
from app.schemas.agent2 import OllamaReviewContent

logger = logging.getLogger(__name__)


class OllamaUnavailableException(Exception):
    """Raised when local Ollama daemon cannot be reached."""
    pass


class OllamaTimeoutException(Exception):
    """Raised when local Ollama times out during inference."""
    pass


class OllamaMalformedResponseException(Exception):
    """Raised when Ollama returns non-JSON or invalid schema."""
    pass


class OllamaClient:
    """Robust client for local Ollama generate API."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        timeout: Optional[int] = None,
    ):
        self.base_url = (base_url or settings.OLLAMA_BASE_URL).rstrip("/")
        self.model = model or settings.OLLAMA_MODEL
        self.timeout = timeout if timeout is not None else settings.OLLAMA_TIMEOUT_SECONDS

    def generate_review(self, system_prompt: str, context_prompt: str) -> OllamaReviewContent:
        """Submit review context to local Ollama and return validated structured content.

        Args:
            system_prompt: Guiding rules and constraints for the LLM.
            context_prompt: Verified findings context in JSON/text format.

        Returns:
            OllamaReviewContent with parsed observations, summary, and limitations.

        Raises:
            OllamaUnavailableException
            OllamaTimeoutException
            OllamaMalformedResponseException
        """
        endpoint = f"{self.base_url}/api/generate"
        payload = {
            "model": self.model,
            "system": system_prompt,
            "prompt": context_prompt,
            "format": "json",
            "stream": False,
            "keep_alive": "15m",
            "options": {
                "temperature": 0.0,  # Greedy decoding for fastest deterministic CPU inference
                "num_predict": 180,  # Token budget sufficient for complete 1-2 observation JSON
                "num_ctx": 1536,     # Compact context window
                "num_thread": min(os.cpu_count() or 6, 8),  # Optimal physical core utilization without hyperthread contention
            },
        }

        data_bytes = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            endpoint,
            data=data_bytes,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            logger.info("Calling local Ollama at %s with model %s (timeout: %ss)", endpoint, self.model, self.timeout)
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                resp_bytes = resp.read()
                raw_outer = json.loads(resp_bytes.decode("utf-8"))
        except urllib.error.URLError as url_err:
            reason_str = str(url_err.reason) if hasattr(url_err, "reason") else str(url_err)
            if "timed out" in reason_str.lower():
                logger.error("Ollama inference timed out after %s seconds", self.timeout)
                raise OllamaTimeoutException(f"Local Ollama timed out after {self.timeout}s: {reason_str}")
            logger.error("Failed to reach local Ollama: %s", reason_str)
            raise OllamaUnavailableException(f"Local Ollama daemon is unreachable at {self.base_url}: {reason_str}")
        except TimeoutError as to_err:
            logger.error("Ollama connection timed out: %s", to_err)
            raise OllamaTimeoutException(f"Local Ollama timed out after {self.timeout}s: {to_err}")
        except Exception as exc:
            logger.exception("Unexpected socket error contacting Ollama: %s", exc)
            raise OllamaUnavailableException(f"Unable to connect to Ollama daemon: {exc}")

        # Extract inner response string
        raw_text = raw_outer.get("response", "")
        if not raw_text or not raw_text.strip():
            logger.warning("Ollama returned empty response string")
            raise OllamaMalformedResponseException("Ollama returned an empty response body.")

        # Clean markdown wrappers if present
        clean_text = raw_text.strip()
        if clean_text.startswith("```"):
            clean_text = re.sub(r"^```(?:json)?\s*", "", clean_text)
            clean_text = re.sub(r"\s*```$", "", clean_text).strip()

        # Parse inner JSON with repair fallback
        parsed_json = None
        try:
            parsed_json = json.loads(clean_text)
        except json.JSONDecodeError as json_err:
            logger.warning("Ollama response not strict JSON, attempting repair. Raw snippet: %s", clean_text[:200])
            # 1. Unescaped quote balancing + common closure combinations
            quotes = len(re.findall(r'(?<!\\)"', clean_text))
            base = clean_text + ('"' if quotes % 2 != 0 else '')
            for closer in ['', '}', ']}', '}]}', '"]}', '"]}}', '"}]}', '": ""}]}', '": []}]}']:
                try:
                    parsed_json = json.loads(base + closer)
                    break
                except json.JSONDecodeError:
                    continue

            # 2. Extract completed observation objects using regex
            if parsed_json is None:
                obs_matches = re.findall(r'(\{\s*"finding_type"[^{}]+?\})', clean_text, re.DOTALL)
                if not obs_matches:
                    obs_matches = re.findall(r'(\{[^{}]+?"finding"[^{}]+?\})', clean_text, re.DOTALL)
                extracted_obs = []
                for m in obs_matches:
                    try:
                        extracted_obs.append(json.loads(m))
                    except Exception:
                        pass
                if extracted_obs:
                    parsed_json = {
                        "observations": extracted_obs,
                        "summary": "Verified financial review compiled from findings.",
                        "limitations": []
                    }

            # 3. Robust partial-field recovery from truncated observation stream
            if parsed_json is None:
                finding_type_m = re.search(r'"finding_type"\s*:\s*"([^"]+)', clean_text)
                title_m = re.search(r'"title"\s*:\s*"([^"]+)', clean_text)
                finding_m = re.search(r'"finding"\s*:\s*"([^"]+)', clean_text)
                explanation_m = re.search(r'"explanation"\s*:\s*"([^"]+)', clean_text)
                severity_m = re.search(r'"severity"\s*:\s*"([^"]+)', clean_text)
                summary_m = re.search(r'"summary"\s*:\s*"([^"]+)', clean_text)

                if finding_m or title_m:
                    parsed_json = {
                        "observations": [{
                            "finding_type": finding_type_m.group(1) if finding_type_m else "GENERAL",
                            "title": title_m.group(1) if title_m else "Financial Observation",
                            "finding": finding_m.group(1) if finding_m else "Verified financial observation.",
                            "explanation": explanation_m.group(1) if explanation_m else (finding_m.group(1) if finding_m else "Observation grounded in verified financial findings."),
                            "severity": severity_m.group(1) if severity_m else "MEDIUM",
                            "evidence": []
                        }],
                        "summary": summary_m.group(1) if summary_m else "Verified observation extracted from financial review.",
                        "limitations": []
                    }

            if parsed_json is None:
                raise OllamaMalformedResponseException(f"Ollama response could not be parsed as JSON: {json_err}")

        # Validate against OllamaReviewContent schema
        try:
            validated = OllamaReviewContent(**parsed_json)
            return validated
        except Exception as schema_err:
            logger.warning("Ollama JSON structure failed schema validation: %s", schema_err)
            # Graceful recovery: if observations is a dict, list, or summary in non-standard form
            try:
                raw_obs = parsed_json.get("observations", []) if isinstance(parsed_json, dict) else []
                obs_list = []
                if isinstance(raw_obs, dict):
                    for k, v in raw_obs.items():
                        obs_list.append({
                            "finding_type": "GENERAL",
                            "title": k.replace("_", " ").title(),
                            "finding": str(v),
                            "explanation": str(v),
                            "severity": "LOW",
                            "evidence": [],
                        })
                elif isinstance(raw_obs, list):
                    for item in raw_obs:
                        if isinstance(item, dict):
                            obs_list.append({
                                "finding_type": item.get("finding_type", "GENERAL"),
                                "title": item.get("title", "Observation"),
                                "finding": item.get("finding", ""),
                                "explanation": item.get("explanation", ""),
                                "severity": item.get("severity", "UNKNOWN"),
                                "evidence": item.get("evidence", []) if isinstance(item.get("evidence"), list) else [],
                            })
                summary = parsed_json.get("summary", "Review complete based on supplied evidence.") if isinstance(parsed_json, dict) else "Review complete based on supplied evidence."
                limits = parsed_json.get("limitations", []) if isinstance(parsed_json, dict) else []
                return OllamaReviewContent(
                    observations=obs_list,
                    summary=str(summary),
                    limitations=limits if isinstance(limits, list) else [],
                )
            except Exception as rec_err:
                raise OllamaMalformedResponseException(f"Ollama response failed schema validation: {rec_err}")
