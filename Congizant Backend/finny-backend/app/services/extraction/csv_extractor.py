import csv
import re
from pathlib import Path
from typing import Union, List, Any
from app.services.extraction.base_extractor import BaseExtractor
from app.schemas.financial import RawExtractionData, RawTable, DocumentSource


class CSVExtractor(BaseExtractor):
    """Extractor for Comma-Separated Values (.csv) and delimited text files."""

    NULL_LITERALS = {"nan", "null", "none", "n/a", "na", "."}

    def __init__(self):
        super().__init__(file_type="csv")

    def extract(self, file_path: Union[str, Path]) -> RawExtractionData:
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"CSV file not found: {file_path}")

        source = DocumentSource(filename=path.name, file_type=self.file_type)

        try:
            delimiter = self._detect_delimiter(path)
            raw_lines: List[List[str]] = []
            encodings = ["utf-8", "utf-8-sig", "latin1", "cp1252"]
            read_success = False

            for enc in encodings:
                try:
                    with open(path, "r", encoding=enc, errors="replace") as f:
                        reader = csv.reader(f, delimiter=delimiter)
                        raw_lines = [row for row in reader if any(cell.strip() for cell in row)]
                    read_success = True
                    break
                except Exception:
                    continue

            if not read_success or not raw_lines:
                return RawExtractionData(source=source, tables=[])

            # Header inference from first non-empty row
            header_row = [c.strip() for c in raw_lines[0]]
            headers = [h if h else f"Col_{i+1}" for i, h in enumerate(header_row)]

            # Clean rows and reconcile unquoted comma-split numbers if necessary
            data_rows: List[List[str]] = []
            for row in raw_lines[1:]:
                clean_cells = [
                    "" if str(c).strip().lower() in self.NULL_LITERALS else str(c).strip()
                    for c in row
                ]
                if not any(clean_cells):
                    continue

                # If delimiter was comma and row was split across numbers (e.g. ['Revenue', '12', '500', '000'] or ['$ 12', '500', '000'])
                # reconcile numeric chunks if header has fewer columns
                if delimiter == "," and len(clean_cells) > len(headers) and len(headers) == 2:
                    label = clean_cells[0]
                    remainder = clean_cells[1:]
                    # Check if all remainder parts are numeric or currency-prefixed numeric
                    curr_prefix_pat = r"^(?:₹|\$|€|£|¥|A\$|C\$|S\$|Rs\.?|INR|USD|EUR|GBP|JPY|AUD|CAD|SGD|CHF|AED|\s)+"
                    stripped_parts = [
                        re.sub(curr_prefix_pat, "", part, flags=re.IGNORECASE).replace(".", "").strip()
                        for part in remainder
                    ]
                    if all(sp.isdigit() for sp in stripped_parts if sp):
                        reconciled_val = ",".join(remainder)
                        clean_cells = [label, reconciled_val]

                data_rows.append(clean_cells)

            # Pad headers if rows have more columns
            max_cols = max((len(r) for r in data_rows), default=len(headers))
            if len(headers) < max_cols:
                headers.extend([f"Col_{i+1}" for i in range(len(headers), max_cols)])

            table = RawTable(headers=headers, rows=data_rows)
            return RawExtractionData(
                source=source,
                tables=[table],
                metadata={"delimiter": delimiter, "total_rows": len(data_rows)}
            )

        except Exception as err:
            raise ValueError(f"Failed to extract CSV data: {str(err)}")

    def _detect_delimiter(self, path: Path) -> str:
        """Heuristically sniff delimiter (, ; \t |) using csv.Sniffer with line counting fallback."""
        candidate_delimiters = [",", ";", "\t", "|"]
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                sample = f.read(4096)
                if not sample:
                    return ","
                sniffer = csv.Sniffer()
                dialect = sniffer.sniff(sample, delimiters=",\t;|")
                return dialect.delimiter
        except Exception:
            try:
                with open(path, "r", encoding="utf-8", errors="ignore") as f:
                    first_line = f.readline()
                    counts = {d: first_line.count(d) for d in candidate_delimiters}
                    best_delim = max(counts, key=counts.get)
                    return best_delim if counts[best_delim] > 0 else ","
            except Exception:
                return ","
