"""PDF Report Generator for Finny Financial Statement Review.

Generates a publication-grade PDF report containing:
- Document header & metadata (company, fiscal period, currency, dates)
- Risk Tier executive badge (LOW, MEDIUM, HIGH) with derivation rationale
- Core Key Financial Indicators table
- Mathematical Balance Sheet validation
- Financial Ratios (Liquidity, Profitability, Leverage)
- Year-over-Year (YoY) Variances
- Isolation Forest ML Anomaly Assessment
- Agent 2 Grounded Review Observations & Recommendations
"""

import io
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import (
    HRFlowable,
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

logger = logging.getLogger(__name__)

# Styling Palette (Modern Navy & Slate Theme)
COLOR_PRIMARY = colors.HexColor("#0f172a")      # Slate 900
COLOR_SECONDARY = colors.HexColor("#4f46e5")    # Indigo 600
COLOR_TEXT_MAIN = colors.HexColor("#1e293b")    # Slate 800
COLOR_TEXT_MUTED = colors.HexColor("#64748b")   # Slate 500
COLOR_BG_LIGHT = colors.HexColor("#f8fafc")     # Slate 50
COLOR_BORDER = colors.HexColor("#e2e8f0")       # Slate 200

COLOR_EMERALD = colors.HexColor("#059669")
COLOR_EMERALD_BG = colors.HexColor("#ecfdf5")
COLOR_AMBER = colors.HexColor("#d97706")
COLOR_AMBER_BG = colors.HexColor("#fffbeb")
COLOR_ROSE = colors.HexColor("#e11d48")
COLOR_ROSE_BG = colors.HexColor("#fff1f2")


from app.services.normalization.currency_normalizer import CurrencyNormalizer


def _format_currency(val: Any, currency: Optional[str] = "USD") -> str:
    """Format numeric values into clean currency strings using detected document currency."""
    if val is None:
        return "N/A"
    try:
        num = float(val)
        curr_symbol = CurrencyNormalizer.get_currency_symbol(currency)

        if abs(num) >= 1_000_000_000:
            return f"{curr_symbol}{num / 1_000_000_000:,.2f}B"
        elif abs(num) >= 1_000_000:
            return f"{curr_symbol}{num / 1_000_000:,.2f}M"
        elif abs(num) >= 1_000:
            return f"{curr_symbol}{num:,.0f}"
        else:
            return f"{curr_symbol}{num:,.2f}"
    except (ValueError, TypeError):
        return str(val)


def _format_num(val: Any, suffix: str = "") -> str:
    """Format float or ratio values."""
    if val is None:
        return "N/A"
    try:
        return f"{float(val):.2f}{suffix}"
    except (ValueError, TypeError):
        return str(val)


class PDFReportBuilder:
    """Generates clean executive PDF reports from DashboardSummaryResponse data."""

    @classmethod
    def build_pdf(cls, data: Dict[str, Any]) -> io.BytesIO:
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            leftMargin=36,
            rightMargin=36,
            topMargin=36,
            bottomMargin=36,
            title=f"Finny Financial Review - {data.get('filename', 'Report')}",
            author="Finny Intelligent Financial Review Agent",
        )

        styles = getSampleStyleSheet()

        # Base custom styles
        style_title = ParagraphStyle(
            "DocTitle",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=18,
            leading=22,
            textColor=COLOR_PRIMARY,
        )
        style_subtitle = ParagraphStyle(
            "DocSubtitle",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=9,
            leading=12,
            textColor=COLOR_TEXT_MUTED,
        )
        style_sec_heading = ParagraphStyle(
            "SecHeading",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=12,
            leading=16,
            textColor=COLOR_SECONDARY,
            spaceAfter=4,
            spaceBefore=10,
        )
        style_body = ParagraphStyle(
            "Body",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=8.5,
            leading=11,
            textColor=COLOR_TEXT_MAIN,
        )
        style_body_bold = ParagraphStyle(
            "BodyBold",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=8.5,
            leading=11,
            textColor=COLOR_PRIMARY,
        )
        style_badge = ParagraphStyle(
            "RiskBadge",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=11,
            leading=13,
            alignment=1,  # Centered
        )

        story: List[Any] = []

        # ==========================================
        # 1. HEADER SECTION
        # ==========================================
        company = data.get("company_name") or "Entity Financial Statement"
        period = data.get("period") or "Latest Fiscal Period"
        currency = data.get("currency") or "USD"
        filename = data.get("filename") or "statement.pdf"
        processed_at = data.get("processed_at") or data.get("uploaded_at") or datetime.now().isoformat()
        try:
            date_str = datetime.fromisoformat(str(processed_at).replace("Z", "+00:00")).strftime("%b %d, %Y %H:%M UTC")
        except Exception:
            date_str = str(processed_at)

        header_data = [
            [
                Paragraph("<b>FINNY FINANCIAL STATEMENT REVIEW</b>", style_title),
                Paragraph(f"<b>Generated:</b> {date_str}<br/><b>File:</b> {filename}", style_subtitle),
            ],
            [
                Paragraph(f"<b>Entity:</b> {company} &nbsp;|&nbsp; <b>Period:</b> {period} &nbsp;|&nbsp; <b>Currency:</b> {currency}", style_body),
                "",
            ],
        ]

        header_table = Table(header_data, colWidths=[380, 160])
        header_table.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("SPAN", (0, 1), (1, 1)),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ("TOPPADDING", (0, 0), (-1, -1), 2),
        ]))
        story.append(header_table)
        story.append(HRFlowable(width="100%", thickness=1.5, color=COLOR_SECONDARY, spaceBefore=4, spaceAfter=8))

        # ==========================================
        # 2. EXECUTIVE SUMMARY & RISK ASSESSMENT
        # ==========================================
        risk = data.get("risk") or {}
        tier = str(risk.get("tier", "UNKNOWN")).upper()
        iso_score = risk.get("score")
        iso_cls = risk.get("classification", "NORMAL")
        bs_stat = risk.get("balance_sheet_status", "UNKNOWN")

        if tier == "LOW":
            badge_bg = COLOR_EMERALD_BG
            badge_fg = COLOR_EMERALD
            badge_border = COLOR_EMERALD
        elif tier == "MEDIUM":
            badge_bg = COLOR_AMBER_BG
            badge_fg = COLOR_AMBER
            badge_border = COLOR_AMBER
        else:
            badge_bg = COLOR_ROSE_BG
            badge_fg = COLOR_ROSE
            badge_border = COLOR_ROSE

        badge_style = ParagraphStyle(
            "BadgeStyle",
            parent=style_badge,
            textColor=badge_fg,
        )

        derivation_notes = risk.get("derivation_notes") or []
        notes_text = "<br/>".join([f"• {note}" for note in derivation_notes]) if derivation_notes else "Full deterministic accounting and statistical evaluation completed."

        score_text = f"{iso_score:.4f}" if iso_score is not None else "N/A"
        risk_summary_data = [
            [
                Paragraph(f"<b>OVERALL RISK TIER:</b><br/>{tier}", badge_style),
                Paragraph(
                    f"<b>Isolation Forest Score:</b> {score_text} ({iso_cls})<br/>"
                    f"<b>Balance Sheet Status:</b> {bs_stat}<br/>"
                    f"<b>Issues Flagged:</b> {risk.get('critical_count', 0)} Critical, {risk.get('high_count', 0)} High, {risk.get('medium_count', 0)} Medium",
                    style_body,
                ),
                Paragraph(f"<b>Risk Derivation:</b><br/>{notes_text}", style_subtitle),
            ]
        ]

        risk_table = Table(risk_summary_data, colWidths=[130, 180, 230])
        risk_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (0, 0), badge_bg),
            ("BOX", (0, 0), (0, 0), 1, badge_border),
            ("BOX", (0, 0), (-1, -1), 0.5, COLOR_BORDER),
            ("BACKGROUND", (1, 0), (-1, -1), COLOR_BG_LIGHT),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ]))
        story.append(risk_table)
        story.append(Spacer(1, 10))

        # ==========================================
        # 3. CORE FINANCIAL HEALTH INDICATORS
        # ==========================================
        story.append(Paragraph("1. Core Financial Indicators", style_sec_heading))
        fin = data.get("financial_data") or {}

        fin_rows = [
            [
                Paragraph("<b>Revenue</b>", style_body),
                Paragraph(_format_currency(fin.get("revenue"), currency), style_body_bold),
                Paragraph("<b>Operating Income</b>", style_body),
                Paragraph(_format_currency(fin.get("operating_income"), currency), style_body_bold),
            ],
            [
                Paragraph("<b>Gross Profit</b>", style_body),
                Paragraph(_format_currency(fin.get("gross_profit"), currency), style_body_bold),
                Paragraph("<b>Net Income</b>", style_body),
                Paragraph(_format_currency(fin.get("net_income"), currency), style_body_bold),
            ],
            [
                Paragraph("<b>Total Assets</b>", style_body),
                Paragraph(_format_currency(fin.get("assets"), currency), style_body_bold),
                Paragraph("<b>Total Liabilities</b>", style_body),
                Paragraph(_format_currency(fin.get("liabilities"), currency), style_body_bold),
            ],
            [
                Paragraph("<b>Shareholders' Equity</b>", style_body),
                Paragraph(_format_currency(fin.get("equity"), currency), style_body_bold),
                Paragraph("<b>Cash & Equivalents</b>", style_body),
                Paragraph(_format_currency(fin.get("cash"), currency), style_body_bold),
            ],
        ]

        fin_table = Table(fin_rows, colWidths=[130, 140, 130, 140])
        fin_table.setStyle(TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.5, COLOR_BORDER),
            ("BACKGROUND", (0, 0), (0, -1), COLOR_BG_LIGHT),
            ("BACKGROUND", (2, 0), (2, -1), COLOR_BG_LIGHT),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ]))
        story.append(fin_table)
        story.append(Spacer(1, 8))

        # ==========================================
        # 4. BALANCE SHEET MATHEMATICAL VALIDATION
        # ==========================================
        story.append(Paragraph("2. Mathematical Validation (Assets = Liabilities + Equity)", style_sec_heading))
        val = (data.get("validation") or {}).get("balance_sheet_check") or {}
        val_status = val.get("status", "UNKNOWN")
        diff = val.get("difference", 0.0)
        assets_val = val.get("assets")
        l_plus_e = val.get("liabilities_plus_equity")

        val_rows = [
            [
                Paragraph("<b>Equation Status</b>", style_body),
                Paragraph(f"<b>{val_status}</b>", ParagraphStyle("VS", parent=style_body, textColor=COLOR_EMERALD if val_status == "VALID" else COLOR_ROSE)),
                Paragraph("<b>Variance Difference</b>", style_body),
                Paragraph(_format_currency(diff, currency), style_body_bold),
            ],
            [
                Paragraph("<b>Total Assets</b>", style_body),
                Paragraph(_format_currency(assets_val, currency), style_body),
                Paragraph("<b>Liabilities + Equity</b>", style_body),
                Paragraph(_format_currency(l_plus_e, currency), style_body),
            ],
        ]
        val_table = Table(val_rows, colWidths=[130, 140, 130, 140])
        val_table.setStyle(TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.5, COLOR_BORDER),
            ("BACKGROUND", (0, 0), (0, -1), COLOR_BG_LIGHT),
            ("BACKGROUND", (2, 0), (2, -1), COLOR_BG_LIGHT),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ]))
        story.append(val_table)
        story.append(Spacer(1, 8))

        # ==========================================
        # 5. FINANCIAL RATIOS (Liquidity, Profitability, Leverage)
        # ==========================================
        story.append(Paragraph("3. Financial Ratio Analysis", style_sec_heading))
        ratio_obj = (data.get("ratio_analysis") or {}).get("ratios") or {}
        liq = ratio_obj.get("liquidity") or {}
        prof = ratio_obj.get("profitability") or {}
        lev = ratio_obj.get("leverage") or {}

        def _val(d: Dict, k: str, suffix: str = "") -> str:
            item = d.get(k) or {}
            v = item.get("value")
            return _format_num(v, suffix)

        ratio_rows = [
            [
                Paragraph("<b>Category</b>", style_body_bold),
                Paragraph("<b>Ratio Metric</b>", style_body_bold),
                Paragraph("<b>Result</b>", style_body_bold),
                Paragraph("<b>Benchmark / Guidance</b>", style_body_bold),
            ],
            # Liquidity
            [
                Paragraph("Liquidity", style_body),
                Paragraph("Current Ratio", style_body),
                Paragraph(_val(liq, "current_ratio"), style_body_bold),
                Paragraph(">= 1.0 (Healthy working capital)", style_subtitle),
            ],
            [
                Paragraph("", style_body),
                Paragraph("Quick Ratio (Acid-Test)", style_body),
                Paragraph(_val(liq, "quick_ratio"), style_body_bold),
                Paragraph(">= 0.8 (Liquid cash & receivables)", style_subtitle),
            ],
            # Profitability
            [
                Paragraph("Profitability", style_body),
                Paragraph("Gross Profit Margin", style_body),
                Paragraph(_val(prof, "gross_profit_margin", "%"), style_body_bold),
                Paragraph("Direct margin efficiency", style_subtitle),
            ],
            [
                Paragraph("", style_body),
                Paragraph("Net Profit Margin", style_body),
                Paragraph(_val(prof, "net_profit_margin", "%"), style_body_bold),
                Paragraph("Bottom-line profitability", style_subtitle),
            ],
            [
                Paragraph("", style_body),
                Paragraph("Return on Assets (ROA)", style_body),
                Paragraph(_val(prof, "return_on_assets", "%"), style_body_bold),
                Paragraph("Asset utilization performance", style_subtitle),
            ],
            [
                Paragraph("", style_body),
                Paragraph("Return on Equity (ROE)", style_body),
                Paragraph(_val(prof, "return_on_equity", "%"), style_body_bold),
                Paragraph("Shareholder capital efficiency", style_subtitle),
            ],
            # Leverage
            [
                Paragraph("Leverage", style_body),
                Paragraph("Debt-to-Equity", style_body),
                Paragraph(_val(lev, "debt_to_equity"), style_body_bold),
                Paragraph("<= 2.0 (Conservative leverage)", style_subtitle),
            ],
            [
                Paragraph("", style_body),
                Paragraph("Debt Ratio", style_body),
                Paragraph(_val(lev, "debt_ratio"), style_body_bold),
                Paragraph("Proportion of assets financed by debt", style_subtitle),
            ],
        ]

        ratio_table = Table(ratio_rows, colWidths=[90, 150, 90, 210])
        ratio_table.setStyle(TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.5, COLOR_BORDER),
            ("BACKGROUND", (0, 0), (-1, 0), COLOR_BG_LIGHT),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("LEFTPADDING", (0, 0), (-1, -1), 5),
            ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ]))
        story.append(ratio_table)
        story.append(Spacer(1, 8))

        # ==========================================
        # 6. YEAR-OVER-YEAR (YOY) VARIANCES
        # ==========================================
        yoy = data.get("yoy_analysis") or {}
        yoy_fin = yoy.get("financial_data") or {}
        periods = yoy.get("periods") or {}
        p_prev = periods.get("previous") or "Prior"
        p_curr = periods.get("current") or "Current"

        if yoy_fin and yoy.get("status") != "INSUFFICIENT_PERIODS":
            story.append(Paragraph(f"4. Year-over-Year Analysis ({p_prev} vs {p_curr})", style_sec_heading))
            yoy_rows = [
                [
                    Paragraph("<b>Metric</b>", style_body_bold),
                    Paragraph(f"<b>{p_prev}</b>", style_body_bold),
                    Paragraph(f"<b>{p_curr}</b>", style_body_bold),
                    Paragraph("<b>Absolute Variance</b>", style_body_bold),
                    Paragraph("<b>YoY %</b>", style_body_bold),
                ]
            ]
            key_metrics = ["revenue", "gross_profit", "net_income", "assets", "liabilities", "equity", "cash"]
            for m in key_metrics:
                m_data = yoy_fin.get(m) or {}
                prev_v = m_data.get("previous")
                curr_v = m_data.get("current")
                abs_v = m_data.get("absolute_change")
                pct_v = m_data.get("percentage_change")
                if prev_v is not None or curr_v is not None:
                    pct_str = f"{pct_v:+.1f}%" if pct_v is not None else "N/A"
                    yoy_rows.append([
                        Paragraph(m.replace("_", " ").title(), style_body),
                        Paragraph(_format_currency(prev_v, currency), style_body),
                        Paragraph(_format_currency(curr_v, currency), style_body),
                        Paragraph(_format_currency(abs_v, currency), style_body_bold),
                        Paragraph(pct_str, style_body_bold),
                    ])

            yoy_table = Table(yoy_rows, colWidths=[120, 105, 105, 110, 100])
            yoy_table.setStyle(TableStyle([
                ("GRID", (0, 0), (-1, -1), 0.5, COLOR_BORDER),
                ("BACKGROUND", (0, 0), (-1, 0), COLOR_BG_LIGHT),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
            ]))
            story.append(yoy_table)
            story.append(Spacer(1, 8))

        # ==========================================
        # 7. AGENT 2 AUDIT OBSERVATIONS & RECOMMENDATIONS
        # ==========================================
        obs_container = data.get("review_observations") or {}
        observations = obs_container.get("observations") or []

        if observations:
            obs_flowables: List[Any] = [
                Paragraph("5. AI Agent 2 Review Findings & Recommendations", style_sec_heading),
                Paragraph(
                    f"Audit model {obs_container.get('model', 'LLM')} completed grounded inspection based strictly on mathematical verification and ML anomaly metrics.",
                    style_subtitle,
                ),
                Spacer(1, 4),
            ]

            obs_rows = [
                [
                    Paragraph("<b>Finding & Explanation</b>", style_body_bold),
                    Paragraph("<b>Severity</b>", style_body_bold),
                    Paragraph("<b>Evidence</b>", style_body_bold),
                    Paragraph("<b>Actionable Recommendation</b>", style_body_bold),
                ]
            ]

            for o in observations:
                title_val = o.get('finding') or o.get('title') or o.get('observation') or "Review Finding"
                finding_text = f"<b>{title_val}</b>"
                expl_val = o.get("explanation") or o.get("detail") or (o.get("observation") if title_val != o.get("observation") else None)
                if expl_val:
                    finding_text += f"<br/><font color='#64748b'>{expl_val}</font>"

                sev = str(o.get("severity", "LOW")).upper()
                sev_color = COLOR_EMERALD if sev == "LOW" else (COLOR_AMBER if sev == "MEDIUM" else COLOR_ROSE)
                sev_p = Paragraph(f"<b>{sev}</b>", ParagraphStyle("ObsSev", parent=style_body, textColor=sev_color))

                ev_items = o.get("evidence") or []
                if isinstance(ev_items, (str, bytes)):
                    ev_items = [ev_items]
                elif not isinstance(ev_items, list):
                    ev_items = [str(ev_items)]

                ev_lines = []
                for ev in ev_items:
                    if isinstance(ev, dict):
                        f_name = ev.get("field", "")
                        src = ev.get("source", "")
                        val_e = ev.get("value")
                        if f_name or src or val_e is not None:
                            ev_lines.append(f"• {f_name} ({src}): {val_e}")
                        else:
                            ev_lines.append(f"• {str(ev)}")
                    elif isinstance(ev, str):
                        ev_lines.append(f"• {ev}")
                    else:
                        ev_lines.append(f"• {str(ev)}")
                ev_p = Paragraph("<br/>".join(ev_lines) if ev_lines else "Grounded", style_subtitle)

                rec_text = o.get("recommendation") or o.get("evidence") or "Standard compliance check."
                if isinstance(rec_text, list):
                    rec_text = "; ".join(str(x) for x in rec_text)
                rec_p = Paragraph(str(rec_text), style_body)

                obs_rows.append([
                    Paragraph(finding_text, style_body),
                    sev_p,
                    ev_p,
                    rec_p,
                ])

            obs_table = Table(obs_rows, colWidths=[180, 55, 145, 160])
            obs_table.setStyle(TableStyle([
                ("GRID", (0, 0), (-1, -1), 0.5, COLOR_BORDER),
                ("BACKGROUND", (0, 0), (-1, 0), COLOR_BG_LIGHT),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
            ]))
            obs_flowables.append(obs_table)
            story.append(KeepTogether(obs_flowables))

        # Build document
        doc.build(story)
        buffer.seek(0)
        return buffer
