"use client";

import { useState, FormEvent } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { authRegister } from "@/lib/api-client";
import { useAuthStore } from "@/store/auth-store";
import Input from "@/components/ui/Input";
import Button from "@/components/ui/Button";

export default function RegisterPage() {
  const router = useRouter();
  const setAccessToken = useAuthStore((s) => s.setAccessToken);
  const setUser = useAuthStore((s) => s.setUser);

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);

    if (password !== confirm) {
      setError("Passwords do not match.");
      return;
    }
    if (password.length < 8) {
      setError("Password must be at least 8 characters.");
      return;
    }

    setLoading(true);
    try {
      const data = await authRegister(email, password);
      setAccessToken(data.access_token);
      const payload = JSON.parse(atob(data.access_token.split(".")[1]));
      setUser({ id: payload.sub, email, role: "user" });
      router.push("/dashboard");
    } catch (err: unknown) {
      const httpErr = err as { status?: number; message?: string };
      if (httpErr.status === 409) {
        setError("An account with that email already exists.");
      } else {
        setError(
          err instanceof Error ? err.message : "An unexpected error occurred.",
        );
      }
    } finally {
      setLoading(false);
    }
  }

  // Password strength 0–3
  const strength =
    password.length === 0
      ? 0
      : password.length < 8
        ? 1
        : password.length < 12
          ? 2
          : 3;

  const STRENGTH_COLOURS = ["", "bg-brand-breach", "bg-brand-watch", "bg-brand-safe"];
  const STRENGTH_WIDTHS = ["0%", "33%", "66%", "100%"];

  return (
    <div className="flex min-h-screen items-center justify-center bg-brand-bg p-6">
      {/* Ambient gradient */}
      <div
        aria-hidden="true"
        className="pointer-events-none fixed inset-0"
        style={{
          background:
            "radial-gradient(ellipse at 40% 0%, hsla(235,40%,10%,0.9) 0%, transparent 60%)",
        }}
      />

      <div className="relative z-10 w-full max-w-[420px]">
        {/* Logo */}
        <div className="mb-8 flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg border border-brand-accent/30 bg-brand-accent/10">
            <svg
              width="18"
              height="18"
              viewBox="0 0 18 18"
              fill="none"
              aria-hidden="true"
            >
              <path
                d="M3 14L6.5 8L10 11L13.5 5L16 7"
                stroke="var(--color-accent)"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          </div>
          <span className="text-sm font-semibold text-brand-primary tracking-tight">
            RiskLens
          </span>
        </div>

        {/* Card */}
        <div className="rounded-xl border border-brand-border bg-brand-elevated p-8">
          <h1 className="text-xl font-semibold text-brand-primary mb-1">
            Create an account
          </h1>
          <p className="text-sm text-brand-tertiary mb-6">
            Start monitoring your portfolio risk today
          </p>

          {error && (
            <div
              role="alert"
              className="flex items-center gap-2 rounded-lg border border-brand-breach/30 bg-brand-breach-m px-3 py-2 text-sm text-brand-breach mb-5"
            >
              <svg
                width="14"
                height="14"
                viewBox="0 0 14 14"
                fill="none"
                aria-hidden="true"
                className="shrink-0"
              >
                <circle cx="7" cy="7" r="6" stroke="currentColor" strokeWidth="1.2" />
                <path
                  d="M7 4.5v3M7 9.5h.01"
                  stroke="currentColor"
                  strokeWidth="1.2"
                  strokeLinecap="round"
                />
              </svg>
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4" noValidate>
            <Input
              id="register-email"
              label="Email"
              type="email"
              autoComplete="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@example.com"
            />

            <div className="space-y-1.5">
              <Input
                id="register-password"
                label="Password"
                type="password"
                autoComplete="new-password"
                required
                minLength={8}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="At least 8 characters"
              />
              {/* Strength bar */}
              {password.length > 0 && (
                <div
                  className="h-1 bg-brand-border rounded-full overflow-hidden"
                  aria-label={`Password strength: ${["", "weak", "medium", "strong"][strength]}`}
                  role="meter"
                  aria-valuenow={strength}
                  aria-valuemin={0}
                  aria-valuemax={3}
                >
                  <div
                    className={`h-full rounded-full transition-[width,background-color] duration-normal ${STRENGTH_COLOURS[strength]}`}
                    style={{ width: STRENGTH_WIDTHS[strength] }}
                  />
                </div>
              )}
            </div>

            <Input
              id="register-confirm"
              label="Confirm password"
              type="password"
              autoComplete="new-password"
              required
              value={confirm}
              onChange={(e) => setConfirm(e.target.value)}
              placeholder="••••••••"
              error={
                confirm && confirm !== password
                  ? "Passwords don't match"
                  : undefined
              }
            />

            <Button
              id="register-submit"
              type="submit"
              variant="primary"
              loading={loading}
              disabled={loading || (confirm.length > 0 && password !== confirm)}
              className="w-full mt-2"
            >
              Create account
            </Button>
          </form>

          <p className="mt-5 text-center text-xs text-brand-tertiary">
            Already have an account?{" "}
            <Link
              href="/login"
              className="text-brand-accent hover:underline focus-visible:outline focus-visible:outline-2 focus-visible:outline-[var(--color-accent)] rounded-sm"
            >
              Sign in
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
