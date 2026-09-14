import React, { useState, useEffect } from 'react';
import { Link as RouterLink } from 'react-router-dom';
import { 
  Settings, 
  User, 
  Bell, 
  Save, 
  ShieldCheck, 
  CheckCircle2, 
  ArrowLeft, 
  Sliders,
  Mail,
  X,
  AlertCircle,
  Lock,
  Loader2
} from 'lucide-react';
import { useAuth } from '../services/authContext';
import api from '../services/api';

export const SettingsPage = () => {
  const { user, updateUser, updateSession } = useAuth();
  const [saved, setSaved] = useState(false);
  const [saveError, setSaveError] = useState('');
  const [isSaving, setIsSaving] = useState(false);

  // Authenticated Profile states
  const [fullName, setFullName] = useState(user?.full_name || '');
  const [email, setEmail] = useState(user?.email || '');
  const [roleTitle, setRoleTitle] = useState(user?.role || 'Senior Financial Analyst');

  // Email Change Modal states
  const [showEmailModal, setShowEmailModal] = useState(false);
  const [newEmail, setNewEmail] = useState('');
  const [confirmNewEmail, setConfirmNewEmail] = useState('');
  const [currentPassword, setCurrentPassword] = useState('');
  const [emailError, setEmailError] = useState('');
  const [emailSuccess, setEmailSuccess] = useState('');
  const [isSubmittingEmail, setIsSubmittingEmail] = useState(false);

  // Preferences (Local UI preferences)
  const [emailNotifications, setEmailNotifications] = useState(true);
  const [anomalyAlerts, setAnomalyAlerts] = useState(true);

  // Synchronize with authenticated user whenever session loads or updates
  useEffect(() => {
    if (user) {
      if (user.full_name) setFullName(user.full_name);
      if (user.email) setEmail(user.email);
      if (user.role) setRoleTitle(user.role);
    }
  }, [user]);

  const handleSaveProfile = async (e) => {
    e.preventDefault();
    setSaveError('');
    setIsSaving(true);
    try {
      const response = await api.put('/auth/me', {
        full_name: fullName.trim(),
        role: roleTitle.trim()
      });
      if (updateUser) {
        updateUser(response.data);
      }
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    } catch (err) {
      setSaveError(err.response?.data?.detail || 'Failed to update account profile.');
    } finally {
      setIsSaving(false);
    }
  };

  const handleOpenEmailModal = () => {
    setNewEmail('');
    setConfirmNewEmail('');
    setCurrentPassword('');
    setEmailError('');
    setEmailSuccess('');
    setShowEmailModal(true);
  };

  const handleCloseEmailModal = () => {
    setShowEmailModal(false);
    setEmailError('');
    setEmailSuccess('');
  };

  const handleEmailSubmit = async (e) => {
    e.preventDefault();
    setEmailError('');
    setEmailSuccess('');

    if (!newEmail.trim() || !confirmNewEmail.trim()) {
      setEmailError('Please fill out both email fields.');
      return;
    }
    if (newEmail.trim().toLowerCase() !== confirmNewEmail.trim().toLowerCase()) {
      setEmailError('New email and confirmation email do not match.');
      return;
    }
    if (newEmail.trim().toLowerCase() === email.toLowerCase()) {
      setEmailError('New email must be different from your current email.');
      return;
    }
    if (user?.auth_provider !== 'google' && !currentPassword) {
      setEmailError('Current password is required to confirm email change.');
      return;
    }

    setIsSubmittingEmail(true);
    try {
      const payload = {
        new_email: newEmail.trim().toLowerCase(),
        confirm_new_email: confirmNewEmail.trim().toLowerCase(),
        current_password: user?.auth_provider === 'google' ? undefined : currentPassword
      };
      const res = await api.put('/auth/me/email', payload);
      const { access_token, user: updatedUser } = res.data;
      
      // Update global session (token + user) so active JWT stays uninterrupted
      if (updateSession) {
        updateSession(access_token, updatedUser);
      } else if (updateUser) {
        updateUser(updatedUser);
      }
      setEmail(updatedUser.email);
      setEmailSuccess('Email updated successfully.');
      setTimeout(() => {
        handleCloseEmailModal();
      }, 1500);
    } catch (err) {
      const detail = err.response?.data?.detail;
      setEmailError(typeof detail === 'string' ? detail : 'Failed to update email address.');
    } finally {
      setIsSubmittingEmail(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto space-y-6 pb-12 animate-in fade-in duration-300">
      {/* Navigation Breadcrumb */}
      <div className="flex items-center justify-between">
        <RouterLink
          to="/dashboard"
          className="inline-flex items-center space-x-2 text-xs font-mono text-slate-400 hover:text-cyan-400 transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>Back to Dashboard</span>
        </RouterLink>
      </div>

      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-4 border-b border-slate-800/80 pb-5">
        <div>
          <div className="inline-flex items-center space-x-2 px-3 py-1 rounded-full bg-cyan-950/80 border border-cyan-500/30 text-cyan-300 text-xs font-mono mb-2">
            <Settings className="w-3.5 h-3.5 text-cyan-400" />
            <span>Platform Configuration</span>
          </div>
          <h1 className="text-2xl font-bold text-white tracking-tight uppercase">Settings</h1>
          <p className="text-xs text-slate-400 mt-1">
            Manage your account credentials, notifications, and platform preferences.
          </p>
        </div>

        {saved && (
          <div className="flex items-center space-x-2 px-3.5 py-2 rounded-xl bg-emerald-950/80 border border-emerald-500/40 text-emerald-400 text-xs font-mono shadow-sm">
            <CheckCircle2 className="w-4 h-4" />
            <span>Profile settings saved successfully</span>
          </div>
        )}
        {saveError && (
          <div className="flex items-center space-x-2 px-3.5 py-2 rounded-xl bg-rose-950/80 border border-rose-500/40 text-rose-400 text-xs font-mono shadow-sm">
            <span>{saveError}</span>
          </div>
        )}
      </div>

      {/* ── Section 1: Account / Profile ──────────────────────────────── */}
      <div className="p-6 rounded-2xl bg-[#0B1120] border border-slate-800 space-y-5">
        <div className="flex items-center justify-between">
          <h2 className="text-xs font-bold text-slate-200 font-mono uppercase tracking-wider flex items-center space-x-2">
            <User className="w-4 h-4 text-cyan-400" />
            <span>Account & Profile</span>
          </h2>
          <span className="text-[11px] text-cyan-400 font-mono flex items-center gap-1.5">
            <ShieldCheck className="w-3.5 h-3.5 text-cyan-400" />
            <span>Authenticated Session</span>
          </span>
        </div>

        <form onSubmit={handleSaveProfile} className="space-y-4">
          <div className="grid sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs text-slate-400 font-mono mb-1.5">Full Name</label>
              <input
                type="text"
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                placeholder="Enter your name"
                required
                className="w-full bg-[#070B14] border border-slate-800 rounded-xl px-3.5 py-2.5 text-xs text-slate-100 focus:outline-none focus:border-cyan-500 font-mono"
              />
            </div>

            <div>
              <label className="block text-xs text-slate-400 font-mono mb-1.5">Professional Title / Role</label>
              <input
                type="text"
                value={roleTitle}
                onChange={(e) => setRoleTitle(e.target.value)}
                placeholder="e.g. Senior Financial Analyst"
                className="w-full bg-[#070B14] border border-slate-800 rounded-xl px-3.5 py-2.5 text-xs text-slate-100 focus:outline-none focus:border-cyan-500 font-mono"
              />
            </div>
          </div>

          <div>
            <div className="flex items-center justify-between mb-1.5">
              <label className="block text-xs text-slate-400 font-mono">Email Address</label>
              <button
                type="button"
                onClick={handleOpenEmailModal}
                className="text-xs font-mono text-cyan-400 hover:text-cyan-300 hover:underline cursor-pointer flex items-center space-x-1"
              >
                <Mail className="w-3 h-3" />
                <span>Change Email</span>
              </button>
            </div>
            <div className="relative">
              <input
                type="email"
                disabled
                value={email}
                className="w-full bg-[#070B14]/60 border border-slate-800/80 rounded-xl px-3.5 py-2.5 text-xs text-slate-400 font-mono cursor-not-allowed pr-10"
              />
              <Lock className="w-3.5 h-3.5 text-slate-600 absolute right-3 top-3" />
            </div>
            <p className="text-[10px] text-slate-500 mt-1 font-mono">
              Account email is bound to your authentication provider ({user?.auth_provider === 'google' ? 'Google OAuth' : 'Institutional Password'}).
            </p>
          </div>

          <div className="pt-2 flex justify-end">
            <button
              type="submit"
              disabled={isSaving}
              className="flex items-center space-x-2 px-5 py-2.5 rounded-xl bg-gradient-to-r from-cyan-500 to-blue-600 text-slate-950 font-bold text-xs shadow-glow-cyan hover:scale-105 active:scale-95 transition-all disabled:opacity-50 cursor-pointer"
            >
              {isSaving ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Save className="w-3.5 h-3.5" />}
              <span>{isSaving ? 'Saving Profile...' : 'Save Profile Changes'}</span>
            </button>
          </div>
        </form>
      </div>

      {/* ── Section 2: Preferences ────────────────────────────────────────── */}
      <div className="p-6 rounded-2xl bg-[#0B1120] border border-slate-800 space-y-5">
        <h2 className="text-xs font-bold text-slate-200 font-mono uppercase tracking-wider flex items-center space-x-2">
          <Sliders className="w-4 h-4 text-cyan-400" />
          <span>Notification & Analysis Preferences</span>
        </h2>

        <div className="space-y-4">
          <div className="flex items-center justify-between p-3.5 rounded-xl bg-[#070B14] border border-slate-800">
            <div>
              <div className="flex items-center space-x-2">
                <Bell className="w-3.5 h-3.5 text-cyan-400" />
                <p className="text-xs font-semibold text-slate-200">Discrepancy & Anomaly Notifications</p>
              </div>
              <p className="text-[11px] text-slate-400 mt-0.5">
                Highlight high-severity mathematical balance discrepancies on dashboard
              </p>
            </div>
            <label className="relative inline-flex items-center cursor-pointer">
              <input
                type="checkbox"
                checked={anomalyAlerts}
                onChange={(e) => setAnomalyAlerts(e.target.checked)}
                className="sr-only peer"
              />
              <div className="w-9 h-5 bg-slate-800 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-slate-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-cyan-500"></div>
            </label>
          </div>

          <div className="flex items-center justify-between p-3.5 rounded-xl bg-[#070B14] border border-slate-800">
            <div>
              <p className="text-xs font-semibold text-slate-200">Email Review Completion Alerts</p>
              <p className="text-[11px] text-slate-400 mt-0.5">
                Receive email summary notifications when 9-stage analysis finishes (UI Preference)
              </p>
            </div>
            <label className="relative inline-flex items-center cursor-pointer">
              <input
                type="checkbox"
                checked={emailNotifications}
                onChange={(e) => setEmailNotifications(e.target.checked)}
                className="sr-only peer"
              />
              <div className="w-9 h-5 bg-slate-800 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-slate-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-cyan-500"></div>
            </label>
          </div>
        </div>
      </div>

      {/* ── Change Email Modal ────────────────────────────────────────────── */}
      {showEmailModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm animate-in fade-in duration-200">
          <div className="w-full max-w-md bg-[#0B1120] border border-slate-800 rounded-2xl p-6 shadow-2xl space-y-4">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div className="flex items-center space-x-2">
                <Mail className="w-4 h-4 text-cyan-400" />
                <h3 className="text-sm font-bold text-white font-mono uppercase tracking-wide">Change Email Address</h3>
              </div>
              <button
                onClick={handleCloseEmailModal}
                className="text-slate-400 hover:text-slate-200 cursor-pointer p-1"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {emailError && (
              <div className="flex items-center space-x-2 p-3 rounded-xl bg-rose-950/80 border border-rose-500/40 text-rose-400 text-xs font-mono">
                <AlertCircle className="w-4 h-4 shrink-0" />
                <span>{emailError}</span>
              </div>
            )}

            {emailSuccess && (
              <div className="flex items-center space-x-2 p-3 rounded-xl bg-emerald-950/80 border border-emerald-500/40 text-emerald-400 text-xs font-mono">
                <CheckCircle2 className="w-4 h-4 shrink-0" />
                <span>{emailSuccess}</span>
              </div>
            )}

            <form onSubmit={handleEmailSubmit} className="space-y-3.5">
              <div>
                <label className="block text-[11px] text-slate-400 font-mono mb-1">Current Email</label>
                <input
                  type="text"
                  disabled
                  value={email}
                  className="w-full bg-[#070B14]/70 border border-slate-800 rounded-xl px-3 py-2 text-xs text-slate-400 font-mono cursor-not-allowed"
                />
              </div>

              <div>
                <label className="block text-[11px] text-slate-300 font-mono mb-1">New Email Address</label>
                <input
                  type="email"
                  required
                  value={newEmail}
                  onChange={(e) => setNewEmail(e.target.value)}
                  placeholder="analyst@firm.com"
                  className="w-full bg-[#070B14] border border-slate-800 focus:border-cyan-500 rounded-xl px-3 py-2 text-xs text-slate-100 font-mono focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-[11px] text-slate-300 font-mono mb-1">Confirm New Email</label>
                <input
                  type="email"
                  required
                  value={confirmNewEmail}
                  onChange={(e) => setConfirmNewEmail(e.target.value)}
                  placeholder="analyst@firm.com"
                  className="w-full bg-[#070B14] border border-slate-800 focus:border-cyan-500 rounded-xl px-3 py-2 text-xs text-slate-100 font-mono focus:outline-none"
                />
              </div>

              {user?.auth_provider !== 'google' ? (
                <div>
                  <label className="block text-[11px] text-slate-300 font-mono mb-1">Current Account Password</label>
                  <input
                    type="password"
                    required
                    value={currentPassword}
                    onChange={(e) => setCurrentPassword(e.target.value)}
                    placeholder="••••••••••••"
                    className="w-full bg-[#070B14] border border-slate-800 focus:border-cyan-500 rounded-xl px-3 py-2 text-xs text-slate-100 font-mono focus:outline-none"
                  />
                  <p className="text-[10px] text-slate-500 mt-1 font-mono">
                    Required to confirm security ownership of this account.
                  </p>
                </div>
              ) : (
                <div className="p-2.5 rounded-xl bg-cyan-950/40 border border-cyan-500/20 text-cyan-300 text-[11px] font-mono">
                  Google OAuth Account: Password verification is bypassed for Google authenticated sessions.
                </div>
              )}

              <div className="pt-2 flex items-center justify-end space-x-2">
                <button
                  type="button"
                  onClick={handleCloseEmailModal}
                  disabled={isSubmittingEmail}
                  className="px-4 py-2 rounded-xl bg-slate-900 border border-slate-800 text-slate-300 hover:text-white text-xs font-mono cursor-pointer transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSubmittingEmail}
                  className="flex items-center space-x-1.5 px-4 py-2 rounded-xl bg-gradient-to-r from-cyan-500 to-blue-600 text-slate-950 font-bold text-xs font-mono shadow-glow-cyan hover:scale-105 active:scale-95 transition-all disabled:opacity-50 cursor-pointer"
                >
                  {isSubmittingEmail ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Save className="w-3.5 h-3.5" />}
                  <span>{isSubmittingEmail ? 'Updating...' : 'Update Email'}</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
