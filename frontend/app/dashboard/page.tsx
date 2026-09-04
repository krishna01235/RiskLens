"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { apiClient } from "@/lib/api-client";
import { useRiskSocket } from "@/hooks/useRiskSocket";
import { ArrowLeft, Loader2, AlertCircle } from "lucide-react";
import MetricCard from "@/components/dashboard/MetricCard";
import AlertBanner from "@/components/dashboard/AlertBanner";
import RiskBudgetBar from "@/components/dashboard/RiskBudgetBar";
import RiskBudgetModal, { RiskBudget } from "@/components/settings/RiskBudgetModal";
import { ConcentrationWarning } from "@/components/dashboard/ConcentrationWarning";
import { RiskContributionList } from "@/components/dashboard/RiskContributionList";
import { RegimeBadge } from "@/components/dashboard/RegimeBadge";

export default function DashboardPage() {
  const router = useRouter();
  const [portfolioId, setPortfolioId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [apiError, setApiError] = useState<string | null>(null);
  const [budget, setBudget] = useState<RiskBudget | null>(null);
  const [isBudgetModalOpen, setIsBudgetModalOpen] = useState(false);

  useEffect(() => {
    async function fetchPortfolioAndBudget() {
      try {
        const portfolios = await apiClient.get<any[]>("/portfolios");
        if (portfolios && portfolios.length > 0) {
          const pid = portfolios[0].id;
          setPortfolioId(pid);
          
          try {
            const b = await apiClient.get<RiskBudget>(`/portfolios/${pid}/risk-budget`);
            setBudget(b);
          } catch (budgetErr) {
            console.error("Failed to fetch budget", budgetErr);
          }
        } else {
          router.push("/onboarding");
        }
      } catch (err: any) {
        console.error("Failed to fetch portfolios", err);
        setApiError("Failed to load portfolio. Please try again.");
      } finally {
        setLoading(false);
      }
    }
    fetchPortfolioAndBudget();
  }, [router]);

  const { riskData, alertMsg, decisionMsg, error: wsError } = useRiskSocket(portfolioId);

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-950">
        <Loader2 className="h-8 w-8 animate-spin text-blue-500" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-950 p-8 text-white">
      <div className="mx-auto max-w-4xl">
        <button
          onClick={() => router.push("/onboarding")}
          className="mb-8 flex items-center gap-2 text-sm font-medium text-slate-400 transition-colors hover:text-slate-200"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to onboarding
        </button>

        <div className="mb-8 flex flex-col items-start justify-between gap-4 sm:flex-row sm:items-center">
          <h1 className="text-3xl font-bold tracking-tight sm:text-4xl">
            Risk Dashboard
          </h1>
          <RegimeBadge />
        </div>
        
        {(apiError || wsError) && (
          <div className="mb-6 flex items-center gap-3 rounded-lg border border-red-500/50 bg-red-500/10 p-4 text-sm text-red-400">
            <AlertCircle className="h-5 w-5" />
            <p>{apiError || wsError}</p>
          </div>
        )}

        <AlertBanner alertMsg={alertMsg} decisionMsg={decisionMsg} />
        
        <div className="grid gap-6 sm:grid-cols-2">
          {/* Portfolio Value Card */}
          <div className="rounded-xl border border-slate-800 bg-slate-900/50 p-6 shadow-lg backdrop-blur-sm">
            <h2 className="mb-2 text-sm font-medium text-slate-400">Total Portfolio Value</h2>
            <div className="flex items-baseline gap-2">
              <span className="text-4xl font-semibold tracking-tight text-white">
                {riskData ? riskData.portfolio_value : "---"}
              </span>
            </div>
          </div>

          {/* Daily PnL Card */}
          <div className="rounded-xl border border-slate-800 bg-slate-900/50 p-6 shadow-lg backdrop-blur-sm">
            <h2 className="mb-2 text-sm font-medium text-slate-400">Daily PnL</h2>
            <div className="flex items-baseline gap-2">
              <span className={`text-4xl font-semibold tracking-tight ${
                !riskData 
                  ? "text-white" 
                  : parseFloat(riskData.daily_pnl) >= 0 
                    ? "text-emerald-400" 
                    : "text-red-400"
              }`}>
                {riskData ? riskData.daily_pnl : "---"}
              </span>
            </div>
          </div>
        </div>

        <div className="mt-8 border-t border-slate-800 pt-8">
          <h2 className="mb-6 text-xl font-semibold tracking-tight">Risk Metrics</h2>
          
          {(!riskData || riskData.data_status === "pending") ? (
            <div className="rounded-xl border border-slate-800 bg-slate-900/50 p-8 text-center text-slate-400">
              <Loader2 className="mx-auto mb-4 h-6 w-6 animate-spin text-blue-500" />
              <p>Waiting for market data to compute risk metrics...</p>
            </div>
          ) : riskData.data_status === "insufficient_data" ? (
            <div className="rounded-xl border border-slate-800 bg-slate-900/50 p-8 text-center text-slate-400">
              <AlertCircle className="mx-auto mb-4 h-6 w-6 text-amber-500" />
              <p>Insufficient historical data to compute risk metrics.</p>
              <p className="mt-1 text-sm text-slate-500">More price history is needed for a reliable estimate.</p>
            </div>
          ) : riskData.metrics ? (
            <div className="space-y-6">
              <ConcentrationWarning correlationFlags={riskData.correlation_flags} />
              <RiskBudgetBar 
                budget={budget} 
                currentCvar={riskData.metrics.cvar_95}
                onConfigureClick={() => setIsBudgetModalOpen(true)}
              />
              <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
              <MetricCard 
                label="95% Value at Risk (VaR)" 
                value={`$${riskData.metrics.var_95.toFixed(2)}`} 
                sub="Max expected loss in 95% of days" 
                accent="negative"
              />
              <MetricCard 
                label="95% Conditional VaR (CVaR)" 
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
        </div>

        <div className="mt-8 flex justify-end">
          <p className="text-xs text-slate-500">
            {riskData 
              ? `Last updated: ${new Date(riskData.timestamp * 1000).toLocaleTimeString()}`
              : "Waiting for market data..."}
          </p>
        </div>
      </div>

      {isBudgetModalOpen && portfolioId && (
        <RiskBudgetModal
          portfolioId={portfolioId}
          initialBudget={budget}
          onClose={() => setIsBudgetModalOpen(false)}
          onSave={(updatedBudget) => {
            setBudget(updatedBudget);
            setIsBudgetModalOpen(false);
          }}
        />
      )}
    </div>
  );
}
