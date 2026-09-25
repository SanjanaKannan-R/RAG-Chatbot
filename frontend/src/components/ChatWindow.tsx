import React, { useState, useRef, useEffect } from 'react';
import type { ChatMessage } from '../types';
import { CitationChip } from './CitationChip';
import {
  Send,
  Bot,
  User,
  AlertTriangle,
  Sparkles,
  ShieldCheck,
  PlusCircle,
  Loader2,
  HelpCircle
} from 'lucide-react';

interface ChatWindowProps {
  messages: ChatMessage[];
  apiBase: string;
  isSending: boolean;
  sessionId: string;
  onSendMessage: (text: string) => void;
  onNewChat: () => void;
}

export const ChatWindow: React.FC<ChatWindowProps> = ({
  messages,
  apiBase,
  isSending,
  sessionId,
  onSendMessage,
  onNewChat,
}) => {
  const [inputText, setInputText] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isSending]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputText.trim() || isSending) return;
    onSendMessage(inputText.trim());
    setInputText('');
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  return (
    <div className="flex-1 flex flex-col h-full bg-slate-900/60 overflow-hidden">
      {/* Top action header */}
      <header className="h-14 border-b border-slate-800 bg-slate-950/80 px-6 flex items-center justify-between shrink-0">
        <div className="flex items-center gap-2">
          <ShieldCheck className="w-5 h-5 text-indigo-400" />
          <span className="font-semibold text-sm text-slate-200">Verifiable Retrieval Grounding</span>
          <span className="text-xs text-slate-500 font-mono hidden sm:inline-block">
            (Session: {sessionId.slice(0, 8)}...)
          </span>
        </div>

        <button
          onClick={onNewChat}
          className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-slate-300 hover:text-white bg-slate-800 hover:bg-slate-700 rounded-lg transition-colors border border-slate-700 cursor-pointer"
        >
          <PlusCircle className="w-3.5 h-3.5" />
          <span>New Chat</span>
        </button>
      </header>

      {/* Messages stream */}
      <div className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-6">
        {messages.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-center max-w-lg mx-auto p-6 space-y-4">
            <div className="p-4 bg-indigo-600/10 border border-indigo-500/20 rounded-2xl text-indigo-400">
              <Sparkles className="w-10 h-10" />
            </div>
            <h2 className="text-lg font-bold text-white">Ask your documents anything</h2>
            <p className="text-xs text-slate-400 leading-relaxed">
              Every statement in every answer must cite its exact source chunk, page/row range, and verbatim quote.
              If an answer cannot be verified against the SQLite chunks, the system warns you rather than hallucinating.
            </p>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 w-full pt-2">
              <button
                onClick={() => onSendMessage("What is the remote work equipment stipend?")}
                className="p-2.5 text-left text-xs bg-slate-800/60 hover:bg-slate-800 border border-slate-700/80 rounded-lg text-slate-300 hover:text-white transition-all cursor-pointer"
              >
                💼 "What is the remote work stipend?"
              </button>
              <button
                onClick={() => onSendMessage("Summarize the total amount due and due date.")}
                className="p-2.5 text-left text-xs bg-slate-800/60 hover:bg-slate-800 border border-slate-700/80 rounded-lg text-slate-300 hover:text-white transition-all cursor-pointer"
              >
                🧾 "Summarize total due and due date"
              </button>
            </div>
          </div>
        ) : (
          messages.map((msg) => (
            <div
              key={msg.id}
              className={`flex gap-3 max-w-3xl ${
                msg.role === 'user' ? 'ml-auto flex-row-reverse' : 'mr-auto'
              }`}
            >
              {/* Avatar */}
              <div
                className={`w-8 h-8 rounded-lg flex items-center justify-center shrink-0 ${
                  msg.role === 'user'
                    ? 'bg-indigo-600 text-white'
                    : msg.grounded === false
                    ? 'bg-rose-900/60 text-rose-300 border border-rose-700'
                    : 'bg-slate-800 text-indigo-400 border border-slate-700'
                }`}
              >
                {msg.role === 'user' ? (
                  <User className="w-4 h-4" />
                ) : msg.grounded === false ? (
                  <AlertTriangle className="w-4 h-4" />
                ) : (
                  <Bot className="w-4 h-4" />
                )}
              </div>

              {/* Message content */}
              <div className="flex-1 min-w-0">
                {/* Check if ungrounded warning bubble required */}
                {msg.role === 'assistant' && msg.grounded === false ? (
                  <div className="bg-rose-950/40 border border-rose-800/80 rounded-2xl p-4 text-xs space-y-2 shadow-lg">
                    <div className="flex items-center gap-2 text-rose-400 font-semibold">
                      <AlertTriangle className="w-4 h-4 shrink-0" />
                      <span>This answer could not be grounded in your documents</span>
                    </div>
                    <div className="text-slate-300 leading-relaxed font-sans">
                      {msg.content}
                    </div>
                    <div className="text-[11px] text-rose-300/80 italic pt-1">
                      No retrieved chunks supported this claim. The model's assertions have been flagged to prevent unverified hallucinations.
                    </div>
                  </div>
                ) : (
                  <div
                    className={`rounded-2xl p-4 text-xs leading-relaxed ${
                      msg.role === 'user'
                        ? 'bg-indigo-600 text-white shadow-md'
                        : 'bg-slate-800/90 border border-slate-700 text-slate-200 shadow-md'
                    }`}
                  >
                    <div className="whitespace-pre-wrap font-sans">{msg.content}</div>

                    {/* Citations section */}
                    {msg.role === 'assistant' && msg.citations && msg.citations.length > 0 && (
                      <div className="mt-3 pt-3 border-t border-slate-700/80">
                        <div className="text-[10px] font-bold uppercase tracking-wider text-indigo-300 mb-1.5 flex items-center gap-1.5">
                          <ShieldCheck className="w-3.5 h-3.5" />
                          <span>Verifiable Sources ({msg.citations.length})</span>
                        </div>
                        <div className="flex flex-wrap gap-1">
                          {msg.citations.map((cite, idx) => (
                            <CitationChip key={`${cite.chunk_id}-${idx}`} citation={cite} apiBase={apiBase} />
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
          ))
        )}

        {/* Loading state indicator */}
        {isSending && (
          <div className="flex gap-3 max-w-3xl mr-auto animate-pulse">
            <div className="w-8 h-8 rounded-lg bg-slate-800 border border-slate-700 flex items-center justify-center text-indigo-400">
              <Bot className="w-4 h-4" />
            </div>
            <div className="p-3.5 bg-slate-800/80 border border-slate-700 rounded-2xl text-xs text-slate-400 flex items-center gap-2">
              <Loader2 className="w-4 h-4 animate-spin text-indigo-400" />
              <span>Searching SQLite vector index and validating citations...</span>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input bar */}
      <div className="p-4 bg-slate-950/90 border-t border-slate-800 shrink-0">
        <form onSubmit={handleSubmit} className="max-w-3xl mx-auto flex items-end gap-2">
          <div className="flex-1 relative bg-slate-900 border border-slate-700 focus-within:border-indigo-500 rounded-xl transition-all">
            <textarea
              ref={inputRef}
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask a question about your uploaded documents..."
              rows={1}
              className="w-full bg-transparent px-4 py-3 text-xs text-white placeholder-slate-500 focus:outline-none resize-none max-h-32"
              disabled={isSending}
            />
          </div>

          <button
            type="submit"
            disabled={!inputText.trim() || isSending}
            className="p-3 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-40 disabled:hover:bg-indigo-600 text-white rounded-xl transition-colors shrink-0 shadow-md cursor-pointer"
            title="Send query"
          >
            <Send className="w-4 h-4" />
          </button>
        </form>
        <div className="text-center mt-2 text-[10px] text-slate-400 flex items-center justify-center gap-1">
          <HelpCircle className="w-3 h-3 text-slate-500" />
          <span>Press Enter to send, Shift+Enter for new line. Every claim is strictly cross-checked with SQLite chunks.</span>
        </div>
      </div>
    </div>
  );
};
