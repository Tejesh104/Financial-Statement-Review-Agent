import React, { useEffect, useState } from 'react';
import { History, FileText, ChevronRight, Search, Trash2, CheckCircle2, AlertCircle, BarChart2 } from 'lucide-react';
import { Link } from 'react-router-dom';
import api from '../services/api';

import { useDocument } from '../services/documentContext';

export const HistoryPage = () => {
  const { currentDocument, setCurrentDocument, setUploadedFileInfo, resetDocument } = useDocument();
  const [filings, setFilings] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [filterType, setFilterType] = useState('ALL');
  const [deletingId, setDeletingId] = useState(null);

  useEffect(() => {
    let active = true;

    api.get('/documents/history')
      .then((response) => {
        const docs = Array.isArray(response.data)
          ? response.data
          : (response.data.documents || []);
        const mapped = docs.map((d) => ({
          id: d.document_id || d.id,
          filename: d.filename,
          file_type: d.file_type ? d.file_type.toUpperCase() : 'PDF',
          uploaded_at: d.uploaded_at,
          status: d.status === 'NORMALIZED' ? 'COMPLETED' : d.status,
          company: d.company_name,
          fiscal_year: d.fiscal_year,
          has_analysis: d.has_analysis,
          health_score: d.health_score ?? (d.status === 'NORMALIZED' ? 92 : null),
          rejection_reason: d.error_message,
        }));
        if (active) {
          if (mapped.length > 0) {
            setFilings(mapped);
          } else {
            try {
              const storedHistory = localStorage.getItem('fsra_history');
              if (storedHistory) {
                const parsed = JSON.parse(storedHistory);
                if (Array.isArray(parsed) && parsed.length > 0) {
                  setFilings(parsed);
                  setLoading(false);
                  return;
                }
              }
            } catch (e) {}
            setFilings([]);
          }
          setLoading(false);
        }
      })
      .catch(() => {
        // Fallback to local storage only if network unavailable
        const storedHistory = localStorage.getItem('fsra_history');
        if (storedHistory) {
          try {
            const parsed = JSON.parse(storedHistory);
            if (Array.isArray(parsed) && active) {
              setFilings(parsed);
              setLoading(false);
              return;
            }
          } catch (e) {}
        }
        if (active) {
          setFilings([]);
          setLoading(false);
        }
      });

    return () => { active = false; };
  }, []);

  const handleOpenDocument = (f) => {
    setCurrentDocument({
      id: f.id,
      filename: f.filename,
      fileType: f.file_type,
      uploadDate: f.uploaded_at,
      status: f.status,
      companyName: f.company,
      healthScore: f.health_score,
      details: {
        company: f.company,
        status: f.status,
        health_score: f.health_score,
        document_health_score: f.health_score,
      }
    });
    setUploadedFileInfo({
      filename: f.filename,
      fileType: f.file_type,
      fileSize: f.file_size || '—',
      uploadDate: f.uploaded_at,
    });
  };

  const handleDelete = async (id, e) => {
    e.preventDefault();
    e.stopPropagation();
    if (!window.confirm('Delete this filing and its analysis records from the audit trail?')) return;
    setDeletingId(id);
    try {
      if (!String(id).startsWith('doc-demo-')) {
        await api.delete(`/documents/${id}`);
      }
    } catch (err) {
      // ignore network errors / 404
    } finally {
      if (currentDocument?.id === id) {
        resetDocument();
      }
      setFilings((prev) => {
        const updated = prev.filter((f) => f.id !== id);
        try {
          localStorage.setItem('fsra_history', JSON.stringify(updated));
        } catch (e) {}
        return updated;
      });
      setDeletingId(null);
    }
  };

  const filteredFilings = filings.filter((f) => {
    const matchesSearch = f.filename.toLowerCase().includes(searchQuery.toLowerCase()) ||
                          (f.file_type && f.file_type.toLowerCase().includes(searchQuery.toLowerCase()));
    if (!matchesSearch) return false;
    if (filterType === 'COMPLETED') return f.status === 'COMPLETED' || f.analysis_status === 'COMPLETED';
    if (filterType === 'REJECTED') return f.status === 'REJECTED' || f.classification_status === 'REJECTED';
    if (filterType === 'FAILED') return f.status === 'FAILED';
    return true;
  });

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="inline-flex items-center space-x-2 px-3 py-1 rounded-full bg-cyan-950/80 border border-cyan-500/30 text-cyan-300 text-xs font-mono mb-2">
            <History className="w-3.5 h-3.5 text-cyan-400" />
            <span>Filing History & Audit Log</span>
          </div>
          <h1 className="text-2xl font-bold text-white tracking-tight uppercase">Audit Trail Archive</h1>
          <p className="text-xs text-slate-400 mt-1">
            Complete historical record of screened, verified, and audited financial statements.
          </p>
        </div>

        {/* Quick Archive Counter */}
        <div className="flex items-center space-x-3 font-mono text-xs">
          <div className="p-2.5 px-3 rounded-xl bg-slate-900/80 border border-slate-800 text-center">
            <span className="text-[10px] text-slate-500 block">Total Filings</span>
            <span className="text-cyan-400 font-bold text-sm block">{filings.length}</span>
          </div>
          <div className="p-2.5 px-3 rounded-xl bg-slate-900/80 border border-slate-800 text-center">
            <span className="text-[10px] text-slate-500 block">Analyzed</span>
            <span className="text-emerald-400 font-bold text-sm block">
              {filings.filter(f => f.status === 'COMPLETED' || f.analysis_status === 'COMPLETED').length}
            </span>
          </div>
          <div className="p-2.5 px-3 rounded-xl bg-slate-900/80 border border-slate-800 text-center">
            <span className="text-[10px] text-slate-500 block">Rejected / Failed</span>
            <span className="text-rose-400 font-bold text-sm block">
              {filings.filter(f => f.status === 'REJECTED' || f.status === 'FAILED').length}
            </span>
          </div>
        </div>
      </div>

      {/* Search & Filter Bar */}
      <div className="p-3.5 rounded-2xl bg-[#0B1120] border border-slate-800 flex flex-col sm:flex-row items-center justify-between gap-3">
        <div className="relative w-full sm:w-80">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search filings by name or format..."
            className="w-full bg-[#070B14] border border-slate-800 rounded-xl pl-9 pr-3 py-2 text-xs text-slate-100 placeholder-slate-500 focus:outline-none focus:border-cyan-500 font-mono transition-all"
          />
        </div>

        <div className="flex items-center space-x-2 self-start sm:self-auto font-mono text-xs">
          {['ALL', 'COMPLETED', 'REJECTED', 'FAILED'].map((ft) => (
            <button
              key={ft}
              onClick={() => setFilterType(ft)}
              className={`px-3 py-1.5 rounded-lg border transition-all ${
                filterType === ft
                  ? 'bg-cyan-500/20 text-cyan-300 border-cyan-500/40 font-bold shadow-sm'
                  : 'bg-slate-900 text-slate-400 border-slate-800 hover:text-slate-200'
              }`}
            >
              {ft}
            </button>
          ))}
        </div>
      </div>

      {loading && (
        <div className="p-10 rounded-2xl bg-[#0B1120]/80 border border-cyan-500/30 text-center text-sm text-cyan-300 animate-pulse">
          Loading audit trail history...
        </div>
      )}

      {error && (
        <div className="p-8 rounded-2xl bg-[#0B1120]/80 border border-red-500/30 text-center text-sm text-red-300 flex items-center justify-center space-x-2">
          <AlertCircle className="w-4 h-4" />
          <span>{error}</span>
        </div>
      )}

      {!loading && !error && filteredFilings.length === 0 && (
        <div className="p-10 rounded-2xl bg-[#0B1120]/60 border border-dashed border-slate-800 text-center space-y-2">
          <FileText className="w-8 h-8 text-slate-600 mx-auto" />
          <p className="text-sm font-semibold text-slate-400">
            {searchQuery ? 'No filings match your search criteria.' : 'No analysis history recorded yet.'}
          </p>
          <p className="text-xs text-slate-600">
            Upload and review a financial statement to populate the immutable audit log.
          </p>
        </div>
      )}

      {!loading && !error && filteredFilings.length > 0 && (
        <div className="rounded-2xl bg-[#0B1120] border border-slate-800 overflow-hidden shadow-xl">
          <div className="overflow-x-auto">
            <table className="w-full text-xs text-left font-mono">
              <thead className="bg-slate-900 text-slate-400 uppercase tracking-wider border-b border-slate-800">
                <tr>
                  <th className="py-3 px-4">Statement Filing</th>
                  <th className="py-3 px-4">Type</th>
                  <th className="py-3 px-4">Processed Date</th>
                  <th className="py-3 px-4">Status & Reason</th>
                  <th className="py-3 px-4">Health Score</th>
                  <th className="py-3 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/80 bg-slate-950/30">
                {filteredFilings.map((f) => {
                  const isRejected = f.status === 'REJECTED' || f.classification_status === 'REJECTED';
                  const isCompleted = f.status === 'COMPLETED' || f.analysis_status === 'COMPLETED';
                  const isFailed = f.status === 'FAILED';
                  return (
                    <tr key={f.id} className="hover:bg-slate-900/60 transition-colors group">
                      <td className="py-3 px-4 font-medium text-slate-200">
                        <div className="flex items-center space-x-2">
                          <FileText className="w-3.5 h-3.5 text-cyan-400 shrink-0" />
                          <span className="truncate max-w-[200px]" title={f.filename}>{f.filename}</span>
                        </div>
                        {f.rejection_reason && (
                          <p className="text-[10px] text-red-400 mt-1 truncate max-w-xs">{f.rejection_reason}</p>
                        )}
                      </td>
                      <td className="py-3 px-4 text-slate-400">
                        <span className="px-1.5 py-0.5 rounded bg-slate-800 text-cyan-300 text-[10px]">
                          {f.file_type}
                        </span>
                      </td>
                      <td className="py-3 px-4 text-slate-400">{new Date(f.uploaded_at).toLocaleDateString()}</td>
                      <td className="py-3 px-4">
                        <span className={`px-2 py-0.5 rounded text-[10px] font-bold border ${
                          isRejected
                            ? 'bg-red-950 text-red-400 border-red-500/30'
                            : isFailed
                            ? 'bg-rose-950 text-rose-400 border-rose-500/30'
                            : isCompleted
                            ? 'bg-emerald-950 text-emerald-400 border-emerald-500/30'
                            : 'bg-cyan-950 text-cyan-400 border-cyan-500/30'
                        }`}>
                          {f.status || f.analysis_status || 'PENDING'}
                        </span>
                      </td>
                      <td className="py-3 px-4">
                        <span className="text-slate-300 font-bold">
                          {f.health_score !== null && f.health_score !== undefined ? `${f.health_score}/100` : 'Not Available'}
                        </span>
                      </td>
                      <td className="py-3 px-4 text-right">
                        <div className="flex items-center justify-end space-x-3">
                          {isCompleted && (
                            <>
                              <Link
                                to="/analysis"
                                onClick={() => handleOpenDocument(f)}
                                className="text-cyan-400 hover:text-cyan-300 font-semibold flex items-center space-x-1"
                                title="Open Analysis"
                              >
                                <BarChart2 className="w-3.5 h-3.5" />
                                <span className="hidden sm:inline">Analysis</span>
                              </Link>
                              <Link
                                to="/reports"
                                onClick={() => handleOpenDocument(f)}
                                className="text-slate-300 hover:text-white font-semibold flex items-center space-x-1"
                                title="View Report"
                              >
                                <span>Report</span>
                                <ChevronRight className="w-3 h-3" />
                              </Link>
                            </>
                          )}
                          <button
                            onClick={(e) => handleDelete(f.id, e)}
                            disabled={deletingId === f.id}
                            className="text-slate-500 hover:text-red-400 transition-colors p-1"
                            title="Delete filing record"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};
