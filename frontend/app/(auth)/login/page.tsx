"use client";

import { useState, FormEvent } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { authLogin } from "@/lib/api-client";
import { useAuthStore } from "@/store/auth-store";

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
      // Decode user info from JWT payload (non-sensitive fields only)
      const payload = JSON.parse(atob(data.access_token.split(".")[1]));
      setUser({ id: payload.sub, email, role: "user" });
      router.push("/");
    } catch (err: unknown) {
      const msg =
        err instanceof Error ? err.message : "An unexpected error occurred.";
      setError(msg);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div style={styles.root}>
      {/* Ambient glow blobs */}
      <div style={styles.blob1} />
      <div style={styles.blob2} />

      <div style={styles.card}>
        {/* Logo mark */}
        <div style={styles.logoWrap}>
          <div style={styles.logoIcon}>
            <svg width="28" height="28" viewBox="0 0 28 28" fill="none">
              <path
                d="M4 22 L10 12 L16 17 L22 6"
                stroke="url(#lg)"
                strokeWidth="2.5"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
              <defs>
                <linearGradient id="lg" x1="4" y1="22" x2="22" y2="6" gradientUnits="userSpaceOnUse">
                  <stop stopColor="#818cf8" />
                  <stop offset="1" stopColor="#38bdf8" />
                </linearGradient>
              </defs>
            </svg>
          </div>
          <span style={styles.logoText}>RiskLens</span>
        </div>

        <h1 style={styles.heading}>Welcome back</h1>
        <p style={styles.subheading}>Sign in to your portfolio dashboard</p>

        {error && (
          <div style={styles.errorBanner} role="alert">
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none" style={{ flexShrink: 0 }}>
              <circle cx="8" cy="8" r="7" stroke="#f87171" strokeWidth="1.5" />
              <path d="M8 5v3.5M8 11h.01" stroke="#f87171" strokeWidth="1.5" strokeLinecap="round" />
            </svg>
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} style={styles.form} noValidate>
          <div style={styles.fieldGroup}>
            <label htmlFor="login-email" style={styles.label}>Email</label>
            <input
              id="login-email"
              type="email"
              autoComplete="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@example.com"
              style={styles.input}
              onFocus={(e) => Object.assign(e.target.style, styles.inputFocus)}
              onBlur={(e) => Object.assign(e.target.style, styles.inputBlur)}
            />
          </div>

          <div style={styles.fieldGroup}>
            <label htmlFor="login-password" style={styles.label}>Password</label>
            <input
              id="login-password"
              type="password"
              autoComplete="current-password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              style={styles.input}
              onFocus={(e) => Object.assign(e.target.style, styles.inputFocus)}
              onBlur={(e) => Object.assign(e.target.style, styles.inputBlur)}
            />
          </div>

          <button
            id="login-submit"
            type="submit"
            disabled={loading}
            style={{
              ...styles.submitBtn,
              ...(loading ? styles.submitBtnDisabled : {}),
            }}
          >
            {loading ? (
              <span style={styles.spinnerWrap}>
                <span style={styles.spinner} />
                Signing in…
              </span>
            ) : (
              "Sign in"
            )}
          </button>
        </form>

        <p style={styles.switchText}>
          Don&apos;t have an account?{" "}
          <Link href="/register" style={styles.switchLink}>
            Create one
          </Link>
        </p>
      </div>

      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { font-family: 'Inter', sans-serif; }
        @keyframes spin { to { transform: rotate(360deg); } }
        @keyframes fadeIn { from { opacity: 0; transform: translateY(12px); } to { opacity: 1; transform: translateY(0); } }
        @keyframes blobPulse { 0%, 100% { transform: scale(1); } 50% { transform: scale(1.08); } }
      `}</style>
    </div>
  );
}

// ── Inline styles (avoids any Tailwind / CSS-module dependencies) ─────────

const styles: Record<string, React.CSSProperties> = {
  root: {
    minHeight: "100vh",
    background: "radial-gradient(ellipse at 60% 0%, hsl(235,40%,10%) 0%, hsl(220,30%,6%) 60%)",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    position: "relative",
    overflow: "hidden",
    padding: "24px",
    fontFamily: "'Inter', sans-serif",
  },
  blob1: {
    position: "absolute",
    top: "-120px",
    right: "-80px",
    width: "420px",
    height: "420px",
    borderRadius: "50%",
    background: "radial-gradient(circle, hsla(248,80%,60%,0.18) 0%, transparent 70%)",
    animation: "blobPulse 8s ease-in-out infinite",
    pointerEvents: "none",
  },
  blob2: {
    position: "absolute",
    bottom: "-100px",
    left: "-60px",
    width: "340px",
    height: "340px",
    borderRadius: "50%",
    background: "radial-gradient(circle, hsla(200,80%,55%,0.14) 0%, transparent 70%)",
    animation: "blobPulse 10s ease-in-out infinite 2s",
    pointerEvents: "none",
  },
  card: {
    position: "relative",
    zIndex: 1,
    width: "100%",
    maxWidth: "420px",
    background: "hsla(230,30%,12%,0.85)",
    backdropFilter: "blur(24px)",
    WebkitBackdropFilter: "blur(24px)",
    border: "1px solid hsla(240,20%,100%,0.08)",
    borderRadius: "20px",
    padding: "40px",
    boxShadow: "0 32px 80px hsla(220,30%,4%,0.6), 0 0 0 1px hsla(240,20%,100%,0.04)",
    animation: "fadeIn 0.4s ease",
  },
  logoWrap: {
    display: "flex",
    alignItems: "center",
    gap: "10px",
    marginBottom: "28px",
  },
  logoIcon: {
    width: "42px",
    height: "42px",
    background: "linear-gradient(135deg, hsla(248,80%,60%,0.2), hsla(200,80%,55%,0.2))",
    border: "1px solid hsla(248,80%,70%,0.3)",
    borderRadius: "12px",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
  },
  logoText: {
    fontSize: "18px",
    fontWeight: "700",
    color: "#f1f5f9",
    letterSpacing: "-0.3px",
  },
  heading: {
    fontSize: "24px",
    fontWeight: "700",
    color: "#f1f5f9",
    letterSpacing: "-0.5px",
    marginBottom: "6px",
  },
  subheading: {
    fontSize: "14px",
    color: "hsla(220,20%,70%,1)",
    marginBottom: "28px",
  },
  errorBanner: {
    display: "flex",
    alignItems: "center",
    gap: "8px",
    background: "hsla(0,80%,60%,0.1)",
    border: "1px solid hsla(0,80%,60%,0.25)",
    borderRadius: "10px",
    padding: "12px 14px",
    color: "#fca5a5",
    fontSize: "13px",
    marginBottom: "20px",
  },
  form: {
    display: "flex",
    flexDirection: "column",
    gap: "18px",
  },
  fieldGroup: {
    display: "flex",
    flexDirection: "column",
    gap: "6px",
  },
  label: {
    fontSize: "13px",
    fontWeight: "500",
    color: "hsla(220,20%,75%,1)",
  },
  input: {
    background: "hsla(230,25%,16%,0.8)",
    border: "1px solid hsla(240,15%,100%,0.1)",
    borderRadius: "10px",
    padding: "11px 14px",
    fontSize: "14px",
    color: "#f1f5f9",
    outline: "none",
    transition: "border-color 0.2s, box-shadow 0.2s",
    width: "100%",
  },
  inputFocus: {
    borderColor: "hsla(248,80%,65%,0.6)",
    boxShadow: "0 0 0 3px hsla(248,80%,60%,0.12)",
  },
  inputBlur: {
    borderColor: "hsla(240,15%,100%,0.1)",
    boxShadow: "none",
  },
  submitBtn: {
    marginTop: "6px",
    padding: "12px",
    background: "linear-gradient(135deg, hsl(248,70%,62%), hsl(220,80%,58%))",
    border: "none",
    borderRadius: "10px",
    color: "#fff",
    fontSize: "15px",
    fontWeight: "600",
    cursor: "pointer",
    transition: "opacity 0.2s, transform 0.15s",
    letterSpacing: "-0.2px",
  },
  submitBtnDisabled: {
    opacity: 0.6,
    cursor: "not-allowed",
  },
  spinnerWrap: {
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    gap: "8px",
  },
  spinner: {
    display: "inline-block",
    width: "14px",
    height: "14px",
    border: "2px solid hsla(0,0%,100%,0.3)",
    borderTopColor: "#fff",
    borderRadius: "50%",
    animation: "spin 0.7s linear infinite",
  },
  switchText: {
    marginTop: "24px",
    textAlign: "center",
    fontSize: "13px",
    color: "hsla(220,20%,60%,1)",
  },
  switchLink: {
    color: "#818cf8",
    textDecoration: "none",
    fontWeight: "500",
  },
};
