from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from app.services.validation.statement_classifier import FinancialStatementClassifier
from app.schemas.financial import RawExtractionData, RawTable, DocumentSource
from app.models.document import DocumentStatus


def test_classifier_financial_statement_indicators():
    classifier = FinancialStatementClassifier()
    raw = RawExtractionData(
        source=DocumentSource(filename="annual_financial_statements.csv", file_type="csv"),
        tables=[
            RawTable(
                headers=["Line Item", "2023"],
                rows=[
                    ["Revenue", "5000000"],
                    ["Net Income", "450000"],
                ]
            )
        ]
    )
    is_valid, reason, metrics = classifier.classify(raw)
    assert is_valid is True
    assert "revenue" in metrics or "net_income" in metrics


def test_classifier_non_financial_file_rejected():
    classifier = FinancialStatementClassifier()
    raw = RawExtractionData(
        source=DocumentSource(filename="groceries.csv", file_type="csv"),
        tables=[
            RawTable(
                headers=["Item", "Quantity", "Store"],
                rows=[
                    ["Apples", "5", "Kroger"],
                    ["Milk", "2", "Costco"],
                    ["Bread", "1", "Trader Joes"],
                ]
            )
        ]
    )
    is_valid, reason, metrics = classifier.classify(raw)
    assert is_valid is False
    assert "rejected" in reason.lower()
    assert len(metrics) == 0


def test_classifier_random_text_rejected():
    classifier = FinancialStatementClassifier()
    raw = RawExtractionData(
        source=DocumentSource(filename="meeting_notes.txt", file_type="pdf"),
        tables=[],
        metadata={"raw_text": "Meeting notes: Discussed the marketing team roadmap for Q3."}
    )
    is_valid, reason, metrics = classifier.classify(raw)
    assert is_valid is False
    assert "rejected" in reason.lower() or "no readable tabular data" in reason.lower()


def test_process_non_financial_document_api_rejection(client: TestClient, tmp_path: Path):
    """Test that uploading and processing a non-financial file returns 422 and marks document as REJECTED."""
    # 1. Create a non-financial CSV
    non_fin_csv = tmp_path / "employee_roster.csv"
    non_fin_csv.write_text("Name,Department,Age\nAlice,Design,28\nBob,Engineering,34\n", encoding="utf-8")

    # 2. Upload
    with open(non_fin_csv, "rb") as f:
        up_resp = client.post(
            "/api/v1/documents/upload",
            files={"file": ("employee_roster.csv", f, "text/csv")}
        )
    assert up_resp.status_code == 201
    doc_id = up_resp.json()["document_id"]

    # 3. Process -> Should be rejected with 422
    proc_resp = client.post(f"/api/v1/documents/{doc_id}/process")
    assert proc_resp.status_code == 422
    detail = proc_resp.json()["detail"]
    assert "rejected" in detail.lower()

    # 4. Check status endpoint -> status must be REJECTED
    stat_resp = client.get(f"/api/v1/documents/{doc_id}")
    assert stat_resp.status_code == 200
    assert stat_resp.json()["status"] == DocumentStatus.REJECTED.value
    assert stat_resp.json()["error_message"] is not None
