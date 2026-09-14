import React, { useState, useEffect, useRef } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import {
  Bot,
  Send,
  Mic,
  MicOff,
  Volume2,
  VolumeX,
  ShieldCheck,
  Sparkles,
  ArrowRight,
  CornerDownLeft,
  CheckCircle2,
  RotateCcw,
  Zap,
  HelpCircle,
  FileText
} from 'lucide-react';

export const FinnyGuidePage = () => {
  const navigate = useNavigate();
  const messagesEndRef = useRef(null);
  const starCanvasRef = useRef(null);  // 2D starfield behind AI core
  const coreRef = useRef(null);        // AI core div for cursor tracking

  // ── 2D Starfield Canvas Animation ──
  // Renders drifting particles on a canvas behind the AI core.
  // Uses vanilla 2D context — no Three.js dependency.
  useEffect(() => {
    const canvas = starCanvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    const parent = canvas.parentElement;
    if (!parent) return;

    // Size canvas to match parent container
    const resize = () => {
      canvas.width = parent.offsetWidth;
      canvas.height = parent.offsetHeight;
    };
    resize();
    window.addEventListener('resize', resize);

    // Create star particles with random positions and speeds
    const STAR_COUNT = 80;
    const stars = Array.from({ length: STAR_COUNT }, () => ({
      x: Math.random() * canvas.width,
      y: Math.random() * canvas.height,
      r: Math.random() * 1.2 + 0.3,           // radius between 0.3 and 1.5
      speed: 0.1 + Math.random() * 0.35,       // upward drift speed
      phase: Math.random() * Math.PI * 2,      // sine wobble phase offset
    }));

    let frameId;
    const draw = (t) => {
      ctx.clearRect(0, 0, canvas.width, canvas.height);

      for (const s of stars) {
        // Drift upward, wrap at top
        s.y -= s.speed;
        if (s.y < -2) s.y = canvas.height + 2;

        // Subtle horizontal sine wobble
        const wx = s.x + Math.sin(t * 0.001 + s.phase) * 0.6;

        ctx.beginPath();
        ctx.arc(wx, s.y, s.r, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(159, 159, 255, ${0.35 + s.r * 0.25})`;
        ctx.fill();
      }

      frameId = requestAnimationFrame(draw);
    };

    frameId = requestAnimationFrame(draw);

    return () => {
      cancelAnimationFrame(frameId);
      window.removeEventListener('resize', resize);
    };
  }, []);

  // ── Cursor-Following AI Core ──
  // Smoothly lerps the AI core position toward the mouse cursor
  // using requestAnimationFrame, replicating the FinnyLandingPage effect.
  useEffect(() => {
    let mouseX = 0;
    let mouseY = 0;
    let posX = 0;
    let posY = 0;
    let frameId;

    const onMouseMove = (e) => {
      // Normalize mouse to [-1, 1] range
      mouseX = (e.clientX / window.innerWidth - 0.5) * 2;
      mouseY = (e.clientY / window.innerHeight - 0.5) * 2;
    };

    window.addEventListener('mousemove', onMouseMove);

    const animate = () => {
      frameId = requestAnimationFrame(animate);

      if (!coreRef.current) return;

      // Lerp toward mouse with 8% easing per frame
      const targetX = mouseX * 18;
      const targetY = -mouseY * 14;
      posX += (targetX - posX) * 0.08;
      posY += (targetY - posY) * 0.08;

      // Subtle tilt based on position offset
      const tiltX = posY * 0.05;
      const tiltY = posX * 0.05;

      coreRef.current.style.transform =
        `translate3d(${posX}px, ${posY}px, 0) rotateX(${tiltX}deg) rotateY(${tiltY}deg)`;
    };

    frameId = requestAnimationFrame(animate);

    return () => {
      cancelAnimationFrame(frameId);
      window.removeEventListener('mousemove', onMouseMove);
    };
  }, []);

  // Voice Assist States
  const [voiceEnabled, setVoiceEnabled] = useState(true);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [isListening, setIsListening] = useState(false);
  const [recognitionSupported, setRecognitionSupported] = useState(false);

  // Chat States
  const [inputMessage, setInputMessage] = useState('');
  const [messages, setMessages] = useState([
    {
      id: 1,
      sender: 'finny',
      text: "👋 Welcome to Financial Statement Review Agent! I'm Finny, your autonomous review companion. I perform mathematical checks in deterministic Python with zero hallucinations. Ask me anything or speak to me directly before accessing the review portal!",
      time: 'Just now'
    }
  ]);

  const quickPrompts = [
    { label: "🔑 How do I log in?", prompt: "How do I log into the review portal?" },
    { label: "🛡️ Document Screening", prompt: "How do you verify document authenticity and integrity?" },
    { label: "⚖️ Balance Sheet Math", prompt: "How do you validate the balance sheet equation?" },
    { label: "⚡ Zero Hallucination", prompt: "What makes this review agent zero-hallucination?" },
  ];

  // Speech Recognition Setup
  const recognitionRef = useRef(null);

  useEffect(() => {
    // Check speech recognition support
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (SpeechRecognition) {
      setRecognitionSupported(true);
      const recog = new SpeechRecognition();
      recog.continuous = false;
      recog.interimResults = false;
      recog.lang = 'en-US';

      recog.onstart = () => {
        setIsListening(true);
      };

      recog.onresult = (event) => {
        const transcript = event.results[0][0].transcript;
        setInputMessage(transcript);
        handleSendMessage(transcript);
        setIsListening(false);
      };

      recog.onerror = () => {
        setIsListening(false);
      };

      recog.onend = () => {
        setIsListening(false);
      };

      recognitionRef.current = recog;
    }
  }, []);

  // Voice synthesis function
  const speakText = (text) => {
    if (!voiceEnabled || !('speechSynthesis' in window)) return;

    window.speechSynthesis.cancel(); // cancel prior speech
    const cleanText = text.replace(/[*#•👋🛡️⚖️⚡🔑💡🤖]/g, '');
    const utterance = new SpeechSynthesisUtterance(cleanText);
    utterance.rate = 1.05;
    utterance.pitch = 1.05;

    // Pick a pleasant voice if available
    const voices = window.speechSynthesis.getVoices();
    const englishVoice = voices.find(v => v.lang.includes('en') && (v.name.includes('Google') || v.name.includes('Natural') || v.name.includes('Samantha')));
    if (englishVoice) {
      utterance.voice = englishVoice;
    }

    utterance.onstart = () => setIsSpeaking(true);
    utterance.onend = () => setIsSpeaking(false);
    utterance.onerror = () => setIsSpeaking(false);

    window.speechSynthesis.speak(utterance);
  };

  const toggleMic = () => {
    if (!recognitionRef.current) {
      alert("Speech recognition is not supported in this browser. Please type your message.");
      return;
    }

    if (isListening) {
      recognitionRef.current.stop();
      setIsListening(false);
    } else {
      window.speechSynthesis.cancel();
      setIsSpeaking(false);
      try {
        recognitionRef.current.start();
      } catch (e) {
        setIsListening(false);
      }
    }
  };

  const toggleVoice = () => {
    if (isSpeaking) {
      window.speechSynthesis.cancel();
      setIsSpeaking(false);
    }
    setVoiceEnabled(!voiceEnabled);
  };

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isSpeaking]);

  const handleSendMessage = (textToSend) => {
    const query = textToSend || inputMessage;
    if (!query.trim()) return;

    const userMsg = {
      id: Date.now(),
      sender: 'user',
      text: query,
      time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    };

    setMessages((prev) => [...prev, userMsg]);
    setInputMessage('');

    // Finny AI Response Generation
    setTimeout(() => {
      const lower = query.toLowerCase();
      let reply = '';

      if (lower.includes('login') || lower.includes('sign in') || lower.includes('access') || lower.includes('demo') || lower.includes('google')) {
        reply = "You can access the portal in 3 ways: 1) Click 'Sign in with Google' for one-tap SSO, 2) Use corporate email 'analyst@fintechreview.ai' with 'Password@123', or 3) Click the 'One-Click Lead Auditor Demo Access' button on the login page! Click 'Proceed to Sign In' below whenever you're ready.";
      } else if (lower.includes('screen') || lower.includes('tamper') || lower.includes('integrity') || lower.includes('pdf')) {
        reply = "My Document Screening engine uses 6 deterministic checks: Font layer consistency, PDF metadata inspection, SHA-256 hash validation, text layer alignment, structural header extraction, and modification timeline analysis. Any document alteration is flagged before analysis begins.";
      } else if (lower.includes('balance sheet') || lower.includes('math') || lower.includes('equation')) {
        reply = "I verify the fundamental accounting invariance: Total Assets = Total Liabilities + Stockholders' Equity. If there's even a $1 rounding discrepancy or balance mismatch, it is mathematically flagged with pure Python computations — never guessing or approximating.";
      } else if (lower.includes('hallucination') || lower.includes('zero') || lower.includes('deterministic')) {
        reply = "Large language models frequently make arithmetic errors. Our system eliminates this: all mathematical operations, ratios, and YoY deltas are calculated deterministically by Python backend code. I only provide cognitive narrative explanations for the exact mathematical findings.";
      } else if (lower.includes('compare') || lower.includes('yoy') || lower.includes('multi-year')) {
        reply = "For multi-year comparisons, I calculate compound annual growth rates (CAGR), YoY revenue margins, and cross-year variance matrices to immediately highlight abnormal trends or unsustainable spikes.";
      } else {
        reply = `I heard you ask: "${query}". I'm Finny, your autonomous guide. You can ask me how to log in, how document screening works, or how deterministic arithmetic validates financial statements. When you're ready, click 'Proceed to Sign In'!`;
      }

      setMessages((prev) => [
        ...prev,
        {
          id: Date.now() + 1,
          sender: 'finny',
          text: reply,
          time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
        }
      ]);

      speakText(reply);
    }, 500);
  };

  return (
    <div className="min-h-screen bg-[#070B14] flex flex-col justify-between py-6 px-4 sm:px-6 lg:px-8 relative overflow-hidden bg-grid-pattern">
      {/* Background Ambient Orbs */}
      <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-cyan-500/15 blur-[140px] rounded-full pointer-events-none animate-float-1" />
      <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-blue-600/15 blur-[140px] rounded-full pointer-events-none animate-float-2" />

      {/* Top Navigation Bar */}
      <header className="max-w-6xl w-full mx-auto flex items-center justify-between z-10 pb-4 border-b border-slate-800/80">
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-cyan-500 to-blue-600 flex items-center justify-center shadow-glow-cyan">
            <ShieldCheck className="w-6 h-6 text-slate-950 stroke-[2.5]" />
          </div>
          <div>
            <h1 className="font-extrabold text-sm sm:text-base text-slate-100 tracking-tight leading-tight">
              Financial Statement Review Agent
            </h1>
            <p className="text-[11px] text-cyan-400 font-mono tracking-wider">
              Finny Autonomous Guide & Voice Assistant
            </p>
          </div>
        </div>

        <div className="flex items-center space-x-3">
          {/* Voice Assist Toggle */}
          <button
            onClick={toggleVoice}
            className={`px-3 py-1.5 rounded-xl border text-xs font-mono flex items-center space-x-2 transition-all ${voiceEnabled
                ? 'bg-cyan-500/10 border-cyan-500/40 text-cyan-300'
                : 'bg-slate-900 border-slate-800 text-slate-500'
              }`}
            title={voiceEnabled ? "Mute Finny Voice" : "Enable Finny Voice"}
          >
            {voiceEnabled ? <Volume2 className="w-4 h-4 text-cyan-400" /> : <VolumeX className="w-4 h-4" />}
            <span className="hidden sm:inline">{voiceEnabled ? "Voice: ON" : "Voice: Muted"}</span>
          </button>

          <Link
            to="/login"
            className="flex items-center space-x-2 py-2 px-4 rounded-xl bg-gradient-to-r from-cyan-500 to-blue-600 text-slate-950 font-bold text-xs shadow-glow-cyan hover:scale-[1.02] active:scale-[0.98] transition-all"
          >
            <span>Proceed to Sign In</span>
            <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      </header>

      {/* Main Content: Finny Doll Showcase + Interactive Chat with Voice Assist */}
      <main className="max-w-6xl w-full mx-auto my-6 grid lg:grid-cols-12 gap-8 items-center z-10 flex-grow">

        {/* Left Column: AI Core Visual */}
        <div className="lg:col-span-5 flex flex-col items-center text-center space-y-4">
          <div className="relative group finny-core-appear">
            {/* 2D starfield canvas rendered behind the AI core */}
            <canvas
              ref={starCanvasRef}
              className="absolute inset-0 rounded-2xl pointer-events-none"
              style={{ zIndex: 0 }}
            />

            {/* Breathing ambient glow layer */}
            <div className="finny-ambient-glow" />

            {/* AI Core assembly: orbits + glow + sphere — cursor-following */}
            <div
              className="relative w-64 h-64 sm:w-72 sm:h-72 rounded-2xl overflow-hidden border-2 border-cyan-400/50 shadow-2xl bg-slate-950/90 flex items-center justify-center"
              style={{ zIndex: 1 }}
            >
              <div className="finny-ai-core" ref={coreRef}>
                <div className="finny-orbit finny-orbit-1" />
                <div className="finny-orbit finny-orbit-2" />
                <div className="finny-core-glow" />
                <div className="finny-core">
                  <span>✦</span>
                </div>
              </div>

              {/* Gradient overlay at bottom for visual polish */}
              <div className="absolute inset-0 bg-gradient-to-t from-[#070B14] via-transparent to-transparent opacity-40 pointer-events-none" />

              {/* Status HUD Ribbon — preserved from original */}
              <div className="absolute bottom-3 left-3 right-3 flex items-center justify-between text-[11px] font-mono bg-slate-950/85 px-3 py-1.5 rounded-xl border border-cyan-500/40 text-cyan-300 backdrop-blur-md" style={{ zIndex: 2 }}>
                <span className="flex items-center space-x-1.5">
                  <Bot className="w-3.5 h-3.5 text-cyan-400" />
                  <span className="font-bold">Finny v1.4</span>
                </span>
                <span className="flex items-center space-x-1 text-emerald-400">
                  <span className="w-2 h-2 rounded-full bg-emerald-400 animate-ping"></span>
                  <span>Agent Online</span>
                </span>
              </div>
            </div>
          </div>

          {/* Voice Assist Live Equalizer Wave Animation */}
          <div className="w-full max-w-xs p-3 rounded-xl bg-[#0B1120]/80 border border-slate-800 flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <div className="w-6 h-6 rounded-lg bg-cyan-500/20 flex items-center justify-center text-cyan-400">
                <Volume2 className="w-3.5 h-3.5" />
              </div>
              <span className="text-xs font-mono text-slate-300">
                {isSpeaking ? "Finny Speaking..." : isListening ? "Listening to your voice..." : "Voice Assist Ready"}
              </span>
            </div>

            {/* Audio Wavebars */}
            <div className="flex items-center space-x-1 h-5">
              {[0.4, 0.9, 0.5, 1.0, 0.7].map((height, i) => (
                <div
                  key={i}
                  className={`w-1 bg-cyan-400 rounded-full transition-all duration-200 ${isSpeaking || isListening ? 'animate-pulse' : 'opacity-30'
                    }`}
                  style={{ height: (isSpeaking || isListening) ? `${height * 18}px` : '4px' }}
                />
              ))}
            </div>
          </div>

          <p className="text-xs text-slate-400 font-mono">
            Autonomous Review Agent • Voice Synthesis & Chat Enabled
          </p>
        </div>

        {/* Right Column: Live Chat with Voice Assist */}
        <div className="lg:col-span-7 bg-[#0B1120]/95 border border-slate-800/80 rounded-2xl shadow-2xl flex flex-col h-[520px] backdrop-blur-xl overflow-hidden">

          {/* Chat Header */}
          <div className="p-4 bg-gradient-to-r from-[#0F172A] to-[#0B1120] border-b border-slate-800/80 flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <div className="w-8 h-8 rounded-lg bg-gradient-to-tr from-cyan-400 to-blue-600 flex items-center justify-center text-slate-950 shadow-glow-cyan font-bold">
                <Bot className="w-4 h-4 stroke-[2.5]" />
              </div>
              <div>
                <h3 className="text-sm font-bold text-white flex items-center space-x-2">
                  <span>Chat with Finny</span>
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-cyan-950 text-cyan-300 border border-cyan-500/30">
                    Voice Copilot
                  </span>
                </h3>
                <p className="text-[11px] text-slate-400">Ask audit questions or tap the mic to speak</p>
              </div>
            </div>

            <button
              onClick={() => setMessages([{
                id: Date.now(),
                sender: 'finny',
                text: "Chat reset! How can I assist you with your financial statement review today?",
                time: 'Just now'
              }])}
              className="p-1.5 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition text-xs flex items-center space-x-1 font-mono"
              title="Reset Chat"
            >
              <RotateCcw className="w-3.5 h-3.5" />
              <span className="hidden sm:inline">Clear</span>
            </button>
          </div>

          {/* Quick Prompt Chips */}
          <div className="px-4 py-2.5 bg-[#070B14]/90 border-b border-slate-800 flex items-center space-x-2 overflow-x-auto no-scrollbar">
            {quickPrompts.map((item, idx) => (
              <button
                key={idx}
                onClick={() => handleSendMessage(item.prompt)}
                className="whitespace-nowrap px-2.5 py-1 rounded-lg bg-slate-900 hover:bg-slate-800 border border-slate-800 hover:border-cyan-500/40 text-[11px] text-slate-300 font-mono transition"
              >
                {item.label}
              </button>
            ))}
          </div>

          {/* Chat Messages Body */}
          <div className="flex-1 overflow-y-auto p-4 space-y-4">
            {messages.map((msg) => (
              <div
                key={msg.id}
                className={`flex flex-col ${msg.sender === 'user' ? 'items-end' : 'items-start'}`}
              >
                <div className="flex items-center space-x-1.5 mb-1 text-[10px] font-mono text-slate-400">
                  <span>{msg.sender === 'user' ? 'Auditor / Analyst' : 'Finny'}</span>
                  <span>•</span>
                  <span>{msg.time}</span>
                </div>

                <div
                  className={`max-w-[85%] rounded-2xl p-3.5 text-xs leading-relaxed ${msg.sender === 'user'
                      ? 'bg-gradient-to-r from-cyan-600 to-blue-600 text-white rounded-tr-none shadow-glow-cyan'
                      : 'bg-slate-900/90 text-slate-200 border border-slate-800/80 rounded-tl-none relative group'
                    }`}
                >
                  <p className="whitespace-pre-line">{msg.text}</p>

                  {msg.sender === 'finny' && (
                    <button
                      onClick={() => speakText(msg.text)}
                      className="mt-2 text-[10px] font-mono text-cyan-400 hover:text-cyan-300 flex items-center space-x-1 opacity-75 group-hover:opacity-100 transition"
                    >
                      <Volume2 className="w-3 h-3" />
                      <span>Replay Voice</span>
                    </button>
                  )}
                </div>
              </div>
            ))}
            <div ref={messagesEndRef} />
          </div>

          {/* Input & Voice Controls */}
          <div className="p-3 bg-[#070B14] border-t border-slate-800/80">
            <form
              onSubmit={(e) => {
                e.preventDefault();
                handleSendMessage();
              }}
              className="flex items-center space-x-2"
            >
              {/* Mic Speech Recognition Button */}
              <button
                type="button"
                onClick={toggleMic}
                className={`p-2.5 rounded-xl border transition-all ${isListening
                    ? 'bg-red-500 text-white border-red-400 animate-pulse shadow-[0_0_15px_#EF4444]'
                    : 'bg-slate-900 text-cyan-400 hover:bg-slate-800 border-slate-700/80'
                  }`}
                title={isListening ? "Listening... click to stop" : "Click to speak with voice assist"}
              >
                {isListening ? <MicOff className="w-4 h-4" /> : <Mic className="w-4 h-4" />}
              </button>

              <input
                type="text"
                value={inputMessage}
                onChange={(e) => setInputMessage(e.target.value)}
                placeholder={isListening ? "Listening to your voice..." : "Ask Finny anything or tap mic to speak..."}
                className="flex-1 bg-[#0B1120] border border-slate-800 rounded-xl px-4 py-2.5 text-xs text-slate-100 placeholder-slate-400 focus:outline-none focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500 font-mono transition-all"
              />

              <button
                type="submit"
                className="p-2.5 rounded-xl bg-gradient-to-r from-cyan-500 to-blue-600 text-slate-950 font-bold hover:scale-[1.02] active:scale-[0.98] transition shadow-glow-cyan"
              >
                <Send className="w-4 h-4" />
              </button>
            </form>
          </div>
        </div>
      </main>

      {/* Bottom Footer CTA */}
      <footer className="max-w-6xl w-full mx-auto flex flex-col sm:flex-row items-center justify-between pt-4 border-t border-slate-800/80 text-xs text-slate-400 z-10 space-y-2 sm:space-y-0">
        <div>
          Deterministic Financial Calculations. AI-Powered Explanations.
        </div>
        <div className="flex items-center space-x-4">
          <Link to="/login" className="text-cyan-400 hover:underline font-semibold">
            Sign In to Portal
          </Link>
          <span className="text-slate-600">•</span>
          <Link to="/signup" className="text-slate-300 hover:text-white">
            Create Account
          </Link>
        </div>
      </footer>
    </div>
  );
};
