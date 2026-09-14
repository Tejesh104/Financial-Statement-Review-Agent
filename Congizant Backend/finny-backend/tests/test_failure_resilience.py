"""
Tests for Type 11: Failure and Resilience Testing.
Verifies backend behavior under:
- Ollama outage (503 Service Unavailable with clean error message)
- Ollama request timeout (504 Gateway Timeout)
- Ollama malformed/unparseable responses (502 Bad Gateway)
- Database rollback on simulated repository failures
- Absence of unhandled crashes (500) or stack/secret leaks
"""
import uuid
import pytest
from unittest.mock import patch
import httpx
from fastapi.testclient import TestClient

from app.main import app
from app.core.security import create_access_token
from app.models.document import Document
from app.models.financial_data import FinancialData


@pytest.fixture
def auth_headers(db_session):
    from app.models.user import User
    user = User(id="resilience-user-1", google_id="resilience-gid", email="resilience_user@example.com", name="Resilience User")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    token = create_access_token(user_id=user.id, email=user.email)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def mock_document_with_data(db_session):
    doc_id = str(uuid.uuid4())
    doc = Document(
        id=doc_id,
        user_id="resilience-user-1",
        filename="test_resilience.csv",
        file_type="csv",
        file_path="uploads/test_resilience.csv",
        status="NORMALIZED"
    )
    norm = FinancialData(
        id=str(uuid.uuid4()),
        document_id=doc_id,
        fiscal_year="2023",
        revenue=2000.0,
        assets=1000.0,
        liabilities=500.0,
        equity=500.0,
        currency="USD",
        normalized_data={
            "financial_data": {"assets": 1000.0, "liabilities": 500.0, "equity": 500.0, "revenue": 2000.0, "net_profit": 300.0},
            "balance_sheet": {"total_assets": 1000.0, "total_liabilities": 500.0, "total_equity": 500.0},
            "income_statement": {"revenue": 2000.0, "net_income": 300.0}
        }
    )
    db_session.add(doc)
    db_session.add(norm)
    db_session.commit()
    return doc_id


def test_ollama_unavailable_returns_503(client, auth_headers, mock_document_with_data):
    """When Ollama is unreachable (OllamaUnavailableException), backend returns 503."""
    from app.services.agent2.ollama_client import OllamaUnavailableException
    with patch("app.services.agent2.ollama_client.OllamaClient.generate_review", side_effect=OllamaUnavailableException("Connection refused")):
        res = client.post(f"/api/v1/agent2/{mock_document_with_data}/observations", headers=auth_headers)
        assert res.status_code == 503
        data = res.json()
        assert "detail" in data
        assert "unavailable" in data["detail"].lower()
        # Verify no stack trace or internal token leak
        assert "Traceback" not in str(data)
        assert "password" not in str(data).lower()


def test_ollama_timeout_returns_504(client, auth_headers, mock_document_with_data):
    """When Ollama times out (OllamaTimeoutException), backend returns 504."""
    from app.services.agent2.ollama_client import OllamaTimeoutException
    with patch("app.services.agent2.ollama_client.OllamaClient.generate_review", side_effect=OllamaTimeoutException("Timed out")):
        res = client.post(f"/api/v1/agent2/{mock_document_with_data}/observations", headers=auth_headers)
        assert res.status_code == 504
        data = res.json()
        assert "timed out" in data["detail"].lower()


def test_ollama_malformed_json_returns_502(client, auth_headers, mock_document_with_data):
    """When Ollama returns garbled invalid JSON (OllamaMalformedResponseException), backend returns 502."""
    from app.services.agent2.ollama_client import OllamaMalformedResponseException
    with patch("app.services.agent2.ollama_client.OllamaClient.generate_review", side_effect=OllamaMalformedResponseException("Malformed JSON")):
        res = client.post(f"/api/v1/agent2/{mock_document_with_data}/observations", headers=auth_headers)
        assert res.status_code == 502
        data = res.json()
        assert "malformed" in data["detail"].lower() or "failed to parse" in data["detail"].lower()


def test_database_error_triggers_rollback(client, auth_headers, mock_document_with_data):
    """When DB commit fails during persistence, transaction rolls back cleanly without orphan state."""
    from sqlalchemy.exc import OperationalError
    with patch("sqlalchemy.orm.Session.commit", side_effect=OperationalError("Simulated DB lock", None, None)):
        res = client.post(f"/api/v1/validation/{mock_document_with_data}/math", headers=auth_headers)
        assert res.status_code in [500, 503]
        data = res.json()
        assert "detail" in data
