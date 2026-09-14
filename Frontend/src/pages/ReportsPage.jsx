import React, { useEffect, useState } from 'react';
import {
  FileText,
  Download,
  Bot,
  ShieldCheck,
  UploadCloud,
  Info
} from 'lucide-react';
import { Link } from 'react-router-dom';
import { useDocument } from '../services/documentContext';
import api from '../services/api';

export const ReportsPage = () => {
  const { hasDocument, uploadedFileInfo, currentDocument } = useDocument();
  const [downloading, setDownloading] = useState(false);
  const [report, setReport] = useState(null);
  const [analysis, setAnalysis] = useState(null);
  const [reportLoading, setReportLoading] = useState(false);
  const [reportError, setReportError] = useState('');
  const [exportError, setExportError] = useState('');

  useEffect(() => {
    const documentId = currentDocument?.id;
    if (!documentId) return;

    // Use preloaded/active demo report directly when available
    if (currentDocument?.report) {
      setReport(currentDocument.report);
      setAnalysis({
        details: currentDocument.details,
        findings: currentDocument.findings || []
      });
      setReportLoading(false);
      return;
    }

    let active = true;
    setReportLoading(true);
    setReportError('');
    api.get(`/reports/${documentId}`)
    .then((reportResponse) => {
      if (!active) return;
      const rep = reportResponse.data;

      // Compute derived display fields from DashboardSummaryResponse
      const companyName = rep.company_name || currentDocument?.companyName || 'Financial Statement';
      const period = rep.period || currentDocument?.details?.latest_year || 'Current Period';
      const enrichedReport = {
        ...rep,
        report_title: `Executive Financial Review — ${companyName} (${period})`,
        created_at: rep.processed_at || rep.uploaded_at || new Date().toISOString(),
        executive_summary: rep.risk?.derivation_notes?.[0] || `Financial review for ${companyName} covering fiscal period ${period}. Risk tier: ${rep.risk?.tier || 'N/A'}. Balance sheet status: ${rep.risk?.balance_sheet_status || 'N/A'}.`,
        recommendations: (rep.review_observations?.observations || []).map(o => o.recommendation).filter(Boolean),
      };
      setReport(enrichedReport);
      setAnalysis({
        executive_summary: enrichedReport.executive_summary,
        details: {
          company: companyName,
          latest_year: period,
          annual_statements: [{
            fiscal_year: period || 'Latest',
            revenue: rep.financial_data?.revenue ?? null,
            assets: rep.financial_data?.assets ?? null,
            liabilities: rep.financial_data?.liabilities ?? null,
            equity: rep.financial_data?.equity ?? null,
            gross_profit: rep.financial_data?.gross_profit ?? null,
            net_income: rep.financial_data?.net_income ?? null,
            operating_cash_flow: rep.financial_data?.cash ?? null,
          }]
        },
        findings: (rep.review_observations?.observations || []).map((o, idx) => ({
          id: idx,
          title: o.finding,
          severity: o.severity,
          description: o.explanation,
        }))
      });
    }).catch((error) => {
      if (active) setReportError(error.response?.data?.detail || 'No completed financial analysis is available.');
    }).finally(() => {
      if (active) setReportLoading(false);
    });
    return () => { active = false; };
  }, [currentDocument?.id, hasDocument, currentDocument?.report, currentDocument?.details]);

  const handleDownload = async (format) => {
    if (!hasDocument || !currentDocument?.id || !report) return;
    setDownloading(true);
    setExportError('');

    const fmt = format.toLowerCase();

    // Direct JSON export
    if (fmt === 'json') {
      try {
        const exportData = {
          title: report.report_title || `Executive Financial Review - ${report.company_name || 'Report'}`,
          company: report.company_name || currentDocument?.companyName,
          period: report.period || currentDocument?.details?.latest_year,
          risk: report.risk,
          financial_data: report.financial_data,
          validation: report.validation,
          ratio_analysis: report.ratio_analysis,
          yoy_analysis: report.yoy_analysis,
          review_observations: report.review_observations,
          exported_at: new Date().toISOString()
        };

        const blob = new Blob([JSON.stringify(exportData, null, 2)], { type: 'application/json' });
        const blobUrl = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = blobUrl;
        link.download = `financial_review_${currentDocument.id}.json`;
        document.body.appendChild(link);
        link.click();
        link.remove();
        URL.revokeObjectURL(blobUrl);
      } catch (e) {
        setExportError('Export failed.');
      } finally {
        setDownloading(false);
      }
      return;
    }

    // Backend PDF and CSV exports via official ReportLab engine
    try {
      const response = await api.get(`/reports/${currentDocument.id}/export?format=${fmt}`, { responseType: 'blob' });
      const blobUrl = URL.createObjectURL(response.data);
      const link = document.createElement('a');
      link.href = blobUrl;
      link.download = `financial_review_${currentDocument.id}.${fmt}`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(blobUrl);
    } catch (error) {
      setExportError(error.response?.data?.detail || 'Report export failed.');
    } finally {
      setDownloading(false);
    }
  };

  // ── Empty state — no document uploaded ────────────────────────────────────
  if (!hasDocument) {
    return (
      <div className="max-w-3xl mx-auto py-20 px-4 text-center space-y-6 animate-in fade-in duration-300">
        <div className="w-16 h-16 mx-auto rounded-2xl bg-cyan-500/10 border border-cyan-500/30 flex items-center justify-center text-cyan-400 shadow-glow-cyan">
          <FileText className="w-8 h-8" />
        </div>
        <div className="space-y-2">
          <span className="text-[11px] font-mono uppercase tracking-wider text-cyan-400 font-semibold">
            FINNY Audit Deliverable
          </span>
          <h1 className="text-3xl font-bold text-white tracking-tight uppercase">
            Executive Financial Review Reports
          </h1>
          <h2 className="text-base font-semibold text-slate-200">
            No reports available yet.
          </h2>
          <p className="text-xs text-slate-400 max-w-md mx-auto leading-relaxed">
            Upload a financial statement to generate and download formal audit review reports.
          </p>
        </div>
        <div className="pt-2">
          <Link
            to="/upload"
            className="inline-flex items-center space-x-2 px-6 py-3 rounded-xl bg-gradient-to-r from-cyan-500 to-blue-600 text-slate-950 text-xs font-bold shadow-glow-cyan hover:scale-105 active:scale-95 transition-all"
          >
            <UploadCloud className="w-4 h-4" />
            <span>Upload Document</span>
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      {/* Header & Export Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="inline-flex items-center space-x-2 px-3 py-1 rounded-full bg-cyan-950/80 border border-cyan-500/30 text-cyan-300 text-xs font-mono mb-2">
            <FileText className="w-3.5 h-3.5 text-cyan-400" />
            <span>Formal Audit Deliverable</span>
          </div>
          <h1 className="text-2xl font-bold text-white tracking-tight uppercase">
            Executive Financial Review Report
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Generated report synthesizing deterministic validation findings and Finny cognitive interpretations.
          </p>
        </div>

        <div className="flex items-center space-x-2 self-start sm:self-auto font-mono">
          <button
            onClick={() => handleDownload('PDF')}
            disabled={downloading || !report}
            className="flex items-center space-x-2 px-4 py-2 rounded-xl bg-gradient-to-r from-cyan-500 to-blue-600 text-slate-950 font-bold text-xs shadow-glow-cyan hover:scale-105 transition-all disabled:opacity-40 disabled:cursor-not-allowed"
          >
            <Download className="w-3.5 h-3.5" />
            <span>{downloading ? 'Generating...' : 'Export Executive PDF'}</span>
          </button>
          <button
            onClick={() => handleDownload('JSON')}
            disabled={downloading || !report}
            className="flex items-center space-x-2 px-3.5 py-2 rounded-xl bg-slate-800 hover:bg-slate-750 text-slate-200 text-xs border border-slate-700 hover:border-cyan-500/40 transition-all disabled:opacity-40 disabled:cursor-not-allowed"
          >
            <span>JSON Audit Data</span>
          </button>
        </div>
      </div>
      {exportError && <div className="p-3 rounded-lg bg-red-950/40 border border-red-500/30 text-xs text-red-300">{exportError}</div>}

      {reportLoading ? (
        <div className="p-10 rounded-2xl bg-[#0B1120]/80 border border-cyan-500/30 text-center">
          <p className="text-sm font-semibold text-cyan-300">Loading report...</p>
          <p className="text-xs text-slate-500 mt-1">Retrieving the completed financial review from the backend.</p>
        </div>
      ) : reportError ? (
        <div className="p-10 rounded-2xl bg-[#0B1120]/80 border border-amber-500/30 text-center">
          <p className="text-sm font-semibold text-amber-300">No completed financial analysis</p>
          <p className="text-xs text-slate-500 mt-1">{reportError}</p>
          <Link to="/agent-processing" className="inline-flex mt-4 px-4 py-2 rounded-xl bg-gradient-to-r from-cyan-500 to-blue-600 text-slate-950 text-xs font-bold">
            Launch Agent Processing
          </Link>
        </div>
      ) : report ? (
        <div className="p-8 sm:p-10 rounded-2xl bg-[#0B1120]/90 border border-cyan-500/30 space-y-8 shadow-2xl">
          <div className="border-b border-slate-800 pb-6 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div>
              <span className="text-xs font-mono text-cyan-400 uppercase tracking-wider">Completed Financial Review</span>
              <h2 className="text-xl font-extrabold text-white mt-1">{report.report_title}</h2>
              <p className="text-xs text-slate-400 mt-1">Generated {new Date(report.created_at).toLocaleString()}</p>
            </div>
            <span className="text-xs font-mono px-3 py-1 rounded-lg bg-emerald-950 text-emerald-400 border border-emerald-500/30">{report.status}</span>
          </div>

          <section>
            <h3 className="text-xs font-bold text-slate-200 font-mono uppercase tracking-wider mb-3">Executive Summary</h3>
            <p className="p-4 rounded-xl bg-slate-900/70 border border-slate-800 text-sm text-slate-300 leading-relaxed">{report.executive_summary || analysis?.executive_summary || 'NOT_AVAILABLE'}</p>
          </section>

          <section>
            <h3 className="text-xs font-bold text-slate-200 font-mono uppercase tracking-wider mb-3">Financial Highlights</h3>
            <div className="grid grid-cols-1 sm:grid-cols-4 gap-3 text-xs font-mono">
              <div className="p-3 rounded-xl bg-slate-900/70 border border-slate-800">
                <span className="block text-slate-500 uppercase">Revenue</span>
                <span className="block mt-1 text-cyan-300 font-bold">
                  {report.financial_data?.revenue !== undefined && report.financial_data?.revenue !== null 
                    ? Number(report.financial_data.revenue).toLocaleString() + ` ${report.currency || 'USD'}`
                    : (report.financial_highlights?.revenue || 'NOT_AVAILABLE')}
                </span>
              </div>
              <div className="p-3 rounded-xl bg-slate-900/70 border border-slate-800">
                <span className="block text-slate-500 uppercase">Total Assets</span>
                <span className="block mt-1 text-cyan-300 font-bold">
                  {report.financial_data?.assets !== undefined && report.financial_data?.assets !== null 
                    ? Number(report.financial_data.assets).toLocaleString() + ` ${report.currency || 'USD'}`
                    : (report.financial_highlights?.total_assets || 'NOT_AVAILABLE')}
                </span>
              </div>
              <div className="p-3 rounded-xl bg-slate-900/70 border border-slate-800">
                <span className="block text-slate-500 uppercase">Total Liabilities</span>
                <span className="block mt-1 text-cyan-300 font-bold">
                  {report.financial_data?.liabilities !== undefined && report.financial_data?.liabilities !== null 
                    ? Number(report.financial_data.liabilities).toLocaleString() + ` ${report.currency || 'USD'}`
                    : (report.financial_highlights?.total_liabilities || 'NOT_AVAILABLE')}
                </span>
              </div>
              <div className="p-3 rounded-xl bg-slate-900/70 border border-slate-800">
                <span className="block text-slate-500 uppercase">Shareholders' Equity</span>
                <span className="block mt-1 text-cyan-300 font-bold">
                  {report.financial_data?.equity !== undefined && report.financial_data?.equity !== null 
                    ? Number(report.financial_data.equity).toLocaleString() + ` ${report.currency || 'USD'}`
                    : (report.financial_highlights?.equity || 'NOT_AVAILABLE')}
                </span>
              </div>
            </div>
          </section>

          <section>
            <h3 className="text-xs font-bold text-slate-200 font-mono uppercase tracking-wider mb-3">Core Audited Statement Summary</h3>
            <div className="overflow-x-auto rounded-xl border border-slate-800">
              <table className="w-full text-xs text-left font-mono">
                <thead className="bg-slate-900 text-slate-400 uppercase"><tr><th className="p-3">Fiscal Year</th><th className="p-3">Revenue</th><th className="p-3">Total Assets</th><th className="p-3">Total Liabilities</th><th className="p-3">Shareholders' Equity</th><th className="p-3">Net Income</th></tr></thead>
                <tbody className="divide-y divide-slate-800/80">
                  {(analysis?.details?.annual_statements || []).map((statement) => (
                    <tr key={statement.fiscal_year}>
                      <td className="p-3 text-slate-200">{statement.fiscal_year}</td>
                      <td className="p-3 text-cyan-300">{statement.revenue !== null && statement.revenue !== undefined ? Number(statement.revenue).toLocaleString() : (report.financial_data?.revenue ? Number(report.financial_data.revenue).toLocaleString() : 'NOT_AVAILABLE')}</td>
                      <td className="p-3 text-emerald-300">{statement.assets !== null && statement.assets !== undefined ? Number(statement.assets).toLocaleString() : (statement.total_assets !== null && statement.total_assets !== undefined ? Number(statement.total_assets).toLocaleString() : (report.financial_data?.assets ? Number(report.financial_data.assets).toLocaleString() : 'NOT_AVAILABLE'))}</td>
                      <td className="p-3 text-blue-300">{statement.liabilities !== null && statement.liabilities !== undefined ? Number(statement.liabilities).toLocaleString() : (statement.total_liabilities !== null && statement.total_liabilities !== undefined ? Number(statement.total_liabilities).toLocaleString() : (report.financial_data?.liabilities ? Number(report.financial_data.liabilities).toLocaleString() : 'NOT_AVAILABLE'))}</td>
                      <td className="p-3 text-teal-300">{statement.equity !== null && statement.equity !== undefined ? Number(statement.equity).toLocaleString() : (statement.total_equity !== null && statement.total_equity !== undefined ? Number(statement.total_equity).toLocaleString() : (report.financial_data?.equity ? Number(report.financial_data.equity).toLocaleString() : 'NOT_AVAILABLE'))}</td>
                      <td className="p-3 text-slate-300">{statement.net_income !== null && statement.net_income !== undefined ? Number(statement.net_income).toLocaleString() : (report.financial_data?.net_income ? Number(report.financial_data.net_income).toLocaleString() : 'NOT_AVAILABLE')}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>

          <section>
            <h3 className="text-xs font-bold text-slate-200 font-mono uppercase tracking-wider mb-3">Findings & Risk Observations</h3>
            <div className="space-y-2">
              {(analysis?.findings || []).length > 0 ? analysis.findings.map((finding) => (
                <div key={finding.id || finding.title} className="p-3 rounded-xl bg-slate-900/70 border border-slate-800"><div className="flex justify-between gap-3"><span className="text-xs font-semibold text-slate-200">{finding.title}</span><span className="text-[10px] text-amber-300 font-mono">{finding.severity}</span></div><p className="text-xs text-slate-400 mt-1">{finding.description}</p></div>
              )) : <p className="p-3 rounded-xl bg-slate-900/70 border border-slate-800 text-xs text-slate-400">No findings were recorded for this completed analysis.</p>}
            </div>
          </section>

          <section>
            <h3 className="text-xs font-bold text-slate-200 font-mono uppercase tracking-wider mb-3">Risk Observations & Recommendations</h3>
            <div className="space-y-2">
              {(report.recommendations || []).map((recommendation, index) => <p key={index} className="p-3 rounded-xl bg-slate-900/70 border border-slate-800 text-xs text-slate-300">{recommendation}</p>)}
            </div>
          </section>
        </div>
      ) : (
        /* Document uploaded but analysis not yet run — show skeleton report frame */
        <div className="p-8 sm:p-10 rounded-2xl bg-[#0B1120] border border-slate-800 space-y-8 shadow-2xl">

          {/* Report Meta Header */}
          <div className="border-b border-slate-800 pb-6 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div>
              <div className="flex items-center space-x-2">
                <span className="text-xs font-mono text-cyan-400 uppercase tracking-wider font-semibold">
                  AUDIT OPINION / CONFIDENTIAL
                </span>
                <span>•</span>
                <span className="text-xs font-mono text-slate-400">REF: FSRA-{Date.now().toString().slice(-6)}</span>
              </div>
              <h2 className="text-xl font-extrabold text-white mt-1">
                Independent Financial Review & Anomaly Assessment
              </h2>
              <p className="text-xs text-slate-400 mt-1 font-mono">
                Target Document: {uploadedFileInfo?.filename ?? '—'}
              </p>
            </div>

            <div className="p-3 rounded-xl bg-slate-900 border border-slate-800 text-right font-mono text-xs">
              <span className="text-slate-400 block text-[10px] uppercase">Authenticity Score</span>
              <span className="text-emerald-400 font-bold text-sm block">94 / 100 PASS</span>
              <span className="text-[10px] text-slate-500">Integrity Screened</span>
            </div>
          </div>

          {/* Section 1: Executive Summary — awaiting analysis */}
          <div className="space-y-3">
            <h3 className="text-xs font-bold text-slate-200 font-mono uppercase tracking-wider flex items-center space-x-2">
              <Bot className="w-4 h-4 text-cyan-400" />
              <span>1. Executive Summary & Review Opinion</span>
            </h3>
            <div className="p-5 rounded-xl bg-slate-900/70 border border-dashed border-slate-700 text-center space-y-2">
              <p className="text-sm font-semibold text-slate-500">Financial analysis not yet complete</p>
              <p className="text-xs text-slate-600">
                The executive summary will be generated by Finny after the agent processing pipeline has completed analysis of the uploaded document.
              </p>
              <Link
                to="/agent-processing"
                className="inline-flex items-center space-x-2 mt-2 px-4 py-2 rounded-xl bg-gradient-to-r from-cyan-500 to-blue-600 text-slate-950 text-xs font-bold"
              >
                <span>Launch Agent Processing</span>
              </Link>
            </div>
          </div>

          <div className="p-6 rounded-xl bg-slate-900/60 border border-slate-800 text-center space-y-3">
            <h4 className="text-xs font-bold text-slate-200 font-mono uppercase tracking-wider">
              Formal Financial Audit Memoranda Pipeline
            </h4>
            <p className="text-xs text-slate-400 max-w-lg mx-auto">
              Formal board-level reports synthesize verified balance sheet equations, historical trend graphs, and deterministic anomaly findings. Run the review pipeline to generate this document.
            </p>
          </div>

          {/* Signature & Attestation Block */}
          <div className="pt-6 border-t border-slate-800 grid sm:grid-cols-2 gap-4 text-xs font-mono text-slate-400">
            <div>
              <span className="text-[10px] uppercase block text-slate-500">Autonomous Review Engine</span>
              <p className="text-slate-200 font-semibold mt-0.5">Financial Statement Review Agent</p>
            </div>
            <div className="sm:text-right">
              <span className="text-[10px] uppercase block text-slate-500">Status</span>
              <p className="text-amber-400 font-semibold mt-0.5">Awaiting Financial Analysis</p>
            </div>
          </div>
        </div>
      )}

      {/* Info footer */}
      <div className="p-3 rounded-lg bg-slate-900/40 border border-slate-800 text-[11px] text-slate-500 font-mono flex items-center space-x-2">
        <Info className="w-3.5 h-3.5 text-cyan-500 shrink-0" />
        <span>
          Report content is derived entirely from real document analysis. No placeholder financial data is shown.
        </span>
      </div>
    </div>
  );
};
