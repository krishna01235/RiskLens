"use client";

/**
 * AiPreview.tsx — Non-functional AI chat preview for the landing page.
 *
 * Renders the shell of AiChatPanel (same token-based styling, same message
 * list structure) but with canned mock responses — no API call, no auth
 * token required. Demonstrates the interface visually.
 *
 * Mock replies use setTimeout to simulate the streaming feel.
 */

import { useState, useRef, useEffect } from "react";

interface MockMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  typing?: boolean;
}

const MOCK_QA: Record<string, string> = {
  "What if AAPL drops 20%?":
    "Your portfolio VaR would widen by ~18% to −$9,720. AAPL is your second-largest allocation but only your 4th-largest risk contributor — the primary driver is NVDA's correlation with your tech cluster.",
  "Explain my current risk":
    "Your portfolio VaR (95%) is −$8,240 and CVaR is −$14,900. NVDA drives 34% of total volatility despite being only 15% of capital. The HMM model indicates a High Volatility regime with 71% confidence.",
  "What if interest rates rise 2%?":
    "Rate sensitivity is primarily through your AMZN and MSFT positions. A +200bp shock reduces expected P&L by approximately −$3,100. Duration-sensitive positions represent 45% of portfolio capital.",
};

const SUGGESTED = Object.keys(MOCK_QA);

export default function AiPreview() {
  const [messages, setMessages] = useState<MockMessage[]>([]);
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  function handleQuestion(q: string) {
    if (loading) return;
    const userMsg: MockMessage = { id: crypto.randomUUID(), role: "user", content: q };
    const typingMsg: MockMessage = { id: crypto.randomUUID(), role: "assistant", content: "", typing: true };
    setMessages((prev) => [...prev, userMsg, typingMsg]);
    setLoading(true);

    setTimeout(() => {
      const reply = MOCK_QA[q] ?? "I can analyse your portfolio's risk in detail once you connect a real portfolio.";
      setMessages((prev) =>
        prev.map((m) => (m.typing ? { ...m, content: reply, typing: false } : m))
      );
      setLoading(false);
    }, 1100);
  }

  return (
    <section
      style={{
        borderTop: "1px solid var(--color-border)",
        backgroundColor: "var(--color-bg-elevated)",
      }}
      aria-label="AI Risk Analyst preview"
    >
      <div
        style={{
          maxWidth: 1100,
          margin: "0 auto",
          padding: "var(--sp-12) var(--sp-6)",
          display: "grid",
          gridTemplateColumns: "1fr 1fr",
          gap: "var(--sp-12)",
          alignItems: "start",
        }}
      >
        {/* Left: copy */}
        <div>
          <p
            style={{
              fontFamily: "var(--font-mono)",
              fontSize: "var(--text-xs)",
              color: "var(--color-accent)",
              letterSpacing: "0.1em",
              textTransform: "uppercase",
              marginBottom: "var(--sp-2)",
            }}
          >
            AI Risk Analyst
          </p>
          <h2
            style={{
              fontFamily: "var(--font-ui)",
              fontSize: "var(--text-lg)",
              fontWeight: "var(--fw-semibold)",
              color: "var(--color-text-primary)",
              marginBottom: "var(--sp-2)",
              lineHeight: 1.3,
            }}
          >
            Ask it anything about your portfolio. It computes first, then
            explains.
          </h2>
          <p
            style={{
              fontFamily: "var(--font-ui)",
              fontSize: "var(--text-sm)",
              color: "var(--color-text-secondary)",
              lineHeight: 1.6,
            }}
          >
            The AI never fabricates numbers. Every claim passes through the
            same quant engine that powers your live risk dashboard — GARCH
            volatility, Monte Carlo paths, EVT tail estimates. It then
            explains what it found in plain language.
          </p>
        </div>

        {/* Right: interactive preview */}
        <div
          style={{
            border: "1px solid var(--color-border)",
            borderRadius: "var(--radius-xl)",
            backgroundColor: "var(--color-bg)",
            overflow: "hidden",
            display: "flex",
            flexDirection: "column",
            height: 360,
          }}
        >
          {/* Header */}
          <div
            style={{
              padding: "var(--sp-3) var(--sp-4)",
              borderBottom: "1px solid var(--color-border)",
              display: "flex",
              alignItems: "center",
              gap: "var(--sp-2)",
            }}
          >
            <div
              style={{
                width: 8,
                height: 8,
                borderRadius: "50%",
                backgroundColor: "var(--color-safe)",
              }}
            />
            <span
              style={{
                fontFamily: "var(--font-ui)",
                fontSize: "var(--text-xs)",
                fontWeight: "var(--fw-medium)",
                color: "var(--color-text-secondary)",
              }}
            >
              AI Risk Analyst
            </span>
            <span
              style={{
                marginLeft: "auto",
                fontFamily: "var(--font-mono)",
                fontSize: "10px",
                color: "var(--color-text-tertiary)",
              }}
            >
              demo mode
            </span>
          </div>

          {/* Message list */}
          <div
            style={{
              flex: 1,
              overflowY: "auto",
              padding: "var(--sp-4)",
              display: "flex",
              flexDirection: "column",
              gap: "var(--sp-3)",
            }}
          >
            {messages.length === 0 && (
              <p
                style={{
                  fontFamily: "var(--font-ui)",
                  fontSize: "var(--text-xs)",
                  color: "var(--color-text-tertiary)",
                  textAlign: "center",
                  marginTop: "auto",
                  marginBottom: "auto",
                }}
              >
                Try one of the questions below ↓
              </p>
            )}
            {messages.map((msg) => (
              <div
                key={msg.id}
                style={{
                  display: "flex",
                  justifyContent: msg.role === "user" ? "flex-end" : "flex-start",
                }}
              >
                <div
                  style={{
                    maxWidth: "85%",
                    padding: "var(--sp-2) var(--sp-3)",
                    borderRadius: "var(--radius-lg)",
                    fontFamily: "var(--font-ui)",
                    fontSize: "var(--text-xs)",
                    lineHeight: 1.6,
                    backgroundColor:
                      msg.role === "user"
                        ? "var(--color-accent)"
                        : "var(--color-bg-elevated)",
                    color:
                      msg.role === "user"
                        ? "#fff"
                        : "var(--color-text-primary)",
                    border: msg.role === "assistant" ? "1px solid var(--color-border)" : "none",
                  }}
                >
                  {msg.typing ? (
                    <span style={{ display: "flex", gap: 3 }}>
                      {[0, 1, 2].map((i) => (
                        <span
                          key={i}
                          style={{
                            display: "inline-block",
                            width: 4,
                            height: 4,
                            borderRadius: "50%",
                            backgroundColor: "var(--color-text-tertiary)",
                            animation: `pulse 1s ease-in-out ${i * 0.2}s infinite`,
                          }}
                        />
                      ))}
                    </span>
                  ) : (
                    msg.content
                  )}
                </div>
              </div>
            ))}
            <div ref={bottomRef} />
          </div>

          {/* Suggested questions */}
          <div
            style={{
              padding: "var(--sp-3) var(--sp-4)",
              borderTop: "1px solid var(--color-border)",
              display: "flex",
              flexWrap: "wrap",
              gap: "var(--sp-2)",
            }}
          >
            {SUGGESTED.map((q) => (
              <button
                key={q}
                onClick={() => handleQuestion(q)}
                disabled={loading}
                style={{
                  fontFamily: "var(--font-ui)",
                  fontSize: "10px",
                  color: "var(--color-accent)",
                  backgroundColor: "var(--color-accent-muted)",
                  border: "1px solid rgba(62,123,250,0.2)",
                  borderRadius: "var(--radius-md)",
                  padding: "4px 10px",
                  cursor: loading ? "not-allowed" : "pointer",
                  opacity: loading ? 0.6 : 1,
                  transition: "opacity 150ms",
                }}
              >
                {q}
              </button>
            ))}
          </div>
        </div>
      </div>

      <style>{`
        @keyframes pulse {
          0%, 100% { opacity: 0.3; transform: scale(0.8); }
          50% { opacity: 1; transform: scale(1); }
        }
      `}</style>
    </section>
  );
}
