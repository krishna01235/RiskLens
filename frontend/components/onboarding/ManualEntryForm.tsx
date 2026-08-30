"use client";

import { useState, useEffect, useRef } from "react";
import { Plus, Trash2, Search, Loader2 } from "lucide-react";
import { apiClient } from "@/lib/api-client";

interface SymbolSuggestion {
  symbol: string;
  name: string;
  exchange: string;
}

interface HoldingRow {
  id: string; // client-side only ID
  symbol: string;
  quantity: string;
  average_price: string;
}

interface ManualEntryFormProps {
  market: "us" | "india";
  marketCurrency: string; // USD or INR
  onSubmit: (holdings: Omit<HoldingRow, "id">[]) => Promise<void>;
  isSubmitting: boolean;
}

export default function ManualEntryForm({
  market,
  marketCurrency,
  onSubmit,
  isSubmitting,
}: ManualEntryFormProps) {
  const [rows, setRows] = useState<HoldingRow[]>([
    { id: crypto.randomUUID(), symbol: "", quantity: "", average_price: "" },
  ]);

  // Autocomplete state
  const [activeRowId, setActiveRowId] = useState<string | null>(null);
  const [suggestions, setSuggestions] = useState<SymbolSuggestion[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const searchTimeout = useRef<NodeJS.Timeout>();

  const currencySymbol = marketCurrency === "INR" ? "₹" : "$";

  const addRow = () => {
    setRows((prev) => [
      ...prev,
      { id: crypto.randomUUID(), symbol: "", quantity: "", average_price: "" },
    ]);
  };

  const removeRow = (id: string) => {
    if (rows.length === 1) return;
    setRows((prev) => prev.filter((r) => r.id !== id));
  };

  const updateRow = (id: string, field: keyof HoldingRow, value: string) => {
    setRows((prev) =>
      prev.map((r) => (r.id === id ? { ...r, [field]: value.toUpperCase() } : r))
    );

    if (field === "symbol") {
      setActiveRowId(id);
      fetchSuggestions(value);
    }
  };

  const fetchSuggestions = (query: string) => {
    if (searchTimeout.current) clearTimeout(searchTimeout.current);
    
    if (query.length < 1) {
      setSuggestions([]);
      return;
    }

    searchTimeout.current = setTimeout(async () => {
      setIsSearching(true);
      try {
        const data = await apiClient.get<SymbolSuggestion[]>(
          `/market/symbols?query=${query}&exchange=${market}`
        );
        setSuggestions(data);
      } catch (err) {
        console.error("Failed to fetch symbols", err);
        setSuggestions([]);
      } finally {
        setIsSearching(false);
      }
    }, 300); // 300ms debounce
  };

  const selectSuggestion = (rowId: string, suggestion: SymbolSuggestion) => {
    setRows((prev) =>
      prev.map((r) =>
        r.id === rowId ? { ...r, symbol: suggestion.symbol } : r
      )
    );
    setActiveRowId(null);
    setSuggestions([]);
  };

  // Close suggestions if clicking outside (simplified logic by closing on blur)
  useEffect(() => {
    const handleClickOutside = () => setActiveRowId(null);
    document.addEventListener("click", handleClickOutside);
    return () => document.removeEventListener("click", handleClickOutside);
  }, []);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    // Filter out completely empty rows
    const validRows = rows.filter(
      (r) => r.symbol || r.quantity || r.average_price
    );
    onSubmit(validRows);
  };

  const isValid = rows.some((r) => r.symbol && r.quantity && r.average_price);

  return (
    <form onSubmit={handleSubmit} className="w-full rounded-xl border border-slate-700 bg-slate-900/50 p-6">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h3 className="text-lg font-semibold text-slate-100">Manual Entry</h3>
          <p className="text-sm text-slate-400">
            Enter your holdings. Market is set to <span className="uppercase text-slate-300 font-medium">{market}</span> ({marketCurrency}).
          </p>
        </div>
        <button
          type="button"
          onClick={addRow}
          className="flex items-center gap-2 rounded-lg border border-slate-700 bg-slate-800 px-4 py-2 text-sm font-medium text-slate-200 transition-colors hover:bg-slate-700"
        >
          <Plus className="h-4 w-4" />
          Add Row
        </button>
      </div>

      <div className="space-y-4">
        <div className="grid grid-cols-[3fr_2fr_2fr_auto] gap-4 px-2 text-xs uppercase text-slate-500">
          <div>Symbol / Ticker</div>
          <div>Quantity</div>
          <div>Avg Price ({currencySymbol})</div>
          <div className="w-10"></div>
        </div>

        {rows.map((row) => (
          <div key={row.id} className="grid grid-cols-[3fr_2fr_2fr_auto] items-start gap-4">
            {/* Symbol Input with Autocomplete */}
            <div className="relative" onClick={(e) => e.stopPropagation()}>
              <div className="relative">
                <Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-500" />
                <input
                  type="text"
                  value={row.symbol}
                  onChange={(e) => updateRow(row.id, "symbol", e.target.value)}
                  onFocus={() => {
                    setActiveRowId(row.id);
                    if (row.symbol) fetchSuggestions(row.symbol);
                  }}
                  placeholder="e.g. AAPL"
                  required
                  className="w-full rounded-lg border border-slate-700 bg-slate-950 py-2 pl-9 pr-4 text-sm uppercase text-slate-200 outline-none transition-colors focus:border-teal-500"
                />
                {isSearching && activeRowId === row.id && (
                  <Loader2 className="absolute right-3 top-2.5 h-4 w-4 animate-spin text-slate-500" />
                )}
              </div>

              {/* Suggestions Dropdown */}
              {activeRowId === row.id && suggestions.length > 0 && (
                <div className="absolute z-10 mt-1 max-h-60 w-full overflow-y-auto rounded-lg border border-slate-700 bg-slate-800 shadow-xl">
                  {suggestions.map((s) => (
                    <button
                      key={s.symbol}
                      type="button"
                      onClick={() => selectSuggestion(row.id, s)}
                      className="flex w-full items-center justify-between px-4 py-2 text-left hover:bg-slate-700"
                    >
                      <div>
                        <div className="font-medium text-slate-200">{s.symbol}</div>
                        <div className="text-xs text-slate-400">{s.name}</div>
                      </div>
                      <span className="rounded bg-slate-900 px-1.5 py-0.5 text-xs text-slate-500">
                        {s.exchange}
                      </span>
                    </button>
                  ))}
                </div>
              )}
            </div>

            {/* Quantity */}
            <div>
              <input
                type="number"
                step="any"
                min="0"
                value={row.quantity}
                onChange={(e) => updateRow(row.id, "quantity", e.target.value)}
                placeholder="0"
                required
                className="w-full rounded-lg border border-slate-700 bg-slate-950 px-4 py-2 text-sm text-slate-200 outline-none transition-colors focus:border-teal-500"
              />
            </div>

            {/* Price */}
            <div className="relative">
              <span className="absolute left-3 top-2.5 text-sm text-slate-500">{currencySymbol}</span>
              <input
                type="number"
                step="any"
                min="0"
                value={row.average_price}
                onChange={(e) => updateRow(row.id, "average_price", e.target.value)}
                placeholder="0.00"
                required
                className="w-full rounded-lg border border-slate-700 bg-slate-950 py-2 pl-7 pr-4 text-sm text-slate-200 outline-none transition-colors focus:border-teal-500"
              />
            </div>

            {/* Delete button */}
            <button
              type="button"
              onClick={() => removeRow(row.id)}
              disabled={rows.length === 1}
              className="mt-2 text-slate-500 hover:text-red-400 disabled:opacity-30"
            >
              <Trash2 className="h-5 w-5" />
            </button>
          </div>
        ))}
      </div>

      <div className="mt-8 flex justify-end">
        <button
          type="submit"
          disabled={!isValid || isSubmitting}
          className="flex min-w-[200px] items-center justify-center rounded-lg bg-teal-600 px-6 py-2.5 font-medium text-white transition-colors hover:bg-teal-700 disabled:pointer-events-none disabled:opacity-50"
        >
          {isSubmitting ? (
            <span className="flex items-center gap-2">
              <Loader2 className="h-4 w-4 animate-spin" /> Saving...
            </span>
          ) : (
            "Create Portfolio"
          )}
        </button>
      </div>
    </form>
  );
}
