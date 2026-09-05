"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { apiClient } from "@/lib/api-client";
import { useRiskSocket } from "@/hooks/useRiskSocket";
import MetricCard from "@/components/dashboard/MetricCard";
import AlertBanner from "@/components/dashboard/AlertBanner";
import RiskBudgetBar from "@/components/dashboard/RiskBudgetBar";
import RiskBudgetModal, { RiskBudget } from "@/components/settings/RiskBudgetModal";
import { ConcentrationWarning } from "@/components/dashboard/ConcentrationWarning";
import { RiskContributionList } from "@/components/dashboard/RiskContributionList";
import { RegimeBadge } from "@/components/dashboard/RegimeBadge";
import { AiChatPanel } from "@/components/ai/AiChatPanel";
import AppShell from "@/components/layout/AppShell";
import { MetricCardSkeleton } from "@/components/ui/Skeleton";

export default function DashboardPage() {
  const router = useRouter();
  const [portfolioId, setPortfolioId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [apiError, setApiError] = useState<string | null>(null);
  const [budget, setBudget] = useState<RiskBudget | null>(null);
  const [isBudgetModalOpen, setIsBudgetModalOpen] = useState(false);
  const [isAiPanelOpen, setIsAiPanelOpen] = useState(false);

  useEffect(() => {
    async function init() {
      try {
        const portfolios = await apiClient.get<{ id: string }[]>("/portfolios");
        if (portfolios && portfolios.length > 0) {
          const pid = portfolios[0].id;
          setPortfolioId(pid);
          try {
            const b = await apiClient.get<RiskBudget>(
              `/portfolios/${pid}/risk-budget`,
            );
            setBudget(b);
          } catch {
            // budget not yet set — that's fine
          }
        } else {
          router.push("/onboarding");
        }
      } catch {
        setApiError("Failed to load portfolio. Please try again.");
      } finally {
        setLoading(false);
      }
    }
    init();
  }, [router]);

  const { riskData, alertMsg, decisionMsg, error: wsError } = useRiskSocket(portfolioId);

  // ── Loading state — skeleton placeholders ──────────────────────────────
  if (loading) {
    return (
      <AppShell>
        <div className="mb-6">
          <div className="h-8 w-40 skeleton-shimmer rounded-md" />
          <div className="mt-2 h-4 w-24 skeleton-shimmer rounded-md" />
        </div>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 5 }).map((_, i) => (
            <MetricCardSkeleton key={i} />
          ))}
        </div>
      </AppShell>
    );
  }

  return (
    <AppShell wsConnected={!wsError}>
      {/* Page header */}
      <div className="mb-6 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-xl font-semibold text-brand-primary tracking-tight">
            Risk Dashboard
          </h1>
          <p className="text-xs text-brand-tertiary mt-0.5">
            {riskData
              ? `Updated ${new Date(riskData.timestamp * 1000).toLocaleTimeString()}`
              : "Waiting for market data…"}
          </p>
        </div>
        <div className="flex items-center gap-3">
          <RegimeBadge />
          <button
            id="ai-analyst-toggle"
            onClick={() => setIsAiPanelOpen((o) => !o)}
            aria-expanded={isAiPanelOpen}
            className="flex items-center gap-1.5 rounded-lg border border-brand-accent/30 bg-brand-accent/10 px-3 py-1.5 text-xs font-medium text-brand-accent hover:bg-brand-accent/20 transition-colors duration-fast focus-visible:outline focus-visible:outline-2 focus-visible:outline-[var(--color-accent)]"
          >
            {/* Sparkles */}
            <svg width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden="true">
              <path d="M7 1.5L8 5L11.5 6L8 7L7 10.5L6 7L2.5 6L6 5L7 1.5Z" stroke="currentColor" strokeWidth="1.2" strokeLinejoin="round" fill="currentColor" fillOpacity="0.2" />
            </svg>
            AI Analyst
            <svg width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden="true" className={`transition-transform duration-fast ${isAiPanelOpen ? "rotate-180" : ""}`}>
              <path d="M3 4.5L6 7.5L9 4.5" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" />
            </svg>
          </button>
        </div>
      </div>

      {/* Error banners */}
      {(apiError || wsError) && (
        <div
          role="alert"
          className="flex items-center gap-0 overflow-hidden rounded-lg border border-brand-breach/30 bg-brand-elevated mb-5"
        >
          <div className="w-1 self-stretch shrink-0 bg-brand-breach" />
          <div className="flex items-center gap-3 px-4 py-3">
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none" className="text-brand-breach shrink-0" aria-hidden="true">
              <circle cx="8" cy="8" r="7" stroke="currentColor" strokeWidth="1.3" />
              <path d="M8 5v4M8 11h.01" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" />
            </svg>
            <p className="text-sm text-brand-primary">{apiError || wsError}</p>
          </div>
        </div>
      )}

      <AlertBanner alertMsg={alertMsg} decisionMsg={decisionMsg} />

      {/* Risk metrics area */}
      {(!riskData || riskData.data_status === "pending") ? (
        <div className="rounded-lg border border-brand-border bg-brand-elevated p-10 text-center">
          <svg aria-label="Loading" className="h-6 w-6 animate-spin text-brand-accent mx-auto mb-4" viewBox="0 0 24 24" fill="none">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4l3-3-3-3v4a8 8 0 11-8 8z" />
          </svg>
          <p className="text-sm text-brand-secondary">Waiting for market data…</p>
          <p className="mt-1 text-xs text-brand-tertiary">Risk metrics compute once live prices arrive.</p>
        </div>
      ) : riskData.data_status === "insufficient_data" ? (
        <div className="rounded-lg border border-brand-border bg-brand-elevated p-10 text-center">
          <svg width="32" height="32" viewBox="0 0 32 32" fill="none" className="mx-auto mb-4 text-brand-watch" aria-hidden="true">
            <path d="M16 4L28 26H4L16 4Z" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round" />
            <path d="M16 13v6M16 22h.01" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
          </svg>
          <p className="text-sm font-medium text-brand-secondary">Insufficient historical data</p>
          <p className="mt-1 text-xs text-brand-tertiary">
            More price history is required for reliable VaR/CVaR estimates.
          </p>
        </div>
      ) : riskData.metrics ? (
        <div className="space-y-6">
          <ConcentrationWarning correlationFlags={riskData.correlation_flags} />
          <RiskBudgetBar
            budget={budget}
            currentCvar={riskData.metrics.cvar_95}
            onConfigureClick={() => setIsBudgetModalOpen(true)}
          />

          {/* Summary row */}
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
            {[
              { label: "Portfolio Value", value: riskData.portfolio_value, accent: "default" as const },
              {
                label: "Daily P&L",
                value: riskData.daily_pnl,
                accent: (parseFloat(riskData.daily_pnl) >= 0 ? "positive" : "negative") as "positive" | "negative",
              },
            ].map((m) => (
              <MetricCard key={m.label} label={m.label} value={m.value} accent={m.accent} />
            ))}
          </div>

          {/* Detailed metrics */}
          <h2 className="text-xs font-semibold text-brand-tertiary uppercase tracking-wide mt-2">
            Risk Metrics
          </h2>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            <MetricCard
              label="95% VaR"
              value={`$${riskData.metrics.var_95.toFixed(2)}`}
              sub="Max expected loss in 95% of days"
              accent="negative"
            />
            <MetricCard
              label="95% CVaR"
              value={`$${riskData.metrics.cvar_95.toFixed(2)}`}
              sub="Expected loss in worst 5% of days"
              accent="negative"
            />
            <MetricCard
              label="Annualized Volatility"
              value={`${(riskData.metrics.volatility * 100).toFixed(2)}%`}
            />
            <MetricCard
              label="Max Drawdown"
              value={`${(riskData.metrics.max_drawdown * 100).toFixed(2)}%`}
            />
            <MetricCard
              label="Sharpe Ratio"
              value={riskData.metrics.sharpe !== null ? riskData.metrics.sharpe.toFixed(2) : "N/A"}
              accent={riskData.metrics.sharpe !== null && riskData.metrics.sharpe >= 1 ? "positive" : "default"}
            />
          </div>

          <RiskContributionList contributions={riskData.risk_contributions} />
        </div>
      ) : null}

      {/* AI Analyst expandable panel */}
      {portfolioId && isAiPanelOpen && (
        <div className="mt-6 h-[540px]">
          <AiChatPanel portfolioId={portfolioId} />
        </div>
      )}

      {/* Risk Budget modal */}
      {isBudgetModalOpen && portfolioId && (
        <RiskBudgetModal
          portfolioId={portfolioId}
          initialBudget={budget}
          onClose={() => setIsBudgetModalOpen(false)}
          onSave={(b) => {
            setBudget(b);
            setIsBudgetModalOpen(false);
          }}
        />
      )}
    </AppShell>
  );
}
