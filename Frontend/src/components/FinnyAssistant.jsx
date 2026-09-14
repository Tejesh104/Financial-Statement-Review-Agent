import React, { useState, useRef, useEffect } from 'react';
import { Sparkles, MessageSquare, Send, X, Bot, ChevronUp, ChevronDown, Check, ArrowRight, CornerDownLeft, Loader2 } from 'lucide-react';
import { useDocument } from '../services/documentContext';
import api from '../services/api';

export const FinnyAssistant = () => {
  const [isOpen, setIsOpen] = useState(false);
  const [inputMessage, setInputMessage] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const { hasDocument, uploadedFileInfo, currentDocument } = useDocument();
  const messagesEndRef = useRef(null);

  const [messages, setMessages] = useState([
    {
      id: 1,
      sender: 'finny',
      text: "Hi! I'm Finny, your Financial Review Assistant. I help you review financial filings, interpret variances, and verify accounting consistency with zero arithmetic hallucinations.",
      time: 'Just now',
    },
  ]);

  const quickActions = [
    { label: 'Review Financial Statement', prompt: 'Review the financial statement and provide a comprehensive performance analysis.' },
    { label: 'Compare Previous Years', prompt: 'Compare the financial performance across the available previous years.' },
    { label: 'Find Anomalies', prompt: 'Are there any unusual financial movements or anomalies in the statements?' },
    { label: 'Explain Key Metrics', prompt: 'What is the current ratio and what do liquidity and solvency metrics indicate?' },
    { label: 'Generate Review Report', prompt: 'Is the company financially healthy? Provide a comprehensive financial review.' },
  ];

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    if (isOpen) {
      scrollToBottom();
    }
  }, [messages, isOpen, isTyping]);

  const handleSendMessage = async (textToSend) => {
    const query = textToSend || inputMessage;
    if (!query.trim() || isTyping) return;

    // Add user message
    const userMsg = {
      id: Date.now(),
      sender: 'user',
      text: query,
      time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };

    setMessages((prev) => [...prev, userMsg]);
    setInputMessage('');
    setIsTyping(true);

    let finnyReply = '';

    try {
      const docId = currentDocument?.id;

      if (docId) {
        // Send message to real backend grounded chat API: POST /api/v1/chat/{docId}
        const res = await api.post(`/chat/${docId}`, { message: query });
        if (res.data && res.data.reply) {
          finnyReply = res.data.reply;
        } else if (res.data && res.data.answer) {
          finnyReply = res.data.answer;
        } else {
          finnyReply = "Unable to process the financial query. Please try again.";
        }
      } else {
        // If no document is currently uploaded, inform the user to upload a financial statement
        finnyReply = "Please upload or select a financial document first.";
      }
    } catch (err) {
      if (err.response?.data?.reply) {
        finnyReply = err.response.data.reply;
      } else if (err.response?.data?.detail) {
        finnyReply = String(err.response.data.detail);
      } else if (err.code === 'ECONNABORTED' || err.message?.includes('timeout')) {
        finnyReply = "FINNY AI request timed out while generating a response. Please try again.";
      } else {
        finnyReply = "FINNY AI is temporarily unavailable. Please make sure Ollama is running and try again.";
      }
    } finally {
      setMessages((prev) => [
        ...prev,
        {
          id: Date.now() + 1,
          sender: 'finny',
          text: finnyReply,
          time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        },
      ]);
      setIsTyping(false);
    }
  };

  return (
    <div className="finny-assistant fixed bottom-6 right-6 z-50 flex flex-col items-end">
      {/* Expanded Chat Drawer */}
      {isOpen && (
        <div className="finny-assistant-panel mb-3 w-96 sm:w-[420px] h-[520px] max-h-[calc(100vh-8rem)] rounded-2xl bg-[#0B1120] border border-cyan-500/40 shadow-2xl flex flex-col overflow-hidden backdrop-blur-xl animate-in fade-in slide-in-from-bottom-5 duration-200">
          {/* Header */}
          <div className="p-4 bg-gradient-to-r from-[#0F172A] to-[#0B1120] border-b border-slate-800 flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <div className="w-8 h-8 rounded-lg bg-gradient-to-tr from-cyan-400 to-blue-600 flex items-center justify-center text-slate-950 shadow-glow-cyan">
                <Bot className="w-5 h-5 stroke-[2.5]" />
              </div>
              <div>
                <div className="flex items-center space-x-2">
                  <h3 className="text-sm font-bold text-slate-100">FINNY</h3>
                  <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-cyan-950 text-cyan-300 border border-cyan-500/30">
                    Review Assistant
                  </span>
                </div>
                <p className="text-[11px] text-slate-400">Deterministic Financial Review</p>
              </div>
            </div>
            <button
              onClick={() => setIsOpen(false)}
              className="p-1 rounded-md text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition-colors"
            >
              <X className="w-4 h-4" />
            </button>
          </div>

          {/* Quick Action Suggestion Chips */}
          <div className="px-3 py-2 bg-[#070B14]/80 border-b border-slate-800/80 overflow-x-auto flex space-x-2 no-scrollbar">
            {quickActions.map((action, idx) => (
              <button
                key={idx}
                disabled={isTyping}
                onClick={() => handleSendMessage(action.prompt)}
                className="whitespace-nowrap px-2.5 py-1 rounded-full bg-slate-900 hover:bg-cyan-950/60 border border-slate-800 hover:border-cyan-500/40 text-[11px] text-slate-300 hover:text-cyan-300 transition-all font-mono disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {action.label}
              </button>
            ))}
          </div>

          {/* Messages Feed */}
          <div className="flex-1 p-4 overflow-y-auto space-y-3 bg-[#070B14]/50">
            {messages.map((msg) => (
              <div
                key={msg.id}
                className={`flex flex-col ${msg.sender === 'user' ? 'items-end' : 'items-start'}`}
              >
                <div
                  className={`max-w-[85%] rounded-xl p-3 text-xs leading-relaxed ${
                    msg.sender === 'user'
                      ? 'bg-gradient-to-r from-blue-600 to-cyan-600 text-white rounded-tr-none'
                      : 'bg-slate-900 border border-slate-800/80 text-slate-200 rounded-tl-none whitespace-pre-line shadow-sm'
                  }`}
                >
                  {msg.text}
                </div>
                <span className="text-[9px] text-slate-400 mt-1 px-1 font-mono">{msg.time}</span>
              </div>
            ))}
            {isTyping && (
              <div className="flex flex-col items-start">
                <div className="max-w-[85%] rounded-xl p-3 text-xs leading-relaxed bg-slate-900 border border-slate-800/80 text-cyan-400 rounded-tl-none shadow-sm flex items-center space-x-2">
                  <Loader2 className="w-3.5 h-3.5 animate-spin text-cyan-400 shrink-0" />
                  <span className="text-slate-400 font-mono text-[11px]">Finny is analyzing financial data...</span>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Bottom Input Area */}
          <div className="p-3 bg-[#0B1120] border-t border-slate-800">
            <form
              onSubmit={(e) => {
                e.preventDefault();
                handleSendMessage();
              }}
              className="flex items-center space-x-2"
            >
              <input
                type="text"
                disabled={isTyping}
                value={inputMessage}
                onChange={(e) => setInputMessage(e.target.value)}
                placeholder="Ask Finny about anomalies, ratios, YoY deltas..."
                className="flex-1 bg-[#070B14] border border-slate-800 rounded-xl px-3 py-2 text-xs text-slate-100 placeholder-slate-400 focus:outline-none focus:border-cyan-500/60 focus:ring-1 focus:ring-cyan-500/40 disabled:opacity-50"
              />
              <button
                type="submit"
                disabled={!inputMessage.trim() || isTyping}
                className="p-2 rounded-xl bg-gradient-to-r from-cyan-500 to-blue-600 text-slate-950 font-bold hover:brightness-110 disabled:opacity-40 disabled:cursor-not-allowed transition-all shadow-glow-cyan"
              >
                <Send className="w-4 h-4" />
              </button>
            </form>
          </div>
        </div>
      )}

      {/* Floating Toggle Button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="group flex items-center space-x-2.5 px-4 py-3 rounded-full bg-gradient-to-r from-cyan-500 to-blue-600 text-slate-950 font-semibold shadow-2xl hover:scale-105 active:scale-95 transition-all duration-200 shadow-glow-cyan"
      >
        <div className="w-6 h-6 rounded-full bg-slate-950/20 flex items-center justify-center">
          <Sparkles className="w-4 h-4 text-slate-950" />
        </div>
        <span className="text-xs font-bold tracking-wide">
          {isOpen ? 'Minimize Finny' : 'Ask Finny'}
        </span>
      </button>
    </div>
  );
};
