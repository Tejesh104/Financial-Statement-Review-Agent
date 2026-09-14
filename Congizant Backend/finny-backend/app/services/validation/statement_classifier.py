"""Financial Statement Verification and Classification Engine.

Verifies whether an uploaded document qualifies as a genuine financial statement
(e.g., Balance Sheet, Income Statement, Cash Flow Statement, or core financial metrics)
before permitting downstream extraction, normalization, and analytical pipelines.
"""

import logging
from typing import Tuple, List, Set, Optional

from app.schemas.financial import RawExtractionData
from app.services.normalization.field_mapper import FieldMapper
from app.services.normalization.value_cleaner import ValueCleaner

logger = logging.getLogger(__name__)


class FinancialStatementClassifier:
    """Verifies that an extracted document is a bona fide financial statement."""

    # Explicit financial statement title / heading markers
    STATEMENT_INDICATORS = [
        "balance sheet",
        "statement of financial position",
        "statement of condition",
        "income statement",
        "statement of income",
        "statement of operations",
        "statement of earnings",
        "profit and loss",
        "profit & loss",
        "p&l",
        "statement of comprehensive income",
        "cash flow",
        "statement of cash flows",
        "cash flows",
        "financial statement",
        "financial statements",
        "financial report",
        "annual report",
        "interim report",
        "10-k",
        "10-q",
        "trial balance",
        "statement of changes in equity",
        "statement of shareholders equity",
    ]

    # Core canonical metrics that strongly characterize financial statements
    CORE_FINANCIAL_METRICS = {
        "revenue",
        "assets",
        "liabilities",
        "equity",
        "net_income",
        "operating_income",
        "gross_profit",
        "cash",
        "expenses",
        "current_assets",
        "current_liabilities",
        "ebitda",
        "accounts_receivable",
        "accounts_payable",
        "inventory",
        "current_ratio",
        "debt_to_equity",
        "roe",
        "roa",
    }

    def __init__(self, field_mapper: Optional[FieldMapper] = None):
        self.field_mapper = field_mapper or FieldMapper()
        self.value_cleaner = ValueCleaner()

    def classify(self, raw_data: RawExtractionData) -> Tuple[bool, str, Set[str]]:
        """Determine whether raw extracted data represents a valid financial statement.

        Args:
            raw_data: Standardized raw extraction output.

        Returns:
            Tuple of:
              - is_valid (bool): True if verified as a financial statement, False otherwise.
              - reason (str): Human-readable justification or rejection explanation.
              - detected_metrics (Set[str]): Canonical metrics identified in document.
        """
        if not raw_data or not raw_data.tables:
            raw_text = str(raw_data.metadata.get("raw_text", "")) if raw_data and raw_data.metadata else ""
            if not raw_text.strip():
                return False, "Document contains no readable tabular data or financial statement text.", set()

        detected_metrics: Set[str] = set()
        matched_indicators: List[str] = []
        numeric_count = 0

        # 1. Check filename and metadata for indicators
        filename = (raw_data.source.filename if raw_data.source else "").lower()
        metadata_str = " ".join(str(v) for v in (raw_data.metadata or {}).values()).lower()
        combined_meta = f"{filename} {metadata_str}"

        for ind in self.STATEMENT_INDICATORS:
            if ind in combined_meta:
                matched_indicators.append(ind)

        # 2. Inspect tables: headers, row labels, and numeric cells
        for table in raw_data.tables:
            # Inspect table headers
            for header in table.headers:
                h_str = str(header).strip().lower()
                for ind in self.STATEMENT_INDICATORS:
                    if ind in h_str and ind not in matched_indicators:
                        matched_indicators.append(ind)

                canonical = self.field_mapper.map_field(h_str)
                if canonical and canonical in self.CORE_FINANCIAL_METRICS:
                    detected_metrics.add(canonical)

            # Inspect table rows
            for row in table.rows:
                if not row:
                    continue
                label_cell = str(row[0]).strip()
                l_lower = label_cell.lower()

                for ind in self.STATEMENT_INDICATORS:
                    if ind in l_lower and ind not in matched_indicators:
                        matched_indicators.append(ind)

                canonical = self.field_mapper.map_field(label_cell)
                if canonical and canonical in self.CORE_FINANCIAL_METRICS:
                    detected_metrics.add(canonical)

                for cell in row[1:]:
                    num_val, _ = self.value_cleaner.clean_numeric(cell)
                    if num_val is not None:
                        numeric_count += 1

                num_val0, _ = self.value_cleaner.clean_numeric(label_cell)
                if num_val0 is not None:
                    numeric_count += 1

        # 3. Inspect metadata raw_text (PDF fallback)
        raw_text = str(raw_data.metadata.get("raw_text", "")) if raw_data.metadata else ""
        if raw_text:
            text_lower = raw_text.lower()
            for ind in self.STATEMENT_INDICATORS:
                if ind in text_lower and ind not in matched_indicators:
                    matched_indicators.append(ind)
            for line in raw_text.splitlines()[:50]:
                canonical = self.field_mapper.map_field(line.strip())
                if canonical and canonical in self.CORE_FINANCIAL_METRICS:
                    detected_metrics.add(canonical)

        # 4. Evaluation Rules
        # Rule A: Explicit statement indicator found AND at least 1 financial metric or numeric financial data
        if matched_indicators and (len(detected_metrics) >= 1 or numeric_count >= 1):
            return True, f"Verified financial statement matching '{matched_indicators[0]}' with {len(detected_metrics)} financial metrics.", detected_metrics

        # Rule B: At least 2 distinct core financial metrics found
        if len(detected_metrics) >= 2:
            metrics_joined = ", ".join(sorted(detected_metrics))
            return True, f"Verified financial statement containing {len(detected_metrics)} core financial metrics: {metrics_joined}.", detected_metrics

        # Rule C: At least 1 core balance sheet / income statement metric AND numeric data
        primary_metrics = {"revenue", "assets", "liabilities", "equity", "net_income"}
        if len(detected_metrics.intersection(primary_metrics)) >= 1 and numeric_count >= 1:
            return True, "Verified financial statement containing primary financial metric with numeric data.", detected_metrics

        logger.info(
            "Document rejected: Not a financial statement. Indicators=%s, Metrics=%s, NumericCount=%d",
            matched_indicators, detected_metrics, numeric_count
        )
        return (
            False,
            "Document rejected: Uploaded file is not recognized as a valid financial statement. "
            "A valid financial statement must contain a Balance Sheet, Income Statement, Cash Flow statement, "
            "or core financial metrics (e.g., Revenue, Assets, Liabilities, Equity).",
            detected_metrics,
        )
