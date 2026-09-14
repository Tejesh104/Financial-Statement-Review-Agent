import React from 'react';

export const StatCard = ({ title, value, change, isPositive, icon: Icon, color = 'cyan', subtitle, alert }) => {
  const colorMap = {
    cyan: {
      border: 'hover:border-cyan-500/50',
      badge: 'text-cyan-400 bg-cyan-950/60 border-cyan-500/30',
      iconBg: 'bg-cyan-500/10 text-cyan-400 border-cyan-500/20',
      glow: 'shadow-[0_0_20px_rgba(0,229,255,0.06)]'
    },
    green: {
      border: 'hover:border-emerald-500/50',
      badge: 'text-emerald-400 bg-emerald-950/60 border-emerald-500/30',
      iconBg: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20',
      glow: 'shadow-[0_0_20px_rgba(16,185,129,0.06)]'
    },
    yellow: {
      border: 'hover:border-amber-500/50',
      badge: 'text-amber-400 bg-amber-950/60 border-amber-500/30',
      iconBg: 'bg-amber-500/10 text-amber-400 border-amber-500/20',
      glow: 'shadow-[0_0_20px_rgba(245,158,11,0.06)]'
    },
    red: {
      border: 'hover:border-red-500/50',
      badge: 'text-red-400 bg-red-950/60 border-red-500/30',
      iconBg: 'bg-red-500/10 text-red-400 border-red-500/20',
      glow: 'shadow-[0_0_20px_rgba(239,68,68,0.06)]'
    },
    purple: {
      border: 'hover:border-purple-500/50',
      badge: 'text-purple-400 bg-purple-950/60 border-purple-500/30',
      iconBg: 'bg-purple-500/10 text-purple-400 border-purple-500/20',
      glow: 'shadow-[0_0_20px_rgba(139,92,246,0.06)]'
    },
  };

  const scheme = colorMap[color] || colorMap.cyan;

  return (
    <div className={`p-5 rounded-xl bg-slate-900/80 border border-slate-800 transition-all duration-300 ${scheme.border} ${scheme.glow} relative overflow-hidden group`}>
      <div className="flex items-start justify-between">
        <div>
          <p className="text-xs font-medium text-slate-400 tracking-wider uppercase font-mono">{title}</p>
          <div className="mt-2 flex items-baseline space-x-2">
            <span className="text-2xl font-bold text-slate-100 font-mono tracking-tight">{value}</span>
            {change && (
              <span className={`text-[11px] font-mono px-1.5 py-0.5 rounded border ${isPositive ? 'text-emerald-400 bg-emerald-950/40 border-emerald-500/30' : 'text-amber-400 bg-amber-950/40 border-amber-500/30'}`}>
                {change}
              </span>
            )}
          </div>
          {subtitle && (
            <p className="text-[11px] text-slate-400 mt-1 font-mono">{subtitle}</p>
          )}
        </div>
        {Icon && (
          <div className={`w-10 h-10 rounded-xl border flex items-center justify-center transition-transform group-hover:scale-110 ${scheme.iconBg}`}>
            <Icon className="w-5 h-5" />
          </div>
        )}
      </div>

      {alert && (
        <div className="mt-3 pt-2.5 border-t border-slate-800/80 flex items-center justify-between text-[11px]">
          <span className="text-slate-400">{alert.label}</span>
          <span className={`font-mono font-medium ${alert.color || 'text-slate-300'}`}>{alert.val}</span>
        </div>
      )}
    </div>
  );
};
