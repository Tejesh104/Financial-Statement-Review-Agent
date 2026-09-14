import React, { useState, useRef, useEffect } from 'react';
import { Link as RouterLink } from 'react-router-dom';
import { Search, Bell, Shield, ChevronDown, CheckCircle2, User, Sparkles, Settings, ExternalLink, ShieldCheck } from 'lucide-react';
import { useAuth } from '../services/authContext';
import { ThemeToggle } from './ThemeToggle';

export const TopBar = () => {
  const { user } = useAuth();
  const [showNotifications, setShowNotifications] = useState(false);
  const [showProfileMenu, setShowProfileMenu] = useState(false);
  const [notifications, setNotifications] = useState([]); // Populated with real alerts after document processing
  const profileRef = useRef(null);

  // Close profile dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (profileRef.current && !profileRef.current.contains(event.target)) {
        setShowProfileMenu(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  return (
    <header className="h-16 bg-[#0B1120]/90 backdrop-blur-md border-b border-slate-800/80 px-6 flex items-center justify-between z-20">
      {/* Title / Current App Branding */}
      <div className="flex items-center space-x-4">
        <span className="text-sm font-semibold text-slate-200 tracking-wide">
          Financial Statement Review Agent
        </span>
        <span className="hidden md:inline-flex items-center space-x-1.5 px-2 py-0.5 rounded-full bg-cyan-950/60 border border-cyan-500/30 text-[11px] text-cyan-300 font-mono">
          <Sparkles className="w-3 h-3 text-cyan-400" />
          <span>Finny v2.4 Active</span>
        </span>
      </div>

      {/* Middle Search Bar */}
      <div className="hidden lg:flex items-center relative w-80">
        <Search className="w-4 h-4 text-slate-400 absolute left-3 pointer-events-none" />
        <input
          type="text"
          placeholder="Search statements, ratios, line items (Ctrl+K)..."
          className="w-full bg-[#070B14] border border-slate-800 rounded-lg pl-9 pr-3 py-1.5 text-xs text-slate-200 placeholder-slate-400 focus:outline-none focus:border-cyan-500/60 focus:ring-1 focus:ring-cyan-500/40 transition-all font-mono"
        />
      </div>

      {/* Right Controls: Notifications, Status, Profile */}
      <div className="flex items-center space-x-4">
        {/* Real-time Online Indicator */}
        <div className="flex items-center space-x-2 px-2.5 py-1 rounded-full bg-slate-900 border border-slate-800">
          <span className="relative flex h-2 w-2">
            <span className="inline-flex rounded-full h-2 w-2 bg-emerald-400 shadow-[0_0_8px_rgba(52,211,153,0.8)]"></span>
          </span>
          <span className="text-[11px] font-mono text-slate-300 uppercase tracking-wider">Live</span>
        </div>

        {/* Visual Theme Toggle */}
        <ThemeToggle />

        {/* Notification Bell */}
        <div className="relative">
          <button
            onClick={() => setShowNotifications(!showNotifications)}
            className="p-2 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-slate-800/60 transition-colors relative"
            title="Notifications"
          >
            <Bell className="w-4 h-4" />
            <span className="absolute top-1.5 right-1.5 w-2 h-2 rounded-full bg-cyan-400 ring-2 ring-[#0B1120]"></span>
          </button>

          {showNotifications && (
            <div className="absolute right-0 mt-2 w-80 rounded-xl bg-[#0B1120] border border-slate-800 shadow-2xl p-3 z-50">
              <div className="flex items-center justify-between pb-2 border-b border-slate-800 px-1">
                <span className="text-xs font-semibold text-slate-200 uppercase font-mono tracking-wider">Audit Alerts</span>
                <button 
                  onClick={() => setNotifications(notifications.map(n => ({ ...n, unread: false })))}
                  className="text-[10px] text-cyan-400 hover:underline"
                >
                  Mark all read
                </button>
              </div>
              <div className="mt-2 space-y-2 max-h-64 overflow-y-auto">
                {notifications.map((n) => (
                  <div key={n.id} className={`p-2 rounded-lg text-xs transition-colors ${n.unread ? 'bg-slate-900/90 border border-cyan-500/20' : 'bg-slate-900/40 border border-transparent'}`}>
                    <div className="flex justify-between items-center text-slate-200 font-medium">
                      <span>{n.title}</span>
                      <span className="text-[10px] text-slate-400 font-mono">{n.time}</span>
                    </div>
                    <p className="text-slate-400 text-[11px] mt-0.5">{n.text}</p>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Real Authenticated User Profile with Dropdown */}
        <div className="relative" ref={profileRef}>
          <button
            type="button"
            onClick={() => setShowProfileMenu(!showProfileMenu)}
            className="flex items-center space-x-3 pl-2 border-l border-slate-800 hover:opacity-90 transition-opacity cursor-pointer group focus:outline-none"
            title="View Personal Details"
          >
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-cyan-600 to-indigo-700 flex items-center justify-center font-bold text-xs text-white shadow-inner group-hover:ring-2 group-hover:ring-cyan-500/50 transition-all">
              {user?.full_name
                ? user.full_name.split(' ').filter(Boolean).map(n => n[0]).join('').slice(0, 2).toUpperCase()
                : (user?.email ? user.email.slice(0, 2).toUpperCase() : 'AU')}
            </div>
            <div className="hidden sm:block text-left">
              <div className="text-xs font-medium text-slate-200 leading-tight flex items-center space-x-1">
                <span>{user?.full_name || user?.email || 'Authenticated User'}</span>
                <ChevronDown className="w-3 h-3 text-slate-400 group-hover:text-cyan-400 transition-colors" />
              </div>
              <div className="text-[10px] text-slate-400 font-mono">
                {user?.role || 'Senior Financial Analyst'}
              </div>
            </div>
          </button>

          {/* Personal Details Dropdown */}
          {showProfileMenu && (
            <div className="absolute right-0 mt-2 w-72 rounded-2xl bg-[#0B1120] border border-slate-800 shadow-2xl p-4 z-50 animate-in fade-in slide-in-from-top-2 duration-150 space-y-3 font-mono">
              <div className="flex items-center space-x-3 pb-3 border-b border-slate-800">
                <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-cyan-600 to-indigo-700 flex items-center justify-center font-bold text-sm text-white shadow-inner shrink-0">
                  {user?.full_name
                    ? user.full_name.split(' ').filter(Boolean).map(n => n[0]).join('').slice(0, 2).toUpperCase()
                    : (user?.email ? user.email.slice(0, 2).toUpperCase() : 'AU')}
                </div>
                <div className="overflow-hidden">
                  <div className="text-xs font-bold text-slate-100 truncate">
                    {user?.full_name || 'Finny Analyst'}
                  </div>
                  <div className="text-[10px] text-slate-400 truncate">
                    {user?.email || 'analyst@finny.internal'}
                  </div>
                </div>
              </div>

              {/* Personal Details List */}
              <div className="space-y-2 text-xs">
                <div className="p-2 rounded-xl bg-[#070B14] border border-slate-800/80">
                  <div className="text-[10px] uppercase text-slate-500">Professional Role</div>
                  <div className="text-[11px] text-slate-200 font-semibold mt-0.5">
                    {user?.role || 'Senior Financial Analyst'}
                  </div>
                </div>

                <div className="p-2 rounded-xl bg-[#070B14] border border-slate-800/80 flex items-center justify-between">
                  <div>
                    <div className="text-[10px] uppercase text-slate-500">Auth Method</div>
                    <div className="text-[11px] text-cyan-400 font-semibold mt-0.5">
                      {user?.auth_provider === 'google' ? 'Google OAuth 2.0' : 'Institutional Password'}
                    </div>
                  </div>
                  <ShieldCheck className="w-4 h-4 text-emerald-400" />
                </div>
              </div>

              {/* Action Link to Settings */}
              <div className="pt-2 border-t border-slate-800">
                <RouterLink
                  to="/settings"
                  onClick={() => setShowProfileMenu(false)}
                  className="w-full flex items-center justify-center space-x-2 px-3 py-2 rounded-xl bg-slate-900 hover:bg-slate-800 border border-slate-800 text-cyan-400 hover:text-cyan-300 text-xs font-semibold transition-colors"
                >
                  <Settings className="w-3.5 h-3.5" />
                  <span>Account & Settings</span>
                </RouterLink>
              </div>
            </div>
          )}
        </div>
      </div>
    </header>
  );
};
