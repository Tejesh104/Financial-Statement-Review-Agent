import re
from typing import Tuple, Optional, Any


class ValueCleaner:
    """Robust parser and normalizer for financial numeric values."""

    # Multipliers for financial scales
    SCALE_MULTIPLIERS = {
        "m": 1_000_000.0,
        "million": 1_000_000.0,
        "millions": 1_000_000.0,
        "b": 1_000_000_000.0,
        "billion": 1_000_000_000.0,
        "billions": 1_000_000_000.0,
        "bn": 1_000_000_000.0,
        "k": 1_000.0,
        "thousand": 1_000.0,
        "thousands": 1_000.0,
        "cr": 10_000_000.0,
        "crore": 10_000_000.0,
        "crores": 10_000_000.0,
        "l": 100_000.0,
        "lakh": 100_000.0,
        "lakhs": 100_000.0,
        "lac": 100_000.0,
        "lacs": 100_000.0,
    }

    MISSING_INDICATORS = {"", "-", "--", "---", "n/a", "na", "null", "none", "nil", "."}

    @classmethod
    def clean_numeric(cls, raw_val: Any) -> Tuple[Optional[float], Optional[str]]:
        """Parse raw financial value into a canonical float.
        
        Args:
            raw_val: The raw value (string, int, float, or None)
            
        Returns:
            Tuple[Optional[float], Optional[str]]: (normalized_value, warning_message)
        """
        if raw_val is None:
            return None, None

        if isinstance(raw_val, (int, float)):
            # Check for NaN / Inf
            if raw_val != raw_val:  # NaN check
                return None, None
            return float(raw_val), None

        val_str = str(raw_val).strip()

        # Check missing indicators
        if val_str.lower() in cls.MISSING_INDICATORS:
            return None, None

        # Check for negative indication via parentheses, e.g. (5,000,000) or (12.5M)
        is_negative = False
        paren_match = re.match(r"^\((.+)\)$", val_str)
        if paren_match:
            is_negative = True
            val_str = paren_match.group(1).strip()
        elif val_str.startswith("-") or val_str.endswith("-"):
            is_negative = True
            val_str = val_str.replace("-", "").strip()

        # Strip currency symbols and ISO codes at beginning or end
        # E.g. ₹, $, €, £, ¥, A$, C$, S$, Rs., Rs, INR, USD, EUR, GBP, JPY, AUD, CAD, SGD, CHF, AED
        curr_pattern = r"(?:₹|\$|€|£|¥|A\$|C\$|S\$|Rs\.?|INR|USD|EUR|GBP|JPY|AUD|CAD|SGD|CHF|AED)"
        val_str = re.sub(rf"^{curr_pattern}\s*", "", val_str, flags=re.IGNORECASE)
        val_str = re.sub(rf"\s*{curr_pattern}$", "", val_str, flags=re.IGNORECASE)
        val_str = val_str.strip()

        # Detect scale suffix, e.g. '12.5M', '12.5 million', '10 Cr'
        multiplier = 1.0
        scale_pattern = re.compile(
            r"^(.*?)\s*(million|millions|billion|billions|bn|thousand|thousands|crores|crore|lakhs|lakh|lacs|lac|[mbk]|cr|l)$",
            re.IGNORECASE
        )
        scale_match = scale_pattern.match(val_str)
        if scale_match:
            number_part = scale_match.group(1).strip()
            unit_part = scale_match.group(2).lower()
            if unit_part in cls.SCALE_MULTIPLIERS and (number_part.replace(",", "").replace(".", "").isdigit() or number_part == ""):
                multiplier = cls.SCALE_MULTIPLIERS[unit_part]
                val_str = number_part if number_part else "1"

        # Strip trailing percentage sign if present, e.g. '10%' -> 10.0
        val_str = re.sub(r"%\s*$", "", val_str).strip()

        # Check for European number format with dot thousands separators and comma decimal:
        # e.g. '10.000.000,50' or '10.000,50' (must have dot grouping of 3 digits followed by comma and decimal digits)
        cleaned_str = val_str.replace("\xa0", "").strip()
        if re.match(r"^\d{1,3}(?:\.\d{3})+,\d+$", cleaned_str):
            cleaned_num = cleaned_str.replace(".", "").replace(",", ".")
        else:
            # Standard format: remove commas as thousands separators
            cleaned_num = cleaned_str.replace(",", "").strip()

        try:
            parsed_float = float(cleaned_num)
            result = parsed_float * multiplier
            if is_negative:
                result = -result
            return result, None
        except ValueError:
            warning = f"Could not reliably parse numeric value '{raw_val}'; preserved as unparsed."
            return None, warning
