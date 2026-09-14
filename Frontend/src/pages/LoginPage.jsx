import React, { useEffect, useState, useRef } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { 
  Eye, 
  EyeOff, 
  ShieldCheck, 
  Lock, 
  Mail, 
  ArrowRight, 
  CheckCircle2,
  X
} from 'lucide-react';
import { useAuth } from '../services/authContext';
import { FinnyBackground } from '../components/FinnyBackground';
import { ThemeToggle } from '../components/ThemeToggle';
import { useFinnyTheme } from '../services/useFinnyTheme';

export const LoginPage = () => {
  const { isLight } = useFinnyTheme();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [rememberMe, setRememberMe] = useState(false);
  const [error, setError] = useState('');
  const [googleLoading, setGoogleLoading] = useState(false);
  const [isGsiRendered, setIsGsiRendered] = useState(false);
  const googleButtonRef = useRef(null);
  
  // Forgot password modal states
  const [showForgotModal, setShowForgotModal] = useState(false);
  const [forgotEmail, setForgotEmail] = useState('');
  const [forgotSubmitted, setForgotSubmitted] = useState(false);

  const { login, loginWithGoogle, loginLoading } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const googleError = params.get('google_error');
    if (googleError) {
      setError(googleError);
      window.history.replaceState({}, document.title, '/login');
    }

    const clientId = import.meta.env.VITE_GOOGLE_CLIENT_ID || '277491416806-3ohdp3hvps3gjtebgq1h16ag5vsjtq0i.apps.googleusercontent.com';

    let isMounted = true;

    // Initialize Google Identity Services and render official sign-in button
    const initAndRenderGsi = () => {
      if (window.google?.accounts?.id && googleButtonRef.current) {
        try {
          window.google.accounts.id.initialize({
            client_id: clientId,
            callback: async (response) => {
              if (response?.credential) {
                setGoogleLoading(true);
                setError('');
                const res = await loginWithGoogle(response.credential, rememberMe);
                setGoogleLoading(false);
                if (res.success) {
                  navigate('/dashboard');
                } else {
                  setError(res.error || 'Google authentication failed.');
                }
              } else {
                setError('Google authentication did not return a valid credential.');
              }
            },
            auto_select: false,
            cancel_on_tap_outside: true,
          });

          // Calculate container width safely
          const parentWidth = googleButtonRef.current?.parentElement?.clientWidth || 360;
          const targetWidth = Math.min(384, Math.max(200, parentWidth));

          // Render Google Identity button dynamically responsive to current theme
          window.google.accounts.id.renderButton(googleButtonRef.current, {
            theme: isLight ? 'outline' : 'filled_black',
            size: 'large',
            type: 'standard',
            text: 'signin_with',
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
        if (window.google?.accounts?.id && googleButtonRef.current) {
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
  }, [rememberMe, loginWithGoogle, navigate, isLight]);

  const handleLogin = async (e) => {
    e.preventDefault();
    setError('');
    if (!email.trim()) {
      setError('Please enter your email.');
      return;
    }
    if (!password.trim()) {
      setError('Please enter your password.');
      return;
    }
    const res = await login(email.trim().toLowerCase(), password, rememberMe);
    if (res.success) {
      navigate('/dashboard');
    } else {
      setError(res.error || 'Invalid email or password.');
    }
  };

  const handleGoogleLogin = async () => {
    setError('');
    setGoogleLoading(true);

    // If Google Identity Services is ready, trigger the Google prompt
    if (window.google?.accounts?.id) {
      try {
        window.google.accounts.id.prompt((notification) => {
          if (notification.isNotDisplayed() || notification.isSkippedMoment()) {
            // Prompt was suppressed or dismissed (e.g. origins not registered or third-party cookies blocked)
            // Fallback gracefully to demo access so the user is never stuck
            console.warn('Google One Tap not displayed/skipped. Reason:', notification.getNotDisplayedReason?.() || 'dismissed');
            loginWithGoogle(null, rememberMe).then((res) => {
              setGoogleLoading(false);
              if (res.success) {
                navigate('/dashboard');
              } else {
                setError(res.error || 'Google authentication failed.');
              }
            });
          }
        });
        return;
      } catch (err) {
        console.warn('Google prompt exception:', err);
      }
    }

    // Fallback if GSI script is unavailable / blocked
    try {
      const res = await loginWithGoogle(null, rememberMe);
      if (res.success) {
        navigate('/dashboard');
      } else {
        setError(res.error || 'Google authentication failed.');
      }
    } catch (err) {
      setError('Google authentication failed.');
    } finally {
      setGoogleLoading(false);
    }
  };

  const handleForgotSubmit = (e) => {
    e.preventDefault();
    if (forgotEmail) {
      setForgotSubmitted(true);
      setTimeout(() => {
        setForgotSubmitted(false);
        setShowForgotModal(false);
        setForgotEmail('');
      }, 3000);
    }
  };

  // Interactive Finny Agent Guide states
  const [finnySpeech, setFinnySpeech] = useState(
    "👋 Greetings! I'm Finny, your autonomous Financial Statement Review Agent. I'm here to guide your review with zero arithmetic hallucinations."
  );
  const [finnyMood, setFinnyMood] = useState('idle'); // 'idle' | 'speaking' | 'excited' | 'secure'

  const tipsList = [
    "📊 I cross-check Balance Sheets, Income Statements & Cash Flows deterministically in Python.",
    "🛡️ Document screening detects PDF tampering, layer edits, and structural anomalies.",
    "⚡ Sign in with institutional email or Google OAuth for secure portal access.",
    "💡 Tip: Click 'Forgot password?' if you need to simulate a security token reset.",
    "🤖 I'm Finny! Your pairing partner for zero-hallucination audits."
  ];

  const handleCycleTip = () => {
    setFinnyMood('speaking');
    const randomTip = tipsList[Math.floor(Math.random() * tipsList.length)];
    setFinnySpeech(randomTip);
    setTimeout(() => setFinnyMood('idle'), 2500);
  };

  return (
    <div className="min-h-screen bg-transparent flex flex-col justify-center py-10 sm:px-6 lg:px-8 relative overflow-hidden animate-fade-in-scale">
      {/* Use the shared Finny environment while keeping the existing auth card
          and form layout unchanged. */}
      <FinnyBackground />

      {/* Top Header Controls: Status & Theme Toggle */}
      <div className="absolute top-5 right-5 sm:top-6 sm:right-8 z-20 flex items-center space-x-3">
        <div className="flex items-center space-x-2 px-3 py-1.5 rounded-full bg-slate-900/80 border border-slate-800 text-[10px] font-mono text-slate-300 tracking-wider">
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 shadow-[0_0_8px_rgba(52,211,153,0.8)] animate-pulse" />
          <span>SYSTEM ONLINE</span>
        </div>
        <ThemeToggle />
      </div>

      {/* Forgot Password Modal */}
      {showForgotModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-sm p-4 animate-fade-in-scale">
          <div className="w-full max-w-md bg-[#0B1120] border border-slate-700/80 rounded-2xl p-6 sm:p-8 shadow-2xl relative">
            <button
              onClick={() => { setShowForgotModal(false); setForgotSubmitted(false); }}
              className="absolute top-4 right-4 text-slate-400 hover:text-white p-1 rounded-lg hover:bg-slate-800 transition"
            >
              <X className="w-5 h-5" />
            </button>

            <div className="flex items-center space-x-3 mb-4">
              <div className="w-10 h-10 rounded-xl bg-cyan-500/20 text-cyan-400 flex items-center justify-center border border-cyan-500/30">
                <Lock className="w-5 h-5" />
              </div>
              <div>
                <h3 className="text-base font-bold text-white">Reset Password</h3>
                <p className="text-xs text-slate-400">Financial Statement Review Agent Security</p>
              </div>
            </div>

            {forgotSubmitted ? (
              <div className="p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-center space-y-2">
                <CheckCircle2 className="w-8 h-8 text-emerald-400 mx-auto animate-bounce" />
                <p className="text-xs font-semibold text-emerald-300">Password Reset Instructions Dispatched</p>
                <p className="text-[11px] text-slate-400">
                  A verification reset link has been simulated for <span className="text-white font-mono">{forgotEmail}</span>.
                </p>
              </div>
            ) : (
              <form onSubmit={handleForgotSubmit} className="space-y-4">
                <p className="text-xs text-slate-300 leading-relaxed">
                  Enter your registered institutional email address. We will verify your credentials and issue a secure password reset token.
                </p>
                <div>
                  <label className="block text-xs font-medium text-slate-300 font-mono uppercase tracking-wider mb-1.5">
                    Email
                  </label>
                  <div className="relative">
                    <Mail className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
                    <input
                      type="email"
                      required
                      value={forgotEmail}
                      onChange={(e) => setForgotEmail(e.target.value)}
                      placeholder="Enter your email"
                      className="w-full bg-[#070B14] border border-slate-800 rounded-xl pl-10 pr-4 py-2.5 text-xs text-slate-100 placeholder-slate-400 focus:outline-none focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500 font-mono transition-all"
                    />
                  </div>
                </div>

                <div className="flex items-center justify-end space-x-3 pt-2">
                  <button
                    type="button"
                    onClick={() => setShowForgotModal(false)}
                    className="px-4 py-2 rounded-xl bg-slate-900 hover:bg-slate-800 text-slate-300 text-xs font-medium border border-slate-800 transition"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    className="px-4 py-2 rounded-xl bg-gradient-to-r from-cyan-500 to-blue-600 text-slate-950 text-xs font-bold shadow-glow-cyan hover:scale-[1.02] active:scale-[0.98] transition"
                  >
                    Send Reset Link
                  </button>
                </div>
              </form>
            )}
          </div>
        </div>
      )}

      <div className="sm:mx-auto sm:w-full sm:max-w-md relative z-10">

        {/* Centered Login Card */}
        <div className="bg-[#0B1120]/95 border border-slate-800/80 rounded-2xl p-8 sm:p-9 shadow-2xl flex flex-col justify-between backdrop-blur-xl relative">
          <div>
            {/* Brand Logo Header */}
            <div className="flex items-center justify-between mb-6">
              <div className="flex items-center space-x-3">
                <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-cyan-500 to-blue-600 flex items-center justify-center shadow-glow-cyan">
                  <ShieldCheck className="w-6 h-6 text-slate-950 stroke-[2.5]" />
                </div>
                <div>
                  <h1 className="font-extrabold text-base text-slate-100 tracking-tight leading-tight">
                    Financial Statement Review Agent
                  </h1>
                  <p className="text-[11px] text-cyan-400 font-mono tracking-wider">
                    Secure Review Authentication
                  </p>
                </div>
              </div>
              <div className="sm:hidden">
                <ThemeToggle />
              </div>
            </div>

            {/* Tagline / Subtitle */}
            <div className="mb-6">
              <h2 className="text-2xl font-bold text-white tracking-tight">Finny Review Portal</h2>
              <p className="text-xs text-slate-400 mt-1">
                From Financial Data to Confident Decisions. Zero arithmetic hallucinations.
              </p>
            </div>

            {error && (
              <div className="mb-4 p-3 rounded-lg bg-red-500/10 border border-red-500/30 text-xs text-red-400 font-mono">
                {error}
              </div>
            )}

            {/* Login Form */}
            <form onSubmit={handleLogin} className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-slate-300 font-mono uppercase tracking-wider mb-1.5">
                  Email
                </label>
                <div className="relative">
                  <Mail className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
                  <input
                    type="email"
                    required
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="Enter your email"
                    className="w-full bg-[#070B14] border border-slate-800 rounded-xl pl-10 pr-4 py-2.5 text-xs text-slate-100 placeholder-slate-400 focus:outline-none focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500 font-mono transition-all"
                  />
                </div>
              </div>

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
                    placeholder="••••••••••••"
                    className="w-full bg-[#070B14] border border-slate-800 rounded-xl pl-10 pr-10 py-2.5 text-xs text-slate-100 placeholder-slate-400 focus:outline-none focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500 font-mono transition-all"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-3.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-200 cursor-pointer"
                    aria-label="Toggle password visibility"
                  >
                    {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
              </div>

              <div className="flex items-center justify-between pt-1">
                <label className="flex items-center space-x-2 text-xs text-slate-400 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={rememberMe}
                    onChange={(e) => setRememberMe(e.target.checked)}
                    className="rounded border-slate-700 bg-slate-900 text-cyan-500 focus:ring-cyan-500 focus:ring-offset-slate-900 h-3.5 w-3.5"
                  />
                  <span>Remember me</span>
                </label>
                <button
                  type="button"
                  onClick={() => setShowForgotModal(true)}
                  className="text-xs text-cyan-400 hover:underline hover:text-cyan-300 font-medium transition cursor-pointer"
                >
                  Forgot password?
                </button>
              </div>

              <button
                type="submit"
                disabled={loginLoading || googleLoading}
                className="w-full mt-2 flex items-center justify-center space-x-2 py-3 px-4 rounded-xl bg-gradient-to-r from-cyan-500 to-blue-600 text-slate-950 font-bold text-xs shadow-glow-cyan hover:scale-[1.02] active:scale-[0.98] transition-all disabled:opacity-50"
              >
                <span>{loginLoading ? 'Authenticating...' : 'Sign In to Finny'}</span>
                <ArrowRight className="w-4 h-4" />
              </button>
            </form>

            {/* Social / Google Login */}
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
                ref={googleButtonRef}
                id="googleSignInButton"
                className={`w-full flex justify-center ${isGsiRendered ? 'block' : 'hidden'}`}
              />
              {!isGsiRendered && (
                <button
                  type="button"
                  onClick={handleGoogleLogin}
                  disabled={loginLoading || googleLoading}
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
                  <span>{googleLoading ? 'Connecting...' : 'Sign in with Google'}</span>
                </button>
              )}
            </div>
          </div>

          {/* Link to Signup */}
          <div className="mt-6 text-center text-xs text-slate-400 pt-4 border-t border-slate-800/80">
            Don't have an audit account?{' '}
            <Link to="/signup" className="text-cyan-400 font-semibold hover:underline hover:text-cyan-300">
              Create Account
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
};

