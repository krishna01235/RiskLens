/**
 * RiskBudgetModal.tsx — Risk budget settings, migrated to Modal primitive.
 *
 * Changes from Phase 14:
 * - Uses <Modal> primitive (Escape-to-close, proper overlay, token colours)
 * - Uses <Input> primitive for all form fields
 * - Uses <Button> for Save / Cancel
 * - Error displayed inline in breach colour
 */

"use client";

import { useState, useEffect } from "react";
import Modal from "@/components/ui/Modal";
import Input from "@/components/ui/Input";
import Button from "@/components/ui/Button";
import { useAuthStore } from "@/store/auth-store";

export interface RiskBudget {
  max_cvar: number;
  watch_threshold: number;
  high_threshold: number;
  breach_threshold: number;
}

interface Props {
  portfolioId: string;
  initialBudget: RiskBudget | null;
  onClose: () => void;
  onSave: (budget: RiskBudget) => void;
}

export default function RiskBudgetModal({
  portfolioId,
  initialBudget,
  onClose,
  onSave,
}: Props) {
  const [maxCvar, setMaxCvar] = useState("5000");
  const [watch, setWatch] = useState("60");
  const [high, setHigh] = useState("80");
  const [breach, setBreach] = useState("100");
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (initialBudget) {
      setMaxCvar(initialBudget.max_cvar.toString());
      setWatch((initialBudget.watch_threshold * 100).toFixed(0));
      setHigh((initialBudget.high_threshold * 100).toFixed(0));
      setBreach((initialBudget.breach_threshold * 100).toFixed(0));
    }
  }, [initialBudget]);

  const handleSave = async () => {
    setError(null);
    const m = parseFloat(maxCvar);
    const w = parseFloat(watch) / 100;
    const h = parseFloat(high) / 100;
    const b = parseFloat(breach) / 100;

    if (Number.isNaN(m) || m <= 0) {
      setError("Max CVaR must be a positive number.");
      return;
    }
    if (!(w < h && h <= b)) {
      setError("Thresholds must satisfy Watch < High ≤ Breach.");
      return;
    }

    setIsSaving(true);
    try {
      const resp = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/portfolios/${portfolioId}/risk-budget`,
        {
          method: "PUT",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${useAuthStore.getState().accessToken}`,
          },
          body: JSON.stringify({
            max_cvar: m,
            watch_threshold: w,
            high_threshold: h,
            breach_threshold: b,
          }),
        },
      );

      if (!resp.ok) throw new Error(await resp.text());

      const updated = await resp.json();
      onSave(updated);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to save budget.");
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <Modal open title="Risk Budget" onClose={onClose} size="sm">
      <div className="space-y-4">
        {error && (
          <p className="text-sm text-brand-breach rounded-lg border border-brand-breach/30 bg-brand-breach-m px-3 py-2" role="alert">
            {error}
          </p>
        )}

        <Input
          id="budget-max-cvar"
          label="Max CVaR ($)"
          type="number"
          value={maxCvar}
          onChange={(e) => setMaxCvar(e.target.value)}
          placeholder="e.g. 5000"
          hint="Maximum acceptable 95% CVaR limit."
        />

        <div className="grid grid-cols-3 gap-3">
          <Input
            id="budget-watch"
            label="Watch (%)"
            type="number"
            value={watch}
            onChange={(e) => setWatch(e.target.value)}
          />
          <Input
            id="budget-high"
            label="High (%)"
            type="number"
            value={high}
            onChange={(e) => setHigh(e.target.value)}
          />
          <Input
            id="budget-breach"
            label="Breach (%)"
            type="number"
            value={breach}
            onChange={(e) => setBreach(e.target.value)}
          />
        </div>

        <p className="text-xs text-brand-tertiary">
          Thresholds are percentages of Max CVaR. Must satisfy Watch &lt; High ≤ Breach.
        </p>
      </div>

      <div className="flex justify-end gap-3 mt-6">
        <Button type="button" variant="ghost" onClick={onClose}>
          Cancel
        </Button>
        <Button
          id="budget-save-btn"
          type="button"
          variant="primary"
          loading={isSaving}
          onClick={handleSave}
        >
          Save Budget
        </Button>
      </div>
    </Modal>
  );
}
