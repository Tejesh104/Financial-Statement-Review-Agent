import re
from typing import List, Optional, Dict, Any
from app.schemas.financial import (
    RawExtractionData,
    NormalizedFinancialData,
    CompanyInfo,
    PeriodInfo,
    FinancialMetrics,
    RawTable,
)
from app.services.normalization.field_mapper import FieldMapper
from app.services.normalization.value_cleaner import ValueCleaner
from app.services.normalization.currency_normalizer import CurrencyNormalizer
from app.services.normalization.date_normalizer import DateNormalizer


class Normalizer:
    """Core normalization engine transforming common raw tabular data into canonical financial schemas."""

    def __init__(self, field_mapper: Optional[FieldMapper] = None):
        self.field_mapper = field_mapper or FieldMapper()
        self.value_cleaner = ValueCleaner()
        self.currency_normalizer = CurrencyNormalizer()
        self.date_normalizer = DateNormalizer()

    def normalize(self, raw_data: RawExtractionData, document_id: str) -> NormalizedFinancialData:
        """Execute full normalization pipeline on raw extracted tables.
        
        Args:
            raw_data: Standardized raw extraction data.
            document_id: UUID of the document.
            
        Returns:
            NormalizedFinancialData: Canonical validated financial record.
        """
        warnings: List[str] = []
        metrics_dict: Dict[str, float] = {}
        detected_currency: Optional[str] = None
        period_info = PeriodInfo()
        company_name: Optional[str] = None
        previous_period_data: Optional[Dict[str, Any]] = None

        # Look for metadata clues
        if "company_name" in raw_data.metadata:
            company_name = str(raw_data.metadata["company_name"])

        detected_currencies: List[str] = []

        for table in raw_data.tables:
            # 1. Currency detection in headers and rows
            tbl_currencies = self._detect_currencies_in_table(table)
            for c in tbl_currencies:
                if c not in detected_currencies:
                    detected_currencies.append(c)

            # 2. Period / Date / Fiscal year detection in headers
            if not (period_info.start or period_info.end or period_info.fiscal_year):
                table_period = self._detect_period_in_table(table)
                if table_period.start or table_period.end or table_period.fiscal_year:
                    period_info = table_period

            # 3. Company name inference from early rows or headers
            if not company_name:
                company_name = self._detect_company_name(table)

            # 4. Extract metrics from row-based layout (Particulars | Value)
            self._extract_row_metrics(table, metrics_dict, warnings)

            # 5. Extract metrics and multi-period data from column-based layout (Headers are line items)
            table_prev = self._extract_column_metrics(table, metrics_dict, warnings)
            if table_prev and not previous_period_data:
                previous_period_data = table_prev

            # If fiscal year was not set but table has year column, set it
            if not period_info.fiscal_year and table.headers and table.rows:
                for col_idx, h in enumerate(table.headers):
                    h_clean = re.sub(r"[^\w\s]", "", str(h).lower()).strip()
                    if h_clean in ("year", "fiscal year", "fy", "period", "date"):
                        if col_idx < len(table.rows[0]):
                            c_val = str(table.rows[0][col_idx]).strip()
                            if c_val:
                                period_info.fiscal_year = c_val
                        break

        # Contextual fallback: check page_texts if currency, period, or company were outside tables
        for p_text in raw_data.metadata.get("page_texts", []):
            p_curr = self.currency_normalizer.detect_currency(p_text)
            if p_curr and p_curr not in detected_currencies:
                detected_currencies.append(p_curr)
            if not (period_info.start or period_info.end or period_info.fiscal_year):
                p_period = self.date_normalizer.normalize_period(p_text)
                if p_period.start or p_period.end or p_period.fiscal_year:
                    period_info = p_period
            if not company_name:
                company_name = self._detect_company_name_in_text(p_text)

        # Final currency check: if currency wasn't explicitly inside cells, inspect original source filename
        if not detected_currencies and raw_data.source and raw_data.source.filename:
            f_curr = self.currency_normalizer.detect_currency(raw_data.source.filename)
            if f_curr and f_curr not in detected_currencies:
                detected_currencies.append(f_curr)

        if detected_currencies:
            detected_currency = detected_currencies[0]
            if len(detected_currencies) > 1:
                warnings.append(
                    f"Conflicting currencies detected across document: {', '.join(detected_currencies)}. "
                    f"Preserving primary currency '{detected_currency}' without automatic conversion."
                )

        # 6. Apply standard accounting identity derivations
        self._derive_accounting_identities(metrics_dict)

        # Build FinancialMetrics pydantic model
        financial_metrics = FinancialMetrics(**metrics_dict)

        return NormalizedFinancialData(
            document_id=document_id,
            company=CompanyInfo(name=company_name),
            currency=detected_currency,
            period=period_info,
            financial_data=financial_metrics,
            previous_period_data=previous_period_data,
            source=raw_data.source,
            normalization_warnings=warnings,
        )

    @staticmethod
    def _derive_accounting_identities(metrics: Dict[str, float]) -> None:
        """Derive missing balance sheet and financial metrics using standard accounting identities."""
        # 1. Total Assets from ROA: ROA = (Net Income / Total Assets) * 100 => Assets = (Net Income / (ROA / 100))
        if metrics.get("assets") is None:
            net_inc = metrics.get("net_income") or metrics.get("net_profit")
            roa = metrics.get("roa") or metrics.get("return_on_assets")
            if net_inc is not None and roa is not None and roa != 0:
                metrics["assets"] = round((net_inc / (roa / 100.0)), 2)

        # 2. Total Liabilities from Balance Sheet Equation: Assets = Liabilities + Equity => Liabilities = Assets - Equity
        if metrics.get("liabilities") is None:
            if metrics.get("assets") is not None and metrics.get("equity") is not None:
                metrics["liabilities"] = round(metrics["assets"] - metrics["equity"], 2)
            elif metrics.get("debt_to_equity") is not None and metrics.get("equity") is not None:
                metrics["liabilities"] = round(metrics["debt_to_equity"] * metrics["equity"], 2)

        # 3. Total Assets if Liabilities and Equity are known: Assets = Liabilities + Equity
        if metrics.get("assets") is None:
            if metrics.get("liabilities") is not None and metrics.get("equity") is not None:
                metrics["assets"] = round(metrics["liabilities"] + metrics["equity"], 2)

        # 4. Equity if Assets and Liabilities are known: Equity = Assets - Liabilities
        if metrics.get("equity") is None:
            if metrics.get("assets") is not None and metrics.get("liabilities") is not None:
                metrics["equity"] = round(metrics["assets"] - metrics["liabilities"], 2)

        # 5. Current Assets derivation
        if metrics.get("current_assets") is None:
            cr = metrics.get("current_ratio")
            if cr is not None and cr > 0 and metrics.get("current_liabilities") is not None:
                metrics["current_assets"] = round(cr * metrics["current_liabilities"], 2)
            else:
                # Sum known liquid components: cash + accounts_receivable + inventory
                liquid_components = [metrics.get(k) for k in ("cash", "accounts_receivable", "inventory") if metrics.get(k) is not None]
                if liquid_components:
                    metrics["current_assets"] = round(sum(liquid_components), 2)
        elif metrics.get("inventory") is None:
            # If current assets is known, inventory = max(0, current_assets - cash - accounts_receivable)
            non_inv = [metrics.get(k) for k in ("cash", "accounts_receivable") if metrics.get(k) is not None]
            if non_inv:
                inv_calc = metrics["current_assets"] - sum(non_inv)
                if inv_calc >= 0:
                    metrics["inventory"] = round(inv_calc, 2)

        # 6. Current Liabilities derivation
        if metrics.get("current_liabilities") is None:
            cr = metrics.get("current_ratio")
            if cr is not None and cr > 0 and metrics.get("current_assets") is not None:
                metrics["current_liabilities"] = round(metrics["current_assets"] / cr, 2)
            elif metrics.get("current_assets") is not None and metrics.get("liabilities") is not None:
                # In single-statement presentations where liabilities aren't split into current/long-term,
                # use total liabilities as the conservative upper bound for current liabilities
                metrics["current_liabilities"] = round(metrics["liabilities"], 2)

    def _detect_currencies_in_table(self, table: RawTable) -> List[str]:
        """Scan table headers and rows for all distinct currency symbols or indicators."""
        found: List[str] = []
        for header in table.headers:
            curr = self.currency_normalizer.detect_currency(str(header))
            if curr and curr not in found:
                found.append(curr)

        for row in table.rows[:15]:
            for cell in row:
                curr = self.currency_normalizer.detect_currency(str(cell))
                if curr and curr not in found:
                    found.append(curr)
        return found

    def _detect_currency_in_table(self, table: RawTable) -> Optional[str]:
        """Scan table headers and early rows for primary currency symbol."""
        currencies = self._detect_currencies_in_table(table)
        return currencies[0] if currencies else None

    def _detect_period_in_table(self, table: RawTable) -> PeriodInfo:
        """Scan table headers for fiscal years or dates."""
        for header in table.headers:
            period = self.date_normalizer.normalize_period(str(header))
            if period.fiscal_year or period.end:
                return period

        for row in table.rows[:3]:
            for cell in row:
                period = self.date_normalizer.normalize_period(str(cell))
                if period.fiscal_year or period.end:
                    return period

        return PeriodInfo()

    def _detect_company_name(self, table: RawTable) -> Optional[str]:
        """Infer company name from table headers, company column, or top banner rows."""
        # 1. Check if table headers have a designated company column
        for col_idx, header in enumerate(table.headers):
            h_clean = re.sub(r"[^\w\s]", "", str(header).lower()).strip()
            if h_clean in ("company", "company name", "entity", "organization", "issuer", "ticker"):
                for row in table.rows:
                    if col_idx < len(row):
                        val = str(row[col_idx]).strip()
                        if val and len(val) >= 2 and not val.lower().startswith(("total", "nan", "null", "none")):
                            return val

        # 2. Check for corporate entity patterns in headers and early rows
        company_patterns = [
            re.compile(r"([A-Za-z0-9\s&,.-]+?(?:Limited|Ltd|Inc\.?|Corp\.?|Corporation|LLC|Pvt\.?\s*Ltd\.?))\b", re.IGNORECASE)
        ]
        
        for header in table.headers:
            for pat in company_patterns:
                match = pat.search(str(header))
                if match:
                    return match.group(1).strip()

        for row in table.rows[:3]:
            for cell in row:
                for pat in company_patterns:
                    match = pat.search(str(cell))
                    if match:
                        return match.group(1).strip()
        return None

    def _detect_company_name_in_text(self, text: str) -> Optional[str]:
        """Infer company name from general page or paragraph text."""
        company_patterns = [
            re.compile(r"([A-Za-z0-9\s&,.-]+?(?:Limited|Ltd|Inc\.?|Corp\.?|Corporation|LLC|Pvt\.?\s*Ltd\.?))\b", re.IGNORECASE)
        ]
        for line in text.splitlines()[:6]:
            clean_line = line.strip()
            for pat in company_patterns:
                match = pat.search(clean_line)
                if match:
                    cand = match.group(1).strip()
                    if len(cand) > 3 and not cand.lower().startswith(("annual", "financial", "statement", "balance")):
                        return cand
        return None

    def _extract_row_metrics(self, table: RawTable, metrics: Dict[str, float], warnings: List[str]) -> None:
        """Extract financial metrics where particulars/labels are in column 0 and values in subsequent columns."""
        for row in table.rows:
            if not row or len(row) < 2:
                continue

            label = str(row[0]).strip()
            canonical_field = self.field_mapper.map_field(label)
            if not canonical_field:
                continue

            # Prioritize the most recent / rightmost valid numeric column
            parsed_val = None
            for cell in reversed(row[1:]):
                if cell is None or str(cell).strip() == "":
                    continue
                val, warn = self.value_cleaner.clean_numeric(cell)
                if warn:
                    warnings.append(f"Field '{canonical_field}' ({label}): {warn}")
                if val is not None:
                    parsed_val = val
                    break

            if parsed_val is not None and canonical_field not in metrics:
                metrics[canonical_field] = parsed_val

    def _extract_column_metrics(self, table: RawTable, metrics: Dict[str, float], warnings: List[str]) -> Optional[Dict[str, Any]]:
        """Extract financial metrics where table headers represent line items and rows represent records.
        
        Also detects if consecutive rows represent consecutive reporting periods (e.g. 2022 vs 2021)
        and returns previous period data for YoY analysis.
        """
        if not table.headers or not table.rows:
            return None

        # Check if table has a Year / Period column
        year_col_idx = None
        for col_idx, header in enumerate(table.headers):
            h_clean = re.sub(r"[^\w\s]", "", str(header).lower()).strip()
            if h_clean in ("year", "fiscal year", "fy", "period", "reporting period", "date"):
                year_col_idx = col_idx
                break

        # 1. Current period metrics from row 0
        for col_idx, header in enumerate(table.headers):
            canonical_field = self.field_mapper.map_field(str(header))
            if not canonical_field or canonical_field in metrics:
                continue

            # Check row 0
            if col_idx < len(table.rows[0]):
                cell = table.rows[0][col_idx]
                val, warn = self.value_cleaner.clean_numeric(cell)
                if warn:
                    warnings.append(f"Column '{canonical_field}' ({header}): {warn}")
                if val is not None:
                    metrics[canonical_field] = val

        # 2. Previous period extraction if row 1 represents prior period
        if len(table.rows) >= 2 and year_col_idx is not None:
            prev_year_val = str(table.rows[1][year_col_idx]).strip()
            prev_metrics: Dict[str, float] = {}

            for col_idx, header in enumerate(table.headers):
                canonical_field = self.field_mapper.map_field(str(header))
                if not canonical_field or canonical_field in prev_metrics or col_idx >= len(table.rows[1]):
                    continue
                cell = table.rows[1][col_idx]
                val, _ = self.value_cleaner.clean_numeric(cell)
                if val is not None:
                    prev_metrics[canonical_field] = val

            self._derive_accounting_identities(prev_metrics)

            return {
                "period": prev_year_val,
                "fiscal_year": prev_year_val,
                "financial_data": prev_metrics
            }

        return None

