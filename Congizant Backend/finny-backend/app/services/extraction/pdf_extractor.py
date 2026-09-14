import logging
import re
from pathlib import Path
from typing import Union, List, Any
import pdfplumber
import pymupdf as fitz
from app.services.extraction.base_extractor import BaseExtractor
from app.schemas.financial import RawExtractionData, RawTable, DocumentSource

# Ensure pdfminer logging stays silenced during extraction
for _pkg in ("pdfminer", "pdfplumber", "PIL"):
    logging.getLogger(_pkg).setLevel(logging.WARNING)


class PDFExtractor(BaseExtractor):
    """Extractor for Portable Document Format (.pdf) files."""

    def __init__(self):
        super().__init__(file_type="pdf")

    def extract(self, file_path: Union[str, Path]) -> RawExtractionData:
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"PDF file not found: {file_path}")

        extracted_tables: List[RawTable] = []
        page_texts: List[str] = []
        source = DocumentSource(filename=path.name, file_type=self.file_type)

        try:
            # 1. Primary extraction with pdfplumber (table recognition)
            with pdfplumber.open(path) as pdf:
                for page_idx, page in enumerate(pdf.pages, start=1):
                    text = page.extract_text()
                    if text:
                        page_texts.append(text)

                    tables = page.extract_tables()
                    page_had_tables = False
                    
                    if tables:
                        for tbl in tables:
                            clean_tbl = self._clean_table(tbl)
                            if clean_tbl and clean_tbl.rows:
                                clean_tbl.page_number = page_idx
                                extracted_tables.append(clean_tbl)
                                page_had_tables = True

                    # 2. Fallback: if no tables found on this page, parse structured text lines
                    if not page_had_tables and text:
                        text_table = self._extract_tables_from_text(text, page_idx)
                        if text_table and text_table.rows:
                            extracted_tables.append(text_table)

        except Exception as plumber_err:
            # 3. Fallback to PyMuPDF (fitz) text parsing if pdfplumber fails
            try:
                doc = fitz.open(path)
                for page_idx, page in enumerate(doc, start=1):
                    text = page.get_text()
                    if text:
                        page_texts.append(text)
                        text_table = self._extract_tables_from_text(text, page_idx)
                        if text_table and text_table.rows:
                            extracted_tables.append(text_table)
                doc.close()
            except Exception as fitz_err:
                raise ValueError(f"Failed to extract PDF data: {str(plumber_err)} | Fitz fallback: {str(fitz_err)}")

        return RawExtractionData(
            source=source,
            tables=extracted_tables,
            metadata={"total_tables_found": len(extracted_tables), "page_texts": page_texts}
        )

    def _clean_table(self, table_data: List[List[Any]]) -> RawTable:
        """Sanitize raw pdfplumber table rows and identify header."""
        if not table_data:
            return RawTable(headers=[], rows=[])

        # Filter out rows that are entirely None or whitespace
        filtered_rows = []
        for row in table_data:
            cleaned_row = [str(cell).strip() if cell is not None else "" for cell in row]
            if any(cell != "" for cell in cleaned_row):
                filtered_rows.append(cleaned_row)

        if not filtered_rows:
            return RawTable(headers=[], rows=[])

        # Infer header from first row, or generate default headers if single row
        if len(filtered_rows) == 1:
            headers = [f"Col_{i+1}" for i in range(len(filtered_rows[0]))]
            rows = filtered_rows
        else:
            headers = filtered_rows[0]
            # If headers are mostly blank, use Col_N
            if all(h == "" for h in headers):
                headers = [f"Col_{i+1}" for i in range(len(headers))]
                rows = filtered_rows
            else:
                rows = filtered_rows[1:]

        return RawTable(headers=headers, rows=rows)

    def _extract_tables_from_text(self, text: str, page_num: int) -> RawTable:
        """Parse structured tabular financial statements from plaintext lines."""
        rows: List[List[str]] = []
        lines = text.splitlines()

        # Check for multi-year header declarations (e.g. 'June 30, 2025 2024')
        should_reverse_cols = False
        detected_headers: List[str] = []
        for l in lines[:8]:
            years = re.findall(r"\b(20\d\d|19\d\d)\b", l)
            if len(years) >= 2:
                # If years are descending (e.g. 2025, 2024), order columns so rightmost is latest period
                if int(years[0]) > int(years[-1]):
                    should_reverse_cols = True
                    detected_headers = ["Particulars"] + list(reversed(years))
                else:
                    detected_headers = ["Particulars"] + years
                break

        line_pattern = re.compile(
            r"^([A-Za-z\s'&/.-]+?)\s*[:=]?\s+([₹$€£]?\s*\(?[\d,]+(?:\.\d+)?\s*(?:M|million|B|billion|K|thousand|Cr|L)?\)?(?:\s+[₹$€£]?\s*\(?[\d,]+(?:\.\d+)?\s*(?:M|million|B|billion|K|thousand|Cr|L)?\)?)*)$",
            re.MULTILINE | re.IGNORECASE
        )

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Sanitize curly apostrophes and quotes
            cleaned_line = line.replace(chr(8216), "'").replace(chr(8217), "'").replace(chr(8220), '"').replace(chr(8221), '"')
            # Join split numbers from typesetting (e.g. '512, 163' -> '512,163')
            cleaned_line = re.sub(r"(\d+),\s+(\d{3})", r"\1,\2", cleaned_line)
            # Attach separated currency symbol to adjacent number (e.g. '$ 619,003' -> '$619,003')
            cleaned_line = re.sub(r"([$€£₹])\s+(\(?[\d,]+(?:\.\d+)?)", r"\1\2", cleaned_line)

            # Check for label followed by multiple tokens or values
            parts = re.split(r"\s{2,}|\t", cleaned_line)
            if len(parts) >= 2 and any(re.search(r"\d", p) for p in parts[1:]):
                label = parts[0].strip()
                vals = [p.strip() for p in parts[1:]]
                if should_reverse_cols:
                    vals = list(reversed(vals))
                rows.append([label] + vals)
                continue

            match = line_pattern.match(cleaned_line)
            if match:
                particular = match.group(1).strip()
                vals_raw = match.group(2).strip()
                val_tokens = [v.strip() for v in re.split(r"\s+", vals_raw) if v.strip() and v.strip() not in ("$", "€", "£", "₹")]
                if val_tokens:
                    if should_reverse_cols:
                        val_tokens = list(reversed(val_tokens))
                    rows.append([particular] + val_tokens)

        if detected_headers and rows:
            headers = detected_headers
        else:
            headers = ["Particulars"] + [f"Value_{i+1}" for i in range(max((len(r) - 1 for r in rows), default=1))]
        return RawTable(headers=headers, rows=rows, page_number=page_num)
