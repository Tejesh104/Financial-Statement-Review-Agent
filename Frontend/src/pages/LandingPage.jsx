import React from 'react';
import { Link } from 'react-router-dom';
import {
  ShieldCheck,
  ArrowRight,
  Sparkles,
  Activity,
} from 'lucide-react';


export const LandingPage = () => {
  return (
    <div className="min-h-screen bg-[#070B14] text-slate-100 selection:bg-cyan-500/30 selection:text-cyan-200">
      {/* Navigation Header */}
      <nav className="border-b border-slate-800/80 bg-[#0B1120]/80 backdrop-blur-md sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="w-9 h-9 rounded-lg bg-gradient-to-tr from-cyan-500 to-blue-600 flex items-center justify-center shadow-glow-cyan">
              <ShieldCheck className="w-5 h-5 text-slate-950 stroke-[2.5]" />
            </div>
            <div>
              <span className="font-bold text-base text-slate-100 tracking-tight">
                Financial Statement Review Agent
              </span>
              <span className="ml-2 text-[10px] font-mono px-1.5 py-0.5 rounded bg-cyan-950/80 text-cyan-300 border border-cyan-500/30">
                Finny v2.4
              </span>
            </div>
          </div>

          <div className="flex items-center space-x-4">
            <Link
              to="/login"
              className="text-xs font-medium text-slate-300 hover:text-cyan-400 transition-colors px-3 py-2"
            >
              Sign In
            </Link>
            <Link
              to="/dashboard"
              className="flex items-center space-x-2 px-4 py-2 rounded-lg bg-gradient-to-r from-cyan-500 to-blue-600 text-slate-950 text-xs font-bold shadow-glow-cyan hover:scale-105 active:scale-95 transition-all"
            >
              <span>Launch Review Portal</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </Link>
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <section className="relative overflow-hidden pt-20 pb-28 px-6">
        {/* Glow Spheres */}
        <div className="absolute top-10 left-1/2 -translate-x-1/2 w-[600px] h-[300px] bg-cyan-500/10 blur-[120px] rounded-full pointer-events-none" />
        <div className="absolute top-40 right-1/4 w-[400px] h-[300px] bg-indigo-600/10 blur-[120px] rounded-full pointer-events-none" />

        <div className="max-w-5xl mx-auto text-center relative z-10">
          <div className="inline-flex items-center space-x-2 px-3 py-1.5 rounded-full bg-slate-900/90 border border-cyan-500/30 text-cyan-300 text-xs font-mono mb-6 shadow-sm">
            <Sparkles className="w-3.5 h-3.5 text-cyan-400" />
            <span>From Financial Data to Confident Decisions</span>
          </div>

          <h1 className="text-4xl sm:text-6xl font-extrabold tracking-tight text-white leading-tight">
            Verify. Validate. Compare. Explain. <br />
            <span className="bg-gradient-to-r from-cyan-400 via-sky-300 to-indigo-400 bg-clip-text text-transparent">
              Deterministic Financial Calculations. AI-Powered Explanations.
            </span>
          </h1>

          <p className="mt-6 text-base sm:text-lg text-slate-400 max-w-3xl mx-auto leading-relaxed">
            The next-generation FinTech review engine combining <span className="text-slate-200 font-semibold">deterministic Python mathematics</span> with <span className="text-cyan-300 font-semibold">Finny</span> for anomaly contextualization, document integrity screening, and executive reporting.
          </p>

          <div className="mt-10 flex flex-wrap items-center justify-center gap-4">
            <Link
              to="/upload"
              className="flex items-center space-x-2.5 px-6 py-3.5 rounded-xl bg-gradient-to-r from-cyan-400 to-blue-600 text-slate-950 font-bold text-sm shadow-glow-cyan hover:scale-105 active:scale-95 transition-all"
            >
              <span>Upload Statement for Review</span>
              <ArrowRight className="w-4 h-4" />
            </Link>
            <Link
              to="/dashboard"
              className="flex items-center space-x-2 px-6 py-3.5 rounded-xl bg-slate-900 hover:bg-slate-800 text-slate-200 border border-slate-700 text-sm font-semibold transition-all"
            >
              <Activity className="w-4 h-4 text-cyan-400" />
              <span>Explore Live Analytics</span>
            </Link>
          </div>

          {/* Quick Metrics Banner */}
          <div className="mt-16 grid grid-cols-2 md:grid-cols-4 gap-4 max-w-4xl mx-auto">
            <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 text-left">
              <span className="text-xs text-slate-400 font-mono uppercase">Calculations</span>
              <p className="text-xl font-bold text-emerald-400 font-mono mt-1">Deterministic</p>
              <p className="text-[11px] text-slate-400 mt-0.5">Python Math Validation</p>
            </div>
            <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 text-left">
              <span className="text-xs text-slate-400 font-mono uppercase">Screening</span>
              <p className="text-xl font-bold text-cyan-400 font-mono mt-1">6 Integrity Vectors</p>
              <p className="text-[11px] text-slate-400 mt-0.5">Pre-ingestion filter</p>
            </div>
            <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 text-left">
              <span className="text-xs text-slate-400 font-mono uppercase">AI Assistant</span>
              <p className="text-xl font-bold text-indigo-400 font-mono mt-1">Finny Copilot</p>
              <p className="text-[11px] text-slate-400 mt-0.5">Root cause synthesis</p>
            </div>
            <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 text-left">
              <span className="text-xs text-slate-400 font-mono uppercase">Accounting Eq.</span>
              <p className="text-xl font-bold text-emerald-400 font-mono mt-1">Assets = L + E</p>
              <p className="text-[11px] text-slate-400 mt-0.5">Verified exact delta</p>
            </div>
          </div>
        </div>
      </section>

      {/* Core Workflow Pipeline Showcase */}
      <section className="py-20 px-6 border-t border-slate-800/80 bg-[#0B1120]/40">
        <div className="max-w-6xl mx-auto">
          <div className="text-center max-w-2xl mx-auto mb-14">
            <span className="text-xs font-mono text-cyan-400 uppercase tracking-widest">End-to-End SDLC Pipeline</span>
            <h2 className="text-3xl font-bold text-white mt-2">How Financial Statement Review Works</h2>
            <p className="text-slate-400 text-sm mt-3">
              A transparent multi-agent pipeline from document screening to final report visualization.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="p-6 rounded-2xl bg-slate-900/90 border border-slate-800 relative hover:border-emerald-500/40 transition-colors">
              <div className="w-10 h-10 rounded-xl bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 flex items-center justify-center font-bold mb-4 font-mono">
                02
              </div>
              <h3 className="text-base font-bold text-slate-100">Deterministic Financial Math</h3>
              <p className="text-xs text-slate-400 mt-2 leading-relaxed">
                Recomputes subtotals, reconciles Cash Flow against Net Income, audits the Accounting Equation ($A = L + E$), and calculates YoY percentage variances.
              </p>
            </div>

            <div className="p-6 rounded-2xl bg-slate-900/90 border border-slate-800 relative hover:border-indigo-500/40 transition-colors">
              <div className="w-10 h-10 rounded-xl bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 flex items-center justify-center font-bold mb-4 font-mono">
                03
              </div>
              <h3 className="text-base font-bold text-slate-100">Finny Narrative &amp; Reports</h3>
              <p className="text-xs text-slate-400 mt-2 leading-relaxed">
                LLM explains WHY an anomaly matters, drafts executive findings, formulates audit sample requests, and generates formal board-level PDF reports.
              </p>
            </div>
          </div>
        </div>
      </section>


      {/* Footer */}
      <footer className="border-t border-slate-800/80 py-8 px-6 bg-[#070B14]">
        <div className="max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between text-xs text-slate-400 space-y-4 sm:space-y-0">
          <div className="flex items-center space-x-2 font-mono">
            <span>Financial Statement Review Agent</span>
            <span>•</span>
            <span className="text-cyan-400">Finny</span>
          </div>
          <div className="text-slate-400">
            Hackathon MVP • Designed for Auditing & Credit Intelligence
          </div>
        </div>
      </footer>
    </div>
  );
};
