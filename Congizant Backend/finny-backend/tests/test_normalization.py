from pathlib import Path
from fastapi.testclient import TestClient

from app.services.normalization.field_mapper import FieldMapper
from app.services.normalization.value_cleaner import ValueCleaner
from app.services.normalization.currency_normalizer import CurrencyNormalizer
from app.services.normalization.date_normalizer import DateNormalizer
from app.services.normalization.normalizer import Normalizer
from app.schemas.financial import RawExtractionData, RawTable, DocumentSource


def test_field_mapper():
    """Test mapping diverse financial synonyms and labels to canonical keys."""
    mapper = FieldMapper()

    # Revenue synonyms
    assert mapper.map_field("Revenue") == "revenue"
    assert mapper.map_field("Total Revenue") == "revenue"
    assert mapper.map_field("Net Revenue") == "revenue"
    assert mapper.map_field("Net Sales") == "revenue"
    assert mapper.map_field("Sales") == "revenue"
    assert mapper.map_field("Turnover") == "revenue"
    assert mapper.map_field("REVENUE FROM OPERATIONS") == "revenue"

    # Assets synonyms
    assert mapper.map_field("Assets") == "assets"
    assert mapper.map_field("Total Assets") == "assets"
    assert mapper.map_field("Aggregate Assets") == "assets"

    # Liabilities synonyms
    assert mapper.map_field("Liabilities") == "liabilities"
    assert mapper.map_field("Total Liabilities") == "liabilities"

    # Equity synonyms
    assert mapper.map_field("Equity") == "equity"
    assert mapper.map_field("Shareholders' Equity") == "equity"
    assert mapper.map_field("Shareholders Equity") == "equity"
    assert mapper.map_field("Owners' Equity") == "equity"
    assert mapper.map_field("Stockholders' Equity") == "equity"
    assert mapper.map_field("Net Worth") == "equity"

    # Unknown labels
    assert mapper.map_field("Random Notes") is None


def test_value_cleaner_numeric_formats():
    """Test robust parsing of numeric formats (commas, parentheses negatives, scales)."""
    cleaner = ValueCleaner()

    # Standard comma-separated numbers
    val, warn = cleaner.clean_numeric("12,500,000")
    assert val == 12500000.0
    assert warn is None

    # Currency symbol prefixed
    val, warn = cleaner.clean_numeric("₹12,500,000")
    assert val == 12500000.0
    assert warn is None

    # Negative parentheses accounting format
    val, warn = cleaner.clean_numeric("(5,000,000)")
    assert val == -5000000.0
    assert warn is None

    # Scaled suffixes
    val, warn = cleaner.clean_numeric("12.5 million")
    assert val == 12500000.0
    assert warn is None

    val, warn = cleaner.clean_numeric("12.5M")
    assert val == 12500000.0
    assert warn is None

    val, warn = cleaner.clean_numeric("2.5B")
    assert val == 2500000000.0
    assert warn is None

    val, warn = cleaner.clean_numeric("10 Cr")
    assert val == 100000000.0
    assert warn is None

    val, warn = cleaner.clean_numeric("50 L")
    assert val == 5000000.0
    assert warn is None

    # Negative with scale and parenthesis
    val, warn = cleaner.clean_numeric("(2.5M)")
    assert val == -2500000.0
    assert warn is None


def test_value_cleaner_missing_and_invalid():
    """Test handling of missing indicators and unparseable values."""
    cleaner = ValueCleaner()

    # Missing values should return None without error
    for missing_indicator in ["", "-", "--", "N/A", "na", "null", "None", "nil"]:
        val, warn = cleaner.clean_numeric(missing_indicator)
        assert val is None
        assert warn is None

    # Unparseable strings should return warning and None
    val, warn = cleaner.clean_numeric("confidential_data")
    assert val is None
    assert warn is not None
    assert "Could not reliably parse" in warn


def test_currency_normalizer():
    """Test currency detection and normalization to standard ISO-4217 codes."""
    norm = CurrencyNormalizer()

    assert norm.detect_currency("Revenue in ₹") == "INR"
    assert norm.detect_currency("Amount (Rs.)") == "INR"
    assert norm.detect_currency("Report in INR") == "INR"
    assert norm.detect_currency("Sales ($)") == "USD"
    assert norm.detect_currency("Values in USD") == "USD"
    assert norm.detect_currency("Turnover in €") == "EUR"
    assert norm.detect_currency("Values in EUR") == "EUR"
    assert norm.detect_currency("Total (£)") == "GBP"
    assert norm.detect_currency("Plain text without currency") is None


def test_date_normalizer():
    """Test date parsing and fiscal year extraction."""
    norm = DateNormalizer()

    # ISO formatting
    assert norm.parse_iso_date("31-03-2025") == "2025-03-31"
    assert norm.parse_iso_date("31/03/2025") == "2025-03-31"
    assert norm.parse_iso_date("March 31, 2025") == "2025-03-31"
    assert norm.parse_iso_date("31 March 2025") == "2025-03-31"
    assert norm.parse_iso_date("2025-03-31") == "2025-03-31"

    # Fiscal Year extraction
    assert norm.extract_fiscal_year("Annual Report FY 2024-25") == "2024-25"
    assert norm.extract_fiscal_year("FY 2024-2025") == "2024-25"
    assert norm.extract_fiscal_year("Fiscal Year 2023-24") == "2023-24"

    # Period normalization
    period = norm.normalize_period("For the year ended March 31, 2025 (FY 2024-25)")
    assert period.end == "2025-03-31"
    assert period.fiscal_year == "2024-25"


def test_normalizer_pipeline():
    """Test full normalization of a RawExtractionData instance."""
    raw_data = RawExtractionData(
        source=DocumentSource(filename="report.csv", file_type="csv"),
        tables=[
            RawTable(
                headers=["Particulars", "FY 2024-25 (₹)"],
                rows=[
                    ["ABC Limited", ""],
                    ["Revenue", "12,500,000"],
                    ["Total Assets", "45,000,000"],
                    ["Total Liabilities", "18,000,000"],
                    ["Shareholders' Equity", "27,000,000"]
                ]
            )
        ]
    )

    normalizer = Normalizer()
    normalized = normalizer.normalize(raw_data, document_id="test-doc-uuid")

    assert normalized.document_id == "test-doc-uuid"
    assert normalized.currency == "INR"
    assert normalized.period.fiscal_year == "2024-25"
    assert normalized.financial_data.revenue == 12500000.0
    assert normalized.financial_data.assets == 45000000.0
    assert normalized.financial_data.liabilities == 18000000.0
    assert normalized.financial_data.equity == 27000000.0
    assert len(normalized.normalization_warnings) == 0


def test_end_to_end_pipeline_api(client: TestClient, sample_csv: Path):
    """Test full end-to-end API pipeline: Upload -> Process -> Get Status -> Get Normalized."""
    # 1. Upload CSV file
    with open(sample_csv, "rb") as f:
        upload_resp = client.post(
            "/api/v1/documents/upload",
            files={"file": ("financial_report.csv", f, "text/csv")}
        )
    assert upload_resp.status_code == 201
    doc_id = upload_resp.json()["document_id"]

    # 2. Check initial status
    status_resp = client.get(f"/api/v1/documents/{doc_id}")
    assert status_resp.status_code == 200
    assert status_resp.json()["status"] == "UPLOADED"

    # 3. Process document
    process_resp = client.post(f"/api/v1/documents/{doc_id}/process")
    assert process_resp.status_code == 200
    norm_result = process_resp.json()
    assert norm_result["document_id"] == doc_id
    assert norm_result["status"] == "NORMALIZED"
    assert norm_result["financial_data"]["revenue"] == 12500000.0
    assert norm_result["financial_data"]["assets"] == 45000000.0
    assert norm_result["financial_data"]["liabilities"] == 18000000.0
    assert norm_result["financial_data"]["equity"] == 27000000.0

    # 4. Fetch normalized data via GET endpoint
    get_norm_resp = client.get(f"/api/v1/documents/{doc_id}/normalized")
    assert get_norm_resp.status_code == 200
    assert get_norm_resp.json()["financial_data"]["revenue"] == 12500000.0


def test_invalid_document_id(client: TestClient):
    """Test 404 returned for invalid/missing document IDs."""
    resp = client.get("/api/v1/documents/non-existent-uuid")
    assert resp.status_code == 404

    resp = client.post("/api/v1/documents/non-existent-uuid/process")
    assert resp.status_code == 404

    resp = client.get("/api/v1/documents/non-existent-uuid/normalized")
    assert resp.status_code == 404


def test_normalization_uniformity_across_formats(sample_pdf: Path, sample_excel: Path, sample_csv: Path):
    """Verify Architectural Rule: PDF, Excel, and CSV produce uniform normalized output."""
    from app.services.extraction.extractor_factory import ExtractorFactory

    normalizer = Normalizer()

    # Extract CSV
    csv_raw = ExtractorFactory.get_extractor(sample_csv).extract(sample_csv)
    csv_norm = normalizer.normalize(csv_raw, "doc-csv")

    # Extract Excel
    excel_raw = ExtractorFactory.get_extractor(sample_excel).extract(sample_excel)
    excel_norm = normalizer.normalize(excel_raw, "doc-excel")

    # Extract PDF
    pdf_raw = ExtractorFactory.get_extractor(sample_pdf).extract(sample_pdf)
    pdf_norm = normalizer.normalize(pdf_raw, "doc-pdf")

    # Verify all three extracted the same key metrics
    assert csv_norm.financial_data.revenue == 12500000.0
    assert excel_norm.financial_data.revenue == 12500000.0
    assert pdf_norm.financial_data.revenue == 12500000.0

    assert csv_norm.financial_data.assets == 45000000.0
    assert excel_norm.financial_data.assets == 45000000.0
    assert pdf_norm.financial_data.assets == 45000000.0
