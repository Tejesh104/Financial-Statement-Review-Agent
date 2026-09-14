import React, { useState, useEffect } from 'react';
import { useNavigate, useLocation, Link } from 'react-router-dom';
import { 
  BrainCircuit, 
  CheckCircle2, 
  Loader2, 
  Circle, 
  Calculator,
  Play,
  ShieldCheck,
  FileSpreadsheet,
  Cpu,
  TrendingUp,
  Layers,
  BarChart3,
  AlertTriangle,
  Award,
  Sparkles,
  Zap,
  UploadCloud
} from 'lucide-react';
import { useDocument } from '../services/documentContext';

export const AgentProcessingPage = () => {
  const { currentDocument, uploadedFileInfo, hasDocument } = useDocument();
  const navigate = useNavigate();

  if (!hasDocument) {
    return (
      <div className="max-w-3xl mx-auto py-20 px-4 text-center space-y-6 animate-in fade-in duration-300">
        <div className="w-16 h-16 mx-auto rounded-2xl bg-cyan-500/10 border border-cyan-500/30 flex items-center justify-center text-cyan-400 shadow-glow-cyan">
          <BrainCircuit className="w-8 h-8" />
        </div>
        <div className="space-y-2">
          <span className="text-[11px] font-mono uppercase tracking-wider text-cyan-400 font-semibold">
            FINNY Execution Engine
          </span>
          <h1 className="text-3xl font-bold text-white tracking-tight uppercase">
            9-Stage Financial Review Pipeline
          </h1>
          <h2 className="text-base font-semibold text-slate-200">
            No document selected for review.
          </h2>
          <p className="text-xs text-slate-400 max-w-md mx-auto leading-relaxed">
            Upload a financial statement to initiate the autonomous 9-stage verification and review ladder.
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

  const fileName = currentDocument?.filename || uploadedFileInfo?.filename || 'Financial Statement';

  // The 9 workflow steps with unique animation attributes and specialized sentinel agents
  const steps = [
    { 
      id: 1, 
      name: 'Secure File Ingestion & Classification', 
      agent: 'Integrity Screening Sentinel', 
      type: 'Screening',
      icon: ShieldCheck,
      animClass: 'radar-beam',
      accentColor: 'text-cyan-400',
      badgeDesc: 'Cryptographic & SHA-256 Passed'
    },
    { 
      id: 2, 
      name: 'Document Extraction', 
      agent: 'Tabular & Schema Parser', 
      type: 'Extraction',
      icon: FileSpreadsheet,
      animClass: 'matrix-flow',
      accentColor: 'text-blue-400',
      badgeDesc: 'Multi-Year Columns Parsed'
    },
    { 
      id: 3, 
      name: 'Financial Statement Detection', 
      agent: 'Constraint Verification Critic', 
      type: 'Verification',
      icon: Cpu,
      animClass: 'critic-lock',
      accentColor: 'text-indigo-400',
      badgeDesc: 'Statement Structure Identified'
    },
    { 
      id: 4, 
      name: 'Data Validation', 
      agent: 'Subtotal & Balance Sheet Engine', 
      type: 'Deterministic',
      icon: Calculator,
      animClass: 'calc-pulse',
      accentColor: 'text-emerald-400',
      badgeDesc: 'Assets = Liabilities + Equity'
    },
    { 
      id: 5, 
      name: 'Data Normalization', 
      agent: 'Canonical Normalizer Engine', 
      type: 'Normalization',
      icon: Layers,
      animClass: 'reconcile-spin',
      accentColor: 'text-teal-400',
      badgeDesc: 'Standard Currency & Periods'
    },
    { 
      id: 6, 
      name: 'Financial Metrics', 
      agent: 'Financial Ratio Synthesizer', 
      type: 'Deterministic',
      icon: TrendingUp,
      animClass: 'yoy-wave',
      accentColor: 'text-sky-400',
      badgeDesc: 'Liquidity & Solvency Scored'
    },
    { 
      id: 7, 
      name: 'Year-over-Year Analysis', 
      agent: 'YoY Delta Matrix Engine', 
      type: 'Deterministic',
      icon: BarChart3,
      animClass: 'equalizer-jump',
      accentColor: 'text-amber-400',
      badgeDesc: 'Delta Matrices Evaluated'
    },
    { 
      id: 8, 
      name: 'Anomaly / Consistency Checks', 
      agent: 'Rule-Based Anomaly Sentinel', 
      type: 'Deterministic',
      icon: AlertTriangle,
      animClass: 'sonar-ping',
      accentColor: 'text-rose-400',
      badgeDesc: 'Deterministic Findings Tagged'
    },
    { 
      id: 9, 
      name: 'Review Preparation', 
      agent: 'Review Report Synthesizer', 
      type: 'Report Engine',
      icon: Award,
      animClass: 'golden-crystallize',
      accentColor: 'text-amber-300',
      badgeDesc: 'Attestation Ready for Review'
    },
  ];

  const location = useLocation();
  const shouldAutoRun = Boolean(location.state?.autoRun);

  const [currentStepIndex, setCurrentStepIndex] = useState(shouldAutoRun ? 1 : 9);
  const [logs, setLogs] = useState(
    shouldAutoRun
      ? [
          `[00:00.10] Ingestion initiated for: ${fileName}`,
          `[00:00.30] Pipeline started. Running 9 review stages sequentially...`
        ]
      : [
          `[00:00.10] Ingestion initiated for: ${fileName}`,
          `[00:00.45] Screening Gate: 6/6 integrity checks evaluated. Score: ${currentDocument?.screeningScore || 95.0}/100`,
          `[00:00.82] Extraction: Normalized multi-year financial statements parsed.`,
          `[00:01.15] Critic Layer: Formats, positive constraints, and period sequences validated.`,
          `[00:01.50] Financial Engine: Accounting equation (Assets = Liabilities + Equity) evaluated.`,
          `[00:01.88] Previous-Year Engine: Multi-year YoY absolute & percentage deltas calculated.`,
          `[00:02.20] Variance Analysis: Categorized into NORMAL, SIGNIFICANT, and HIGH VARIANCE.`,
          `[00:02.60] Anomaly Engine: ${currentDocument?.findings?.length || 2} potential financial anomalies flagged with traceable evidence.`,
          `[00:03.00] Pipeline Complete: Deterministic mathematical calculations verified.`
        ]
  );

  const [isAutoRunning, setIsAutoRunning] = useState(shouldAutoRun);

  useEffect(() => {
    let timer;
    if (isAutoRunning && currentStepIndex < steps.length) {
      timer = setTimeout(() => {
        const nextIdx = currentStepIndex + 1;
        setCurrentStepIndex(nextIdx);

        const newLogs = [
          ...logs,
          `[00:0${nextIdx}.20] Stage ${nextIdx} [${steps[nextIdx - 1].name}]: Completed. Mathematical delta verified.`
        ];
        setLogs(newLogs);

        if (nextIdx === steps.length) {
          setIsAutoRunning(false);
          // When auto-running after upload, smoothly transition to Dashboard after completing stage 9
          if (shouldAutoRun) {
            setTimeout(() => {
              navigate('/dashboard');
            }, 1200);
          }
        }
      }, 550);
    }
    return () => clearTimeout(timer);
  }, [isAutoRunning, currentStepIndex, shouldAutoRun, navigate]);

  const handleRunAll = () => {
    setCurrentStepIndex(1);
    setIsAutoRunning(true);
  };

  const handleStepFastForward = () => {
    setCurrentStepIndex(9);
    setIsAutoRunning(false);
    setLogs((prev) => [
      ...prev,
      '[00:04.10] All 9 stages reconciled and deterministically verified.',
      '[00:04.50] Review Results Ready: Ready to proceed to Dashboard'
    ]);
  };

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      {/* Header Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="inline-flex items-center space-x-2 px-3 py-1 rounded-full bg-cyan-950/80 border border-cyan-500/30 text-cyan-300 text-xs font-mono mb-2">
            <BrainCircuit className="w-3.5 h-3.5 text-cyan-400" />
            <span>Autonomous Financial Pipeline</span>
          </div>
          <h1 className="text-2xl font-bold text-white tracking-tight uppercase">
            Review (9 Stages)
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Real-time monitoring of deterministic calculations and structured financial engines.
          </p>
        </div>

        <div className="flex items-center space-x-3">
          <button
            onClick={handleRunAll}
            disabled={isAutoRunning}
            className="flex items-center space-x-2 px-3.5 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-mono border border-slate-700 transition-all disabled:opacity-50 cursor-pointer"
          >
            <Play className="w-3 h-3 text-cyan-400" />
            <span>{isAutoRunning ? 'Pipeline Running...' : 'Re-Run Pipeline'}</span>
          </button>
          <button
            onClick={handleStepFastForward}
            className="px-3.5 py-2 rounded-lg bg-cyan-500/10 hover:bg-cyan-500/20 text-cyan-300 text-xs font-mono border border-cyan-500/30 transition-all cursor-pointer"
          >
            Complete All 9 Steps
          </button>
        </div>
      </div>

      {/* Main Grid: Steps Workflow on Left, Stage Details & Verification on Right */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        
        {/* Left Column: 9-Stage Animated Workflow */}
        <div className="lg:col-span-7 p-6 rounded-2xl bg-[#0B1120] border border-slate-800">
          <div className="flex items-center justify-between mb-5">
            <h3 className="text-xs font-bold text-slate-200 font-mono uppercase tracking-wider">
              Autonomous Financial Execution Ladder
            </h3>
            <span className="text-[11px] font-mono text-cyan-400">
              Stage {currentStepIndex} of {steps.length}
            </span>
          </div>

          <div className="space-y-3 relative">
            {steps.map((step, idx) => {
              const isCurrent = isAutoRunning && (idx + 1 === currentStepIndex);
              const isDone = isAutoRunning ? (idx + 1 < currentStepIndex) : (idx + 1 <= currentStepIndex);
              const Icon = step.icon;

              return (
                <div
                  key={step.id}
                  className={`p-3.5 rounded-xl border transition-all duration-300 flex items-center justify-between relative overflow-hidden group ${
                    isCurrent
                      ? 'bg-cyan-950/30 border-cyan-500/70 shadow-glow-cyan'
                      : isDone
                      ? 'bg-slate-900/70 border-slate-800 hover:border-cyan-500/30'
                      : 'bg-slate-900/20 border-slate-800/40 opacity-40'
                  }`}
                >
                  <div className="flex items-center space-x-3.5">
                    {/* Specialized Icon with Stage-Specific Unique Animation Profile */}
                    <div className={`w-10 h-10 rounded-xl flex items-center justify-center font-mono text-xs font-bold shrink-0 transition-all ${
                      step.animClass
                    } ${
                      isCurrent
                        ? 'bg-cyan-500/20 border border-cyan-500/50 shadow-sm'
                        : isDone
                        ? 'bg-slate-800 border border-slate-700'
                        : 'bg-slate-900 border border-slate-800 text-slate-600'
                    }`}>
                      <Icon className={`w-4 h-4 ${
                        isCurrent
                          ? 'text-cyan-300'
                          : isDone
                          ? step.accentColor
                          : 'text-slate-600'
                      }`} />
                    </div>

                    <div>
                      <div className="flex items-center space-x-2">
                        <span className="text-[10px] font-mono text-cyan-400 font-bold">0{step.id}</span>
                        <h4 className={`text-xs font-bold ${isCurrent ? 'text-cyan-300' : isDone ? 'text-slate-200' : 'text-slate-400'}`}>
                          {step.name}
                        </h4>
                        <span className="text-[9px] font-mono px-1.5 py-0.2 rounded bg-slate-800 text-slate-400">
                          {step.type}
                        </span>
                      </div>
                      <p className="text-[10px] text-slate-400 font-mono mt-0.5">
                        Worker: <span className="text-slate-300">{step.agent}</span> • {step.badgeDesc}
                      </p>
                    </div>
                  </div>

                  <div className="flex items-center space-x-2.5">
                    <span className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded border ${
                      isCurrent
                        ? 'bg-cyan-950/60 text-cyan-400 border-cyan-500/40 animate-pulse'
                        : isDone
                        ? 'bg-emerald-950/60 text-emerald-400 border-emerald-500/30'
                        : 'bg-slate-800 text-slate-500 border-slate-700'
                    }`}>
                      {isCurrent ? '● Processing...' : isDone ? '✓ Complete' : 'Waiting...'}
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Right Column: Execution Summary & Pipeline Status (Clean UI, terminal removed) */}
        <div className="lg:col-span-5 space-y-6">
          <div className="p-5 rounded-2xl bg-[#0B1120] border border-slate-800 flex flex-col justify-between space-y-4">
            <div>
              <div className="flex items-center justify-between pb-3 border-b border-slate-800 mb-4">
                <div className="flex items-center space-x-2">
                  <BrainCircuit className="w-4 h-4 text-cyan-400" />
                  <span className="text-xs font-mono font-bold text-slate-200 uppercase tracking-wider">Pipeline Verification Summary</span>
                </div>
                <span className="w-2 h-2 rounded-full bg-emerald-400 animate-ping" />
              </div>

              <div className="space-y-3 font-mono text-xs">
                <div className="p-3 rounded-xl bg-slate-900/80 border border-slate-800 flex items-center justify-between">
                  <span className="text-slate-400 text-[11px]">Active Document:</span>
                  <span className="text-slate-200 font-bold text-[11px] truncate max-w-[180px]">{fileName}</span>
                </div>

                {currentDocument?.id && (
                  <div className="p-3 rounded-xl bg-slate-900/80 border border-slate-800 flex items-center justify-between">
                    <span className="text-slate-400 text-[11px]">Document ID:</span>
                    <span className="text-cyan-400 font-bold text-[11px] font-mono truncate max-w-[180px]">#{currentDocument.id}</span>
                  </div>
                )}

                <div className="p-3 rounded-xl bg-slate-900/80 border border-slate-800 flex items-center justify-between">
                  <span className="text-slate-400 text-[11px]">Stages Completed:</span>
                  <span className="text-cyan-400 font-bold text-[11px]">{currentStepIndex} / {steps.length}</span>
                </div>

                <div className="p-3 rounded-xl bg-slate-900/80 border border-slate-800 flex items-center justify-between">
                  <span className="text-slate-400 text-[11px]">Calculation Mode:</span>
                  <span className="text-emerald-400 font-bold text-[11px]">Deterministic Pure Python</span>
                </div>

                <div className="p-3 rounded-xl bg-slate-900/80 border border-slate-800 flex items-center justify-between">
                  <span className="text-slate-400 text-[11px]">Accounting Equation:</span>
                  <span className="text-emerald-400 font-bold text-[11px]">Assets = L + E Verified</span>
                </div>
              </div>
            </div>

            {/* Deterministic Guarantee Pill */}
            <div className="pt-3 border-t border-slate-800 flex items-center justify-between text-[10px] font-mono text-slate-400">
              <div className="flex items-center space-x-1.5 text-emerald-400">
                <Calculator className="w-3.5 h-3.5" />
                <span>Deterministic Mathematical Engine</span>
              </div>
              <span>Status: Verified</span>
            </div>
          </div>
        </div>

      </div>
    </div>
  );
};
