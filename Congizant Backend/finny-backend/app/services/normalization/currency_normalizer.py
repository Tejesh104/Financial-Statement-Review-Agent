import re
from typing import Optional, Dict


class CurrencyNormalizer:
    """Detects and normalizes currency symbols and designations to ISO-4217 standard codes.
    
    IMPORTANT: Identifies and standardizes the currency code only; NEVER converts values between currencies.
    """

    # Mapping of currency symbols and textual representations to ISO-4217 codes
    CURRENCY_MAPPINGS: Dict[str, str] = {
        # Indian Rupee
        "₹": "INR",
        "rs.": "INR",
        "rs": "INR",
        "inr": "INR",
        "rupees": "INR",
        "rupee": "INR",
        # US Dollar
        "$": "USD",
        "usd": "USD",
        "us dollar": "USD",
        "us dollars": "USD",
        "dollar": "USD",
        "dollars": "USD",
        # Euro
        "€": "EUR",
        "eur": "EUR",
        "euro": "EUR",
        "euros": "EUR",
        # British Pound
        "£": "GBP",
        "gbp": "GBP",
        "pound": "GBP",
        "pounds": "GBP",
        "sterling": "GBP",
        # Japanese Yen
        "¥": "JPY",
        "jpy": "JPY",
        "yen": "JPY",
        # Canadian Dollar
        "cad": "CAD",
        "c$": "CAD",
        # Australian Dollar
        "aud": "AUD",
        "a$": "AUD",
        # Swiss Franc
        "chf": "CHF",
        # UAE Dirham
        "aed": "AED",
        "dirham": "AED",
        # Singapore Dollar
        "sgd": "SGD",
        "s$": "SGD",
    }

    # Mapping of ISO codes to canonical symbols
    CURRENCY_SYMBOLS: Dict[str, str] = {
        "INR": "₹",
        "USD": "$",
        "EUR": "€",
        "GBP": "£",
        "JPY": "¥",
        "CAD": "C$",
        "AUD": "A$",
        "CHF": "CHF",
        "AED": "AED",
        "SGD": "S$",
    }

    @classmethod
    def get_currency_symbol(cls, currency_code: Optional[str]) -> str:
        """Return standardized currency symbol for ISO-4217 code, defaulting to $."""
        if not currency_code:
            return "$"
        return cls.CURRENCY_SYMBOLS.get(currency_code.upper().strip(), currency_code)

    @classmethod
    def detect_currency(cls, text: Optional[str]) -> Optional[str]:
        """Detect currency from table header, cell text, or metadata.
        
        Args:
            text: Arbitrary string snippet that may contain currency indicators.
            
        Returns:
            Optional[str]: Standardized ISO 3-letter currency code (e.g. 'INR', 'USD') or None.
        """
        if not text:
            return None

        clean_text = str(text).strip()

        # 1. Check symbols sorted by length descending (e.g. 'a$', 'c$', 's$' before '$')
        clean_lower = clean_text.lower()
        non_alnum_patterns = sorted(
            [p for p in cls.CURRENCY_MAPPINGS.keys() if not p.isalnum()],
            key=lambda x: len(x),
            reverse=True
        )
        for pattern in non_alnum_patterns:
            if pattern.lower() in clean_lower:
                return cls.CURRENCY_MAPPINGS[pattern]

        # 2. Check alphanumeric codes and words with word boundaries
        alnum_patterns = [p for p in cls.CURRENCY_MAPPINGS.keys() if p.isalnum()]
        for pattern in alnum_patterns:
            regex = rf"\b{re.escape(pattern)}\b"
            if re.search(regex, clean_text, re.IGNORECASE):
                return cls.CURRENCY_MAPPINGS[pattern]

        return None
