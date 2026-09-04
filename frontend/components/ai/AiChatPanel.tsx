"use client";

import { useState, useRef, useEffect } from "react";
import {
  Send,
  Bot,
  User,
  Loader2,
  Clock,
  HelpCircle,
  Sparkles,
} from "lucide-react";
import { ScenarioResultCard, type ScenarioResult } from "./ScenarioResultCard";
import { apiClient } from "@/lib/api-client";

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

      if (response.conversation_id) {
        setConversationId(response.conversation_id);
      }

      const assistantMsg: AiMessage = {
        id: crypto.randomUUID(),
        role: "assistant",
        content: response.narration ?? response.clarification_question ?? "",
        scenario_result: response.scenario_result,
        timeout: response.timeout,
        clarification_question: response.clarification_question,
      };
      setMessages((prev) => [...prev, assistantMsg]);
    } catch (err: unknown) {
      const errorMsg: AiMessage = {
        id: crypto.randomUUID(),
        role: "assistant",
        content: "Sorry, something went wrong. Please try again.",
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-full bg-gray-900/50 border border-gray-800 rounded-xl overflow-hidden">
      {/* Header */}
      <div className="flex items-center gap-2 px-4 py-3 border-b border-gray-800 bg-gray-900/80">
        <Sparkles className="w-4 h-4 text-violet-400" />
        <h3 className="text-sm font-semibold text-gray-200">AI Risk Analyst</h3>
        <span className="ml-auto text-xs text-gray-500">
          Powered by Claude · Numbers from quant engine
        </span>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4 min-h-0">
        {messages.length === 0 && (
          <div className="text-center py-6 text-gray-500 text-sm">
            <Bot className="w-10 h-10 mx-auto mb-3 opacity-40" />
            <p className="font-medium text-gray-400">Ask me about your portfolio risk</p>
            <p className="text-xs mt-1 text-gray-600">
              I explain risk metrics and evaluate what-if scenarios.<br />
              Numbers always come from the quant engine — not guessed.
            </p>
          </div>
        )}

        {messages.map((msg) => (
          <div
            key={msg.id}
            className={`flex gap-3 ${
              msg.role === "user" ? "flex-row-reverse" : ""
            }`}
          >
            {/* Avatar */}
            <div
              className={`flex-shrink-0 w-7 h-7 rounded-full flex items-center justify-center ${
                msg.role === "user"
                  ? "bg-violet-600/80"
                  : "bg-gray-700"
              }`}
            >
              {msg.role === "user" ? (
                <User className="w-4 h-4 text-white" />
              ) : (
                <Bot className="w-4 h-4 text-violet-300" />
              )}
            </div>

            {/* Content */}
            <div
              className={`max-w-[85%] ${
                msg.role === "user" ? "items-end" : "items-start"
              } flex flex-col gap-1`}
            >
              <div
                className={`rounded-xl px-3 py-2 text-sm leading-relaxed ${
                  msg.role === "user"
                    ? "bg-violet-600/80 text-white"
                    : "bg-gray-800/80 text-gray-200 border border-gray-700/50"
                }`}
              >
                {msg.timeout && (
                  <span className="flex items-center gap-1 text-amber-400 text-xs mb-1">
                    <Clock className="w-3 h-3" />
                    Narration unavailable (timeout)
                  </span>
                )}
                {msg.clarification_question && !msg.content ? (
                  <span className="flex items-start gap-2">
                    <HelpCircle className="w-4 h-4 text-violet-300 shrink-0 mt-0.5" />
                    {msg.clarification_question}
                  </span>
                ) : (
                  <p>{msg.content}</p>
                )}
              </div>

              {/* Structured scenario result rendered directly from API — not parsed from prose */}
              {msg.scenario_result && (
                <ScenarioResultCard result={msg.scenario_result} />
              )}
            </div>
          </div>
        ))}

        {loading && (
          <div className="flex gap-3">
            <div className="w-7 h-7 rounded-full bg-gray-700 flex items-center justify-center">
              <Bot className="w-4 h-4 text-violet-300" />
            </div>
            <div className="bg-gray-800/80 border border-gray-700/50 rounded-xl px-3 py-2 flex items-center gap-2">
              <Loader2 className="w-3 h-3 animate-spin text-violet-400" />
              <span className="text-xs text-gray-400">Analysing…</span>
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Suggested chips */}
      {messages.length === 0 && (
        <div className="px-4 pb-2 flex flex-wrap gap-2">
          {SUGGESTED_QUESTIONS.map((q) => (
            <button
              key={q}
              onClick={() => sendMessage(q)}
              disabled={loading}
              className="text-xs px-3 py-1.5 rounded-full border border-violet-500/30 bg-violet-500/10 text-violet-300 hover:bg-violet-500/20 transition-colors disabled:opacity-50"
            >
              {q}
            </button>
          ))}
        </div>
      )}

      {/* Input */}
      <div className="border-t border-gray-800 p-3">
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
            className="flex-1 resize-none bg-gray-800/60 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-200 placeholder-gray-500 focus:outline-none focus:border-violet-500/60 transition-colors disabled:opacity-50"
          />
          <button
            id="ai-chat-send"
            onClick={() => sendMessage(input)}
            disabled={loading || !input.trim()}
            className="p-2 rounded-lg bg-violet-600 hover:bg-violet-500 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
          >
            <Send className="w-4 h-4 text-white" />
          </button>
        </div>
        <p className="text-xs text-gray-600 mt-1.5 text-center">
          Rate limited: 30 questions/hour · All numbers verified by the quant engine
        </p>
      </div>
    </div>
  );
}
