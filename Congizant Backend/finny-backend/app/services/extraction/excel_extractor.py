from pathlib import Path
from typing import Union, List, Any
import pandas as pd
from app.services.extraction.base_extractor import BaseExtractor
from app.schemas.financial import RawExtractionData, RawTable, DocumentSource


class ExcelExtractor(BaseExtractor):
    """Extractor for Microsoft Excel (.xlsx, .xls) spreadsheet workbooks."""

    def __init__(self):
        super().__init__(file_type="excel")

    def extract(self, file_path: Union[str, Path]) -> RawExtractionData:
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Excel file not found: {file_path}")

        extracted_tables: List[RawTable] = []
        source = DocumentSource(filename=path.name, file_type=self.file_type)

        try:
            # Read all sheets in workbook
            excel_file = pd.ExcelFile(path)
            sheet_names = excel_file.sheet_names

            for sheet_name in sheet_names:
                df = pd.read_excel(excel_file, sheet_name=sheet_name, header=None)
                
                # Drop all-empty rows and columns
                df = df.dropna(how="all").dropna(axis=1, how="all")
                
                if df.empty:
                    continue

                # Find first row with non-empty values to use as header
                raw_rows: List[List[Any]] = df.values.tolist()
                if not raw_rows:
                    continue

                # Infer headers
                header_row_idx = 0
                for idx, r in enumerate(raw_rows):
                    non_nulls = [c for c in r if pd.notna(c) and str(c).strip() != ""]
                    if len(non_nulls) >= 1:
                        header_row_idx = idx
                        break

                raw_headers = raw_rows[header_row_idx]
                headers = [str(h).strip() if pd.notna(h) and str(h).strip() != "" else f"Col_{i+1}" 
                           for i, h in enumerate(raw_headers)]
                
                data_rows = []
                for r in raw_rows[header_row_idx + 1:]:
                    cleaned_row = [str(c).strip() if pd.notna(c) else "" for c in r]
                    if any(c != "" for c in cleaned_row):
                        data_rows.append(cleaned_row)

                if data_rows:
                    extracted_tables.append(
                        RawTable(
                            headers=headers,
                            rows=data_rows,
                            sheet_name=sheet_name
                        )
                    )

        except Exception as err:
            raise ValueError(f"Failed to extract Excel data: {str(err)}")

        return RawExtractionData(
            source=source,
            tables=extracted_tables,
            metadata={"sheets_processed": len(extracted_tables)}
        )
