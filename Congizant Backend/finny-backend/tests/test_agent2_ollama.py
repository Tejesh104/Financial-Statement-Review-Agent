"""Unit tests for Ollama Client and Grounding Safety."""

import json
import pytest
from unittest.mock import patch, MagicMock
import urllib.error

from app.services.agent2.ollama_client import (
    OllamaClient,
    OllamaUnavailableException,
    OllamaTimeoutException,
    OllamaMalformedResponseException,
)
from app.services.agent2.review_agent import Agent2ReviewAgent
from app.schemas.agent2 import OllamaReviewContent, ObservationFinding


def test_ollama_client_success():
    client = OllamaClient(base_url="http://localhost:11434", model="qwen2.5:7b", timeout=5)
    
    mock_payload = {
        "response": json.dumps({
            "observations": [
                {
                    "finding_type": "VALIDATION",
                    "title": "Math Validation Check",
                    "finding": "Balance sheet is balanced.",
                    "explanation": "Assets equal liabilities plus equity.",
                    "severity": "LOW",
                    "evidence": ["findings.validations.balance_sheet_check"]
                }
            ],
            "summary": "Financial statements are balanced.",
            "limitations": []
        })
    }

    mock_resp = MagicMock()
    mock_resp.read.return_value = json.dumps(mock_payload).encode("utf-8")
    mock_resp.__enter__.return_value = mock_resp

    with patch("urllib.request.urlopen", return_value=mock_resp):
        res = client.generate_review("System prompt", "Context prompt")
        assert isinstance(res, OllamaReviewContent)
        assert len(res.observations) == 1
        assert res.observations[0].finding_type == "VALIDATION"
        assert res.summary == "Financial statements are balanced."


def test_ollama_client_unavailable():
    client = OllamaClient(base_url="http://localhost:9999", model="qwen2.5:7b", timeout=1)
    with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("Connection refused")):
        with pytest.raises(OllamaUnavailableException) as exc:
            client.generate_review("System", "Context")
        assert "unreachable" in str(exc.value).lower() or "connection refused" in str(exc.value).lower()


def test_ollama_client_timeout():
    client = OllamaClient(base_url="http://localhost:11434", model="qwen2.5:7b", timeout=1)
    with patch("urllib.request.urlopen", side_effect=TimeoutError("Request timed out")):
        with pytest.raises(OllamaTimeoutException) as exc:
            client.generate_review("System", "Context")
        assert "timed out" in str(exc.value).lower()


def test_ollama_client_malformed_json():
    client = OllamaClient(base_url="http://localhost:11434", model="qwen2.5:7b", timeout=5)
    mock_payload = {"response": "This is plain text, not JSON at all."}
    mock_resp = MagicMock()
    mock_resp.read.return_value = json.dumps(mock_payload).encode("utf-8")
    mock_resp.__enter__.return_value = mock_resp

    with patch("urllib.request.urlopen", return_value=mock_resp):
        with pytest.raises(OllamaMalformedResponseException):
            client.generate_review("System", "Context")


def test_critical_grounding_numerical_immutability():
    """Agent 1 contains Revenue = 12,500,000. Ollama attempts to claim 99,999,999.
    Agent 1 numbers in evidence must remain untouched.
    """
    mock_client = MagicMock()
    mock_client.model = "qwen2.5:7b"
    mock_client.generate_review.return_value = OllamaReviewContent(
        observations=[
            ObservationFinding(
                finding_type="YOY",
                title="Hallucinated Revenue",
                finding="Revenue was 99,999,999.",
                explanation="The model hallucinated this number.",
                severity="HIGH",
                evidence=["findings.evidence.revenue"]
            )
        ],
        summary="Review summary with hallucinated number.",
        limitations=[]
    )

    findings_data = {
        "status": "COMPLETED",
        "findings": {
            "evidence": [
                {"field": "revenue", "value": 12500000.0, "is_available": True, "source": "normalized_data.financial_data.revenue"}
            ]
        },
        "warnings": []
    }

    result = Agent2ReviewAgent.review_document("doc-123", findings_data, ollama_client=mock_client)
    # The verified evidence pass-through in Agent 2 must still reflect 12,500,000, NOT 99,999,999
    rev_ev = [e for e in result["evidence"] if e["field"] == "revenue"][0]
    assert rev_ev["value"] == 12500000.0


def test_critical_grounding_investment_recommendation_neutralized():
    """Ollama outputs 'Buy this stock immediately'. Backend neutralizes it."""
    mock_client = MagicMock()
    mock_client.model = "qwen2.5:7b"
    mock_client.generate_review.return_value = OllamaReviewContent(
        observations=[
            ObservationFinding(
                finding_type="RELATIONSHIP",
                title="Stock Tip",
                finding="Strong profit growth.",
                explanation="Buy this stock immediately for guaranteed returns.",
                severity="HIGH",
                evidence=["findings.evidence.revenue"]
            )
        ],
        summary="Company is great.",
        limitations=[]
    )

    findings_data = {
        "status": "COMPLETED",
        "findings": {"evidence": []},
        "warnings": []
    }

    result = Agent2ReviewAgent.review_document("doc-123", findings_data, ollama_client=mock_client)
    obs = result["observations"][0]
    assert "Agent 2 does not provide investment advice" in obs["explanation"]
    assert obs["severity"] == "UNKNOWN"
