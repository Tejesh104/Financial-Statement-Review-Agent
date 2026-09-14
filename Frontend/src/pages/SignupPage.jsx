import React, { useState, useEffect, useRef } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { ShieldCheck, Lock, Mail, User, ArrowRight, Eye, EyeOff } from 'lucide-react';
import { useAuth } from '../services/authContext';
import { FinnyBackground } from '../components/FinnyBackground';
import { ThemeToggle } from '../components/ThemeToggle';
import { useFinnyTheme } from '../services/useFinnyTheme';

export const SignupPage = () => {
  const { isLight } = useFinnyTheme();
  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [termsAccepted, setTermsAccepted] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');
  const [googleLoading, setGoogleLoading] = useState(false);
  const [isGsiRendered, setIsGsiRendered] = useState(false);
  const googleSignupButtonRef = useRef(null);

  const { signup, loginWithGoogle, signupLoading } = useAuth();
  const navigate = useNavigate();

  // Calculate Password Strength Score (0 to 4)
  const calculateStrength = (pwd) => {
    let score = 0;
    if (!pwd) return 0;
    if (pwd.length >= 8) score += 1;
    if (/[A-Z]/.test(pwd)) score += 1;
    if (/[0-9]/.test(pwd)) score += 1;
    if (/[^A-Za-z0-9]/.test(pwd)) score += 1;
    return score;
  };

  const strengthScore = calculateStrength(password);
  const strengthLabels = ['Too Weak', 'Weak', 'Fair', 'Good', 'Auditor Grade'];
  const strengthColors = ['bg-slate-700', 'bg-red-500', 'bg-amber-500', 'bg-blue-500', 'bg-emerald-500'];

  const handleSignup = async (e) => {
    e.preventDefault();
    // Clear stale Google or previous signup errors before validating this attempt.
    setError('');

    if (!fullName.trim()) {
      setError('Please enter your full name.');
      return;
    }

    if (!email.trim()) {
      setError('Please enter your email.');
      return;
    }

    if (!password || password.length < 8) {
      setError('Password must be at least 8 characters.');
      return;
    }

    if (password !== confirmPassword) {
      setError('Passwords do not match.');
      return;
    }

    if (!termsAccepted) {
      setError('Please accept the Terms of Service & Confidentiality Agreement.');
      return;
    }

    const res = await signup(fullName.trim(), email.trim().toLowerCase(), password, confirmPassword);
    if (res.success) {
      navigate('/dashboard');
    } else {
      setError(res.error || 'Registration failed. Please try again.');
    }
  };

  useEffect(() => {
    const clientId = import.meta.env.VITE_GOOGLE_CLIENT_ID || '277491416806-3ohdp3hvps3gjtebgq1h16ag5vsjtq0i.apps.googleusercontent.com';

    let isMounted = true;

    const initAndRenderGsi = () => {
      if (window.google?.accounts?.id && googleSignupButtonRef.current) {
        try {
          window.google.accounts.id.initialize({
            client_id: clientId,
            callback: async (response) => {
              if (response?.credential) {
                setGoogleLoading(true);
                setError('');
                const res = await loginWithGoogle(response.credential, true);
                setGoogleLoading(false);
                if (res.success) {
                  navigate('/dashboard');
                } else {
                  setError(res.error || 'Google sign up failed.');
                }
              } else {
                setError('Google sign up did not return a valid credential.');
              }
            },
            auto_select: false,
            cancel_on_tap_outside: true,
          });

          const parentWidth = googleSignupButtonRef.current?.parentElement?.clientWidth || 360;
          const targetWidth = Math.min(384, Math.max(200, parentWidth));

          // Render Google Identity signup button dynamically responsive to current theme
          window.google.accounts.id.renderButton(googleSignupButtonRef.current, {
            theme: isLight ? 'outline' : 'filled_black',
            size: 'large',
            type: 'standard',
            text: 'signup_with',
            shape: 'rectangular',
            logo_alignment: 'left',
            width: targetWidth,
          });

          if (isMounted) {
            setIsGsiRendered(true);
          }
          return true;
        } catch (e) {
          console.warn('Google Identity initialization deferred:', e);
          return false;
        }
      }
      return false;
    };

    const ready = initAndRenderGsi();
    let interval = null;
    let timer = null;

    if (!ready) {
      interval = setInterval(() => {
        if (window.google?.accounts?.id && googleSignupButtonRef.current) {
          const ok = initAndRenderGsi();
          if (ok && interval) {
            clearInterval(interval);
            interval = null;
          }
        }
      }, 400);

      timer = setTimeout(() => {
        if (interval) clearInterval(interval);
      }, 4000);
    }

    return () => {
      isMounted = false;
      if (interval) clearInterval(interval);
      if (timer) clearTimeout(timer);
    };
  }, [loginWithGoogle, navigate, isLight]);

  const handleGoogleSignup = async () => {
    setError('');
    setGoogleLoading(true);

    if (window.google?.accounts?.id) {
      try {
        window.google.accounts.id.prompt((notification) => {
          if (notification.isNotDisplayed() || notification.isSkippedMoment()) {
            console.warn('Google One Tap suppressed/skipped:', notification.getNotDisplayedReason?.() || 'dismissed');
            loginWithGoogle(null, true).then((res) => {
              setGoogleLoading(false);
              if (res.success) {
                navigate('/dashboard');
              } else {
                setError(res.error || 'Google sign up failed.');
              }
            });
          }
        });
        return;
      } catch (err) {
        console.warn('Google prompt exception:', err);
      }
    }

    try {
      const res = await loginWithGoogle(null, true);
      if (res.success) {
        navigate('/dashboard');
      } else {
        setError(res.error || 'Google sign up failed.');
      }
    } catch (err) {
      setError('Google sign up failed.');
    } finally {
      setGoogleLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-transparent flex flex-col justify-center py-12 sm:px-6 lg:px-8 relative animate-fade-in-scale overflow-hidden">
      {/* Keep account creation in the same Finny environment without changing
          the existing signup structure or validation. */}
      <FinnyBackground />

      {/* Top Header Controls: Status & Theme Toggle */}
      <div className="absolute top-5 right-5 sm:top-6 sm:right-8 z-20 flex items-center space-x-3">
        <div className="hidden sm:flex items-center space-x-2 px-3 py-1 rounded-full bg-slate-900/80 border border-slate-800 text-[10px] font-mono text-slate-300 tracking-wider">
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 shadow-[0_0_8px_rgba(52,211,153,0.8)] animate-pulse" />
          <span>SYSTEM ONLINE</span>
        </div>
        <ThemeToggle />
      </div>

      <div className="sm:mx-auto sm:w-full sm:max-w-md relative z-10">
        <div className="bg-[#0B1120]/95 border border-cyan-500/30 rounded-2xl p-8 shadow-2xl backdrop-blur-xl animate-border-glow">
          {/* Header */}
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center space-x-3">
              <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-cyan-500 to-blue-600 flex items-center justify-center shadow-glow-cyan">
                <ShieldCheck className="w-6 h-6 text-slate-950 stroke-[2.5]" />
              </div>
              <div>
                <h1 className="font-extrabold text-base text-slate-100 tracking-tight leading-tight">
                  Create Auditor Account
                </h1>
                <p className="text-[11px] text-cyan-400 font-mono">Financial Statement Review Agent</p>
              </div>
            </div>
            <div className="sm:hidden">
              <ThemeToggle />
            </div>
          </div>

          {error && (
            <div className="mb-4 p-3 rounded-lg bg-red-500/10 border border-red-500/30 text-xs text-red-400 font-mono">
              {error}
            </div>
          )}

          <form onSubmit={handleSignup} className="space-y-4">
            {/* Full Name */}
            <div>
              <label className="block text-xs font-medium text-slate-300 font-mono uppercase tracking-wider mb-1.5">
                Full Name
              </label>
              <div className="relative">
                <User className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
                <input
                  type="text"
                  required
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  placeholder="e.g. Jordan Hayes, CPA"
                  className="w-full bg-[#070B14] border border-slate-800 rounded-xl pl-10 pr-4 py-2.5 text-xs text-slate-100 placeholder-slate-400 focus:outline-none focus:border-cyan-500 font-mono transition-all"
                />
              </div>
            </div>

            {/* Email */}
            <div>
              <label className="block text-xs font-medium text-slate-300 font-mono uppercase tracking-wider mb-1.5">
                Corporate Email
              </label>
              <div className="relative">
                <Mail className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
                <input
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="auditor@firm.com"
                  className="w-full bg-[#070B14] border border-slate-800 rounded-xl pl-10 pr-4 py-2.5 text-xs text-slate-100 placeholder-slate-400 focus:outline-none focus:border-cyan-500 font-mono transition-all"
                />
              </div>
            </div>

            {/* Password */}
            <div>
              <label className="block text-xs font-medium text-slate-300 font-mono uppercase tracking-wider mb-1.5">
                Password
              </label>
              <div className="relative">
                <Lock className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
                <input
                  type={showPassword ? 'text' : 'password'}
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="At least 8 chars with symbols"
                  className="w-full bg-[#070B14] border border-slate-800 rounded-xl pl-10 pr-10 py-2.5 text-xs text-slate-100 placeholder-slate-400 focus:outline-none focus:border-cyan-500 font-mono transition-all"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-200"
                >
                  {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>

              {/* Password Strength Indicator */}
              <div className="mt-2 space-y-1">
                <div className="flex items-center justify-between text-[10px] font-mono">
                  <span className="text-slate-400">Security Strength:</span>
                  <span className={strengthScore >= 3 ? 'text-emerald-400' : 'text-amber-400'}>
                    {strengthLabels[strengthScore]}
                  </span>
                </div>
                <div className="grid grid-cols-4 gap-1.5 h-1.5">
                  {[1, 2, 3, 4].map((step) => (
                    <div
                      key={step}
                      className={`rounded-full transition-all duration-300 ${
                        step <= strengthScore ? strengthColors[strengthScore] : 'bg-slate-800'
                      }`}
                    />
                  ))}
                </div>
              </div>
            </div>

            {/* Confirm Password */}
            <div>
              <label className="block text-xs font-medium text-slate-300 font-mono uppercase tracking-wider mb-1.5">
                Confirm Password
              </label>
              <div className="relative">
                <Lock className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
                <input
                  type="password"
                  required
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  placeholder="Re-enter password"
                  className="w-full bg-[#070B14] border border-slate-800 rounded-xl pl-10 pr-4 py-2.5 text-xs text-slate-100 placeholder-slate-400 focus:outline-none focus:border-cyan-500 font-mono transition-all"
                />
              </div>
            </div>

            {/* Terms Checkbox */}
            <div className="pt-2">
              <label className="flex items-start space-x-2 text-xs text-slate-400 cursor-pointer">
                <input
                  type="checkbox"
                  required
                  checked={termsAccepted}
                  onChange={(e) => setTermsAccepted(e.target.checked)}
                  className="mt-0.5 rounded border-slate-700 bg-slate-900 text-cyan-500 focus:ring-cyan-500 focus:ring-offset-slate-900 h-3.5 w-3.5"
                />
                <span>
                  I agree to the <span className="text-cyan-400 hover:underline">Auditor Terms of Service</span> and acknowledge non-disclosure confidentiality standards.
                </span>
              </label>
            </div>

            {/* Submit Button */}
            <button
              type="submit"
              disabled={signupLoading}
              className="w-full mt-4 flex items-center justify-center space-x-2 py-3 px-4 rounded-xl bg-gradient-to-r from-cyan-500 to-blue-600 text-slate-950 font-bold text-xs shadow-glow-cyan hover:scale-[1.02] active:scale-[0.98] transition-all disabled:opacity-50"
            >
              <span>{signupLoading ? 'Creating Account...' : 'Create Account & Access Suite'}</span>
              <ArrowRight className="w-4 h-4" />
            </button>
          </form>

          {/* Social / Google Sign Up */}
          <div className="relative my-4">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-slate-800/80" />
            </div>
            <div className="relative flex justify-center text-[10px] uppercase font-mono">
              <span className="bg-[#0B1120] px-2 text-slate-400">Or continue with</span>
            </div>
          </div>

          <div className="w-full flex flex-col items-center justify-center min-h-[44px]">
            <div
              ref={googleSignupButtonRef}
              id="googleSignUpButton"
              className={`w-full flex justify-center ${isGsiRendered ? 'block' : 'hidden'}`}
            />
            {!isGsiRendered && (
              <button
                type="button"
                onClick={handleGoogleSignup}
                disabled={signupLoading || googleLoading}
                className="w-full py-2.5 px-4 rounded-xl bg-slate-900/90 hover:bg-slate-800 border border-slate-700/80 hover:border-slate-600 text-slate-200 text-xs font-semibold flex items-center justify-center space-x-3 transition-all hover:scale-[1.01] shadow-sm"
              >
                <svg className="w-4 h-4" viewBox="0 0 24 24">
                  <path
                    fill="#4285F4"
                    d="M23.745 12.27c0-.7-.06-1.4-.19-2.07H12v4.51h6.6c-.29 1.52-1.14 2.82-2.4 3.68v3.05h3.88c2.27-2.09 3.665-5.17 3.665-9.17z"
                  />
                  <path
                    fill="#34A853"
                    d="M12 24c3.24 0 5.95-1.08 7.93-2.91l-3.88-3.05c-1.08.72-2.45 1.16-4.05 1.16-3.12 0-5.77-2.1-6.72-4.93H1.25v3.15C3.26 21.36 7.34 24 12 24z"
                  />
                  <path
                    fill="#FBBC05"
                    d="M5.28 14.27c-.25-.72-.38-1.49-.38-2.27s.13-1.55.38-2.27V6.58H1.25C.45 8.17 0 9.99 0 12s.45 3.83 1.25 5.42l4.03-3.15z"
                  />
                  <path
                    fill="#EA4335"
                    d="M12 4.75c1.77 0 3.35.61 4.6 1.8l3.42-3.42C17.95 1.19 15.24 0 12 0 7.34 0 3.26 2.64 1.25 6.58l4.03 3.15c.95-2.83 3.6-4.98 6.72-4.98z"
                  />
                </svg>
                <span>{googleLoading ? 'Connecting...' : 'Sign up with Google'}</span>
              </button>
            )}
          </div>

          <div className="mt-6 text-center text-xs text-slate-400 pt-4 border-t border-slate-800/80">
            Already have an auditor account?{' '}
            <Link to="/login" className="text-cyan-400 font-semibold hover:underline">
              Sign In
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
};
