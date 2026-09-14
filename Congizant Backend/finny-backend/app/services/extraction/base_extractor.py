from abc import ABC, abstractmethod
from pathlib import Path
from typing import Union
from app.schemas.financial import RawExtractionData


class BaseExtractor(ABC):
    """Abstract base class for all financial document extractors."""

    def __init__(self, file_type: str):
        self.file_type = file_type

    @abstractmethod
    def extract(self, file_path: Union[str, Path]) -> RawExtractionData:
        """Extract raw tabular data and metadata from the given document file.
        
        Args:
            file_path: Path to the target document.
            
        Returns:
            RawExtractionData: Unified raw tables structure.
        """
        pass
