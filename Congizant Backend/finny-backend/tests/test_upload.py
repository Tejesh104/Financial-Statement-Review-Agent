from pathlib import Path
from fastapi.testclient import TestClient


def test_upload_pdf(client: TestClient, sample_pdf: Path):
    """Test successful upload of a PDF file."""
    with open(sample_pdf, "rb") as f:
        response = client.post(
            "/api/v1/documents/upload",
            files={"file": ("report.pdf", f, "application/pdf")}
        )
    assert response.status_code == 201
    data = response.json()
    assert "document_id" in data
    assert data["filename"] == "report.pdf"
    assert data["file_type"] == "pdf"
    assert data["status"] == "UPLOADED"


def test_upload_excel(client: TestClient, sample_excel: Path):
    """Test successful upload of an Excel file."""
    with open(sample_excel, "rb") as f:
        response = client.post(
            "/api/v1/documents/upload",
            files={"file": ("report.xlsx", f, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
        )
    assert response.status_code == 201
    data = response.json()
    assert "document_id" in data
    assert data["filename"] == "report.xlsx"
    assert data["file_type"] == "excel"
    assert data["status"] == "UPLOADED"


def test_upload_csv(client: TestClient, sample_csv: Path):
    """Test successful upload of a CSV file."""
    with open(sample_csv, "rb") as f:
        response = client.post(
            "/api/v1/documents/upload",
            files={"file": ("report.csv", f, "text/csv")}
        )
    assert response.status_code == 201
    data = response.json()
    assert "document_id" in data
    assert data["filename"] == "report.csv"
    assert data["file_type"] == "csv"
    assert data["status"] == "UPLOADED"


def test_upload_invalid_file_type(client: TestClient, tmp_path: Path):
    """Test rejection of unsupported file extensions with 400 Bad Request."""
    invalid_file = tmp_path / "script.py"
    invalid_file.write_text("print('hello')", encoding="utf-8")
    
    with open(invalid_file, "rb") as f:
        response = client.post(
            "/api/v1/documents/upload",
            files={"file": ("script.py", f, "text/plain")}
        )
    assert response.status_code == 400
    assert "Unsupported file extension" in response.json()["detail"]


def test_upload_empty_file(client: TestClient, tmp_path: Path):
    """Test rejection of empty 0-byte file with 400 Bad Request."""
    empty_file = tmp_path / "empty.csv"
    empty_file.write_text("", encoding="utf-8")
    
    with open(empty_file, "rb") as f:
        response = client.post(
            "/api/v1/documents/upload",
            files={"file": ("empty.csv", f, "text/csv")}
        )
    assert response.status_code == 400
    assert "empty" in response.json()["detail"].lower()


def test_upload_missing_file(client: TestClient):
    """Test error when no file payload is attached."""
    response = client.post("/api/v1/documents/upload", files={})
    assert response.status_code == 422
