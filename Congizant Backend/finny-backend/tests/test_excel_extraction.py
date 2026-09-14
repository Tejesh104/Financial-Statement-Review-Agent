from pathlib import Path
import pytest
import pandas as pd
from app.services.extraction.excel_extractor import ExcelExtractor


def test_excel_extraction(sample_excel: Path):
    """Test standard Excel extraction of structured financial sheets."""
    extractor = ExcelExtractor()
    result = extractor.extract(sample_excel)

    assert result.source.file_type == "excel"
    assert len(result.tables) >= 1
    
    table = result.tables[0]
    assert "Particulars" in table.headers
    assert len(table.rows) == 4
    
    # Check row labels
    row_labels = [r[0] for r in table.rows]
    assert "Revenue" in row_labels
    assert "Total Assets" in row_labels


def test_excel_multisheet_extraction(tmp_path: Path):
    """Test extraction across multiple sheets in an Excel workbook."""
    excel_path = tmp_path / "multisheet.xlsx"
    df1 = pd.DataFrame({"Metric": ["Net Sales"], "Amount": [5000000]})
    df2 = pd.DataFrame({"Item": ["Owners' Equity"], "Amount": [3000000]})

    with pd.ExcelWriter(excel_path, engine="openpyxl") as writer:
        df1.to_excel(writer, sheet_name="Income", index=False)
        df2.to_excel(writer, sheet_name="Equity", index=False)

    extractor = ExcelExtractor()
    result = extractor.extract(excel_path)

    assert len(result.tables) == 2
    sheet_names = [tbl.sheet_name for tbl in result.tables]
    assert "Income" in sheet_names
    assert "Equity" in sheet_names


def test_excel_nonexistent_file():
    """Test extractor raises FileNotFoundError on missing file."""
    extractor = ExcelExtractor()
    with pytest.raises(FileNotFoundError):
        extractor.extract("missing_file.xlsx")
