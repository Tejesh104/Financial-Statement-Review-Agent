"""Demo Documents Seeder for FINNY.

Ensures standard preloaded demo documents (doc-demo-healthy-01, doc-demo-highrisk-02, doc-demo-anomalous-03)
exist in the database with canonical financial metrics and observations, enabling full chatbot grounding,
validation, and analysis without 404 errors.
"""

import logging
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.models.document import Document, DocumentStatus
from app.models.financial_data import FinancialData

logger = logging.getLogger(__name__)

DEMO_SCENARIOS_DATA = {
    "doc-demo-healthy-01": {
        "id": "doc-demo-healthy-01",
        "filename": "Finny_Technologies_FY2025-26_Healthy.pdf",
        "company_name": "Finny Technologies Inc.",
        "currency": "USD",
        "fiscal_year": "2026",
        "revenue": 125000000.0,
        "assets": 180000000.0,
        "liabilities": 45000000.0,
        "equity": 135000000.0,
        "net_income": 28000000.0,
        "cash": 42000000.0,
        "operating_income": 35000000.0,
        "operating_cash_flow": 31000000.0,
        "gross_profit": 68000000.0,
        "expenses": 33000000.0,
        "current_assets": 65000000.0,
        "current_liabilities": 20000000.0,
        "previous_period_data": {
            "revenue": 100000000.0,
            "net_income": 22000000.0,
            "assets": 150000000.0,
            "liabilities": 40000000.0,
            "equity": 110000000.0,
        },
        "observations": [
            {
                "title": "Optimal Liquidity Position",
                "severity": "LOW",
                "observation": "Current ratio stands at 3.25x with strong cash buffer of $42.0M.",
                "evidence": "Cash and equivalents are $42M vs current liabilities of $20M."
            },
            {
                "title": "Consistent Revenue & Earnings Expansion",
                "severity": "LOW",
                "observation": "Revenue grew +25% YoY with 22.4% net margin.",
                "evidence": "Top-line expanded from $100M to $125M."
            }
        ],
        "balance_sheet_status": "BALANCED"
    },
    "doc-demo-highrisk-02": {
        "id": "doc-demo-highrisk-02",
        "filename": "Apex_Manufacturing_FY2025-26_HighRisk.pdf",
        "company_name": "Apex Manufacturing Pvt. Ltd.",
        "currency": "INR",
        "fiscal_year": "2026",
        "revenue": 45000000.0,
        "assets": 70200000.0,
        "liabilities": 52000000.0,
        "equity": 18200000.0,
        "net_income": -4500000.0,
        "cash": 2400000.0,
        "operating_income": -2500000.0,
        "operating_cash_flow": -6800000.0,
        "gross_profit": 11000000.0,
        "expenses": 13500000.0,
        "current_assets": 22000000.0,
        "current_liabilities": 28000000.0,
        "previous_period_data": {
            "revenue": 58000000.0,
            "net_income": 2500000.0,
            "assets": 65000000.0,
            "liabilities": 35000000.0,
            "equity": 30000000.0,
        },
        "observations": [
            {
                "title": "Severe Revenue Contraction & Deteriorating Profitability",
                "severity": "HIGH",
                "observation": "Annual top-line contracted -22.4% from ₹58.0M to ₹45.0M, driving net profit into negative ₹4.5M.",
                "evidence": "Revenue dropped from ₹58M to ₹45M; Net income fell from +₹2.5M to -₹4.5M."
            },
            {
                "title": "Negative Operating Cash Flow Burn",
                "severity": "HIGH",
                "observation": "Operating cash flow dropped to -₹6.8M, requiring external borrowing to sustain daily operations.",
                "evidence": "Cash flow from operations is negative ₹6.8M."
            },
            {
                "title": "Critical Debt-to-Equity Over-Leverage",
                "severity": "HIGH",
                "observation": "Total liabilities surged +48.5% to ₹52.0M against depleted shareholder equity of ₹18.2M (D/E: 2.86).",
                "evidence": "Debt-to-equity ratio of 2.86x indicates severe insolvency risk."
            }
        ],
        "balance_sheet_status": "BALANCED"
    },
    "doc-demo-anomalous-03": {
        "id": "doc-demo-anomalous-03",
        "filename": "Nova_Trading_FY2025-26_Anomalous.pdf",
        "company_name": "Nova Trading Pvt. Ltd.",
        "currency": "INR",
        "fiscal_year": "2026",
        "revenue": 84000000.0,
        "assets": 95000000.0,
        "liabilities": 62000000.0,
        "equity": 33000000.0,
        "net_income": 14200000.0,
        "cash": 1800000.0,
        "operating_income": 18000000.0,
        "operating_cash_flow": -4200000.0,
        "gross_profit": 28000000.0,
        "expenses": 10000000.0,
        "current_assets": 54000000.0,
        "current_liabilities": 38000000.0,
        "previous_period_data": {
            "revenue": 43700000.0,
            "net_income": 6500000.0,
            "assets": 60000000.0,
            "liabilities": 35000000.0,
            "equity": 25000000.0,
        },
        "observations": [
            {
                "title": "Divergent Revenue vs Operating Cash Flow Spike",
                "severity": "HIGH",
                "observation": "Revenue jumped +92% while operating cash flow plunged to -₹4.2M.",
                "evidence": "Divergence between accounting revenue and operating cash collection."
            },
            {
                "title": "Unusual Accounts Receivable Accumulation",
                "severity": "HIGH",
                "observation": "Receivables surged +145%, suggesting uncollected paper revenue.",
                "evidence": "Accounts receivable spiked to ₹32M."
            }
        ],
        "balance_sheet_status": "BALANCED"
    }
}


def ensure_demo_documents(db: Session):
    """Seed or update demo document records in DB so chatbot & analytics operate on them."""
    for demo_id, info in DEMO_SCENARIOS_DATA.items():
        doc = db.query(Document).filter(Document.id == demo_id).first()
        if not doc:
            doc = Document(
                id=demo_id,
                user_id=None,
                filename=info["filename"],
                file_type="pdf",
                file_path=info["filename"],
                status=DocumentStatus.NORMALIZED.value,
                uploaded_at=datetime.now(timezone.utc),
                processed_at=datetime.now(timezone.utc),
            )
            db.add(doc)
            db.commit()
            db.refresh(doc)
            logger.info("Seeded demo document: %s (%s)", demo_id, info["company_name"])

        # Check financial data
        fin = db.query(FinancialData).filter(FinancialData.document_id == demo_id).first()
        if not fin:
            normalized_payload = {
                "document_id": demo_id,
                "company": {"name": info["company_name"]},
                "currency": info["currency"],
                "period": {"fiscal_year": info["fiscal_year"]},
                "financial_data": {
                    "revenue": info["revenue"],
                    "assets": info["assets"],
                    "liabilities": info["liabilities"],
                    "equity": info["equity"],
                    "net_income": info["net_income"],
                    "cash": info["cash"],
                    "operating_income": info.get("operating_income"),
                    "operating_cash_flow": info.get("operating_cash_flow"),
                    "gross_profit": info.get("gross_profit"),
                    "expenses": info.get("expenses"),
                    "current_assets": info.get("current_assets"),
                    "current_liabilities": info.get("current_liabilities"),
                },
                "previous_period_data": info.get("previous_period_data"),
                "validation": {
                    "balance_sheet_check": {
                        "status": info["balance_sheet_status"],
                        "assets": info["assets"],
                        "liabilities": info["liabilities"],
                        "equity": info["equity"],
                    }
                },
                "review_observations": {
                    "observations": info.get("observations", [])
                },
                "source": {
                    "filename": info["filename"],
                    "file_type": "pdf"
                },
                "normalization_warnings": []
            }
            fin = FinancialData(
                document_id=demo_id,
                company_name=info["company_name"],
                currency=info["currency"],
                fiscal_year=info["fiscal_year"],
                revenue=info["revenue"],
                assets=info["assets"],
                liabilities=info["liabilities"],
                equity=info["equity"],
                normalized_data=normalized_payload,
            )
            db.add(fin)
            db.commit()
            logger.info("Seeded demo financial data: %s", demo_id)
