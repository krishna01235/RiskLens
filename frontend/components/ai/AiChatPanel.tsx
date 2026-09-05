/**
 * AiChatPanel.tsx — AI Risk Analyst chat, migrated to design tokens.
 *
 * Changes from Phase 18:
 * - All ad-hoc gray/violet colors replaced with brand tokens
 * - Suggested question chips use Button ghost variant
 * - Textarea replaced with <Input> reference styles (keep textarea for multiline)
 * - Send button uses <Button> primary
 * - Empty state uses brand-tertiary colours
 */

"use client";

import { useState, useRef, useEffect } from "react";
import { ScenarioResultCard, type ScenarioResult } from "./ScenarioResultCard";
import { apiClient } from "@/lib/api-client";
import Button from "@/components/ui/Button";

interface AiMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  scenario_result?: ScenarioResult | null;
  timeout?: boolean;
  clarification_question?: string | null;
}

interface AiChatPanelProps {
  portfolioId: string;
}

const SUGGESTED_QUESTIONS = [
  "Explain my current risk",
  "What if NVDA falls 20%?",
  "What if interest rates rise 2%?",
  "What if AAPL drops 15% and MSFT drops 10%?",
];

export function AiChatPanel({ portfolioId }: AiChatPanelProps) {
  const [messages, setMessages] = useState<AiMessage[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const sendMessage = async (question: string) => {
    if (!question.trim() || loading) return;

    const userMsg: AiMessage = {
      id: crypto.randomUUID(),
      role: "user",
      content: question,
    };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setLoading(true);

    try {
      const isExplain =
        question.toLowerCase().includes("explain") &&
        !question.toLowerCase().includes("what if");

      let response;
      if (isExplain) {
        const res = await apiClient.post<{
          narration: string | null;
          timeout: boolean;
          conversation_id: string;
        }>("/ai/explain", {
          portfolio_id: portfolioId,
          conversation_id: conversationId,
        });
        response = {
          narration: res.narration,
          timeout: res.timeout,
          scenario_result: null,
          clarification_question: null,
          conversation_id: res.conversation_id,
        };
      } else {
        const res = await apiClient.post<{
          narration: string | null;
          timeout: boolean;
          scenario_result: ScenarioResult | null;
          clarification_needed: boolean;
          clarification_question: string | null;
          conversation_id: string;
        }>("/ai/what-if", {
          portfolio_id: portfolioId,
          question,
          conversation_id: conversationId,
        });
        response = {
          narration: res.narration,
          timeout: res.timeout,
          scenario_result: res.scenario_result ?? null,
          clarification_question: res.clarification_question ?? null,
          conversation_id: res.conversation_id,
        };
      }

      if (response.conversation_id) setConversationId(response.conversation_id);

      const assistantMsg: AiMessage = {
        id: crypto.randomUUID(),
        role: "assistant",
        content: response.narration ?? response.clarification_question ?? "",
        scenario_result: response.scenario_result,
        timeout: response.timeout,
        clarification_question: response.clarification_question,
      };
      setMessages((prev) => [...prev, assistantMsg]);
    } catch {
      setMessages((prev) => [
        ...prev,
        {
          id: crypto.randomUUID(),
          role: "assistant",
          content: "Something went wrong — please try again.",
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-full bg-brand-elevated border border-brand-border rounded-lg overflow-hidden">
      {/* Header */}
      <div className="flex items-center gap-2 px-4 py-3 border-b border-brand-border shrink-0">
        {/* Sparkles icon */}
        <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true" className="text-brand-accent">
          <path d="M8 2L9 6L13 7L9 8L8 12L7 8L3 7L7 6L8 2Z" stroke="currentColor" strokeWidth="1.3" strokeLinejoin="round" />
        </svg>
        <h3 className="text-sm font-semibold text-brand-primary">AI Risk Analyst</h3>
        <span className="ml-auto text-xs text-brand-tertiary">
          Powered by Claude · Numbers from quant engine
        </span>
      </div>

      {/* Messages */}
      <div
        className="flex-1 overflow-y-auto p-4 space-y-4 min-h-0"
        aria-label="Conversation"
        aria-live="polite"
      >
        {messages.length === 0 && (
          <div className="text-center py-8 text-brand-tertiary text-sm">
            {/* Bot icon */}
            <svg width="40" height="40" viewBox="0 0 40 40" fill="none" className="mx-auto mb-3 opacity-30" aria-hidden="true">
              <rect x="8" y="14" width="24" height="18" rx="4" stroke="currentColor" strokeWidth="1.5" />
              <circle cx="15" cy="23" r="2" fill="currentColor" />
              <circle cx="25" cy="23" r="2" fill="currentColor" />
              <path d="M20 8v6M16 8h8" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
            </svg>
            <p className="font-medium text-brand-secondary">Ask me about your portfolio risk</p>
            <p className="text-xs mt-1 text-brand-tertiary">
              I explain risk metrics and evaluate what-if scenarios.
              <br />
              All numbers come from the quant engine — never guessed.
            </p>
          </div>
        )}

        {messages.map((msg) => (
          <div
            key={msg.id}
            className={`flex gap-3 ${msg.role === "user" ? "flex-row-reverse" : ""}`}
          >
            {/* Avatar */}
            <div
              className={`shrink-0 w-7 h-7 rounded-full flex items-center justify-center text-xs font-medium ${
                msg.role === "user"
                  ? "bg-brand-accent text-white"
                  : "bg-brand-hover text-brand-secondary"
              }`}
              aria-hidden="true"
            >
              {msg.role === "user" ? "U" : "AI"}
            </div>

            {/* Bubble */}
            <div
              className={`max-w-[85%] flex flex-col gap-1 ${
                msg.role === "user" ? "items-end" : "items-start"
              }`}
            >
              <div
                className={`rounded-lg px-3 py-2 text-sm leading-relaxed ${
                  msg.role === "user"
                    ? "bg-brand-accent text-white"
                    : "bg-brand-bg border border-brand-border text-brand-primary"
                }`}
              >
                {msg.timeout && (
                  <span className="flex items-center gap-1 text-brand-watch text-xs mb-1">
                    <svg width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden="true">
                      <circle cx="6" cy="6" r="5" stroke="currentColor" strokeWidth="1.2" />
                      <path d="M6 3.5V6l2 1" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" />
                    </svg>
                    Narration unavailable (timeout)
                  </span>
                )}
                {msg.clarification_question && !msg.content ? (
                  <span className="flex items-start gap-2">
                    <svg width="14" height="14" viewBox="0 0 14 14" fill="none" className="text-brand-accent shrink-0 mt-0.5" aria-hidden="true">
                      <circle cx="7" cy="7" r="6" stroke="currentColor" strokeWidth="1.2" />
                      <path d="M7 4.5c-1 0-1.5.8-1.5 1.5h1c0-.3.2-.5.5-.5s.5.2.5.5c0 .7-1 .9-1 1.8h1V8c.5-.2 1-.7 1-1.5 0-.8-.7-1.5-1.5-1.5z" fill="currentColor" />
                      <circle cx="7" cy="10" r=".5" fill="currentColor" />
                    </svg>
                    {msg.clarification_question}
                  </span>
                ) : (
                  <p>{msg.content}</p>
                )}
              </div>

              {msg.scenario_result && (
                <ScenarioResultCard result={msg.scenario_result} />
              )}
            </div>
          </div>
        ))}

        {loading && (
          <div className="flex gap-3">
            <div className="w-7 h-7 rounded-full bg-brand-hover flex items-center justify-center text-xs text-brand-secondary" aria-hidden="true">
              AI
            </div>
            <div className="bg-brand-bg border border-brand-border rounded-lg px-3 py-2 flex items-center gap-2">
              <svg aria-label="Analysing" className="h-3 w-3 animate-spin text-brand-accent" viewBox="0 0 24 24" fill="none">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4l3-3-3-3v4a8 8 0 11-8 8z" />
              </svg>
              <span className="text-xs text-brand-tertiary">Analysing…</span>
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Suggested chips */}
      {messages.length === 0 && (
        <div className="px-4 pb-2 flex flex-wrap gap-1.5">
          {SUGGESTED_QUESTIONS.map((q) => (
            <button
              key={q}
              onClick={() => sendMessage(q)}
              disabled={loading}
              className="text-xs px-3 py-1 rounded-full border border-brand-accent/30 bg-brand-accent/10 text-brand-accent hover:bg-brand-accent/20 transition-colors disabled:opacity-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-[var(--color-accent)]"
            >
              {q}
            </button>
          ))}
        </div>
      )}

      {/* Input row */}
      <div className="border-t border-brand-border p-3 shrink-0">
        <div className="flex gap-2">
          <textarea
            id="ai-chat-input"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                sendMessage(input);
              }
            }}
            placeholder='Ask a what-if question or type "explain my risk"…'
            rows={1}
            disabled={loading}
            aria-label="Message input"
            className="flex-1 resize-none rounded-md border border-brand-border bg-brand-bg px-3 py-2 text-sm text-brand-primary placeholder:text-brand-tertiary focus:outline-none focus:ring-2 focus:ring-brand-accent transition-colors disabled:opacity-50"
          />
          <Button
            id="ai-chat-send"
            onClick={() => sendMessage(input)}
            disabled={loading || !input.trim()}
            loading={loading}
            size="md"
            aria-label="Send message"
          >
            <svg width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden="true">
              <path d="M12 7L2 2l2 5-2 5 10-5z" stroke="currentColor" strokeWidth="1.3" strokeLinejoin="round" fill="currentColor" />
            </svg>
          </Button>
        </div>
        <p className="text-xs text-brand-tertiary mt-1.5 text-center">
          Rate limited: 30 questions/hour · All numbers verified by quant engine
        </p>
      </div>
    </div>
  );
}
