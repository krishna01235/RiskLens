"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Play, Upload, Edit3, ArrowLeft, Loader2, IndianRupee, DollarSign } from "lucide-react";
import { apiClient } from "@/lib/api-client";
import { useAuthStore } from "@/store/auth-store";

import ActionCard from "@/components/onboarding/ActionCard";
import FileDropzone from "@/components/onboarding/FileDropzone";
import ColumnMappingTable, {
  CsvPreviewResponse,
  ColumnMapping,
} from "@/components/onboarding/ColumnMappingTable";
import ManualEntryForm from "@/components/onboarding/ManualEntryForm";

type OnboardingState =
  | "idle"
  | "demo_loading"
  | "csv_upload"
  | "mapping_review"
  | "importing"
  | "manual_form"
  | "submitting";

type Market = "us" | "india";

export default function OnboardingPage() {
  const router = useRouter();
  
  // High-level state
  const [state, setState] = useState<OnboardingState>("idle");
  const [market, setMarket] = useState<Market>("india"); // Defaulting to India as requested
  const [error, setError] = useState<string | null>(null);

  // CSV Flow State
  const [previewData, setPreviewData] = useState<CsvPreviewResponse | null>(null);

  const marketCurrency = market === "india" ? "INR" : "USD";

  // ── Path 1: Demo Portfolio ─────────────────────────────────────────────────
  const handleTryDemo = async () => {
    setState("demo_loading");
    setError(null);
    try {
      await apiClient.post(`/portfolios/demo?market=${market}`);
      router.push("/dashboard");
    } catch (err: any) {
      setError(err.message || "Failed to create demo portfolio");
      setState("idle");
    }
  };

  // ── Path 2: CSV Import ─────────────────────────────────────────────────────
  const handleFileSelect = async (file: File) => {
    setState("importing"); // Temporary loading state while uploading
    setError(null);
    
    const formData = new FormData();
    formData.append("file", file);

    try {
      // apiClient.post by default uses JSON, but we can override it if we wrote it that way
      // We'll use native fetch here to easily send FormData
      const res = await fetch("http://localhost:8000/portfolios/import/preview", {
        method: "POST",
        headers: {
          Authorization: `Bearer ${useAuthStore.getState().accessToken}`,
        },
        body: formData,
      });

      if (!res.ok) {
        const errorData = await res.json();
        throw new Error(errorData.detail || "Failed to parse CSV");
      }

      const data: CsvPreviewResponse = await res.json();
      setPreviewData(data);
      setState("mapping_review");
    } catch (err: any) {
      setError(err.message || "Failed to upload file");
      setState("csv_upload");
    }
  };

  const handleConfirmMapping = async (mapping: ColumnMapping) => {
    if (!previewData) return;
    setState("importing");
    setError(null);

    try {
      await apiClient.post("/portfolios/import/confirm", {
        mapping,
        rows: previewData.preview_rows,
        currency: marketCurrency,
      });
      router.push("/dashboard");
    } catch (err: any) {
      setError(err.message || "Failed to import portfolio");
      setState("mapping_review");
    }
  };

  // ── Path 3: Manual Entry ───────────────────────────────────────────────────
  const handleManualSubmit = async (holdings: { symbol: string; quantity: string; average_price: string }[]) => {
    setState("submitting");
    setError(null);

    try {
      // 1. Create a blank manual portfolio by using the demo endpoint?
      // No, wait. We don't have a POST /portfolios (blank) endpoint yet.
      // Phase 5 says: Create Portfolio submits: POST /portfolios/demo, then POST /holdings for each row
      // To avoid duplicate demo holdings, we should probably just use the demo endpoint, but wait.
      // If we use the demo endpoint, it'll populate 10 holdings.
      // Let's just create an empty portfolio if possible. But the backend only has /portfolios/demo.
      // Wait, Phase 5 didn't spec a blank portfolio endpoint. 
      // Actually, we can just POST /portfolios/import/confirm with empty mapping and the manual rows!
      // Let's construct a pseudo-CSV confirm request:
      const pseudoMapping: ColumnMapping = {
        symbol_col: "symbol",
        quantity_col: "quantity",
        price_col: "average_price",
        currency_col: null,
      };
      
      await apiClient.post("/portfolios/import/confirm", {
        mapping: pseudoMapping,
        rows: holdings, // They already match the mapping keys!
        currency: marketCurrency,
      });

      router.push("/dashboard");
    } catch (err: any) {
      setError(err.message || "Failed to create portfolio");
      setState("manual_form");
    }
  };

  return (
    <div className="flex min-h-screen flex-col items-center justify-center p-6 bg-slate-950">
      <div className="w-full max-w-4xl">
        
        {/* Header & Market Selector */}
        <div className="mb-12 flex flex-col items-center text-center">
          <h1 className="mb-4 text-4xl font-bold tracking-tight text-white sm:text-5xl">
            Let's build your portfolio
          </h1>
          <p className="mb-8 text-lg text-slate-400">
            How would you like to add your holdings?
          </p>

          <div className="inline-flex rounded-lg bg-slate-900 p-1">
            <button
              onClick={() => {
                if (state === "idle") setMarket("india");
              }}
              disabled={state !== "idle" && state !== "csv_upload" && state !== "manual_form"}
              className={`flex items-center gap-2 rounded-md px-6 py-2 text-sm font-medium transition-all ${
                market === "india"
                  ? "bg-slate-800 text-white shadow-sm"
                  : "text-slate-400 hover:text-slate-200"
              }`}
            >
              <IndianRupee className="h-4 w-4" />
              India (NSE)
            </button>
            <button
              onClick={() => {
                if (state === "idle") setMarket("us");
              }}
              disabled={state !== "idle" && state !== "csv_upload" && state !== "manual_form"}
              className={`flex items-center gap-2 rounded-md px-6 py-2 text-sm font-medium transition-all ${
                market === "us"
                  ? "bg-slate-800 text-white shadow-sm"
                  : "text-slate-400 hover:text-slate-200"
              }`}
            >
              <DollarSign className="h-4 w-4" />
              US (NYSE/NASDAQ)
            </button>
          </div>
        </div>

        {/* Dynamic Content Area */}
        <div className="relative">
          
          {/* Main Options (Idle State) */}
          {state === "idle" || state === "demo_loading" ? (
            <div className="grid grid-cols-1 gap-6 sm:grid-cols-3">
              <ActionCard
                title="Try Demo"
                description={`Explore RiskLens instantly with a pre-populated ${market === "india" ? "Indian" : "US"} portfolio.`}
                icon={state === "demo_loading" ? <Loader2 className="animate-spin text-blue-400" /> : <Play className="text-blue-400" />}
                variant="demo"
                onClick={handleTryDemo}
              />
              <ActionCard
                title="Import CSV"
                description="Upload a CSV export from your broker (Zerodha, Groww, Schwab, etc)."
                icon={<Upload className="text-violet-400" />}
                variant="csv"
                onClick={() => setState("csv_upload")}
              />
              <ActionCard
                title="Add Manually"
                description="Search for tickers and enter your holdings one by one."
                icon={<Edit3 className="text-teal-400" />}
                variant="manual"
                onClick={() => setState("manual_form")}
              />
            </div>
          ) : (
            <div>
              {/* Back button for sub-flows */}
              <button
                onClick={() => {
                  setState("idle");
                  setError(null);
                  setPreviewData(null);
                }}
                className="mb-6 flex items-center gap-2 text-sm font-medium text-slate-400 transition-colors hover:text-slate-200"
              >
                <ArrowLeft className="h-4 w-4" />
                Back to options
              </button>

              {/* Error Alert */}
              {error && (
                <div className="mb-6 rounded-lg border border-red-500/50 bg-red-500/10 p-4 text-sm text-red-400">
                  {error}
                </div>
              )}

              {/* CSV Upload Flow */}
              {(state === "csv_upload" || state === "importing" && !previewData) && (
                <FileDropzone
                  onFileSelect={handleFileSelect}
                  isUploading={state === "importing"}
                  error={error}
                />
              )}

              {/* CSV Mapping Review Flow */}
              {(state === "mapping_review" || (state === "importing" && previewData)) && previewData && (
                <ColumnMappingTable
                  preview={previewData}
                  onConfirm={handleConfirmMapping}
                  isConfirming={state === "importing"}
                  marketCurrency={marketCurrency}
                />
              )}

              {/* Manual Entry Flow */}
              {(state === "manual_form" || state === "submitting") && (
                <ManualEntryForm
                  market={market}
                  marketCurrency={marketCurrency}
                  onSubmit={handleManualSubmit}
                  isSubmitting={state === "submitting"}
                />
              )}
            </div>
          )}
        </div>

      </div>
    </div>
  );
}
