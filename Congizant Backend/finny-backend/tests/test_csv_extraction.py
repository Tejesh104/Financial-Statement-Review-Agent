from pathlib import Path
import pytest
from app.services.extraction.csv_extractor import CSVExtractor


def test_csv_extraction_comma(sample_csv: Path):
    """Test CSV extraction with default comma delimiter."""
    extractor = CSVExtractor()
    result = extractor.extract(sample_csv)

    assert result.source.file_type == "csv"
    assert len(result.tables) == 1
    table = result.tables[0]
    assert len(table.rows) >= 4
    
    first_col_values = [r[0] for r in table.rows]
    assert any("Revenue" in val for val in first_col_values)


def test_csv_extraction_semicolon(sample_semicolon_csv: Path):
    """Test CSV extraction with automatic semicolon delimiter detection."""
    extractor = CSVExtractor()
    result = extractor.extract(sample_semicolon_csv)

    assert result.source.file_type == "csv"
    assert len(result.tables) == 1
    table = result.tables[0]
    assert len(table.rows) == 4
    row_keys = [r[0] for r in table.rows]
    assert "Total Revenue" in row_keys
    assert "Assets" in row_keys


def test_csv_extraction_tab_delimited(tmp_path: Path):
    """Test CSV extraction with tab delimiter."""
    tab_csv = tmp_path / "tab_sample.tsv"
    tab_csv.write_text("Particulars\t2025\nSales\t8,000,000\nLiabilities\t3,000,000\n", encoding="utf-8")

    extractor = CSVExtractor()
    result = extractor.extract(tab_csv)

    assert len(result.tables) == 1
    assert result.tables[0].rows[0][0] == "Sales"


def test_csv_missing_values(tmp_path: Path):
    """Test CSV with missing and NaN values does not crash."""
    csv_path = tmp_path / "missing.csv"
    csv_path.write_text("Field,Value\nRevenue,1000\nAssets,\nLiabilities,NaN\nEquity,null\n", encoding="utf-8")

    extractor = CSVExtractor()
    result = extractor.extract(csv_path)

    assert len(result.tables) == 1
    rows = result.tables[0].rows
    assert len(rows) == 4
    assert rows[0][1] == "1000"
    assert rows[1][1] == ""
    assert rows[2][1] == ""
    assert rows[3][1] == ""
