import re
from typing import Dict, List, Optional


class FieldMapper:
    """Configurable financial field mapping taxonomy.
    
    Maps diverse presentation labels (case, punctuation, whitespace, synonyms)
    to canonical standardized financial metric keys.
    """

    DEFAULT_FIELD_MAPPING: Dict[str, List[str]] = {
        "revenue": [
            "revenue",
            "total revenue",
            "net revenue",
            "net sales",
            "sales",
            "turnover",
            "gross sales",
            "operating revenue",
            "revenue from operations",
            "top line",
            "total sales"
        ],
        "assets": [
            "assets",
            "total assets",
            "aggregate assets",
            "total balance sheet assets"
        ],
        "liabilities": [
            "liabilities",
            "total liabilities",
            "aggregate liabilities",
            "total debt and liabilities"
        ],
        "equity": [
            "equity",
            "shareholders equity",
            "shareholders' equity",
            "shareholder equity",
            "share holder equity",
            "stockholders equity",
            "stockholders' equity",
            "owners equity",
            "owners' equity",
            "total equity",
            "net worth",
            "total shareholders equity"
        ],
        # Future-proof extensible fields
        "operating_income": [
            "operating income",
            "operating profit",
            "ebit",
            "operating earnings"
        ],
        "net_income": [
            "net income",
            "net profit",
            "profit after tax",
            "pat",
            "net earnings",
            "bottom line"
        ],
        "cash": [
            "cash",
            "cash and cash equivalents",
            "cash and bank balances",
            "cash flow from operating",
            "cash flow from operations",
            "operating cash flow"
        ],
        "inventory": [
            "inventory",
            "inventories",
            "stock in trade",
            "raw materials"
        ],
        "accounts_receivable": [
            "accounts receivable",
            "trade receivables",
            "debtors"
        ],
        "accounts_payable": [
            "accounts payable",
            "trade payables",
            "creditors"
        ],
        "expenses": [
            "expenses",
            "total expenses",
            "operating expenses"
        ],
        "gross_profit": [
            "gross profit",
            "gross margin"
        ],
        "current_assets": [
            "current assets",
            "total current assets"
        ],
        "current_liabilities": [
            "current liabilities",
            "total current liabilities"
        ],
        "ebitda": [
            "ebitda"
        ],
        "earnings_per_share": [
            "earning per share",
            "earnings per share",
            "eps"
        ],
        "current_ratio": [
            "current ratio"
        ],
        "debt_to_equity": [
            "debt/equity ratio",
            "debt to equity ratio",
            "debt/equity",
            "debt to equity"
        ],
        "roe": [
            "roe",
            "return on equity"
        ],
        "roa": [
            "roa",
            "return on assets"
        ],
        "roi": [
            "roi",
            "return on investment"
        ],
        "net_profit_margin": [
            "net profit margin",
            "profit margin"
        ],
        "gross_profit_margin": [
            "gross profit margin"
        ]
    }

    def __init__(self, custom_mapping: Optional[Dict[str, List[str]]] = None):
        self.field_mapping = custom_mapping or self.DEFAULT_FIELD_MAPPING
        # Precompute normalized lookup index
        self._lookup: Dict[str, str] = {}
        for canonical, synonyms in self.field_mapping.items():
            # Canonical itself
            self._lookup[self._normalize_label(canonical)] = canonical
            for syn in synonyms:
                self._lookup[self._normalize_label(syn)] = canonical

        # Precompute sorted list of synonyms by length descending for priority matching
        self._sorted_synonyms = sorted(
            [(self._normalize_label(syn), canonical) for canonical, syns in self.field_mapping.items() for syn in syns],
            key=lambda x: len(x[0]),
            reverse=True
        )

    @staticmethod
    def _normalize_label(label: str) -> str:
        """Sanitize field label for matching: lowercase, strip punctuation, collapse whitespace."""
        if not label:
            return ""
        # Remove punctuation like quotes, colons, dashes
        cleaned = re.sub(r"[^\w\s]", "", str(label).lower())
        # Collapse multiple spaces into single space
        return re.sub(r"\s+", " ", cleaned).strip()

    def map_field(self, raw_label: str) -> Optional[str]:
        """Map a raw row or column label to a standardized canonical field name.
        
        Args:
            raw_label: The label text extracted from the document.
            
        Returns:
            Optional[str]: Standardized field name (e.g. 'revenue', 'equity') or None.
        """
        normalized = self._normalize_label(raw_label)
        if not normalized:
            return None

        # 1. Exact match in precomputed normalized taxonomy index
        if normalized in self._lookup:
            return self._lookup[normalized]

        # Explicitly avoid false matching on composite / non-canonical phrases
        if normalized in ("liabilities equity", "liabilities and equity", "liabilities plus equity", "total liabilities and equity"):
            return None
        if "fixed assets" in normalized or "non current assets" in normalized:
            return None

        # 2. Substring or token matching for compound labels, prioritized by longest synonym
        for syn_norm, canonical in self._sorted_synonyms:
            # Bare single words 'assets', 'liabilities', 'equity' shouldn't loosely match arbitrary multi-word labels
            if syn_norm in ("assets", "liabilities", "equity") and len(normalized.split()) > 1:
                continue
            pattern = rf"\b{re.escape(syn_norm)}\b"
            if re.search(pattern, normalized):
                return canonical

        return None

