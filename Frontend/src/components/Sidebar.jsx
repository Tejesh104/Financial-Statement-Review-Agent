import React from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import { 
  LayoutDashboard, 
  UploadCloud, 
  BrainCircuit, 
  TrendingUp, 
  AlertTriangle, 
  FileText, 
  History, 
  Settings, 
  LogOut,
  ShieldCheck,
  Zap
} from 'lucide-react';
import { useAuth } from '../services/authContext';
import { useDocument } from '../services/documentContext';

export const Sidebar = () => {
  const { logout } = useAuth();
  const { resetDocument } = useDocument();
  const navigate = useNavigate();

  const navItems = [
    { name: 'Upload Document', path: '/upload', icon: UploadCloud },
    { name: 'Dashboard', path: '/dashboard', icon: LayoutDashboard },
    { name: 'Review', path: '/agent-processing', icon: BrainCircuit, badge: 'Active' },
    { name: 'Previous Year Analysis', path: '/analysis', icon: TrendingUp },
    { name: 'Risk Analysis', path: '/risk', icon: AlertTriangle },
    { name: 'Reports', path: '/reports', icon: FileText },
    { name: 'History', path: '/history', icon: History },
    { name: 'Settings', path: '/settings', icon: Settings },
  ];

  const handleLogout = () => {
    resetDocument();
    logout();
    navigate('/login');
  };

  return (
    <aside className="w-64 bg-[#0B1120]/55 backdrop-blur-md border-r border-slate-800/80 flex flex-col justify-between shrink-0 select-none">
      <div>
        {/* Brand Logo Header — Standardized to FINNY without redundant AI suffixes */}
        <div className="h-16 flex items-center px-6 border-b border-slate-800/80 space-x-3 bg-[#070B14]/30">
          <div className="w-9 h-9 rounded-lg bg-gradient-to-tr from-cyan-500 to-blue-600 flex items-center justify-center shadow-glow-cyan">
            <ShieldCheck className="w-5 h-5 text-slate-950 stroke-[2.5]" />
          </div>
          <div>
            <h1 className="font-bold text-sm text-slate-100 tracking-tight leading-tight">
              FINNY
            </h1>
            <p className="text-[10px] text-slate-400 font-mono tracking-wider uppercase">Financial Review Agent</p>
          </div>
        </div>

        {/* Navigation Items */}
        <nav className="p-4 space-y-1.5">
          <div className="px-3 py-1.5 text-[11px] font-semibold text-slate-400 uppercase tracking-wider font-mono">
            Platform Workflow
          </div>
          {navItems.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink
                key={item.name}
                to={item.path}
                end
                className={({ isActive }) =>
                  `flex items-center justify-between px-3 py-2.5 rounded-lg text-sm font-medium transition-colors duration-150 group ${
                    isActive
                      ? 'bg-cyan-500/10 text-cyan-400 border border-cyan-500/30 shadow-[0_0_15px_rgba(0,229,255,0.08)]'
                      : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
                  }`
                }
              >
                <div className="flex items-center space-x-3">
                  <Icon className="w-4 h-4 transition-transform group-hover:scale-110" />
                  <span>{item.name}</span>
                </div>
                {item.badge && (
                  <span className="text-[10px] uppercase font-mono px-1.5 py-0.5 rounded-full bg-cyan-400/20 text-cyan-300 border border-cyan-400/30 font-semibold">
                    {item.badge}
                  </span>
                )}
              </NavLink>
            );
          })}
        </nav>
      </div>

      {/* System Status & Logout */}
      <div className="p-4 border-t border-slate-800/80 bg-[#070B14]/30 space-y-3">
        <div className="p-2.5 rounded-lg bg-slate-900/80 border border-slate-800 flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <Zap className="w-3.5 h-3.5 text-cyan-400" />
            <span className="text-xs text-slate-300 font-mono">Deterministic Engine</span>
          </div>
          <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-emerald-950/60 text-emerald-400 border border-emerald-500/30">
            ONLINE
          </span>
        </div>

        <button
          onClick={handleLogout}
          className="w-full flex items-center space-x-3 px-3 py-2 rounded-lg text-sm font-medium text-slate-400 hover:text-red-400 hover:bg-red-500/10 border border-transparent hover:border-red-500/20 transition-all duration-200"
        >
          <LogOut className="w-4 h-4" />
          <span>Logout</span>
        </button>
      </div>
    </aside>
  );
};
