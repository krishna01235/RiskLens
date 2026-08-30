"use client";

import { useState, FormEvent } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { authRegister } from "@/lib/api-client";
import { useAuthStore } from "@/store/auth-store";

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
      router.push("/");
    } catch (err: unknown) {
      const httpErr = err as { status?: number; message?: string };
      if (httpErr.status === 409) {
        setError("An account with that email already exists.");
      } else {
        setError(
          err instanceof Error ? err.message : "An unexpected error occurred."
        );
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <div style={styles.root}>
      <div style={styles.blob1} />
      <div style={styles.blob2} />

      <div style={styles.card}>
        {/* Logo */}
        <div style={styles.logoWrap}>
          <div style={styles.logoIcon}>
            <svg width="28" height="28" viewBox="0 0 28 28" fill="none">
              <path
                d="M4 22 L10 12 L16 17 L22 6"
                stroke="url(#lg2)"
                strokeWidth="2.5"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
              <defs>
                <linearGradient id="lg2" x1="4" y1="22" x2="22" y2="6" gradientUnits="userSpaceOnUse">
                  <stop stopColor="#818cf8" />
                  <stop offset="1" stopColor="#38bdf8" />
                </linearGradient>
              </defs>
            </svg>
          </div>
          <span style={styles.logoText}>RiskLens</span>
        </div>

        <h1 style={styles.heading}>Create an account</h1>
        <p style={styles.subheading}>Start monitoring your portfolio risk today</p>

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
            <label htmlFor="register-email" style={styles.label}>Email</label>
            <input
              id="register-email"
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
            <label htmlFor="register-password" style={styles.label}>Password</label>
            <input
              id="register-password"
              type="password"
              autoComplete="new-password"
              required
              minLength={8}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="At least 8 characters"
              style={styles.input}
              onFocus={(e) => Object.assign(e.target.style, styles.inputFocus)}
              onBlur={(e) => Object.assign(e.target.style, styles.inputBlur)}
            />
          </div>

          <div style={styles.fieldGroup}>
            <label htmlFor="register-confirm" style={styles.label}>Confirm password</label>
            <input
              id="register-confirm"
              type="password"
              autoComplete="new-password"
              required
              value={confirm}
              onChange={(e) => setConfirm(e.target.value)}
              placeholder="••••••••"
              style={{
                ...styles.input,
                ...(confirm && confirm !== password ? styles.inputError : {}),
              }}
              onFocus={(e) => Object.assign(e.target.style, styles.inputFocus)}
              onBlur={(e) => Object.assign(e.target.style, styles.inputBlur)}
            />
            {confirm && confirm !== password && (
              <span style={styles.fieldError}>Passwords don&apos;t match</span>
            )}
          </div>

          {/* Password strength hint */}
          {password.length > 0 && (
            <div style={styles.strengthBar}>
              <div
                style={{
                  ...styles.strengthFill,
                  width: `${Math.min(100, (password.length / 16) * 100)}%`,
                  background:
                    password.length < 8
                      ? "#f87171"
                      : password.length < 12
                      ? "#fbbf24"
                      : "#34d399",
                }}
              />
            </div>
          )}

          <button
            id="register-submit"
            type="submit"
            disabled={loading || (confirm.length > 0 && password !== confirm)}
            style={{
              ...styles.submitBtn,
              ...(loading || (confirm.length > 0 && password !== confirm)
                ? styles.submitBtnDisabled
                : {}),
            }}
          >
            {loading ? (
              <span style={styles.spinnerWrap}>
                <span style={styles.spinner} />
                Creating account…
              </span>
            ) : (
              "Create account"
            )}
          </button>
        </form>

        <p style={styles.switchText}>
          Already have an account?{" "}
          <Link href="/login" style={styles.switchLink}>
            Sign in
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

const styles: Record<string, React.CSSProperties> = {
  root: {
    minHeight: "100vh",
    background: "radial-gradient(ellipse at 40% 0%, hsl(235,40%,10%) 0%, hsl(220,30%,6%) 60%)",
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
    top: "-100px",
    left: "-80px",
    width: "400px",
    height: "400px",
    borderRadius: "50%",
    background: "radial-gradient(circle, hsla(248,80%,60%,0.16) 0%, transparent 70%)",
    animation: "blobPulse 9s ease-in-out infinite",
    pointerEvents: "none",
  },
  blob2: {
    position: "absolute",
    bottom: "-120px",
    right: "-60px",
    width: "360px",
    height: "360px",
    borderRadius: "50%",
    background: "radial-gradient(circle, hsla(160,70%,45%,0.12) 0%, transparent 70%)",
    animation: "blobPulse 11s ease-in-out infinite 3s",
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
    gap: "16px",
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
  inputError: {
    borderColor: "hsla(0,80%,60%,0.5)",
  },
  fieldError: {
    fontSize: "12px",
    color: "#f87171",
    marginTop: "2px",
  },
  strengthBar: {
    height: "3px",
    background: "hsla(240,15%,100%,0.08)",
    borderRadius: "2px",
    overflow: "hidden",
    marginTop: "-4px",
  },
  strengthFill: {
    height: "100%",
    borderRadius: "2px",
    transition: "width 0.3s ease, background 0.3s ease",
  },
  submitBtn: {
    marginTop: "4px",
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
    opacity: 0.5,
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
