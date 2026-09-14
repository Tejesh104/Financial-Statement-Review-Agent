import React, { useState, useEffect } from 'react';
import { Link as RouterLink } from 'react-router-dom';
import {
  AlertTriangle,
  AlertOctagon,
  ShieldCheck,
  CheckCircle2,
  FileText,
  UploadCloud,
  ArrowRight,
  Scale,
  Sparkles,
  Info,
  Loader2
} from 'lucide-react';
import { useDocument } from '../services/documentContext';
import api from '../services/api';
import { formatCurrency, extractCurrencyMeta } from '../utils/currency';

/**
 * Safely format evidence whether it's a string, number, or complex dictionary/object.
 * Prevents React child rendering exceptions on JSON objects.
 */
const renderEvidence = (evidence, currencyMeta = null) => {
  if (!evidence) return null;
  if (typeof evidence === 'string') return evidence;
  if (typeof evidence === 'number' || typeof evidence === 'boolean') return String(evidence);
  if (typeof evidence === 'object') {
    if (Array.isArray(evidence)) {
      return evidence
        .map((e) => (typeof e === 'object' ? JSON.stringify(e) : String(e)))
        .join(', ');
    }
    return Object.entries(evidence)
      .map(([key, val]) => {
        const formattedKey = key.replace(/_/g, ' ');
        let formattedVal = val;
        if (typeof val === 'number') {
          if (
            key.toLowerCase().includes('pct') ||
            key.toLowerCase().includes('change') ||
            key.toLowerCase().includes('rate') ||
            key.toLowerCase().includes('ratio') ||
            key.toLowerCase().includes('score')
          ) {
            formattedVal = `${val.toFixed(2)}%`;
          } else if (Math.abs(val) >= 1000) {
            formattedVal = formatCurrency(val, currencyMeta, { compact: false, precision: 2 });
          } else {
            formattedVal = String(val);
          }
        } else if (typeof val === 'object' && val !== null) {
          formattedVal = JSON.stringify(val);
        }
        return `${formattedKey}: ${formattedVal}`;
      })
      .join('  •  ');
  }
  return String(evidence);
};

const RiskAnalysisContent = () => {
  const { hasDocument, currentDocument, isHydrating } = useDocument();
  const [fetchedAnalysis, setFetchedAnalysis] = useState(null);
  const [isFetching, setIsFetching] = useState(false);

  // Fallback direct API fetch if document ID exists but details/findings are not in context
  useEffect(() => {
    if (currentDocument?.id && !currentDocument?.details && !fetchedAnalysis && !isFetching) {
      setIsFetching(true);
      api.get(`/documents/${currentDocument.id}/analysis`)
        .then((res) => {
          setFetchedAnalysis(res.data);
        })
        .catch((err) => {
          console.error("Failed to load risk analysis data:", err);
        })
        .finally(() => {
          setIsFetching(false);
        });
    }
  }, [currentDocument?.id, currentDocument?.details, fetchedAnalysis, isFetching]);

  if (isHydrating || isFetching) {
    return (
      <div className="p-16 rounded-2xl bg-[#0B1120]/80 border border-cyan-500/30 text-center space-y-3">
        <Loader2 className="w-8 h-8 mx-auto text-cyan-400 animate-spin" />
        <p className="text-sm text-cyan-300 font-mono">
          Loading deterministic financial risk assessment...
        </p>
      </div>
    );
  }

  // ── State 1: No document uploaded ──────────────────────────────────────────
  if (!hasDocument) {
    return (
      <div className="max-w-3xl mx-auto py-16 px-4 text-center space-y-6 animate-in fade-in duration-300">
        <div className="w-16 h-16 mx-auto rounded-2xl bg-amber-500/10 border border-amber-500/30 flex items-center justify-center text-amber-400">
          <AlertTriangle className="w-8 h-8" />
        </div>
        <div className="space-y-2">
          <h1 className="text-2xl font-bold text-white tracking-tight uppercase">Risk & Anomaly Analysis</h1>
          <h2 className="text-base font-semibold text-slate-200">Upload a financial statement to generate risk analysis.</h2>
          <p className="text-xs text-slate-400 max-w-md mx-auto">
            FINNY evaluates cross-statement accounting equations, working-capital reconciliation, and forensic variance indicators.
          </p>
        </div>
        <div>
          <RouterLink
            to="/upload"
            className="inline-flex items-center space-x-2 px-6 py-3 rounded-xl bg-gradient-to-r from-cyan-500 to-blue-600 text-slate-950 text-xs font-bold shadow-glow-cyan hover:scale-105 transition-all"
          >
            <UploadCloud className="w-4 h-4" />
            <span>Upload Document</span>
          </RouterLink>
        </div>
      </div>
    );
  }

  // Resolve analysis details from context or local fetch
  const analysis = currentDocument?.details || fetchedAnalysis?.details || null;
  const hasAnalysis = Boolean(
    currentDocument?.id && (
      analysis?.status === 'COMPLETED' ||
      currentDocument?.healthScore !== null ||
      fetchedAnalysis?.document_health_score !== undefined ||
      (currentDocument?.findings && currentDocument.findings.length > 0) ||
      (fetchedAnalysis?.findings && fetchedAnalysis.findings.length > 0)
    )
  );

  // ── State 2: Document uploaded but analysis pending ────────────────────────
  if (!hasAnalysis) {
    return (
      <div className="max-w-3xl mx-auto py-12 px-4 text-center space-y-6 animate-in fade-in duration-300">
        <div className="p-6 rounded-2xl bg-[#0B1120] border border-slate-800 space-y-4">
          <div className="w-12 h-12 mx-auto rounded-xl bg-cyan-500/10 border border-cyan-500/30 flex items-center justify-center text-cyan-400">
            <FileText className="w-6 h-6" />
          </div>
          <div>
            <h2 className="text-base font-bold text-slate-100">{currentDocument?.filename}</h2>
            <p className="text-xs text-slate-400 mt-1">
              Document uploaded. Run the deterministic review engine to evaluate financial risk indicators.
            </p>
          </div>
          <RouterLink
            to="/agent-processing"
            className="inline-flex items-center space-x-2 px-5 py-2.5 rounded-xl bg-gradient-to-r from-cyan-500 to-blue-600 text-slate-950 text-xs font-bold shadow-glow-cyan hover:scale-105 transition-all"
          >
            <Sparkles className="w-4 h-4" />
            <span>Launch Review (9 Stages)</span>
          </RouterLink>
        </div>
      </div>
    );
  }

  // ── State 3: Analysis completed — Real Financial Risk Data ─────────────────
  const health = currentDocument?.healthScore ?? fetchedAnalysis?.document_health_score ?? null;
  const riskCount = currentDocument?.riskFlagCount ?? fetchedAnalysis?.risk_flag_count ?? (analysis?.risk_indicators?.length ?? 0);
  const anomalyCount = currentDocument?.anomalyCount ?? fetchedAnalysis?.anomaly_count ?? (analysis?.anomalies?.length ?? 0);
  const valErrors = currentDocument?.validationErrorCount ?? fetchedAnalysis?.validation_error_count ?? 0;

  const overallRisk = (riskCount > 2 || valErrors > 0) ? 'HIGH' : riskCount > 0 ? 'MODERATE' : 'LOW';
  const riskColor = overallRisk === 'HIGH' ? 'text-rose-400 bg-rose-950/60 border-rose-500/40' :
                    overallRisk === 'MODERATE' ? 'text-amber-400 bg-amber-950/60 border-amber-500/40' :
                    'text-emerald-400 bg-emerald-950/60 border-emerald-500/40';

  const currencyMeta = fetchedAnalysis?.currency_meta || currentDocument?.currency_meta || currentDocument?.details?.currency_meta || analysis?.currency_meta;

  // Consolidate anomalies from details or top-level findings
  const rawAnomalies = (analysis?.anomalies && analysis.anomalies.length > 0)
    ? analysis.anomalies
    : (analysis?.risk_indicators && analysis.risk_indicators.length > 0)
      ? analysis.risk_indicators
      : (currentDocument?.findings && currentDocument.findings.length > 0)
        ? currentDocument.findings
        : (fetchedAnalysis?.findings && fetchedAnalysis.findings.length > 0)
          ? fetchedAnalysis.findings
          : [];

  const consistencyChecks = analysis?.consistency_checks || fetchedAnalysis?.details?.consistency_checks || [];
  const accountingEquation = analysis?.accounting_equation || fetchedAnalysis?.details?.accounting_equation || null;

  return (
    <div className="max-w-5xl mx-auto space-y-6 pb-12 animate-in fade-in duration-300">
      {/* Header Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="inline-flex items-center space-x-2 px-3 py-1 rounded-full bg-cyan-950/80 border border-cyan-500/30 text-cyan-300 text-xs font-mono mb-2">
            <AlertTriangle className="w-3.5 h-3.5 text-cyan-400" />
            <span>Forensic Risk Assessment</span>
          </div>
          <h1 className="text-2xl font-bold text-white tracking-tight uppercase">
            Financial Risk & Anomaly Analysis
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Grounded in deterministic mathematical checks and verified statement consistency.
          </p>
        </div>

        <div className="flex items-center space-x-3">
          <span className="text-xs font-mono text-slate-400">
            Target: <strong className="text-slate-200">{currentDocument.filename}</strong>
          </span>
        </div>
      </div>

      {/* ── Top Financial Risk KPI Summary ─────────────────────────────────── */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Overall Risk Level */}
        <div className="p-5 rounded-2xl bg-[#0B1120] border border-slate-800 space-y-2">
          <span className="text-[10px] text-slate-400 uppercase font-mono block">Overall Financial Risk</span>
          <div className="flex items-center justify-between">
            <span className={`text-xl font-bold font-mono px-3 py-1 rounded-lg border ${riskColor}`}>
              {overallRisk}
            </span>
            <AlertOctagon className="w-6 h-6 text-slate-500" />
          </div>
          <span className="text-[11px] text-slate-500 font-mono block">
            {overallRisk === 'LOW' ? 'No critical risk flags detected' : `${riskCount} risk indicators flagged`}
          </span>
        </div>

        {/* Financial Health Score */}
        <div className="p-5 rounded-2xl bg-[#0B1120] border border-slate-800 space-y-2">
          <span className="text-[10px] text-slate-400 uppercase font-mono block">Financial Health Score</span>
          <div className="flex items-baseline space-x-1.5">
            <span className="text-2xl font-black text-cyan-400 font-mono">
              {health !== null && health !== undefined ? Number(health).toFixed(1) : 'Not Available'}
            </span>
            <span className="text-xs font-bold text-slate-500 font-mono">/ 100</span>
          </div>
          <div className="w-full bg-slate-800 h-1.5 rounded-full overflow-hidden">
            <div
              style={{ width: `${Math.min(100, Math.max(0, health || 0))}%` }}
              className="h-full bg-gradient-to-r from-blue-500 to-cyan-400 rounded-full"
            />
          </div>
        </div>

        {/* Risk Flags */}
        <div className="p-5 rounded-2xl bg-[#0B1120] border border-slate-800 space-y-2">
          <span className="text-[10px] text-slate-400 uppercase font-mono block">Risk Flags</span>
          <div className="flex items-center justify-between">
            <span className="text-2xl font-bold text-amber-400 font-mono">{riskCount}</span>
            <AlertTriangle className="w-5 h-5 text-amber-400" />
          </div>
          <span className="text-[11px] text-slate-500 font-mono block">Identified by screening engine</span>
        </div>

        {/* Validation Errors */}
        <div className="p-5 rounded-2xl bg-[#0B1120] border border-slate-800 space-y-2">
          <span className="text-[10px] text-slate-400 uppercase font-mono block">Validation Status</span>
          <div className="flex items-center justify-between">
            <span className={`text-xl font-bold font-mono ${valErrors === 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
              {valErrors === 0 ? 'PASSED' : `${valErrors} ERRORS`}
            </span>
            <CheckCircle2 className="w-5 h-5 text-emerald-400" />
          </div>
          <span className="text-[11px] text-slate-500 font-mono block">
            {valErrors === 0 ? 'All accounting checks passed' : 'Discrepancies require review'}
          </span>
        </div>
      </div>

      {/* ── Accounting Equation Integrity Banner ───────────────────────────── */}
      {accountingEquation && (
        <div className="p-4 rounded-xl bg-gradient-to-r from-slate-900/90 to-[#0B1120] border border-slate-800 flex flex-col md:flex-row md:items-center justify-between gap-3">
          <div className="flex items-center space-x-3">
            <div className={`w-9 h-9 rounded-lg flex items-center justify-center shrink-0 ${
              accountingEquation.status === 'PASS' || accountingEquation.status === 'BALANCED'
                ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/30'
                : 'bg-rose-500/10 text-rose-400 border border-rose-500/30'
            }`}>
              <Scale className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <span className="text-xs font-bold text-slate-200">Balance Sheet Equation Verification</span>
                <span className={`text-[10px] font-mono px-2 py-0.5 rounded font-bold ${
                  accountingEquation.status === 'PASS' || accountingEquation.status === 'BALANCED'
                    ? 'bg-emerald-950 text-emerald-400 border border-emerald-500/30'
                    : 'bg-rose-950 text-rose-400 border border-rose-500/30'
                }`}>
                  {accountingEquation.status || 'VERIFIED'}
                </span>
              </div>
              <p className="text-[11px] text-slate-400 font-mono mt-0.5">
                {accountingEquation.explanation || 'Assets = Liabilities + Shareholders’ Equity verification'}
              </p>
            </div>
          </div>
          {accountingEquation.evidence && (
            <div className="text-[11px] font-mono text-slate-300 bg-[#070B14] px-3 py-1.5 rounded-lg border border-slate-800 shrink-0">
              {renderEvidence(accountingEquation.evidence, currencyMeta)}
            </div>
          )}
        </div>
      )}

      {/* ── Section: Detected Financial Risk Indicators & Anomalies ────────── */}
      <div className="p-6 rounded-2xl bg-[#0B1120] border border-slate-800 space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-xs font-bold text-slate-200 font-mono uppercase tracking-wider flex items-center space-x-2">
            <AlertTriangle className="w-4 h-4 text-amber-400" />
            <span>Detected Financial Risk Indicators & Anomalies</span>
          </h2>
          <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-900 text-slate-400 border border-slate-800">
            {rawAnomalies.length} Items Flagged
          </span>
        </div>

        {rawAnomalies.length > 0 ? (
          <div className="space-y-3">
            {rawAnomalies.map((item, idx) => {
              const sev = (item.severity || 'MEDIUM').toUpperCase();
              const isHigh = sev === 'HIGH' || sev === 'CRITICAL';
              const isMed = sev === 'MEDIUM';

              const title = item.title || item.risk_type || 'Financial Discrepancy';
              const desc = item.reason || item.description || 'Variance detected in financial data.';
              const evidenceText = renderEvidence(item.evidence, currencyMeta);

              return (
                <div
                  key={idx}
                  className={`p-4 rounded-xl border transition-all ${
                    isHigh ? 'bg-rose-950/20 border-rose-500/30' :
                    isMed ? 'bg-amber-950/20 border-amber-500/30' :
                    'bg-slate-900/60 border-slate-800'
                  }`}
                >
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-2">
                    <div className="flex items-center space-x-2.5">
                      <span className={`text-[10px] font-mono px-2 py-0.5 rounded font-bold uppercase ${
                        isHigh ? 'bg-rose-950 text-rose-400 border border-rose-500/40' :
                        isMed ? 'bg-amber-950 text-amber-400 border border-amber-500/40' :
                        'bg-slate-800 text-slate-300'
                      }`}>
                        {sev} SEVERITY
                      </span>
                      <h3 className="text-xs font-bold text-white">
                        {title}
                      </h3>
                    </div>
                    {item.category && (
                      <span className="text-[10px] font-mono text-cyan-400 bg-cyan-950/60 px-2 py-0.5 rounded border border-cyan-500/30 self-start sm:self-auto">
                        {item.category}
                      </span>
                    )}
                  </div>

                  {desc && (
                    <p className="text-xs text-slate-300 leading-relaxed mb-2 font-mono">
                      {desc}
                    </p>
                  )}

                  {evidenceText && (
                    <div className="p-2.5 rounded-lg bg-[#070B14] border border-slate-800/80 text-[11px] font-mono text-slate-400 mb-2">
                      <strong className="text-slate-300">Supporting Evidence: </strong>
                      <span className="text-slate-300">{evidenceText}</span>
                    </div>
                  )}

                  {item.recommendation && (
                    <div className="flex items-start space-x-2 text-[11px] text-cyan-300 font-mono">
                      <strong className="text-cyan-400 shrink-0">Action:</strong>
                      <span>{item.recommendation}</span>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        ) : (
          <div className="p-6 rounded-xl bg-slate-900/40 border border-slate-800/80 text-center space-y-2">
            <CheckCircle2 className="w-8 h-8 text-emerald-400 mx-auto" />
            <h3 className="text-xs font-bold text-slate-200">Zero Material Anomalies Flagged</h3>
            <p className="text-[11px] text-slate-400">
              The deterministic math engine detected no statistical or structural anomalies in the reported periods.
            </p>
          </div>
        )}
      </div>

      {/* ── Section: Cross-Statement Mathematical Reconciliations ─────────── */}
      {consistencyChecks.length > 0 && (
        <div className="p-6 rounded-2xl bg-[#0B1120] border border-slate-800 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-xs font-bold text-slate-200 font-mono uppercase tracking-wider flex items-center space-x-2">
              <Scale className="w-4 h-4 text-emerald-400" />
              <span>Cross-Statement Consistency Checks</span>
            </h2>
            <span className="text-[10px] font-mono text-slate-500">
              Deterministic Accounting Equations
            </span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {consistencyChecks.map((chk, idx) => {
              const isPass = chk.status === 'PASS';
              const chkEvidence = renderEvidence(chk.evidence, currencyMeta);

              return (
                <div key={idx} className="p-3.5 rounded-xl bg-[#070B14] border border-slate-800 flex flex-col justify-between gap-2">
                  <div className="flex items-start justify-between gap-2">
                    <p className="text-xs font-bold text-slate-200">{chk.name}</p>
                    <span className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded shrink-0 ${
                      isPass ? 'bg-emerald-950/80 text-emerald-400 border border-emerald-500/30' : 'bg-rose-950/80 text-rose-400 border border-rose-500/30'
                    }`}>
                      {chk.status || (isPass ? 'PASS' : 'FAIL')}
                    </span>
                  </div>

                  <p className="text-[11px] text-slate-400 leading-relaxed font-mono">
                    {chk.explanation || 'Verified in balance equation.'}
                  </p>

                  {chkEvidence && (
                    <div className="text-[10px] font-mono text-slate-500 bg-slate-900/60 px-2.5 py-1 rounded border border-slate-800/80">
                      <span className="text-slate-400 font-semibold">Evidence: </span>{chkEvidence}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Footer Note */}
      <div className="p-3 rounded-lg bg-slate-900/40 border border-slate-800/80 text-[11px] text-slate-500 font-mono flex items-center space-x-2">
        <Info className="w-3.5 h-3.5 text-cyan-500 shrink-0" />
        <span>All risk scores and flags originate exclusively from the deterministic Python analysis engine without LLM estimation.</span>
      </div>
    </div>
  );
};

class RiskAnalysisErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.error("RiskAnalysisPage render error:", error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="max-w-3xl mx-auto py-16 px-4 text-center space-y-4 animate-in fade-in">
          <div className="w-14 h-14 mx-auto rounded-2xl bg-rose-500/10 border border-rose-500/30 flex items-center justify-center text-rose-400">
            <AlertTriangle className="w-7 h-7" />
          </div>
          <h2 className="text-lg font-bold text-white">Risk Analysis Render Issue</h2>
          <p className="text-xs text-slate-400 font-mono max-w-md mx-auto">
            {this.state.error?.message || 'An unexpected issue occurred while rendering the financial risk data.'}
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

export const RiskAnalysisPage = () => {
  return (
    <RiskAnalysisErrorBoundary>
      <RiskAnalysisContent />
    </RiskAnalysisErrorBoundary>
  );
};
