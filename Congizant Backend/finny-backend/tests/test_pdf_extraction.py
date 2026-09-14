from pathlib import Path
import pytest
import pymupdf as fitz
from app.services.extraction.pdf_extractor import PDFExtractor


def test_pdf_extraction(sample_pdf: Path):
    """Test extracting tabular lines and metadata from a PDF file."""
    extractor = PDFExtractor()
    result = extractor.extract(sample_pdf)

    assert result.source.file_type == "pdf"
    assert result.source.filename == sample_pdf.name
    assert len(result.tables) >= 1

    # Verify extracted rows contain financial line items
    first_table = result.tables[0]
    all_text = " ".join([str(cell) for row in first_table.rows for cell in row])
    assert "Revenue" in all_text
    assert "12,500,000" in all_text or "12500000" in all_text


def test_pdf_multipage_extraction(tmp_path: Path):
    """Test extraction handles multi-page PDF documents cleanly."""
    pdf_path = tmp_path / "multipage.pdf"
    doc = fitz.open()

    # Page 1: Income statement
    p1 = doc.new_page()
    p1.insert_text((50, 72), "Income Statement\nRevenue 10,000,000\nExpenses 6,000,000", fontsize=11)

    # Page 2: Balance sheet
    p2 = doc.new_page()
    p2.insert_text((50, 72), "Balance Sheet\nTotal Assets 25,000,000\nTotal Liabilities 10,000,000", fontsize=11)

    doc.save(str(pdf_path))
    doc.close()

    extractor = PDFExtractor()
    result = extractor.extract(pdf_path)

    assert len(result.tables) >= 1
    combined_content = " ".join([str(cell) for tbl in result.tables for row in tbl.rows for cell in row])
    assert "Revenue" in combined_content
    assert "Assets" in combined_content or "Total Assets" in combined_content


def test_pdf_nonexistent_file():
    """Test extractor raises FileNotFoundError when given non-existent file."""
    extractor = PDFExtractor()
    with pytest.raises(FileNotFoundError):
        extractor.extract("non_existent_file.pdf")
