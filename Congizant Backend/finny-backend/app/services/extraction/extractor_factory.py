from pathlib import Path
from typing import Union
from app.services.extraction.base_extractor import BaseExtractor
from app.services.extraction.pdf_extractor import PDFExtractor
from app.services.extraction.excel_extractor import ExcelExtractor
from app.services.extraction.csv_extractor import CSVExtractor
from app.services.extraction.docx_extractor import DocxExtractor


class ExtractorFactory:
    """Factory to resolve document extractor based on file extension."""

    _EXTRACTORS = {
        ".pdf": PDFExtractor,
        ".xlsx": ExcelExtractor,
        ".xls": ExcelExtractor,
        ".csv": CSVExtractor,
        ".docx": DocxExtractor,
    }

    @classmethod
    def _normalize_ext(cls, file_path_or_ext: Union[str, Path]) -> str:
        s = str(file_path_or_ext).strip().lower()
        if s.startswith("."):
            return s
        return Path(s).suffix.lower()

    @classmethod
    def get_extractor(cls, file_path_or_ext: Union[str, Path]) -> BaseExtractor:
        """Get the extractor instance for the given file path or extension.
        
        Args:
            file_path_or_ext: File path (e.g. 'report.pdf') or extension (e.g. '.pdf')
            
        Returns:
            BaseExtractor: Concrete extractor instance.
            
        Raises:
            ValueError: If file format is not supported.
        """
        ext = cls._normalize_ext(file_path_or_ext)
        extractor_cls = cls._EXTRACTORS.get(ext)
        if not extractor_cls:
            supported = ", ".join(cls._EXTRACTORS.keys())
            raise ValueError(f"Unsupported document format '{ext}'. Supported formats: {supported}")

        return extractor_cls()

    @classmethod
    def get_file_type_name(cls, file_path_or_ext: Union[str, Path]) -> str:
        """Map file extension to canonical file type name (pdf, excel, csv)."""
        ext = cls._normalize_ext(file_path_or_ext)
        if ext == ".pdf":
            return "pdf"
        elif ext in [".xlsx", ".xls"]:
            return "excel"
        elif ext == ".csv":
            return "csv"
        elif ext == ".docx":
            return "docx"
        return ext.lstrip(".")
