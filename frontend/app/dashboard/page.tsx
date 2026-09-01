"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { apiClient } from "@/lib/api-client";
import { useRiskSocket } from "@/hooks/useRiskSocket";
import { ArrowLeft, Loader2, AlertCircle } from "lucide-react";

export default function DashboardPage() {
  const router = useRouter();
  const [portfolioId, setPortfolioId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [apiError, setApiError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchPortfolio() {
      try {
        const portfolios = await apiClient.get<any[]>("/portfolios");
        if (portfolios && portfolios.length > 0) {
          setPortfolioId(portfolios[0].id);
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
    fetchPortfolio();
  }, [router]);

  const { riskData, error: wsError } = useRiskSocket(portfolioId);

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

        <h1 className="mb-8 text-3xl font-bold tracking-tight sm:text-4xl">
          Risk Dashboard
        </h1>
        
        {(apiError || wsError) && (
          <div className="mb-6 flex items-center gap-3 rounded-lg border border-red-500/50 bg-red-500/10 p-4 text-sm text-red-400">
            <AlertCircle className="h-5 w-5" />
            <p>{apiError || wsError}</p>
          </div>
        )}
        
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

        <div className="mt-8 flex justify-end">
          <p className="text-xs text-slate-500">
            {riskData 
              ? `Last updated: ${new Date(riskData.timestamp * 1000).toLocaleTimeString()}`
              : "Waiting for market data..."}
          </p>
        </div>
      </div>
    </div>
  );
}
