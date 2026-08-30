"use client";

import { useState } from "react";
import { Check, AlertCircle } from "lucide-react";

export interface ColumnMapping {
  symbol_col: string | null;
  quantity_col: string | null;
  price_col: string | null;
  currency_col: string | null;
}

export interface CsvPreviewResponse {
  suggested_mapping: ColumnMapping;
  headers: string[];
  preview_rows: Record<string, string>[];
}

interface ColumnMappingTableProps {
  preview: CsvPreviewResponse;
  onConfirm: (mapping: ColumnMapping) => void;
  isConfirming: boolean;
  marketCurrency: string; // e.g., "USD" or "INR"
}

const CANONICAL_FIELDS = [
  { id: "symbol", label: "Symbol / Ticker", required: true },
  { id: "quantity", label: "Quantity / Shares", required: true },
  { id: "price", label: "Average Price", required: true },
  { id: "currency", label: "Currency (Optional)", required: false },
] as const;

export default function ColumnMappingTable({
  preview,
  onConfirm,
  isConfirming,
  marketCurrency,
}: ColumnMappingTableProps) {
  const [mapping, setMapping] = useState<ColumnMapping>(preview.suggested_mapping);

  const handleSelectChange = (header: string, fieldId: string) => {
    // If the user selects a field for this header, update the mapping.
    // If they select "Ignore", we must remove this header from any mapped field.
    setMapping((prev) => {
      const newMapping = { ...prev };
      
      // First, if this header was mapped to something else, clear it
      Object.entries(newMapping).forEach(([key, val]) => {
        if (val === header) {
          newMapping[key as keyof ColumnMapping] = null;
        }
      });

      // Now set the new field (if it's not "ignore")
      if (fieldId !== "ignore") {
        newMapping[`${fieldId}_col` as keyof ColumnMapping] = header;
      }

      return newMapping;
    });
  };

  const getMappedFieldForHeader = (header: string): string => {
    if (mapping.symbol_col === header) return "symbol";
    if (mapping.quantity_col === header) return "quantity";
    if (mapping.price_col === header) return "price";
    if (mapping.currency_col === header) return "currency";
    return "ignore";
  };

  const isReadyToConfirm =
    mapping.symbol_col !== null &&
    mapping.quantity_col !== null &&
    mapping.price_col !== null;

  return (
    <div className="flex w-full flex-col gap-6">
      <div className="rounded-xl border border-slate-700 bg-slate-900/50 p-6">
        <h3 className="mb-4 text-lg font-semibold text-slate-100">Confirm Column Mapping</h3>
        <p className="mb-6 text-sm text-slate-400">
          We've automatically detected the columns from your CSV. Please verify that the required
          fields are mapped correctly before importing.
        </p>

        <div className="overflow-x-auto rounded-lg border border-slate-800">
          <table className="w-full text-left text-sm">
            <thead className="bg-slate-800/50 text-xs uppercase text-slate-400">
              <tr>
                <th className="px-6 py-3 font-medium">CSV Header</th>
                <th className="px-6 py-3 font-medium">Maps To</th>
                <th className="px-6 py-3 font-medium text-slate-500">Preview Data (First row)</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800">
              {preview.headers.map((header) => {
                const mappedFieldId = getMappedFieldForHeader(header);
                const isMapped = mappedFieldId !== "ignore";
                const firstRowValue = preview.preview_rows[0]?.[header] || "";

                return (
                  <tr key={header} className="hover:bg-slate-800/30">
                    <td className="px-6 py-4 font-medium text-slate-200">
                      <div className="flex items-center gap-2">
                        {header}
                        {isMapped && <Check className="h-4 w-4 text-emerald-500" />}
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <select
                        value={mappedFieldId}
                        onChange={(e) => handleSelectChange(header, e.target.value)}
                        className={`w-full rounded-md border bg-slate-950 px-3 py-2 text-sm outline-none transition-colors ${
                          isMapped
                            ? "border-emerald-500/50 text-emerald-400"
                            : "border-slate-700 text-slate-400 focus:border-violet-500 focus:text-slate-200"
                        }`}
                      >
                        <option value="ignore">-- Ignore this column --</option>
                        {CANONICAL_FIELDS.map((field) => {
                          // Disable option if it's already mapped to another header
                          const isAlreadyMappedToAnotherHeader =
                            mapping[`${field.id}_col` as keyof ColumnMapping] !== null &&
                            mapping[`${field.id}_col` as keyof ColumnMapping] !== header;

                          return (
                            <option
                              key={field.id}
                              value={field.id}
                              disabled={isAlreadyMappedToAnotherHeader}
                            >
                              {field.label} {field.required ? "*" : ""}
                            </option>
                          );
                        })}
                      </select>
                    </td>
                    <td className="px-6 py-4 text-slate-400 truncate max-w-[200px]" title={firstRowValue}>
                      {firstRowValue || <span className="italic opacity-50">Empty</span>}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        <div className="mt-8 flex items-center justify-between">
          <div className="flex items-center gap-2 text-sm">
            {!isReadyToConfirm ? (
              <>
                <AlertCircle className="h-5 w-5 text-amber-500" />
                <span className="text-amber-500">
                  Symbol, Quantity, and Average Price must be mapped.
                </span>
              </>
            ) : (
              <>
                <Check className="h-5 w-5 text-emerald-500" />
                <span className="text-emerald-500">
                  Ready to import. Portfolio currency will be {marketCurrency}.
                </span>
              </>
            )}
          </div>
          
          <button
            onClick={() => onConfirm(mapping)}
            disabled={!isReadyToConfirm || isConfirming}
            className="rounded-lg bg-violet-600 px-6 py-2.5 font-medium text-white transition-colors hover:bg-violet-700 disabled:pointer-events-none disabled:opacity-50"
          >
            {isConfirming ? "Importing..." : "Confirm & Import"}
          </button>
        </div>
      </div>
    </div>
  );
}
