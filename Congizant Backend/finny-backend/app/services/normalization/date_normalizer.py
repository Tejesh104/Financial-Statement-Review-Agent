import re
from datetime import datetime
from typing import Optional, Tuple
from app.schemas.financial import PeriodInfo


class DateNormalizer:
    """Normalizes financial periods, dates, and fiscal years into standard formats."""

    # Date parsing formats
    DATE_FORMATS = [
        "%Y-%m-%d",
        "%d-%m-%Y",
        "%d/%m/%Y",
        "%m/%d/%Y",
        "%B %d, %Y",
        "%d %B %Y",
        "%b %d, %Y",
        "%d %b %Y",
        "%d-%b-%Y",
        "%d-%B-%Y",
    ]

    # Fiscal Year regex: e.g. "FY 2024-25", "FY2024-2025", "FY 24-25", "2024-25"
    FY_REGEX = re.compile(
        r"(?:(?:FY|Fiscal\s+Year|F\.Y\.)\s*)?((?:20\d{2}|19\d{2})[-/](?:20\d{2}|\d{2}))\b(?![-/]\d{1,2})",
        re.IGNORECASE
    )

    # Single Year regex: e.g. "2024", "2025"
    YEAR_REGEX = re.compile(r"\b(20\d{2}|19\d{2})\b")

    @classmethod
    def parse_iso_date(cls, date_str: str) -> Optional[str]:
        """Try to parse a date string into an ISO YYYY-MM-DD string."""
        if not date_str:
            return None

        clean_str = date_str.strip()
        # Remove ordinals like 31st, 1st, 2nd, 3rd
        clean_str = re.sub(r"(\d+)(st|nd|rd|th)", r"\1", clean_str)

        for fmt in cls.DATE_FORMATS:
            try:
                dt = datetime.strptime(clean_str, fmt)
                return dt.strftime("%Y-%m-%d")
            except ValueError:
                continue

        return None

    @classmethod
    def extract_fiscal_year(cls, text: str) -> Optional[str]:
        """Extract standardized fiscal year (e.g. '2024-25') from text."""
        if not text:
            return None

        match = cls.FY_REGEX.search(text)
        if match:
            raw_fy = match.group(1).replace("/", "-")
            parts = raw_fy.split("-")
            if len(parts) == 2:
                # Standardize 2024-2025 into 2024-25
                start_yr = parts[0]
                end_yr = parts[1]
                if len(end_yr) == 4 and len(start_yr) == 4:
                    end_yr = end_yr[-2:]
                return f"{start_yr}-{end_yr}"
            return raw_fy

        return None

    @classmethod
    def normalize_period(cls, text: str) -> PeriodInfo:
        """Parse arbitrary header or metadata string into PeriodInfo."""
        if not text:
            return PeriodInfo()

        fiscal_year = cls.extract_fiscal_year(text)
        start_date = None
        end_date = None

        # Check for range: e.g. "From 01-04-2024 to 31-03-2025" or "2024-04-01 - 2025-03-31"
        range_match = re.search(r"(?:from\s+)?([^\s]+)\s+(?:to|-)\s+([^\s]+)", text, re.IGNORECASE)
        if range_match:
            cand_start = cls.parse_iso_date(range_match.group(1))
            cand_end = cls.parse_iso_date(range_match.group(2))
            if cand_start and cand_end:
                start_date = cand_start
                end_date = cand_end

        # Check for "ended March 31, 2025" or "as of 31/03/2025"
        if not end_date:
            ended_match = re.search(r"(?:ended|as\s+(?:of|at))\s+([A-Za-z0-9\s,/.-]+)", text, re.IGNORECASE)
            if ended_match:
                end_date = cls.parse_iso_date(ended_match.group(1).strip())

        # If still no date found, check the whole string for a single date
        if not end_date:
            iso = cls.parse_iso_date(text)
            if iso:
                end_date = iso

        # If no fiscal year but we have end date, infer fiscal year
        if not fiscal_year and end_date:
            dt = datetime.strptime(end_date, "%Y-%m-%d")
            # Common April-March fiscal year
            if dt.month <= 3:
                fiscal_year = f"{dt.year - 1}-{str(dt.year)[-2:]}"
            else:
                fiscal_year = f"{dt.year}-{str(dt.year + 1)[-2:]}"
        elif not fiscal_year:
            # Fallback: check single 4-digit year like "2025"
            yr_match = cls.YEAR_REGEX.search(text)
            if yr_match:
                fiscal_year = yr_match.group(1)

        return PeriodInfo(start=start_date, end=end_date, fiscal_year=fiscal_year)
