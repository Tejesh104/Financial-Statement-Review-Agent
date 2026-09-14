/**
 * FINNY Demo Financial Datasets (Frontend-Only Demo)
 * 
 * Defines 3 realistic, completely fictional corporate financial scenarios:
 * 1. Healthy: Finny Technologies Pvt. Ltd. (FY 2025-26)
 * 2. High Risk: Apex Manufacturing Pvt. Ltd. (FY 2025-26)
 * 3. Anomalous / Fraud Review: Nova Trading Pvt. Ltd. (FY 2025-26)
 */

export const DEMO_SCENARIOS = {
  healthy: {
    id: 'doc-demo-healthy-01',
    filename: 'Finny_Technologies_FY2025-26_Healthy.pdf',
    companyName: 'Finny Technologies Pvt. Ltd.',
    fileType: 'PDF',
    fileSize: '1.42 MB',
    uploadDate: '2026-03-31 10:15:00 UTC',
    screeningScore: 96.5,
    verificationStatus: 'VERIFIED - REVIEW READY',
    healthScore: 92.0,
    healthLabel: 'GOOD',
    overallRisk: 'LOW',
    fraudRisk: 'LOW / NO INDICATION',
    validationErrorCount: 0,
    riskFlagCount: 0,
    anomalyCount: 0,
    yoyChangePercentage: 25.0,
    currency_meta: { symbol: '₹', code: 'INR', unit: 'INR', divisor: 1 },
    checks: {
      file_integrity: { status: 'PASS', detail: 'SHA-256 cryptographic hash verified. Byte stream intact with zero payload corruption.' },
      document_structure: { status: 'PASS', detail: 'Audited statutory format identified. Multi-year balance sheets and P&L tables mapped.' },
      metadata: { status: 'PASS', detail: 'Authoring timestamp aligns with statutory filing calendar for FY 2025-26.' },
      font_render: { status: 'PASS', detail: 'Embedded OpenType font tables match approved corporate auditor styles.' },
      layer_screening: { status: 'PASS', detail: 'Clean single-layer rendering verified. No graphical overlays or numeric splicing detected.' },
      cross_page: { status: 'PASS', detail: 'All page subtotals and cross-page carry-forward balances reconcile deterministically.' },
      classification_status: 'ACCEPTED'
    },
    findings: [],
    details: {
      company: 'Finny Technologies Pvt. Ltd.',
      latest_year: '2026',
      previous_year: '2025',
      previous_year_status: 'AVAILABLE',
      status: 'COMPLETED',
      health_score: 92.0,
      document_health_score: 92.0,
      currency_meta: { symbol: '₹', code: 'INR', unit: 'INR', divisor: 1 },
      executive_summary: 'Finny Technologies demonstrates exceptional fiscal stability in FY 2025-26 with robust revenue growth (+25.0%), healthy operating margins (24.4%), zero debt covenants, and strong positive operating cash flows (₹9.2M). All mathematical balance sheet equations balance with zero variance.',
      annual_statements: [
        {
          fiscal_year: 2026,
          period: 'FY 2025-26',
          revenue: 45000000,
          cost_of_goods_sold: 22000000,
          gross_profit: 23000000,
          operating_expenses: 12000000,
          operating_income: 11000000,
          net_income: 8500000,
          operating_cash_flow: 9200000,
          total_assets: 65000000,
          current_assets: 32000000,
          cash_and_equivalents: 14000000,
          accounts_receivable: 8500000,
          inventory: 9500000,
          total_liabilities: 20000000,
          current_liabilities: 11000000,
          total_equity: 45000000,
          retained_earnings: 28000000,
        },
        {
          fiscal_year: 2025,
          period: 'FY 2024-25',
          revenue: 36000000,
          cost_of_goods_sold: 18000000,
          gross_profit: 18000000,
          operating_expenses: 10000000,
          operating_income: 8000000,
          net_income: 6200000,
          operating_cash_flow: 7100000,
          total_assets: 52000000,
          current_assets: 25000000,
          cash_and_equivalents: 11000000,
          accounts_receivable: 6800000,
          inventory: 7200000,
          total_liabilities: 18000000,
          current_liabilities: 9500000,
          total_equity: 34000000,
          retained_earnings: 19500000,
        }
      ],
      yoy_comparisons: [
        {
          period_pair: 'FY 2025-26 vs FY 2024-25',
          metrics: {
            revenue: { current: 45000000, previous: 36000000, abs_change: 9000000, pct_change: 25.0, direction: 'UP' },
            gross_profit: { current: 23000000, previous: 18000000, abs_change: 5000000, pct_change: 27.78, direction: 'UP' },
            operating_income: { current: 11000000, previous: 8000000, abs_change: 3000000, pct_change: 37.5, direction: 'UP' },
            net_income: { current: 8500000, previous: 6200000, abs_change: 2300000, pct_change: 37.1, direction: 'UP' },
            operating_cash_flow: { current: 9200000, previous: 7100000, abs_change: 2100000, pct_change: 29.58, direction: 'UP' },
            total_assets: { current: 65000000, previous: 52000000, abs_change: 13000000, pct_change: 25.0, direction: 'UP' },
            total_liabilities: { current: 20000000, previous: 18000000, abs_change: 2000000, pct_change: 11.11, direction: 'UP' },
            total_equity: { current: 45000000, previous: 34000000, abs_change: 11000000, pct_change: 32.35, direction: 'UP' },
          }
        }
      ],
      ratios: [
        { name: 'Gross Profit Margin', value: 51.11, benchmark: '40% - 60%', status: 'HEALTHY', category: 'Profitability' },
        { name: 'Operating Margin', value: 24.44, benchmark: '15% - 25%', status: 'HEALTHY', category: 'Profitability' },
        { name: 'Net Profit Margin', value: 18.89, benchmark: '10% - 20%', status: 'HEALTHY', category: 'Profitability' },
        { name: 'Current Ratio', value: 2.91, benchmark: '1.5 - 3.0', status: 'HEALTHY', category: 'Liquidity' },
        { name: 'Debt-to-Equity Ratio', value: 0.44, benchmark: '< 1.5', status: 'HEALTHY', category: 'Solvency' },
        { name: 'Operating Cash Flow Margin', value: 20.44, benchmark: '> 15%', status: 'HEALTHY', category: 'Cash Flow' },
        { name: 'Return on Equity (ROE)', value: 18.89, benchmark: '> 12%', status: 'HEALTHY', category: 'Returns' },
      ],
      variances: [
        { metric: 'Revenue Growth', variance: 25.0, classification: 'NORMAL', expected_range: '10% - 30%' },
        { metric: 'Gross Profit Expansion', variance: 27.78, classification: 'NORMAL', expected_range: '15% - 35%' },
        { metric: 'Operating Expenses Delta', variance: 20.0, classification: 'NORMAL', expected_range: '10% - 25%' },
        { metric: 'Operating Cash Flow', variance: 29.58, classification: 'NORMAL', expected_range: '15% - 35%' },
      ],
      accounting_equation: {
        balanced: true,
        assets: 65000000,
        liabilities: 20000000,
        equity: 45000000,
        discrepancy: 0,
        formula: 'Assets (₹65,000,000) = Liabilities (₹20,000,000) + Equity (₹45,000,000)'
      },
      consistency_checks: [
        { name: 'Balance Sheet Equation', status: 'PASS', detail: 'Total Assets (₹65.0M) strictly equals Liabilities (₹20.0M) plus Equity (₹45.0M).' },
        { name: 'Operating Cash Flow Reconciliation', status: 'PASS', detail: 'Operating Cash Flow (₹9.2M) exceeds Net Profit (₹8.5M), demonstrating solid earnings quality.' },
        { name: 'Gross Margin Invariance', status: 'PASS', detail: 'Gross profit variance is mathematically congruent with revenue and cost changes.' }
      ],
      anomalies: [],
      risk_indicators: []
    },
    report: {
      report_title: 'Independent Financial Review & Audit Opinion - Finny Technologies',
      created_at: '2026-03-31T10:18:00.000Z',
      status: 'VERIFIED - CLEAN OPINION',
      executive_summary: 'FINNY AUDIT OPINION: UNQUALIFIED (CLEAN). Finny Technologies Pvt. Ltd. shows excellent solvency, sustainable cash flow conversion, and full mathematical integrity across all statements.',
      financial_highlights: {
        total_revenue: '₹45,000,000 (+25.0% YoY)',
        net_profit: '₹8,500,000 (18.89% Margin)',
        operating_cash_flow: '₹9,200,000 (Robust)',
        current_ratio: '2.91 (Strong Liquidity)',
        debt_to_equity: '0.44 (Conservative)',
        composite_health: '92.0 / 100 (GOOD)'
      },
      recommendations: [
        'Maintain conservative working capital reserves while deploying excess operational liquidity into core expansion.',
        'Sustain disciplined trade receivables collections cycle currently performing at optimal velocity.',
        'No corrective accounting adjustments or qualification required for FY 2025-26.'
      ],
      financial_health: 'GOOD',
      risk_level: 'LOW',
      fraud_risk: 'LOW / NO INDICATION',
      composite_score: 92.0,
      generated_at: '2026-03-31 10:18:00 UTC'
    }
  },

  high_risk: {
    id: 'doc-demo-highrisk-02',
    filename: 'Apex_Manufacturing_FY2025-26_HighRisk.pdf',
    companyName: 'Apex Manufacturing Pvt. Ltd.',
    fileType: 'PDF',
    fileSize: '1.68 MB',
    uploadDate: '2026-03-31 11:20:00 UTC',
    screeningScore: 81.0,
    verificationStatus: 'VERIFIED - HIGH RISK DETECTED',
    healthScore: 38.0,
    healthLabel: 'WEAK',
    overallRisk: 'HIGH',
    fraudRisk: 'REVIEW REQUIRED',
    validationErrorCount: 2,
    riskFlagCount: 4,
    anomalyCount: 3,
    yoyChangePercentage: -22.4,
    currency_meta: { symbol: '₹', code: 'INR', unit: 'INR', divisor: 1 },
    checks: {
      file_integrity: { status: 'PASS', detail: 'Binary integrity verified. Document is readable.' },
      document_structure: { status: 'WARNING', detail: 'Elevated debt schedules and restructured current liability maturities detected.' },
      metadata: { status: 'PASS', detail: 'Filing timestamp confirmed for FY 2025-26.' },
      font_render: { status: 'PASS', detail: 'Consistent typography rendered.' },
      layer_screening: { status: 'PASS', detail: 'No PDF layer manipulation found.' },
      cross_page: { status: 'WARNING', detail: 'Operating cash flow deficit noted across Schedule III notes.' },
      classification_status: 'ACCEPTED'
    },
    findings: [
      {
        id: 'RISK-01',
        title: 'Severe Revenue Contraction & Deteriorating Profitability',
        category: 'Operating Distress',
        severity: 'HIGH',
        evidence: 'Annual top-line contracted -22.4% from ₹58.0M to ₹45.0M, driving net profit into negative ₹4.5M.'
      },
      {
        id: 'RISK-02',
        title: 'Negative Operating Cash Flow Burn',
        category: 'Liquidity Risk',
        severity: 'HIGH',
        evidence: 'Operating cash flow dropped to -₹6.8M, requiring external borrowing to sustain daily operations.'
      },
      {
        id: 'RISK-03',
        title: 'Critical Debt-to-Equity Over-Leverage',
        category: 'Solvency Risk',
        severity: 'HIGH',
        evidence: 'Total liabilities surged +48.5% to ₹52.0M against depleted shareholder equity of ₹18.2M (D/E: 2.86).'
      }
    ],
    details: {
      company: 'Apex Manufacturing Pvt. Ltd.',
      latest_year: '2026',
      previous_year: '2025',
      previous_year_status: 'AVAILABLE',
      status: 'COMPLETED',
      health_score: 38.0,
      document_health_score: 38.0,
      currency_meta: { symbol: '₹', code: 'INR', unit: 'INR', divisor: 1 },
      executive_summary: 'Apex Manufacturing exhibits acute financial distress in FY 2025-26 characterized by sharp revenue decline (-22.4%), persistent negative operating cash burn (-₹6.8M), deteriorating net losses (-₹4.5M), and alarming leverage with debt-to-equity reaching 2.86x.',
      annual_statements: [
        {
          fiscal_year: 2026,
          period: 'FY 2025-26',
          revenue: 45000000,
          cost_of_goods_sold: 34000000,
          gross_profit: 11000000,
          operating_expenses: 13500000,
          operating_income: -2500000,
          net_income: -4500000,
          operating_cash_flow: -6800000,
          total_assets: 70200000,
          current_assets: 22000000,
          cash_and_equivalents: 2400000,
          accounts_receivable: 11600000,
          inventory: 8000000,
          total_liabilities: 52000000,
          current_liabilities: 28000000,
          total_equity: 18200000,
          retained_earnings: 6200000,
        },
        {
          fiscal_year: 2025,
          period: 'FY 2024-25',
          revenue: 58000000,
          cost_of_goods_sold: 38000000,
          gross_profit: 20000000,
          operating_expenses: 14000000,
          operating_income: 6000000,
          net_income: 3800000,
          operating_cash_flow: 4200000,
          total_assets: 67000000,
          current_assets: 29000000,
          cash_and_equivalents: 8500000,
          accounts_receivable: 12000000,
          inventory: 8500000,
          total_liabilities: 35000000,
          current_liabilities: 18000000,
          total_equity: 32000000,
          retained_earnings: 10700000,
        }
      ],
      yoy_comparisons: [
        {
          period_pair: 'FY 2025-26 vs FY 2024-25',
          metrics: {
            revenue: { current: 45000000, previous: 58000000, abs_change: -13000000, pct_change: -22.41, direction: 'DOWN' },
            gross_profit: { current: 11000000, previous: 20000000, abs_change: -9000000, pct_change: -45.0, direction: 'DOWN' },
            operating_income: { current: -2500000, previous: 6000000, abs_change: -8500000, pct_change: -141.67, direction: 'DOWN' },
            net_income: { current: -4500000, previous: 3800000, abs_change: -8300000, pct_change: -218.42, direction: 'DOWN' },
            operating_cash_flow: { current: -6800000, previous: 4200000, abs_change: -11000000, pct_change: -261.9, direction: 'DOWN' },
            total_assets: { current: 70200000, previous: 67000000, abs_change: 3200000, pct_change: 4.78, direction: 'UP' },
            total_liabilities: { current: 52000000, previous: 35000000, abs_change: 17000000, pct_change: 48.57, direction: 'UP' },
            total_equity: { current: 18200000, previous: 32000000, abs_change: -13800000, pct_change: -43.12, direction: 'DOWN' },
          }
        }
      ],
      ratios: [
        { name: 'Gross Profit Margin', value: 24.44, benchmark: '40% - 60%', status: 'HIGH RISK', category: 'Profitability' },
        { name: 'Operating Margin', value: -5.56, benchmark: '15% - 25%', status: 'CRITICAL', category: 'Profitability' },
        { name: 'Net Profit Margin', value: -10.0, benchmark: '10% - 20%', status: 'CRITICAL', category: 'Profitability' },
        { name: 'Current Ratio', value: 0.79, benchmark: '1.5 - 3.0', status: 'HIGH RISK', category: 'Liquidity' },
        { name: 'Debt-to-Equity Ratio', value: 2.86, benchmark: '< 1.5', status: 'CRITICAL', category: 'Solvency' },
        { name: 'Operating Cash Flow Margin', value: -15.11, benchmark: '> 15%', status: 'CRITICAL', category: 'Cash Flow' },
        { name: 'Return on Equity (ROE)', value: -24.73, benchmark: '> 12%', status: 'CRITICAL', category: 'Returns' },
      ],
      variances: [
        { metric: 'Revenue Contraction', variance: -22.41, classification: 'HIGH VARIANCE', expected_range: '10% - 30%' },
        { metric: 'Debt Escalation', variance: 48.57, classification: 'HIGH VARIANCE', expected_range: '5% - 20%' },
        { metric: 'Operating Cash Collapse', variance: -261.9, classification: 'HIGH VARIANCE', expected_range: '15% - 35%' },
      ],
      accounting_equation: {
        balanced: true,
        assets: 70200000,
        liabilities: 52000000,
        equity: 18200000,
        discrepancy: 0,
        formula: 'Assets (₹70,200,000) = Liabilities (₹52,000,000) + Equity (₹18,200,000)'
      },
      consistency_checks: [
        { name: 'Current Ratio Assessment', status: 'FAIL', detail: 'Current ratio (0.79) falls below critical liquidity threshold (1.0).' },
        { name: 'Cash Flow Coverage', status: 'FAIL', detail: 'Negative operating cash flow cannot cover mandatory debt servicing obligations.' },
        { name: 'Solvency Margin', status: 'FAIL', detail: 'Debt-to-Equity (2.86x) exposes entity to insolvency default covenant risk.' }
      ],
      anomalies: [
        {
          id: 'RISK-01',
          name: 'Operating Cash vs Net Income Disconnect',
          severity: 'HIGH',
          evidence: 'Operating cash burn exceeds net loss by ₹2.3M, signaling working capital drainage.'
        },
        {
          id: 'RISK-02',
          name: 'Working Capital Deficit',
          severity: 'HIGH',
          evidence: 'Current liabilities (₹28M) exceed current liquid assets (₹22M) by ₹6M.'
        }
      ],
      risk_indicators: [
        {
          id: 'FLAG-01',
          title: 'Liquidity Pressure Warning',
          severity: 'HIGH',
          evidence: 'Cash equivalents depleted from ₹8.5M to ₹2.4M within 12 months.'
        }
      ]
    },
    report: {
      report_title: 'Independent Financial Review & Going-Concern Advisory - Apex Manufacturing',
      created_at: '2026-03-31T11:22:00.000Z',
      status: 'ELEVATED RISK - GOING CONCERN WARNING',
      executive_summary: 'FINNY AUDIT OPINION: GOING-CONCERN ADVISORY. Apex Manufacturing exhibits acute financial distress in FY 2025-26 characterized by sharp revenue decline (-22.4%), persistent negative operating cash burn (-₹6.8M), deteriorating net losses (-₹4.5M), and alarming leverage with debt-to-equity reaching 2.86x.',
      financial_highlights: {
        total_revenue: '₹45,000,000 (-22.4% YoY)',
        net_loss: '-₹4,500,000 (Operating Deficit)',
        operating_cash_flow: '-₹6,800,000 (Critical Burn)',
        current_ratio: '0.79 (Illiquid < 1.0)',
        debt_to_equity: '2.86 (Covenant Risk)',
        composite_health: '38.0 / 100 (WEAK)'
      },
      recommendations: [
        'Urgent restructuring of short-term debt maturities (₹28M due within 12 months vs ₹22M current assets).',
        'Cease discretionary capital expenditure and implement emergency working capital preservation plan.',
        'Review solvency covenants with lenders to avert technical debt default.'
      ],
      financial_health: 'WEAK',
      risk_level: 'HIGH',
      fraud_risk: 'REVIEW REQUIRED',
      composite_score: 38.0,
      generated_at: '2026-03-31 11:22:00 UTC'
    }
  },

  anomalous: {
    id: 'doc-demo-anomalous-03',
    filename: 'Nova_Trading_FY2025-26_Anomalous.pdf',
    companyName: 'Nova Trading Pvt. Ltd.',
    fileType: 'PDF',
    fileSize: '1.85 MB',
    uploadDate: '2026-03-31 14:05:00 UTC',
    screeningScore: 74.0,
    verificationStatus: 'SCREENING ALERT - AUDIT REVIEW MANDATED',
    healthScore: 54.0,
    healthLabel: 'QUESTIONABLE',
    overallRisk: 'HIGH',
    fraudRisk: 'REVIEW REQUIRED',
    validationErrorCount: 2,
    riskFlagCount: 3,
    anomalyCount: 4,
    yoyChangePercentage: 92.5,
    currency_meta: { symbol: '₹', code: 'INR', unit: 'INR', divisor: 1 },
    checks: {
      file_integrity: { status: 'PASS', detail: 'Binary SHA-256 verified.' },
      document_structure: { status: 'WARNING', detail: 'Abnormal trade receivables schedule divergence detected.' },
      metadata: { status: 'PASS', detail: 'Metadata matches filing timeline.' },
      font_render: { status: 'PASS', detail: 'Standard rendering structure.' },
      layer_screening: { status: 'WARNING', detail: 'High variance between reported P&L revenues and cash realization notes.' },
      cross_page: { status: 'FAIL', detail: 'Unexplained ₹18.5M gap between revenue surge and actual customer collections.' },
      classification_status: 'ACCEPTED'
    },
    findings: [
      {
        id: 'FRAUD-01',
        title: 'Extreme Revenue Spike With Negative Cash Realization',
        category: 'Revenue Recognition Anomaly',
        severity: 'HIGH',
        evidence: 'Reported top-line surged +92.5% to ₹82.0M, but operating cash flow plunged to -₹4.2M.'
      },
      {
        id: 'FRAUD-02',
        title: 'Unexplained Accounts Receivable Ballooning',
        category: 'Asset Quality Concern',
        severity: 'HIGH',
        evidence: 'Trade receivables expanded +145% from ₹14.0M to ₹34.3M, indicating potential aggressive premature revenue recognition.'
      },
      {
        id: 'FRAUD-03',
        title: 'COGS Drop Despite Doubled Sales Volume',
        category: 'Expense Anomaly',
        severity: 'HIGH',
        evidence: 'Reported Cost of Goods Sold declined from 62% to 41% of revenue without corresponding production efficiency rationale.'
      }
    ],
    details: {
      company: 'Nova Trading Pvt. Ltd.',
      latest_year: '2026',
      previous_year: '2025',
      previous_year_status: 'AVAILABLE',
      status: 'COMPLETED',
      health_score: 54.0,
      document_health_score: 54.0,
      currency_meta: { symbol: '₹', code: 'INR', unit: 'INR', divisor: 1 },
      executive_summary: 'Nova Trading exhibits severe forensic anomalies in FY 2025-26. Despite an artificial revenue surge of +92.5% to ₹82.0M, operating cash flow turned negative (-₹4.2M) and uncollected receivables spiked +145% to ₹34.3M, flagging potential premature revenue recognition or channel stuffing.',
      annual_statements: [
        {
          fiscal_year: 2026,
          period: 'FY 2025-26',
          revenue: 82000000,
          cost_of_goods_sold: 34000000,
          gross_profit: 48000000,
          operating_expenses: 26000000,
          operating_income: 22000000,
          net_income: 15800000,
          operating_cash_flow: -4200000,
          total_assets: 95000000,
          current_assets: 62000000,
          cash_and_equivalents: 4100000,
          accounts_receivable: 34300000,
          inventory: 23600000,
          total_liabilities: 47000000,
          current_liabilities: 31000000,
          total_equity: 48000000,
          retained_earnings: 32000000,
        },
        {
          fiscal_year: 2025,
          period: 'FY 2024-25',
          revenue: 42600000,
          cost_of_goods_sold: 26400000,
          gross_profit: 16200000,
          operating_expenses: 9800000,
          operating_income: 6400000,
          net_income: 4500000,
          operating_cash_flow: 5100000,
          total_assets: 58000000,
          current_assets: 31000000,
          cash_and_equivalents: 6800000,
          accounts_receivable: 14000000,
          inventory: 10200000,
          total_liabilities: 26000000,
          current_liabilities: 15000000,
          total_equity: 32000000,
          retained_earnings: 16200000,
        }
      ],
      yoy_comparisons: [
        {
          period_pair: 'FY 2025-26 vs FY 2024-25',
          metrics: {
            revenue: { current: 82000000, previous: 42600000, abs_change: 39400000, pct_change: 92.49, direction: 'UP' },
            gross_profit: { current: 48000000, previous: 16200000, abs_change: 31800000, pct_change: 196.3, direction: 'UP' },
            operating_income: { current: 22000000, previous: 6400000, abs_change: 15600000, pct_change: 243.75, direction: 'UP' },
            net_income: { current: 15800000, previous: 4500000, abs_change: 11300000, pct_change: 251.11, direction: 'UP' },
            operating_cash_flow: { current: -4200000, previous: 5100000, abs_change: -9300000, pct_change: -182.35, direction: 'DOWN' },
            total_assets: { current: 95000000, previous: 58000000, abs_change: 37000000, pct_change: 63.79, direction: 'UP' },
            total_liabilities: { current: 47000000, previous: 26000000, abs_change: 21000000, pct_change: 80.77, direction: 'UP' },
            total_equity: { current: 48000000, previous: 32000000, abs_change: 16000000, pct_change: 50.0, direction: 'UP' },
          }
        }
      ],
      ratios: [
        { name: 'Gross Profit Margin', value: 58.54, benchmark: '40% - 60%', status: 'ABNORMAL SPIKE', category: 'Profitability' },
        { name: 'Operating Margin', value: 26.83, benchmark: '15% - 25%', status: 'HIGH VARIANCE', category: 'Profitability' },
        { name: 'Net Profit Margin', value: 19.27, benchmark: '10% - 20%', status: 'QUESTIONABLE', category: 'Profitability' },
        { name: 'Current Ratio', value: 2.0, benchmark: '1.5 - 3.0', status: 'DECEPTIVE', category: 'Liquidity' },
        { name: 'Debt-to-Equity Ratio', value: 0.98, benchmark: '< 1.5', status: 'MODERATE', category: 'Solvency' },
        { name: 'Operating Cash Flow Margin', value: -5.12, benchmark: '> 15%', status: 'CRITICAL MISMATCH', category: 'Cash Flow' },
        { name: 'Receivables Days Outstanding', value: 152.7, benchmark: '< 60 days', status: 'SEVERE ANOMALY', category: 'Asset Quality' },
      ],
      variances: [
        { metric: 'Revenue Surge', variance: 92.49, classification: 'HIGH VARIANCE', expected_range: '10% - 25%' },
        { metric: 'Receivables Inflation', variance: 145.0, classification: 'HIGH VARIANCE', expected_range: '10% - 30%' },
        { metric: 'Cash Flow Decoupling', variance: -182.35, classification: 'HIGH VARIANCE', expected_range: '15% - 35%' },
      ],
      accounting_equation: {
        balanced: true,
        assets: 95000000,
        liabilities: 47000000,
        equity: 48000000,
        discrepancy: 0,
        formula: 'Assets (₹95,000,000) = Liabilities (₹47,000,000) + Equity (₹48,000,000)'
      },
      consistency_checks: [
        { name: 'Cash Earnings Quality', status: 'FAIL', detail: 'Severe divergence: reported profit is ₹15.8M while cash from operations is negative -₹4.2M.' },
        { name: 'Receivables Realization', status: 'FAIL', detail: 'Accounts receivable grew 1.5x faster than revenue, signaling uncollected bookings.' },
        { name: 'COGS Percentage Realism', status: 'WARNING', detail: 'Sudden 21% gross margin leap lacks corresponding operational production evidence.' }
      ],
      anomalies: [
        {
          id: 'FRAUD-01',
          name: 'Aggressive Revenue Recognition Flag',
          severity: 'HIGH',
          evidence: 'Over 41% of FY 2025-26 revenue resides uncollected in trade receivables at year-end.'
        },
        {
          id: 'FRAUD-02',
          name: 'Operating Cash Inversion',
          severity: 'HIGH',
          evidence: 'Net income ₹15.8M diverges from operating cash flow (-₹4.2M) by ₹20.0M.'
        }
      ],
      risk_indicators: [
        {
          id: 'FLAG-02',
          title: 'Potential Channel Stuffing Indicator',
          severity: 'HIGH',
          evidence: 'Days Sales Outstanding jumped from 120 days to 153 days.'
        }
      ]
    },
    report: {
      report_title: 'Independent Financial Review & Forensic Audit Memorandum - Nova Trading',
      created_at: '2026-03-31T14:10:00.000Z',
      status: 'FORENSIC ALERT - AUDIT REVIEW MANDATED',
      executive_summary: 'FINNY AUDIT OPINION: FORENSIC REVIEW MANDATED. Nova Trading exhibits significant divergence between book profit and actual cash conversion, paired with an abnormal 145% surge in uncollected receivables.',
      financial_highlights: {
        reported_revenue: '₹82,000,000 (+92.5% Spike)',
        trade_receivables: '₹34,300,000 (+145.0% Ballooning)',
        operating_cash_flow: '-₹4,200,000 (Severe Mismatch)',
        days_sales_outstanding: '152.7 Days (High Latency)',
        gross_margin: '58.54% (Unexplained Leap)',
        composite_health: '54.0 / 100 (QUESTIONABLE)'
      },
      recommendations: [
        'Initiate formal external circularization of top 10 trade debtor accounts (₹34.3M balance).',
        'Perform independent cutoff verification for Q4 revenue transactions to verify shipping and delivery proofs.',
        'Examine Cost of Goods Sold calculations and inventory valuation methodologies for potential under-accrual.'
      ],
      financial_health: 'QUESTIONABLE',
      risk_level: 'HIGH',
      fraud_risk: 'REVIEW REQUIRED',
      composite_score: 54.0,
      generated_at: '2026-03-31 14:10:00 UTC'
    }
  }
};

export const getDemoScenarioByName = (name = '') => {
  const lower = name.toLowerCase();
  if (lower.includes('apex') || lower.includes('risk') || lower.includes('weak')) {
    return DEMO_SCENARIOS.high_risk;
  }
  if (lower.includes('nova') || lower.includes('fraud') || lower.includes('anomalous') || lower.includes('questionable')) {
    return DEMO_SCENARIOS.anomalous;
  }
  return DEMO_SCENARIOS.healthy;
};
