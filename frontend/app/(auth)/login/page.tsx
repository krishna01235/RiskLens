"use client";

import { useState, FormEvent } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { authLogin } from "@/lib/api-client";
import { useAuthStore } from "@/store/auth-store";
import Input from "@/components/ui/Input";
import Button from "@/components/ui/Button";

export default function LoginPage() {
  const router = useRouter();
  const setAccessToken = useAuthStore((s) => s.setAccessToken);
  const setUser = useAuthStore((s) => s.setUser);

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const data = await authLogin(email, password);
      setAccessToken(data.access_token);
      const payload = JSON.parse(atob(data.access_token.split(".")[1]));
      setUser({ id: payload.sub, email, role: "user" });
      router.push("/dashboard");
    } catch (err: unknown) {
      setError(
        err instanceof Error ? err.message : "An unexpected error occurred."
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-brand-bg p-6">
      {/* Subtle ambient gradient (not decorative — establishes brand presence on entry) */}
      <div
        aria-hidden="true"
        className="pointer-events-none fixed inset-0"
        style={{
          background:
            "radial-gradient(ellipse at 70% 0%, hsla(220,40%,12%,0.8) 0%, transparent 60%)",
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
            Welcome back
          </h1>
          <p className="text-sm text-brand-tertiary mb-6">
            Sign in to your portfolio dashboard
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
              id="login-email"
              label="Email"
              type="email"
              autoComplete="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@example.com"
            />

            <Input
              id="login-password"
              label="Password"
              type="password"
              autoComplete="current-password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
            />

            <Button
              id="login-submit"
              type="submit"
              variant="primary"
              loading={loading}
              className="w-full mt-2"
            >
              Sign in
            </Button>
          </form>

          <p className="mt-5 text-center text-xs text-brand-tertiary">
            Don&apos;t have an account?{" "}
            <Link
              href="/register"
              className="text-brand-accent hover:underline focus-visible:outline focus-visible:outline-2 focus-visible:outline-[var(--color-accent)] rounded-sm"
            >
              Create one
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
