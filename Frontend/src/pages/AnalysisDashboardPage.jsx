import React, { useEffect, useState } from 'react';
import {
  BarChart3,
  TrendingUp,
  UploadCloud,
  Info,
  Calendar,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  ArrowUpRight,
  ArrowDownRight,
  ShieldCheck,
  Building,
  HelpCircle,
  Activity,
  Layers,
  Scale,
  FileText
} from 'lucide-react';
import { Link, useLocation } from 'react-router-dom';
import { useDocument } from '../services/documentContext';
import api from '../services/api';
import { formatCurrency as formatCurrencyUtil, getCurrencyBadgeInfo } from '../utils/currency';

/**
 * AnalysisDashboardPage Component
 * 
 * Comprehensive deterministic financial intelligence dashboard providing:
 * 1. Executive Overview (Company, Reporting Periods, Composite Health Score)
 * 2. Core Financial Statement Line Items (Revenue, GP, Op Income, Net Income, Assets, Liabilities, Cash Flow)
 * 3. Multi-Year Visualizations (Revenue/Net Income Trend, Assets vs Liabilities, Cash Flow, Margin Trend)
 * 4. Multi-Year YoY Comparison Matrix (Absolute changes, percentage variances, directional movement)
 * 5. Deterministic Financial Ratios & Benchmarks (Gross/Operating/Net Margins, OCF Margin, Current Ratio, D/E, ROE, Growth)
 * 6. Variance Analysis Classification (Categorized into LOW, MEDIUM, HIGH variance levels)
 * 7. Cross-Statement Accounting Consistency Reconciliations (Assets=Liabilities+Equity, GP reconciliation, Op Income, Earnings quality)
 * 8. Rule-Based Anomalies & Structural Risk Indicators (LOW, MEDIUM, HIGH severity flags)
 */
class AnalysisErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.error("AnalysisDashboardPage render error:", error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="max-w-3xl mx-auto py-16 px-4 text-center space-y-4 animate-in fade-in">
          <div className="w-14 h-14 mx-auto rounded-2xl bg-rose-500/10 border border-rose-500/30 flex items-center justify-center text-rose-400">
            <AlertTriangle className="w-7 h-7" />
          </div>
          <h2 className="text-lg font-bold text-white">Previous-Year Analysis Notice</h2>
          <p className="text-xs text-slate-400 font-mono max-w-md mx-auto">
            {this.state.error?.message || 'An unexpected issue occurred while rendering previous-year analysis.'}
          </p>
          <button
            onClick={() => this.setState({ hasError: false, error: null })}
            className="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-mono transition-all"
          >
            Retry Loading
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}

const AnalysisDashboardContent = () => {
  const { currentDocument, hasDocument } = useDocument();
  const location = useLocation();
  const isHistoricalView = location.pathname === '/previous-year-analysis' || location.pathname === '/analysis';
  const [analysisData, setAnalysisData] = useState(currentDocument?.details || null);
  const [loading, setLoading] = useState(Boolean(currentDocument?.id && !currentDocument?.details));
  const [loadError, setLoadError] = useState('');
  const [activeChartTab, setActiveChartTab] = useState('revenue_income'); // 'revenue_income' | 'balance_sheet' | 'cash_flow' | 'margins'

  // Fetch analysis data from backend API if not already present in the global document context
  useEffect(() => {
    if (currentDocument?.id && !analysisData) {
      setLoading(true);
      setLoadError('');
      api.get(`/documents/${currentDocument.id}/analysis`)
        .then(res => {
          const fetchedDetails = res.data?.details ? {
            ...res.data.details,
            health_score: res.data?.document_health_score ?? res.data?.details?.health_score ?? null,
            document_health_score: res.data?.document_health_score ?? null,
            findings: res.data?.findings || []
          } : null;
          setAnalysisData(fetchedDetails);
        })
        .catch(err => {
          console.error("Could not fetch financial analysis details:", err);
          setLoadError(err.response?.data?.detail || 'Unable to load financial analysis.');
        })
        .finally(() => setLoading(false));
    } else if (currentDocument?.details) {
      setAnalysisData(currentDocument.details);
    }
  }, [currentDocument]);

  // Extract structured parameters from analysis details payload
  const companyName = analysisData?.company || currentDocument?.companyName || 'Company';
  const annualStatements = analysisData?.annual_statements || [];
  const latestStmt = annualStatements[0] || null;
  const prevStmt = annualStatements[1] || null;
  const latestYear = latestStmt?.fiscal_year || analysisData?.latest_year || '2023';
  const prevYear = prevStmt?.fiscal_year || analysisData?.previous_year || '2022';
  const previousYearStatus = analysisData?.previous_year_status || (prevStmt ? 'AVAILABLE' : 'NOT_AVAILABLE');
  
  const yoyComparisons = analysisData?.yoy_comparisons || analysisData?.comparisons || [];
  const latestYoY = yoyComparisons[0]?.metrics || {};
  const accountingEq = analysisData?.accounting_equation || null;
  const consistencyChecks = analysisData?.consistency_checks || [];
  const variances = analysisData?.variances || [];
  const ratios = analysisData?.ratios || [];
  const anomalies = currentDocument?.findings || analysisData?.anomalies || analysisData?.risk_indicators || [];
  const healthScore = analysisData?.health_score
    ?? analysisData?.document_health_score
    ?? currentDocument?.healthScore
    ?? currentDocument?.document_health_score
    ?? null;

  const currencyMeta = analysisData?.currency_meta || currentDocument?.currency_meta || latestStmt?.currency_meta || latestStmt;
  const currencyBadge = getCurrencyBadgeInfo(currencyMeta);

  // Formats currency values cleanly, displaying NOT_AVAILABLE when missing without inventing values
  const formatCurrency = (val) => {
    if (val === null || val === undefined || val === '') return 'NOT_AVAILABLE';
    const res = formatCurrencyUtil(val, currencyMeta, { compact: true });
    return res === 'N/A' ? 'NOT_AVAILABLE' : res;
  };

  // Formats raw currency in full exact digits with commas
  const formatExactCurrency = (val) => {
    if (val === null || val === undefined || val === '') return 'NOT_AVAILABLE';
    const res = formatCurrencyUtil(val, currencyMeta, { compact: false, precision: 2 });
    return res === 'N/A' ? 'NOT_AVAILABLE' : res;
  };

  // Formats percentage values cleanly
  const formatPercent = (val) => {
    if (val === null || val === undefined) return 'NOT_AVAILABLE';
    const num = Number(val);
    if (isNaN(num)) return 'NOT_AVAILABLE';
    return `${num > 0 ? '+' : ''}${num.toFixed(2)}%`;
  };

  // Prepare chronological statements for visualization (ascending years for left-to-right graphs)
  const chronoStatements = [...annualStatements].sort((a, b) => (a.fiscal_year || 0) - (b.fiscal_year || 0));
  const hasMultiYearData = chronoStatements.length >= 2;

  // State 1: No document uploaded
  if (!hasDocument && !currentDocument?.id && !loading) {
    return (
      <div className="min-h-full flex items-center justify-center py-16">
        <div className="max-w-md w-full p-8 rounded-2xl bg-[#0B1120]/90 border border-slate-800 text-center space-y-4 animate-in fade-in duration-300">
          <div className="w-14 h-14 mx-auto rounded-2xl bg-cyan-500/10 border border-cyan-500/30 flex items-center justify-center text-cyan-400">
            <UploadCloud className="w-7 h-7" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-white">No previous analyses available.</h1>
            <p className="mt-1.5 text-xs text-slate-400">Upload a financial statement to begin analysis.</p>
          </div>
          <Link
            to="/upload"
            className="inline-flex items-center space-x-2 px-5 py-2.5 rounded-xl bg-gradient-to-r from-cyan-500 to-blue-600 text-slate-950 text-xs font-bold shadow-glow-cyan hover:scale-105 transition-all"
          >
            <UploadCloud className="w-4 h-4" />
            <span>Upload Document</span>
          </Link>
        </div>
      </div>
    );
  }

  // State 2: Document uploaded but analysisData is not yet ready and not loading
  if (hasDocument && !analysisData && !loading) {
    return (
      <div className="min-h-full flex items-center justify-center py-16">
        <div className="max-w-md w-full p-8 rounded-2xl bg-[#0B1120]/90 border border-slate-800 text-center space-y-4 animate-in fade-in duration-300">
          <div className="w-14 h-14 mx-auto rounded-2xl bg-cyan-500/10 border border-cyan-500/30 flex items-center justify-center text-cyan-400">
            <Activity className="w-7 h-7" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-white">Analysis Data Pending</h1>
            <p className="mt-1.5 text-xs text-slate-400">
              Document "{currentDocument?.filename || 'Financial Statement'}" uploaded. Analysis is being processed.
            </p>
          </div>
          <button
            onClick={() => {
              if (currentDocument?.id) {
                setLoading(true);
                setLoadError('');
                api.get(`/documents/${currentDocument.id}/analysis`)
                  .then(res => {
                    const fetchedDetails = res.data?.details ? {
                      ...res.data.details,
                      health_score: res.data?.document_health_score ?? res.data?.details?.health_score ?? null,
                      document_health_score: res.data?.document_health_score ?? null,
                      findings: res.data?.findings || []
                    } : null;
                    setAnalysisData(fetchedDetails);
                  })
                  .catch(err => setLoadError(err.response?.data?.detail || 'Unable to load analysis.'))
                  .finally(() => setLoading(false));
              }
            }}
            className="inline-flex items-center space-x-2 px-5 py-2.5 rounded-xl bg-gradient-to-r from-cyan-500 to-blue-600 text-slate-950 text-xs font-bold shadow-glow-cyan hover:scale-105 transition-all"
          >
            <Activity className="w-4 h-4" />
            <span>Refresh Analysis</span>
          </button>
        </div>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="min-h-full flex items-center justify-center">
        <div className="max-w-md w-full p-8 rounded-2xl bg-[#0B1120]/90 border border-cyan-500/30 text-center shadow-glow-cyan">
          <Activity className="w-8 h-8 mx-auto text-cyan-400 animate-pulse" />
          <h1 className="mt-4 text-lg font-bold text-white">Loading financial analysis...</h1>
          <p className="mt-2 text-xs text-slate-400">Retrieving verified analysis results from the financial engine.</p>
        </div>
      </div>
    );
  }

  if (loadError) {
    return (
      <div className="min-h-full flex items-center justify-center">
        <div className="max-w-md w-full p-8 rounded-2xl bg-[#0B1120]/90 border border-red-500/30 text-center">
          <XCircle className="w-8 h-8 mx-auto text-red-400" />
          <h1 className="mt-4 text-lg font-bold text-white">Financial analysis unavailable</h1>
          <p className="mt-2 text-xs text-slate-400">{loadError}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* ── Panel 1: Overview Header ────────────────────────────────────────── */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="inline-flex items-center space-x-2 px-3 py-1 rounded-full bg-cyan-950/80 border border-cyan-500/30 text-cyan-300 text-xs font-mono mb-2">
            <BarChart3 className="w-3.5 h-3.5 text-cyan-400" />
            <span>Deterministic Financial Intelligence Engine</span>
          </div>
          <h1 className="text-2xl font-bold text-white tracking-tight uppercase">
            {isHistoricalView ? 'Previous-Year Analysis' : 'Financial Analysis Dashboard'}
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            {isHistoricalView ? 'Historical comparison, trend direction, and deterministic year-over-year changes.' : 'Multi-year performance, cross-statement reconciliations, and rule-based risk indicators.'}
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-3 font-mono text-xs">
          <div className="flex items-center space-x-2 text-slate-300 bg-slate-900 border border-slate-800 px-3 py-1.5 rounded-lg">
            <Building className="w-3.5 h-3.5 text-cyan-400" />
            <span>Company: <strong className="text-white">{hasDocument ? companyName : 'NOT_AVAILABLE'}</strong></span>
          </div>
          <div className="flex items-center space-x-2 text-slate-300 bg-slate-900 border border-slate-800 px-3 py-1.5 rounded-lg">
            <Calendar className="w-3.5 h-3.5 text-cyan-400" />
            <span>
              Filing Period: <strong className="text-white">
                {hasDocument 
                  ? (previousYearStatus === 'AVAILABLE' ? `${latestYear} (vs ${prevYear})` : `${latestYear} (Single Period)`) 
                  : 'Awaiting Document'}
              </strong>
            </span>
          </div>
          <div className="flex items-center space-x-2 bg-slate-900 border border-slate-800 px-3 py-1.5 rounded-lg">
            <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
            <span className="text-slate-400">Health Score:</span>
            <span className="text-emerald-400 font-bold">
              {healthScore !== null && healthScore !== undefined && !isNaN(Number(healthScore))
                ? `${Number(healthScore).toFixed(1)}/100`
                : 'Not Available'}
            </span>
          </div>
          <div className="flex items-center space-x-2 bg-slate-900 border border-slate-800 px-3 py-1.5 rounded-lg">
            <span className="text-slate-400">Currency:</span>
            <span className={`font-bold ${currencyBadge.isSpecified ? 'text-indigo-300' : 'text-slate-400'}`}>
              {currencyBadge.text}
            </span>
          </div>
        </div>
      </div>

      {/* No document alert prompt */}
      {!hasDocument && (
        <div className="p-6 rounded-xl border-2 border-dashed border-slate-800 bg-[#0B1120]/40 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="flex items-center space-x-4">
            <div className="w-12 h-12 rounded-xl bg-slate-900 border border-slate-800 flex items-center justify-center text-slate-500">
              <UploadCloud className="w-6 h-6" />
            </div>
            <div>
              <h2 className="text-sm font-semibold text-slate-300">No financial statement loaded</h2>
              <p className="text-xs text-slate-500 mt-0.5">
                Upload a company financial statement (CSV, Excel, or PDF) to perform deterministic financial analysis.
              </p>
            </div>
          </div>
          <Link
            to="/upload"
            className="self-start sm:self-auto flex items-center space-x-2 px-4 py-2.5 rounded-xl bg-gradient-to-r from-cyan-500 to-blue-600 text-slate-950 text-xs font-bold shadow-glow-cyan hover:scale-105 transition-all"
          >
            <UploadCloud className="w-4 h-4" />
            <span>Upload Financial Statement</span>
          </Link>
        </div>
      )}

      {/* ── Panel 2: Core Financial Statement Line Items ─────────────────────── */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-xs font-bold text-slate-400 font-mono uppercase tracking-wider">
            Core Financial Line Items ({hasDocument ? latestYear : 'Awaiting Data'})
          </h2>
          <span className="text-[11px] font-mono text-slate-500">
            {previousYearStatus === 'AVAILABLE' ? `Compared against ${prevYear}` : 'Single Period Filing'}
          </span>
        </div>
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3.5">
          {[
            { label: 'Revenue', key: 'Revenue', val: latestStmt?.revenue, yoy: latestYoY['Revenue']?.pct_change },
            { label: 'Gross Profit', key: 'Gross Profit', val: latestStmt?.gross_profit, yoy: latestYoY['Gross Profit']?.pct_change },
            { label: 'Operating Income', key: 'Operating Income', val: latestStmt?.operating_income, yoy: latestYoY['Operating Income']?.pct_change },
            { label: 'Net Income', key: 'Net Income', val: latestStmt?.net_income, yoy: latestYoY['Net Income']?.pct_change },
            { label: 'Total Assets', key: 'Total Assets', val: latestStmt?.total_assets, yoy: latestYoY['Total Assets']?.pct_change },
            { label: 'Operating Cash Flow', key: 'Operating Cash Flow', val: latestStmt?.operating_cash_flow, yoy: latestYoY['Operating Cash Flow']?.pct_change },
          ].map((card, i) => {
            const hasVal = card.val !== undefined && card.val !== null;
            const yoyVal = card.yoy;
            const isPos = yoyVal !== undefined && yoyVal !== null && yoyVal >= 0;

            return (
              <div key={i} className="p-4 rounded-xl bg-slate-900/80 border border-slate-800 hover:border-cyan-500/40 transition-colors flex flex-col justify-between">
                <div>
                  <span className="text-[11px] font-mono text-slate-400 uppercase block">{card.label}</span>
                  <span className="text-lg font-bold text-slate-100 font-mono mt-1.5 block">
                    {hasVal ? formatCurrency(card.val) : 'NOT_AVAILABLE'}
                  </span>
                </div>
                <div className="mt-2.5 pt-2 border-t border-slate-800/80 flex items-center justify-between text-[10px] font-mono">
                  <span className="text-slate-500">YoY:</span>
                  {yoyVal !== undefined && yoyVal !== null ? (
                    <span className={`font-semibold flex items-center ${isPos ? 'text-emerald-400' : 'text-rose-400'}`}>
                      {isPos ? <ArrowUpRight className="w-3 h-3 mr-0.5" /> : <ArrowDownRight className="w-3 h-3 mr-0.5" />}
                      {formatPercent(yoyVal)}
                    </span>
                  ) : (
                    <span className="text-slate-600">NOT_AVAILABLE</span>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* ── Panel 3: Fundamental Accounting Equation Banner ──────────────────── */}
      <div className={`p-4 rounded-xl border flex flex-col sm:flex-row sm:items-center justify-between gap-3 ${
        accountingEq?.status === 'PASS'
          ? 'bg-emerald-950/20 border-emerald-500/30'
          : accountingEq?.status === 'FAIL'
          ? 'bg-rose-950/20 border-rose-500/30'
          : 'bg-slate-900/40 border-slate-800'
      }`}>
        <div className="flex items-center space-x-3">
          {accountingEq?.status === 'PASS' ? (
            <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0" />
          ) : accountingEq?.status === 'FAIL' ? (
            <XCircle className="w-5 h-5 text-rose-400 shrink-0" />
          ) : (
            <Info className="w-5 h-5 text-cyan-400 shrink-0" />
          )}
          <div>
            <span className="text-xs font-bold text-slate-200 font-mono">
              Fundamental Balance Sheet Accounting Equation (Assets = Liabilities + Equity):
            </span>
            <p className="text-xs text-slate-400 font-mono mt-0.5">
              {accountingEq?.explanation || "Assets == Liabilities + Equity — validated deterministically against rounding tolerance."}
            </p>
          </div>
        </div>
        <div className="flex items-center space-x-3 shrink-0">
          {accountingEq?.delta !== null && accountingEq?.delta !== undefined && (
            <span className="text-[11px] font-mono text-slate-400">
              Delta: {formatCurrency(accountingEq.delta)}
            </span>
          )}
          <span className={`text-[10px] font-mono font-bold px-2.5 py-1 rounded border ${
            accountingEq?.status === 'PASS'
              ? 'bg-emerald-950 text-emerald-400 border-emerald-500/40'
              : accountingEq?.status === 'FAIL'
              ? 'bg-rose-950 text-rose-400 border-rose-500/40'
              : 'bg-slate-900 text-slate-500 border-slate-700'
          }`}>
            {accountingEq?.status || 'AWAITING DATA'}
          </span>
        </div>
      </div>

      {/* ── Panel 4: Interactive Visualizations (Step 11) ────────────────────── */}
      <div className="p-5 rounded-2xl bg-[#0B1120] border border-slate-800">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-4">
          <div>
            <h3 className="text-xs font-bold text-slate-200 font-mono uppercase tracking-wider flex items-center space-x-2">
              <Activity className="w-4 h-4 text-cyan-400" />
              <span>Financial Trajectory Visualizations</span>
            </h3>
            <p className="text-[11px] text-slate-400 mt-0.5">
              Deterministic charts generated from extracted financial statement reporting periods.
            </p>
          </div>

          <div className="flex items-center space-x-1.5 p-1 rounded-lg bg-slate-900 border border-slate-800 text-xs font-mono">
            {[
              { id: 'revenue_income', label: 'Revenue & Income' },
              { id: 'expenses_profit', label: 'Expenses & Gross Profit' },
              { id: 'balance_sheet', label: 'Assets vs Liabilities' },
              { id: 'cash_flow', label: 'Operating Cash Flow' },
              { id: 'margins', label: 'Profitability Margins' }
            ].map(tab => (
              <button
                key={tab.id}
                onClick={() => setActiveChartTab(tab.id)}
                className={`px-2.5 py-1 rounded-md text-[11px] font-semibold transition-colors ${
                  activeChartTab === tab.id
                    ? 'bg-cyan-500 text-slate-950'
                    : 'text-slate-400 hover:text-white'
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>
        </div>

        {hasMultiYearData ? (
          <div className="h-64 w-full pt-4">
            {/* 1. Revenue & Net Income Trend Chart */}
            {activeChartTab === 'revenue_income' && (
              <div className="h-full flex flex-col justify-between">
                <div className="flex items-center justify-end space-x-4 text-xs font-mono mb-2">
                  <span className="flex items-center space-x-1.5 text-cyan-400">
                    <span className="w-3 h-3 rounded-full bg-cyan-400 inline-block" />
                    <span>Revenue</span>
                  </span>
                  <span className="flex items-center space-x-1.5 text-emerald-400">
                    <span className="w-3 h-3 rounded-full bg-emerald-400 inline-block" />
                    <span>Net Income</span>
                  </span>
                </div>
                <div className="flex-1 flex items-end justify-around gap-4 pb-2 border-b border-slate-800">
                  {chronoStatements.map((stmt, idx) => {
                    const maxRev = Math.max(...chronoStatements.map(s => s.revenue || 1));
                    const revHeight = Math.max(8, Math.round(((stmt.revenue || 0) / maxRev) * 160));
                    const niHeight = Math.max(4, Math.round((Math.max(0, stmt.net_income || 0) / maxRev) * 160));
                    return (
                      <div key={idx} className="flex-1 flex flex-col items-center justify-end h-full group">
                        <div className="w-full flex items-end justify-center space-x-2 h-44">
                          {/* Revenue bar */}
                          <div
                            style={{ height: `${revHeight}px` }}
                            className="w-1/3 bg-cyan-500/80 hover:bg-cyan-400 rounded-t transition-all flex flex-col justify-start items-center pt-1"
                            title={`Revenue: ${formatCurrency(stmt.revenue)}`}
                          >
                            <span className="text-[9px] font-mono text-slate-950 font-bold hidden group-hover:block truncate px-0.5">
                              {formatCurrency(stmt.revenue)}
                            </span>
                          </div>
                          {/* Net Income bar */}
                          <div
                            style={{ height: `${niHeight}px` }}
                            className="w-1/3 bg-emerald-500/80 hover:bg-emerald-400 rounded-t transition-all flex flex-col justify-start items-center pt-1"
                            title={`Net Income: ${formatCurrency(stmt.net_income)}`}
                          >
                            <span className="text-[9px] font-mono text-slate-950 font-bold hidden group-hover:block truncate px-0.5">
                              {formatCurrency(stmt.net_income)}
                            </span>
                          </div>
                        </div>
                        <span className="mt-2 text-xs font-mono text-slate-300 font-bold">{stmt.fiscal_year}</span>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {/* 2. Expenses & Gross Profit Chart */}
            {activeChartTab === 'expenses_profit' && (
              <div className="h-full flex flex-col justify-between">
                <div className="flex items-center justify-end space-x-4 text-xs font-mono mb-2">
                  <span className="flex items-center space-x-1.5 text-emerald-400">
                    <span className="w-3 h-3 rounded-full bg-emerald-400 inline-block" />
                    <span>Gross Profit</span>
                  </span>
                  <span className="flex items-center space-x-1.5 text-amber-400">
                    <span className="w-3 h-3 rounded-full bg-amber-400 inline-block" />
                    <span>Operating Expenses</span>
                  </span>
                </div>
                <div className="flex-1 flex items-end justify-around gap-4 pb-2 border-b border-slate-800">
                  {chronoStatements.map((stmt, idx) => {
                    const maxVal = Math.max(...chronoStatements.map(s => Math.max(s.gross_profit || 0, s.operating_expenses || 0, 1)));
                    const gpHeight = Math.max(8, Math.round((Math.max(0, stmt.gross_profit || 0) / maxVal) * 160));
                    const opexHeight = Math.max(8, Math.round((Math.max(0, stmt.operating_expenses || 0) / maxVal) * 160));
                    return (
                      <div key={idx} className="flex-1 flex flex-col items-center justify-end h-full group">
                        <div className="w-full flex items-end justify-center space-x-2 h-44">
                          {/* Gross Profit bar */}
                          <div
                            style={{ height: `${gpHeight}px` }}
                            className="w-1/3 bg-emerald-500/80 hover:bg-emerald-400 rounded-t transition-all flex flex-col justify-start items-center pt-1"
                            title={`Gross Profit: ${formatCurrency(stmt.gross_profit)}`}
                          >
                            <span className="text-[9px] font-mono text-slate-950 font-bold hidden group-hover:block truncate px-0.5">
                              {formatCurrency(stmt.gross_profit)}
                            </span>
                          </div>
                          {/* Operating Expenses bar */}
                          <div
                            style={{ height: `${opexHeight}px` }}
                            className="w-1/3 bg-amber-500/80 hover:bg-amber-400 rounded-t transition-all flex flex-col justify-start items-center pt-1"
                            title={`Operating Expenses: ${formatCurrency(stmt.operating_expenses)}`}
                          >
                            <span className="text-[9px] font-mono text-slate-950 font-bold hidden group-hover:block truncate px-0.5">
                              {formatCurrency(stmt.operating_expenses)}
                            </span>
                          </div>
                        </div>
                        <span className="mt-2 text-xs font-mono text-slate-300 font-bold">{stmt.fiscal_year}</span>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {/* 3. Assets vs Liabilities Chart */}
            {activeChartTab === 'balance_sheet' && (
              <div className="h-full flex flex-col justify-between">
                <div className="flex items-center justify-end space-x-4 text-xs font-mono mb-2">
                  <span className="flex items-center space-x-1.5 text-blue-400">
                    <span className="w-3 h-3 rounded-full bg-blue-400 inline-block" />
                    <span>Total Assets</span>
                  </span>
                  <span className="flex items-center space-x-1.5 text-rose-400">
                    <span className="w-3 h-3 rounded-full bg-rose-400 inline-block" />
                    <span>Total Liabilities</span>
                  </span>
                </div>
                <div className="flex-1 flex items-end justify-around gap-4 pb-2 border-b border-slate-800">
                  {chronoStatements.map((stmt, idx) => {
                    const maxAssets = Math.max(...chronoStatements.map(s => s.total_assets || 1));
                    const aHeight = Math.max(8, Math.round(((stmt.total_assets || 0) / maxAssets) * 160));
                    const lHeight = Math.max(4, Math.round(((stmt.total_liabilities || 0) / maxAssets) * 160));
                    return (
                      <div key={idx} className="flex-1 flex flex-col items-center justify-end h-full group">
                        <div className="w-full flex items-end justify-center space-x-2 h-44">
                          <div
                            style={{ height: `${aHeight}px` }}
                            className="w-1/3 bg-blue-500/80 hover:bg-blue-400 rounded-t transition-all"
                            title={`Assets: ${formatCurrency(stmt.total_assets)}`}
                          />
                          <div
                            style={{ height: `${lHeight}px` }}
                            className="w-1/3 bg-rose-500/80 hover:bg-rose-400 rounded-t transition-all"
                            title={`Liabilities: ${formatCurrency(stmt.total_liabilities)}`}
                          />
                        </div>
                        <span className="mt-2 text-xs font-mono text-slate-300 font-bold">{stmt.fiscal_year}</span>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {/* 3. Operating Cash Flow Chart */}
            {activeChartTab === 'cash_flow' && (
              <div className="h-full flex flex-col justify-between">
                <div className="flex items-center justify-end space-x-4 text-xs font-mono mb-2">
                  <span className="flex items-center space-x-1.5 text-teal-400">
                    <span className="w-3 h-3 rounded-full bg-teal-400 inline-block" />
                    <span>Operating Cash Flow</span>
                  </span>
                </div>
                <div className="flex-1 flex items-end justify-around gap-4 pb-2 border-b border-slate-800">
                  {chronoStatements.map((stmt, idx) => {
                    const maxCfo = Math.max(...chronoStatements.map(s => Math.abs(s.operating_cash_flow || 1)));
                    const isPositive = (stmt.operating_cash_flow || 0) >= 0;
                    const cfoHeight = Math.max(8, Math.round((Math.abs(stmt.operating_cash_flow || 0) / maxCfo) * 160));
                    return (
                      <div key={idx} className="flex-1 flex flex-col items-center justify-end h-full group">
                        <div className="w-full flex items-end justify-center h-44">
                          <div
                            style={{ height: `${cfoHeight}px` }}
                            className={`w-1/2 rounded-t transition-all flex flex-col items-center justify-start pt-1 ${
                              isPositive ? 'bg-teal-500/80 hover:bg-teal-400' : 'bg-rose-500/80 hover:bg-rose-400'
                            }`}
                            title={`OCF: ${formatCurrency(stmt.operating_cash_flow)}`}
                          >
                            <span className="text-[9px] font-mono text-slate-950 font-bold hidden group-hover:block truncate px-0.5">
                              {formatCurrency(stmt.operating_cash_flow)}
                            </span>
                          </div>
                        </div>
                        <span className="mt-2 text-xs font-mono text-slate-300 font-bold">{stmt.fiscal_year}</span>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {/* 4. Profitability Margins Trend */}
            {activeChartTab === 'margins' && (
              <div className="h-full flex flex-col justify-between">
                <div className="flex items-center justify-end space-x-4 text-xs font-mono mb-2">
                  <span className="flex items-center space-x-1.5 text-cyan-400">
                    <span className="w-3 h-3 rounded-full bg-cyan-400 inline-block" />
                    <span>Gross Margin</span>
                  </span>
                  <span className="flex items-center space-x-1.5 text-emerald-400">
                    <span className="w-3 h-3 rounded-full bg-emerald-400 inline-block" />
                    <span>Net Margin</span>
                  </span>
                </div>
                <div className="flex-1 flex items-end justify-around gap-4 pb-2 border-b border-slate-800">
                  {chronoStatements.map((stmt, idx) => {
                    const numRev = Number(stmt.revenue);
                    const numGp = Number(stmt.gross_profit);
                    const numNi = Number(stmt.net_income);
                    const gm = !isNaN(numRev) && numRev !== 0 && !isNaN(numGp) ? ((numGp / numRev) * 100) : null;
                    const nm = !isNaN(numRev) && numRev !== 0 && !isNaN(numNi) ? ((numNi / numRev) * 100) : (stmt.net_profit_margin != null && !isNaN(Number(stmt.net_profit_margin)) ? Number(stmt.net_profit_margin) : null);
                    const gmHeight = gm !== null && !isNaN(gm) ? Math.min(160, Math.max(8, Math.round((Math.max(0, gm) / 100) * 160))) : 0;
                    const nmHeight = nm !== null && !isNaN(nm) ? Math.min(160, Math.max(4, Math.round((Math.max(0, nm) / 100) * 160))) : 0;
                    return (
                      <div key={idx} className="flex-1 flex flex-col items-center justify-end h-full group">
                        <div className="w-full flex items-end justify-center space-x-2 h-44">
                          <div
                            style={{ height: `${gmHeight}px` }}
                            className="w-1/3 bg-cyan-500/80 hover:bg-cyan-400 rounded-t transition-all"
                            title={`Gross Margin: ${gm !== null && !isNaN(gm) ? gm.toFixed(2) + '%' : 'NOT_AVAILABLE'}`}
                          />
                          <div
                            style={{ height: `${nmHeight}px` }}
                            className="w-1/3 bg-emerald-500/80 hover:bg-emerald-400 rounded-t transition-all"
                            title={`Net Margin: ${nm !== null && !isNaN(nm) ? nm.toFixed(2) + '%' : 'NOT_AVAILABLE'}`}
                          />
                        </div>
                        <span className="mt-2 text-xs font-mono text-slate-300 font-bold">{stmt.fiscal_year}</span>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}
          </div>
        ) : (
          <div className="h-44 flex flex-col items-center justify-center text-slate-500 font-mono text-xs border border-dashed border-slate-800 rounded-xl p-4 text-center">
            <Info className="w-6 h-6 text-slate-600 mb-2" />
            <p className="text-slate-400 font-semibold">Multi-year trajectory visualization requires at least two fiscal reporting periods.</p>
            <p className="text-slate-600 mt-1">
              Current source document contains single-period data. Trend graphs will activate automatically when multi-year statements are provided.
            </p>
          </div>
        )}
      </div>

      {/* ── Panel 5 & 6: Multi-Year YoY Comparison & Financial Ratios ───────── */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">

        {/* Multi-Year YoY Variance Matrix */}
        <div className="lg:col-span-7 p-5 rounded-2xl bg-[#0B1120] border border-slate-800 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-xs font-bold text-slate-200 font-mono uppercase tracking-wider">
                Multi-Year YoY Variance Matrix ({yoyComparisons[0]?.period || 'Awaiting Periods'})
              </h3>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-cyan-950 text-cyan-300 border border-cyan-500/30">
                Deterministic Calculation
              </span>
            </div>
            <p className="text-xs text-slate-400 mb-4">
              Mathematical variance across reporting periods: <code className="text-cyan-400 font-mono">((Current − Previous) / abs(Previous)) × 100</code>.
            </p>

            {yoyComparisons.length > 0 && yoyComparisons[0]?.metrics ? (
              <div className="space-y-4">
                {/* Visual Comparative Metric Bars */}
                <div className="p-3.5 rounded-xl bg-slate-950/60 border border-slate-800/80 space-y-3">
                  <div className="flex items-center justify-between text-[11px] font-mono text-slate-400">
                    <span>Visual Comparative Trajectory ({prevYear} vs {latestYear})</span>
                    <div className="flex items-center space-x-3">
                      <span className="flex items-center space-x-1 text-slate-400">
                        <span className="w-2 h-2 rounded bg-indigo-500" />
                        <span>Previous ({prevYear})</span>
                      </span>
                      <span className="flex items-center space-x-1 text-cyan-300">
                        <span className="w-2 h-2 rounded bg-cyan-400" />
                        <span>Current ({latestYear})</span>
                      </span>
                    </div>
                  </div>

                  <div className="space-y-2.5">
                    {Object.entries(yoyComparisons[0].metrics || {}).slice(0, 4).map(([name, data]) => {
                      if (!data) return null;
                      const maxVal = Math.max(Math.abs(Number(data.previous) || 0), Math.abs(Number(data.current) || 0), 1);
                      const prevW = Math.max(4, Math.round((Math.abs(Number(data.previous) || 0) / maxVal) * 100));
                      const currW = Math.max(4, Math.round((Math.abs(Number(data.current) || 0) / maxVal) * 100));
                      const isPos = data.pct_change !== null && data.pct_change !== undefined && Number(data.pct_change) >= 0;

                      return (
                        <div key={name} className="space-y-1 font-mono text-[11px]">
                          <div className="flex justify-between text-slate-300">
                            <span className="font-semibold">{name}</span>
                            <span className={data.pct_change === null || data.pct_change === undefined ? 'text-slate-500' : isPos ? 'text-emerald-400 font-bold' : 'text-rose-400 font-bold'}>
                              {formatPercent(data.pct_change)} ({isPos ? '+' : ''}{formatCurrency(data.absolute_change)})
                            </span>
                          </div>
                          <div className="space-y-1">
                            <div className="w-full bg-slate-900 h-2 rounded-full overflow-hidden flex">
                              <div style={{ width: `${prevW}%` }} className="bg-indigo-500/80 rounded-full" title={`Previous: ${formatCurrency(data.previous)}`} />
                            </div>
                            <div className="w-full bg-slate-900 h-2 rounded-full overflow-hidden flex">
                              <div style={{ width: `${currW}%` }} className="bg-gradient-to-r from-cyan-500 to-blue-500 rounded-full" title={`Current: ${formatCurrency(data.current)}`} />
                            </div>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>

                <div className="overflow-x-auto">
                  <table className="w-full text-xs font-mono text-left">
                    <thead>
                      <tr className="border-b border-slate-800 text-slate-400 text-[11px]">
                        <th className="py-2 pr-3">Financial Metric</th>
                        <th className="py-2 px-2 text-right">Previous ({prevYear})</th>
                        <th className="py-2 px-2 text-right">Current ({latestYear})</th>
                        <th className="py-2 px-2 text-right">Abs Change</th>
                        <th className="py-2 pl-2 text-right">YoY %</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800/60">
                      {Object.entries(yoyComparisons[0].metrics || {}).map(([name, data]) => {
                        if (!data) return null;
                        const pct = data.pct_change !== undefined ? data.pct_change : null;
                        const isPos = pct !== null && Number(pct) >= 0;
                        return (
                          <tr key={name} className="hover:bg-slate-900/40">
                            <td className="py-2.5 pr-3 text-slate-200 font-semibold">{name}</td>
                            <td className="py-2.5 px-2 text-right text-slate-400">{formatCurrency(data.previous)}</td>
                            <td className="py-2.5 px-2 text-right text-slate-200 font-bold">{formatCurrency(data.current)}</td>
                            <td className="py-2.5 px-2 text-right text-slate-300">{formatCurrency(data.absolute_change)}</td>
                            <td className={`py-2.5 pl-2 text-right font-bold ${pct === null ? 'text-slate-600' : isPos ? 'text-emerald-400' : 'text-rose-400'}`}>
                              {formatPercent(pct)}
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </div>
            ) : (
              <div className="h-44 flex items-center justify-center text-slate-500 font-mono text-xs border border-dashed border-slate-800 rounded-xl">
                Previous-year data is not available from the source document.
              </div>
            )}
          </div>
        </div>

        {/* Deterministic Financial Ratios & Benchmarks */}
        <div className="lg:col-span-5 p-5 rounded-2xl bg-[#0B1120] border border-slate-800 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-xs font-bold text-slate-200 font-mono uppercase tracking-wider">
                Financial Ratios &amp; Derived Metrics
              </h3>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-950 text-emerald-300 border border-emerald-500/30">
                Deterministic Formulas
              </span>
            </div>
            <p className="text-xs text-slate-400 mb-4">
              Profitability, liquidity, solvency, and growth metrics computed from verified line items.
            </p>

            {ratios.length > 0 ? (
              <div className="space-y-2 max-h-[340px] overflow-y-auto pr-1">
                {ratios.map((r, i) => {
                  const hasVal = r.metric_value !== null && r.metric_value !== undefined;
                  return (
                    <div key={i} className="p-2.5 rounded-xl bg-slate-900/70 border border-slate-800 flex items-center justify-between text-xs font-mono">
                      <div>
                        <span className="text-slate-200 font-bold block">{r.metric_name}</span>
                        <span className="text-[10px] text-slate-500">Benchmark: {r.benchmark || 'N/A'}</span>
                      </div>
                      <div className="text-right">
                        <span className="text-cyan-300 font-bold text-sm block">
                          {hasVal ? `${r.metric_value}${r.unit || ''}` : 'NOT_AVAILABLE'}
                        </span>
                        <span className={`text-[9px] px-1.5 py-0.2 rounded inline-block mt-0.5 ${
                          r.status === 'HEALTHY'
                            ? 'bg-emerald-950 text-emerald-400 border border-emerald-500/30'
                            : r.status === 'WARNING'
                            ? 'bg-amber-950 text-amber-400 border border-amber-500/30'
                            : r.status === 'NORMAL'
                            ? 'bg-blue-950 text-blue-400 border border-blue-500/30'
                            : 'bg-slate-800 text-slate-500'
                        }`}>
                          {r.status}
                        </span>
                      </div>
                    </div>
                  );
                })}
              </div>
            ) : (
              <div className="h-44 flex items-center justify-center text-slate-500 font-mono text-xs border border-dashed border-slate-800 rounded-xl">
                Financial ratios will be calculated deterministically on document analysis.
              </div>
            )}
          </div>
        </div>

      </div>

      {/* ── Panel 7: Deterministic Variance Analysis Classification ─────────── */}
      <div className="p-5 rounded-2xl bg-[#0B1120] border border-slate-800">
        <div className="flex items-center justify-between mb-3">
          <div>
            <h3 className="text-xs font-bold text-slate-200 font-mono uppercase tracking-wider">
              Deterministic Variance Analysis ({variances.length} Metrics)
            </h3>
            <p className="text-[11px] text-slate-400 mt-0.5">
              Identifies movement significance: LOW (&lt;15%), MEDIUM (15%–50%), HIGH (&gt;50%).
            </p>
          </div>
          <span className="text-[10px] font-mono text-slate-400">
            Threshold Classification
          </span>
        </div>

        {variances.length > 0 ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3 mt-3 font-mono text-xs">
            {variances.map((v, i) => {
              const isHigh = v.variance_level === 'HIGH';
              const isMed = v.variance_level === 'MEDIUM';
              const isLow = v.variance_level === 'LOW';
              return (
                <div key={i} className="p-3 rounded-xl bg-slate-900/80 border border-slate-800 flex flex-col justify-between">
                  <div>
                    <div className="flex items-center justify-between mb-1.5">
                      <span className="font-bold text-slate-200 truncate">{v.metric}</span>
                      <span className={`text-[9px] px-1.5 py-0.5 rounded font-bold ${
                        isHigh ? 'bg-rose-950 text-rose-400 border border-rose-500/30' :
                        isMed ? 'bg-amber-950 text-amber-400 border border-amber-500/30' :
                        isLow ? 'bg-emerald-950 text-emerald-400 border border-emerald-500/30' :
                        'bg-slate-800 text-slate-500'
                      }`}>
                        {v.variance_level}
                      </span>
                    </div>
                    <div className="text-[11px] text-slate-400 space-y-0.5">
                      <div>Current: <span className="text-slate-200">{formatCurrency(v.current_value)}</span></div>
                      <div>Previous: <span className="text-slate-400">{formatCurrency(v.previous_value)}</span></div>
                    </div>
                  </div>
                  <div className="mt-2 pt-2 border-t border-slate-800 flex items-center justify-between text-[10px]">
                    <span className="text-slate-500">Direction: {v.direction}</span>
                    <span className={`font-bold ${
                      v.percentage_change === null ? 'text-slate-600' :
                      v.percentage_change >= 0 ? 'text-emerald-400' : 'text-rose-400'
                    }`}>
                      {formatPercent(v.percentage_change)}
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        ) : (
          <div className="p-4 rounded-xl bg-slate-900/40 border border-slate-800 text-center text-xs text-slate-500 font-mono">
            Variance analysis requires multiple reporting periods. Single-period documents exhibit no prior-period variance.
          </div>
        )}
      </div>

      {/* ── Panel 8: Cross-Statement Consistency Reconciliations ────────────── */}
      <div className="p-5 rounded-2xl bg-[#0B1120] border border-slate-800">
        <div className="flex items-center justify-between mb-3">
          <div>
            <h3 className="text-xs font-bold text-slate-200 font-mono uppercase tracking-wider">
              Cross-Statement Accounting Consistency Reconciliations
            </h3>
            <p className="text-[11px] text-slate-400 mt-0.5">
              Auditing mathematical relationships across Balance Sheet, Income Statement, and Cash Flow components.
            </p>
          </div>
          <span className="text-[10px] font-mono text-slate-400">
            Accounting Reconciliations
          </span>
        </div>

        {consistencyChecks.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mt-3 font-mono text-xs">
            {consistencyChecks.map((chk, i) => {
              const isPass = chk.status === 'PASS';
              const isWarn = chk.status === 'WARNING';
              const isFail = chk.status === 'FAIL';
              return (
                <div key={i} className="p-3.5 rounded-xl bg-slate-900/80 border border-slate-800 flex items-start justify-between gap-3">
                  <div>
                    <h4 className="font-bold text-slate-200">{chk.name}</h4>
                    <p className="text-[11px] text-slate-400 mt-1">{chk.explanation}</p>
                    {chk.difference !== null && chk.difference !== undefined && (
                      <div className="mt-2 text-[10px] text-slate-500 flex items-center space-x-3">
                        <span>Reported: {formatCurrency(chk.reported_value)}</span>
                        <span>Calculated: {formatCurrency(chk.calculated_value)}</span>
                        <span>Diff: {formatCurrency(chk.difference)}</span>
                      </div>
                    )}
                  </div>
                  <span className={`text-[10px] font-bold px-2.5 py-1 rounded border shrink-0 ${
                    isPass
                      ? 'bg-emerald-950 text-emerald-400 border-emerald-500/40'
                      : isWarn
                      ? 'bg-amber-950 text-amber-400 border-amber-500/40'
                      : isFail
                      ? 'bg-rose-950 text-rose-400 border-rose-500/40'
                      : 'bg-slate-800 text-slate-500 border-slate-700'
                  }`}>
                    {chk.status}
                  </span>
                </div>
              );
            })}
          </div>
        ) : (
          <div className="p-4 rounded-xl bg-slate-900/40 border border-slate-800 text-center text-xs text-slate-500 font-mono">
            Cross-statement reconciliations will run upon document analysis.
          </div>
        )}
      </div>

      {/* ── Traceability & Source Evidence Notice ───────────────────────────── */}
      <div className="p-3 rounded-lg bg-slate-900/40 border border-slate-800 text-[11px] text-slate-500 font-mono flex items-center space-x-2">
        <Info className="w-3.5 h-3.5 text-cyan-500 shrink-0" />
        <span>
          Traceability Notice: All financial metrics, YoY comparisons, and ratios are calculated deterministically from source document line items without LLM arithmetic. Missing values display as NOT_AVAILABLE.
        </span>
      </div>
    </div>
  );
};

export const AnalysisDashboardPage = () => {
  return (
    <AnalysisErrorBoundary>
      <AnalysisDashboardContent />
    </AnalysisErrorBoundary>
  );
};
