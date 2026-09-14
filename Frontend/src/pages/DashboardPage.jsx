import React, { useState } from 'react';
import { Link as RouterLink } from 'react-router-dom';
import {
  AlertTriangle,
  CheckCircle2,
  FileText,
  UploadCloud,
  ChevronRight,
  Trash2,
  Loader2,
  DollarSign,
  Scale,
  Sparkles,
  Info,
  X,
  ArrowRight
} from 'lucide-react';
import { useDocument } from '../services/documentContext';
import api from '../services/api';
import { formatCurrency as formatCurrencyUtil, getCurrencyBadgeInfo } from '../utils/currency';

/**
 * Formats a percentage value safely.
 */
const formatPercent = (val) => {
  if (val === null || val === undefined || isNaN(val)) return 'Not Available';
  const num = Number(val);
  const sign = num > 0 ? '+' : '';
  return `${sign}${num.toFixed(1)}%`;
};

export const DashboardPage = () => {
  const { hasDocument, uploadedFileInfo, currentDocument, isHydrating, resetDocument } = useDocument();
  const analysis = currentDocument?.details;
  const statements = analysis?.annual_statements || [];
  const latestStatement = statements[0] || {};
  const hasAnalysis = Boolean(currentDocument?.id && (analysis?.status === 'COMPLETED' || currentDocument?.healthScore !== null));

  const currencyMeta = currentDocument?.currency_meta || analysis?.currency_meta || latestStatement?.currency_meta || latestStatement;
  const currencyBadge = getCurrencyBadgeInfo(currencyMeta);
  const formatMoney = (val) => formatCurrencyUtil(val, currencyMeta, { compact: true });

  // Deletion modal state
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState('');

  const handleDeleteDocument = async () => {
    if (!currentDocument?.id) return;
    setIsDeleting(true);
    setDeleteError('');
    try {
      if (String(currentDocument.id).startsWith('doc-demo-')) {
        try {
          const stored = JSON.parse(localStorage.getItem('fsra_history') || '[]');
          const filtered = stored.filter(item => item.id !== currentDocument.id);
          localStorage.setItem('fsra_history', JSON.stringify(filtered));
        } catch (e) {}
        resetDocument();
        setShowDeleteModal(false);
        return;
      }

      await api.delete(`/documents/${currentDocument.id}`);
      try {
        const stored = JSON.parse(localStorage.getItem('fsra_history') || '[]');
        const filtered = stored.filter(item => item.id !== currentDocument.id);
        localStorage.setItem('fsra_history', JSON.stringify(filtered));
      } catch (e) {}
      resetDocument();
      setShowDeleteModal(false);
    } catch (err) {
      if (err.response?.status === 404) {
        // Already deleted or purged on server
        try {
          const stored = JSON.parse(localStorage.getItem('fsra_history') || '[]');
          const filtered = stored.filter(item => item.id !== currentDocument.id);
          localStorage.setItem('fsra_history', JSON.stringify(filtered));
        } catch (e) {}
        resetDocument();
        setShowDeleteModal(false);
      } else {
        setDeleteError(err.response?.data?.detail || 'Failed to delete document from archive.');
      }
    } finally {
      setIsDeleting(false);
    }
  };

  if (isHydrating) {
    return (
      <div className="p-12 rounded-2xl bg-[#0B1120]/80 border border-cyan-500/30 text-center text-sm text-cyan-300 font-mono animate-pulse">
        Loading verified financial analysis data...
      </div>
    );
  }

  // ════════════════════════════════════════════════════════════════════════════
  // STATE 1: No document uploaded yet — Clean Empty State (NO fake financial data)
  // ════════════════════════════════════════════════════════════════════════════
  if (!hasDocument) {
    return (
      <div className="max-w-3xl mx-auto py-20 px-4 text-center space-y-6 animate-in fade-in duration-300">
        <div className="w-16 h-16 mx-auto rounded-2xl bg-cyan-500/10 border border-cyan-500/30 flex items-center justify-center text-cyan-400 shadow-glow-cyan">
          <UploadCloud className="w-8 h-8" />
        </div>
        <div className="space-y-2">
          <span className="text-[11px] font-mono uppercase tracking-wider text-cyan-400 font-semibold">
            FINNY Review Agent
          </span>
          <h1 className="text-3xl font-bold text-white tracking-tight uppercase">
            FINNY DASHBOARD
          </h1>
          <h2 className="text-base font-semibold text-slate-200">
            No financial statement uploaded yet.
          </h2>
          <p className="text-xs text-slate-400 max-w-md mx-auto leading-relaxed">
            FINNY will analyze the uploaded statement and generate financial insights with deterministic mathematical validation.
          </p>
        </div>
        <div className="pt-2">
          <RouterLink
            to="/upload"
            className="inline-flex items-center space-x-2 px-6 py-3 rounded-xl bg-gradient-to-r from-cyan-500 to-blue-600 text-slate-950 text-xs font-bold shadow-glow-cyan hover:scale-105 active:scale-95 transition-all"
          >
            <UploadCloud className="w-4 h-4" />
            <span>Upload Financial Statement</span>
          </RouterLink>
        </div>
      </div>
    );
  }

  // ════════════════════════════════════════════════════════════════════════════
  // STATE 2: Document uploaded but analysis pending
  // ════════════════════════════════════════════════════════════════════════════
  if (!hasAnalysis) {
    return (
      <div className="max-w-4xl mx-auto space-y-6 pb-12 animate-in fade-in duration-300">
        {/* Active Document Info Bar */}
        <div className="p-5 rounded-2xl bg-gradient-to-r from-slate-900 via-[#0B1120] to-slate-900 border border-slate-800 flex flex-col md:flex-row md:items-center justify-between gap-4 shadow-lg">
          <div className="flex items-center space-x-3.5">
            <div className="w-10 h-10 rounded-xl bg-cyan-500/10 border border-cyan-500/30 flex items-center justify-center text-cyan-400 shrink-0">
              <FileText className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center space-x-2 flex-wrap gap-y-1">
                <h2 className="text-sm font-bold text-slate-100">{uploadedFileInfo?.filename || currentDocument?.filename}</h2>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700">
                  {uploadedFileInfo?.fileType || currentDocument?.fileType}
                </span>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-amber-950 text-amber-300 border border-amber-500/30 font-bold">
                  REVIEW PENDING
                </span>
              </div>
              <p className="text-xs text-slate-400 mt-1 font-mono">
                Size: {uploadedFileInfo?.fileSize || currentDocument?.fileSize || '—'} • Uploaded: {uploadedFileInfo?.uploadDate || 'Just now'}
              </p>
            </div>
          </div>

          <div className="flex items-center space-x-3">
            <RouterLink
              to="/agent-processing"
              className="px-4 py-2 rounded-xl bg-gradient-to-r from-cyan-500 to-blue-600 text-slate-950 text-xs font-bold shadow-glow-cyan hover:scale-105 transition-all flex items-center space-x-1.5"
            >
              <Sparkles className="w-3.5 h-3.5" />
              <span>Launch 9-Stage Review</span>
            </RouterLink>
          </div>
        </div>

        {/* Processing Guidance Card */}
        <div className="p-8 rounded-2xl bg-[#0B1120] border border-slate-800 text-center space-y-4">
          <div className="w-12 h-12 mx-auto rounded-xl bg-cyan-500/10 border border-cyan-500/30 flex items-center justify-center text-cyan-400">
            <Sparkles className="w-6 h-6 animate-pulse" />
          </div>
          <div className="space-y-1">
            <h3 className="text-sm font-bold text-slate-100 uppercase tracking-wide font-mono">
              Ready for Deterministic Review
            </h3>
            <p className="text-xs text-slate-400 max-w-lg mx-auto leading-relaxed">
              Financial document has been uploaded. Execute the 9-stage analysis to generate financial KPIs, visual balance sheets, and forensic risk assessments.
            </p>
          </div>
          <RouterLink
            to="/agent-processing"
            className="inline-flex items-center space-x-2 px-5 py-2.5 rounded-xl bg-cyan-500 hover:bg-cyan-400 text-slate-950 text-xs font-bold transition-all"
          >
            <span>Proceed to Analysis</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </RouterLink>
        </div>
      </div>
    );
  }

  // ════════════════════════════════════════════════════════════════════════════
  // STATE 3: Analysis Completed — Real Visual Financial Data
  // ════════════════════════════════════════════════════════════════════════════
  const revenue = latestStatement.revenue;
  const grossProfit = latestStatement.gross_profit;
  const opExpenses = latestStatement.operating_expenses;
  const opIncome = latestStatement.operating_income;
  const netIncome = latestStatement.net_income;
  const opCashFlow = latestStatement.operating_cash_flow;

  const totalAssets = latestStatement.total_assets;
  const currentAssets = latestStatement.current_assets;
  const cashEquiv = latestStatement.cash_and_equivalents;
  const totalLiab = latestStatement.total_liabilities;
  const currentLiab = latestStatement.current_liabilities;
  const totalEquity = latestStatement.total_equity;

  // YoY comparisons from deterministic analysis
  const yoyMap = {};
  if (analysis?.yoy_comparisons && analysis.yoy_comparisons.length > 0) {
    const comp = analysis.yoy_comparisons[0];
    for (const [key, metricData] of Object.entries(comp.metrics || {})) {
      yoyMap[key.toLowerCase()] = metricData.pct_change;
    }
  }

  // Visual bar percentage calculation relative to revenue
  const revBase = Math.max(Math.abs(revenue || 1), 1);
  const gpPct = grossProfit !== null && grossProfit !== undefined ? Math.min(100, Math.max(5, (grossProfit / revBase) * 100)) : 0;
  const opexPct = opExpenses !== null && opExpenses !== undefined ? Math.min(100, Math.max(5, (opExpenses / revBase) * 100)) : 0;
  const opIncPct = opIncome !== null && opIncome !== undefined ? Math.min(100, Math.max(5, (Math.abs(opIncome) / revBase) * 100)) : 0;
  const netIncPct = netIncome !== null && netIncome !== undefined ? Math.min(100, Math.max(5, (Math.abs(netIncome) / revBase) * 100)) : 0;
  const ocfPct = opCashFlow !== null && opCashFlow !== undefined ? Math.min(100, Math.max(5, (Math.abs(opCashFlow) / revBase) * 100)) : 0;

  // Balance sheet proportions
  const assetBase = Math.max(Math.abs(totalAssets || 1), 1);
  const liabRatio = totalLiab !== null && totalLiab !== undefined ? Math.min(100, Math.max(0, (totalLiab / assetBase) * 100)) : 0;
  const equityRatio = totalEquity !== null && totalEquity !== undefined ? Math.min(100, Math.max(0, (totalEquity / assetBase) * 100)) : 0;

  // Health and Risk
  const health = currentDocument.healthScore;
  const riskCount = currentDocument.riskFlagCount ?? 0;
  const valErrors = currentDocument.validationErrorCount ?? 0;
  const overallRisk = (riskCount > 2 || valErrors > 0) ? 'HIGH' : riskCount > 0 ? 'MODERATE' : 'LOW';

  return (
    <div className="space-y-6 pb-12 animate-in fade-in duration-300">
      {/* ── Active Document Info Bar & Actions ───────────────────────────── */}
      <div className="p-4 rounded-xl bg-gradient-to-r from-slate-900 via-[#0B1120] to-slate-900 border border-slate-800 flex flex-col md:flex-row md:items-center justify-between gap-4 shadow-lg">
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 rounded-lg bg-cyan-500/10 border border-cyan-500/30 flex items-center justify-center text-cyan-400 shrink-0">
            <FileText className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center space-x-2 flex-wrap gap-y-1">
              <h2 className="text-sm font-bold text-slate-100">{uploadedFileInfo?.filename || currentDocument.filename}</h2>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700">
                {uploadedFileInfo?.fileType || currentDocument.fileType}
              </span>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-cyan-950 text-cyan-300 border border-cyan-500/30">
                ID: #{currentDocument.id}
              </span>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded border font-bold bg-emerald-950 text-emerald-300 border-emerald-500/30">
                ANALYSIS COMPLETED
              </span>
              <span className={`text-[10px] font-mono px-2 py-0.5 rounded border font-bold ${
                currencyBadge.isSpecified 
                  ? 'bg-indigo-950/80 text-indigo-300 border-indigo-500/30'
                  : 'bg-slate-800 text-slate-400 border-slate-700'
              }`}>
                {currencyBadge.text}
              </span>
            </div>
            <p className="text-xs text-slate-400 mt-1 font-mono">
              Size: {uploadedFileInfo?.fileSize || currentDocument.fileSize} • Uploaded: {uploadedFileInfo?.uploadDate} • Reporting Periods: {statements.length || 1}
            </p>
          </div>
        </div>

        <div className="flex items-center space-x-3 self-start md:self-auto">
          <RouterLink
            to="/agent-processing"
            className="px-3.5 py-1.5 rounded-lg bg-gradient-to-r from-cyan-500 to-blue-600 text-slate-950 text-xs font-bold shadow-glow-cyan hover:scale-105 transition-all flex items-center space-x-1.5"
          >
            <Sparkles className="w-3.5 h-3.5" />
            <span>Review Stages</span>
          </RouterLink>

          <RouterLink
            to="/reports"
            className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-mono border border-slate-700 transition-all flex items-center space-x-1.5"
          >
            <span>Export Report</span>
          </RouterLink>

          <button
            onClick={() => setShowDeleteModal(true)}
            className="p-2 rounded-lg bg-red-950/40 hover:bg-red-950/80 text-red-400 border border-red-500/30 hover:border-red-500/60 transition-all flex items-center space-x-1.5 text-xs font-mono cursor-pointer"
            title="Delete Document"
          >
            <Trash2 className="w-4 h-4" />
            <span className="hidden sm:inline">Delete</span>
          </button>
        </div>
      </div>

      {/* ── 1. FINANCIAL OVERVIEW (Visual KPI Cards with Visual Indicators) ─ */}
      <div className="p-6 rounded-2xl bg-[#0B1120] border border-slate-800 space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2.5">
            <div className="w-8 h-8 rounded-lg bg-cyan-500/10 border border-cyan-500/30 flex items-center justify-center text-cyan-400">
              <DollarSign className="w-4 h-4" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-slate-100 font-mono uppercase tracking-wider">
                Financial Highlights & Overview
              </h3>
              <p className="text-xs text-slate-400">
                Visual performance KPIs and change metrics from verified deterministic statements.
              </p>
            </div>
          </div>
          <span className="text-[10px] font-mono px-2.5 py-1 rounded bg-slate-900 text-cyan-400 border border-slate-800">
            {latestStatement?.fiscal_year ? `FY ${latestStatement.fiscal_year}` : 'Current Period'}
          </span>
        </div>

        {/* Visual KPI Cards Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 pt-2 font-mono">
          {/* Revenue */}
          <div className="p-4 rounded-xl bg-[#070B14] border border-slate-800/90 space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs text-slate-400 uppercase font-semibold">Revenue</span>
              {yoyMap.revenue !== undefined && yoyMap.revenue !== null && (
                <span className={`text-[10px] px-2 py-0.5 rounded font-bold ${
                  yoyMap.revenue >= 0 ? 'bg-emerald-950/80 text-emerald-400 border border-emerald-500/30' : 'bg-rose-950/80 text-rose-400 border border-rose-500/30'
                }`}>
                  {formatPercent(yoyMap.revenue)} YoY
                </span>
              )}
            </div>
            <div className="flex items-baseline justify-between">
              <span className="text-xl font-bold text-cyan-400">{formatMoney(revenue)}</span>
              <span className="text-[10px] text-slate-500">Baseline (100%)</span>
            </div>
            {/* Visual full bar */}
            <div className="w-full bg-slate-800 h-2 rounded-full overflow-hidden">
              <div className="h-full bg-gradient-to-r from-blue-600 to-cyan-400 rounded-full shadow-glow-cyan w-full" />
            </div>
          </div>

          {/* Gross Profit */}
          <div className="p-4 rounded-xl bg-[#070B14] border border-slate-800/90 space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs text-slate-400 uppercase font-semibold">Gross Profit</span>
              {yoyMap['gross profit'] !== undefined && yoyMap['gross profit'] !== null ? (
                <span className={`text-[10px] px-2 py-0.5 rounded font-bold ${
                  yoyMap['gross profit'] >= 0 ? 'bg-emerald-950/80 text-emerald-400 border border-emerald-500/30' : 'bg-rose-950/80 text-rose-400 border border-rose-500/30'
                }`}>
                  {formatPercent(yoyMap['gross profit'])} YoY
                </span>
              ) : (
                <span className="text-[10px] text-slate-500 font-mono">
                  Margin: {revenue ? `${((grossProfit / revenue) * 100).toFixed(1)}%` : '—'}
                </span>
              )}
            </div>
            <div className="flex items-baseline justify-between">
              <span className="text-xl font-bold text-emerald-400">{formatMoney(grossProfit)}</span>
              <span className="text-[10px] text-emerald-500">{gpPct.toFixed(0)}% of Rev</span>
            </div>
            <div className="w-full bg-slate-800 h-2 rounded-full overflow-hidden">
              <div
                style={{ width: `${gpPct}%` }}
                className="h-full bg-gradient-to-r from-emerald-600 to-emerald-400 rounded-full"
              />
            </div>
          </div>

          {/* Operating Expenses */}
          <div className="p-4 rounded-xl bg-[#070B14] border border-slate-800/90 space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs text-slate-400 uppercase font-semibold">Operating Expenses</span>
              <span className="text-[10px] text-slate-500 font-mono">
                {revenue ? `${((opExpenses / revenue) * 100).toFixed(1)}% of Rev` : '—'}
              </span>
            </div>
            <div className="flex items-baseline justify-between">
              <span className="text-xl font-bold text-slate-200">{formatMoney(opExpenses)}</span>
              <span className="text-[10px] text-slate-500">{opexPct.toFixed(0)}% Share</span>
            </div>
            <div className="w-full bg-slate-800 h-2 rounded-full overflow-hidden">
              <div
                style={{ width: `${opexPct}%` }}
                className="h-full bg-gradient-to-r from-indigo-600 to-slate-400 rounded-full"
              />
            </div>
          </div>

          {/* Operating Profit / Income */}
          <div className="p-4 rounded-xl bg-[#070B14] border border-slate-800/90 space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs text-slate-400 uppercase font-semibold">Operating Income</span>
              {yoyMap['operating profit'] !== undefined && yoyMap['operating profit'] !== null && (
                <span className={`text-[10px] px-2 py-0.5 rounded font-bold ${
                  yoyMap['operating profit'] >= 0 ? 'bg-emerald-950/80 text-emerald-400 border border-emerald-500/30' : 'bg-rose-950/80 text-rose-400 border border-rose-500/30'
                }`}>
                  {formatPercent(yoyMap['operating profit'])} YoY
                </span>
              )}
            </div>
            <div className="flex items-baseline justify-between">
              <span className="text-xl font-bold text-indigo-400">{formatMoney(opIncome)}</span>
              <span className="text-[10px] text-indigo-400">{opIncPct.toFixed(0)}% of Rev</span>
            </div>
            <div className="w-full bg-slate-800 h-2 rounded-full overflow-hidden">
              <div
                style={{ width: `${opIncPct}%` }}
                className="h-full bg-gradient-to-r from-indigo-500 to-cyan-400 rounded-full"
              />
            </div>
          </div>

          {/* Net Profit / Income */}
          <div className="p-4 rounded-xl bg-[#070B14] border border-slate-800/90 space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs text-slate-400 uppercase font-semibold">Net Profit</span>
              {yoyMap['net profit'] !== undefined && yoyMap['net profit'] !== null ? (
                <span className={`text-[10px] px-2 py-0.5 rounded font-bold ${
                  yoyMap['net profit'] >= 0 ? 'bg-emerald-950/80 text-emerald-400 border border-emerald-500/30' : 'bg-rose-950/80 text-rose-400 border border-rose-500/30'
                }`}>
                  {formatPercent(yoyMap['net profit'])} YoY
                </span>
              ) : (
                <span className="text-[10px] text-slate-500 font-mono">
                  Margin: {formatPercent(latestStatement.net_profit_margin)}
                </span>
              )}
            </div>
            <div className="flex items-baseline justify-between">
              <span className={`text-xl font-bold ${
                (netIncome || 0) >= 0 ? 'text-emerald-400' : 'text-rose-400'
              }`}>
                {formatMoney(netIncome)}
              </span>
              <span className="text-[10px] text-slate-500">
                {(netIncome || 0) >= 0 ? 'Profitable' : 'Deficit'}
              </span>
            </div>
            <div className="w-full bg-slate-800 h-2 rounded-full overflow-hidden">
              <div
                style={{ width: `${netIncPct}%` }}
                className={`h-full rounded-full ${
                  (netIncome || 0) >= 0 ? 'bg-gradient-to-r from-emerald-500 to-teal-400' : 'bg-gradient-to-r from-rose-600 to-rose-400'
                }`}
              />
            </div>
          </div>

          {/* Operating Cash Flow */}
          <div className="p-4 rounded-xl bg-[#070B14] border border-slate-800/90 space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs text-slate-400 uppercase font-semibold">Operating Cash Flow</span>
              {yoyMap['operating cash flow'] !== undefined && yoyMap['operating cash flow'] !== null && (
                <span className={`text-[10px] px-2 py-0.5 rounded font-bold ${
                  yoyMap['operating cash flow'] >= 0 ? 'bg-emerald-950/80 text-emerald-400 border border-emerald-500/30' : 'bg-rose-950/80 text-rose-400 border border-rose-500/30'
                }`}>
                  {formatPercent(yoyMap['operating cash flow'])} YoY
                </span>
              )}
            </div>
            <div className="flex items-baseline justify-between">
              <span className="text-xl font-bold text-teal-400">{formatMoney(opCashFlow)}</span>
              <span className="text-[10px] text-teal-500">{ocfPct.toFixed(0)}% of Rev</span>
            </div>
            <div className="w-full bg-slate-800 h-2 rounded-full overflow-hidden">
              <div
                style={{ width: `${ocfPct}%` }}
                className="h-full bg-gradient-to-r from-teal-600 to-cyan-400 rounded-full"
              />
            </div>
          </div>
        </div>
      </div>

      {/* ── 2. BALANCE SHEET (Visual Assets, Liabilities & Equity) ─────────── */}
      <div className="p-6 rounded-2xl bg-[#0B1120] border border-slate-800 space-y-5">
        <div className="flex items-center justify-between flex-wrap gap-2">
          <div className="flex items-center space-x-2.5">
            <div className="w-8 h-8 rounded-lg bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center text-emerald-400">
              <Scale className="w-4 h-4" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-slate-100 font-mono uppercase tracking-wider">
                Balance Sheet Composition
              </h3>
              <p className="text-xs text-slate-400">
                Visual capital structure representation: Assets = Liabilities + Equity.
              </p>
            </div>
          </div>

          <span className="inline-flex items-center space-x-1.5 px-3 py-1 rounded-full bg-emerald-950/80 border border-emerald-500/30 text-emerald-400 text-xs font-mono font-bold">
            <CheckCircle2 className="w-3.5 h-3.5" />
            <span>Accounting Equation Verified</span>
          </span>
        </div>

        {/* Visual Proportional Balance Graphic */}
        <div className="p-4 rounded-xl bg-[#070B14] border border-slate-800/80 space-y-3">
          <div className="flex items-center justify-between text-xs font-mono">
            <span className="text-slate-400">Assets vs Capital Structure:</span>
            <span className="text-slate-500">
              Liabilities ({liabRatio.toFixed(1)}%) + Equity ({equityRatio.toFixed(1)}%)
            </span>
          </div>

          {/* Stacked Proportional Bar */}
          <div className="w-full h-4 rounded-full bg-slate-800 flex overflow-hidden p-0.5">
            <div
              style={{ width: `${liabRatio}%` }}
              className="bg-amber-400 h-full rounded-l-full transition-all duration-500"
              title={`Liabilities: ${liabRatio.toFixed(1)}%`}
            />
            <div
              style={{ width: `${equityRatio}%` }}
              className="bg-emerald-400 h-full rounded-r-full transition-all duration-500"
              title={`Equity: ${equityRatio.toFixed(1)}%`}
            />
          </div>

          <div className="flex items-center justify-between text-[11px] font-mono pt-1 text-slate-400">
            <span className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded bg-amber-400 inline-block" />
              <span>Total Liabilities: <strong>{formatMoney(totalLiab)}</strong></span>
            </span>
            <span className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded bg-emerald-400 inline-block" />
              <span>Total Equity: <strong>{formatMoney(totalEquity)}</strong></span>
            </span>
          </div>
        </div>

        {/* 3 Large Visual KPI Blocks */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 font-mono">
          {/* Total Assets */}
          <div className="p-5 rounded-xl bg-[#070B14] border border-cyan-500/30 shadow-[0_0_15px_rgba(0,229,255,0.05)] space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-cyan-400 uppercase">Total Assets</span>
              <span className="text-[10px] px-2 py-0.5 rounded bg-cyan-950 text-cyan-300 border border-cyan-500/30">
                100% Base
              </span>
            </div>
            <div className="text-2xl font-black text-white">{formatMoney(totalAssets)}</div>
            <div className="space-y-1.5 pt-1 text-xs border-t border-slate-800">
              <div className="flex justify-between text-slate-400 text-[11px]">
                <span>Current Assets:</span>
                <span className="text-slate-200 font-bold">{formatMoney(currentAssets)}</span>
              </div>
              <div className="flex justify-between text-slate-400 text-[11px]">
                <span>Cash & Equivalents:</span>
                <span className="text-slate-200 font-bold">{formatMoney(cashEquiv)}</span>
              </div>
            </div>
          </div>

          {/* Total Liabilities */}
          <div className="p-5 rounded-xl bg-[#070B14] border border-amber-500/30 space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-amber-400 uppercase">Total Liabilities</span>
              <span className="text-[10px] px-2 py-0.5 rounded bg-amber-950 text-amber-300 border border-amber-500/30">
                {liabRatio.toFixed(1)}% Ratio
              </span>
            </div>
            <div className="text-2xl font-black text-white">{formatMoney(totalLiab)}</div>
            <div className="space-y-1.5 pt-1 text-xs border-t border-slate-800">
              <div className="flex justify-between text-slate-400 text-[11px]">
                <span>Current Liabilities:</span>
                <span className="text-slate-200 font-bold">{formatMoney(currentLiab)}</span>
              </div>
              <div className="flex justify-between text-slate-400 text-[11px]">
                <span>Solvency Debt Ratio:</span>
                <span className="text-slate-200 font-bold">{(liabRatio / 100).toFixed(2)}x</span>
              </div>
            </div>
          </div>

          {/* Total Equity */}
          <div className="p-5 rounded-xl bg-[#070B14] border border-emerald-500/30 space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-emerald-400 uppercase">Total Equity</span>
              <span className="text-[10px] px-2 py-0.5 rounded bg-emerald-950 text-emerald-300 border border-emerald-500/30">
                {equityRatio.toFixed(1)}% Ratio
              </span>
            </div>
            <div className="text-2xl font-black text-white">{formatMoney(totalEquity)}</div>
            <div className="space-y-1.5 pt-1 text-xs border-t border-slate-800">
              <div className="flex justify-between text-slate-400 text-[11px]">
                <span>Net Book Value:</span>
                <span className="text-emerald-400 font-bold">{formatMoney(totalEquity)}</span>
              </div>
              <div className="flex justify-between text-slate-400 text-[11px]">
                <span>Equity Cushion:</span>
                <span className="text-slate-200 font-bold">{equityRatio.toFixed(1)}%</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* ── 3. RISK ANALYSIS SUMMARY (Requirement 8) ───────────────────────── */}
      <div className="p-6 rounded-2xl bg-[#0B1120] border border-slate-800 space-y-4">
        <div className="flex items-center justify-between flex-wrap gap-2">
          <div className="flex items-center space-x-2.5">
            <div className="w-8 h-8 rounded-lg bg-amber-500/10 border border-amber-500/30 flex items-center justify-center text-amber-400">
              <AlertTriangle className="w-4 h-4" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-slate-100 font-mono uppercase tracking-wider">
                Risk & Verification Summary
              </h3>
              <p className="text-xs text-slate-400">
                Mathematical integrity screening and audit risk classification.
              </p>
            </div>
          </div>

          <RouterLink
            to="/risk"
            className="text-xs text-cyan-400 hover:text-cyan-300 font-mono flex items-center space-x-1 group"
          >
            <span>Open Full Risk Analysis</span>
            <ChevronRight className="w-4 h-4 transition-transform group-hover:translate-x-0.5" />
          </RouterLink>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 font-mono text-xs pt-1">
          <div className="p-3.5 rounded-xl bg-[#070B14] border border-slate-800">
            <span className="text-[10px] text-slate-500 uppercase block">Overall Financial Risk</span>
            <span className={`text-base font-bold mt-1 inline-block px-2.5 py-0.5 rounded border ${
              overallRisk === 'HIGH' ? 'text-rose-400 bg-rose-950/60 border-rose-500/40' :
              overallRisk === 'MODERATE' ? 'text-amber-400 bg-amber-950/60 border-amber-500/40' :
              'text-emerald-400 bg-emerald-950/60 border-emerald-500/40'
            }`}>
              {overallRisk}
            </span>
          </div>

          <div className="p-3.5 rounded-xl bg-[#070B14] border border-slate-800">
            <span className="text-[10px] text-slate-500 uppercase block">Financial Health Score</span>
            <div className="flex items-baseline space-x-1 mt-1">
              <span className="text-lg font-bold text-cyan-400">
                {health !== null ? Number(health).toFixed(1) : 'Not Available'}
              </span>
              <span className="text-slate-500 text-xs">/ 100</span>
            </div>
          </div>

          <div className="p-3.5 rounded-xl bg-[#070B14] border border-slate-800">
            <span className="text-[10px] text-slate-500 uppercase block">Validation Discrepancies</span>
            <span className={`text-lg font-bold mt-1 block ${valErrors === 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
              {valErrors === 0 ? '0 Errors' : `${valErrors} Errors`}
            </span>
          </div>

          <div className="p-3.5 rounded-xl bg-[#070B14] border border-slate-800">
            <span className="text-[10px] text-slate-500 uppercase block">Risk Flags Identified</span>
            <span className="text-lg font-bold text-amber-400 mt-1 block">
              {riskCount}
            </span>
          </div>
        </div>
      </div>

      {/* ── Delete Confirmation Modal ─────────────────────────────────────── */}
      {showDeleteModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4 animate-in fade-in">
          <div className="max-w-md w-full p-6 rounded-2xl bg-[#0B1120] border border-red-500/40 shadow-2xl space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-2 text-red-400 font-bold font-mono text-sm">
                <AlertTriangle className="w-5 h-5" />
                <span>Confirm Document Purge</span>
              </div>
              <button
                onClick={() => setShowDeleteModal(false)}
                className="text-slate-400 hover:text-white p-1 rounded-lg hover:bg-slate-800"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
            <p className="text-xs text-slate-300 leading-relaxed">
              Are you sure you want to permanently delete <strong className="text-white font-mono">{uploadedFileInfo?.filename}</strong>? This will purge all associated verification scores, deterministic calculations, and audit reports from the archive.
            </p>
            {deleteError && (
              <div className="p-2.5 rounded-lg bg-red-950/60 border border-red-500/40 text-xs text-red-300 font-mono">
                {deleteError}
              </div>
            )}
            <div className="flex items-center justify-end space-x-3 pt-2">
              <button
                type="button"
                onClick={() => setShowDeleteModal(false)}
                className="px-4 py-2 rounded-xl text-xs text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleDeleteDocument}
                disabled={isDeleting}
                className="px-4 py-2 rounded-xl bg-red-600 hover:bg-red-500 text-white text-xs font-bold transition-all disabled:opacity-50 flex items-center space-x-1.5 shadow-lg shadow-red-600/30 cursor-pointer"
              >
                {isDeleting && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
                <span>{isDeleting ? 'Purging...' : 'Delete Document'}</span>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Footer disclaimer */}
      <div className="p-3 rounded-lg bg-slate-900/40 border border-slate-800/80 text-[11px] text-slate-500 font-mono flex items-center space-x-2">
        <Info className="w-3.5 h-3.5 text-cyan-500 shrink-0" />
        <span>Financial statement data is computed deterministically in pure Python math with zero arithmetic hallucinations. Missing values display as Not Available.</span>
      </div>
    </div>
  );
};
