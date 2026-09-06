"use client";

/**
 * app/page.tsx — Public landing page.
 *
 * Session redirect: on mount, attempt silentRefresh() via the httpOnly cookie.
 * If a valid session exists, redirect to /dashboard immediately — a returning
 * logged-in user never sees the marketing page.
 *
 * RiskLensExperience is loaded via next/dynamic with { ssr: false } because:
 * 1. It uses Three.js / WebGL (browser-only APIs)
 * 2. It uses framer-motion's useReducedMotion hook
 * 3. We never want this 3D bundle in the dashboard/auth bundle
 */

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import dynamic from "next/dynamic";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

// Lazy-load the full 3D landing experience — never bundled into auth/dashboard routes
const RiskLensExperience = dynamic(
  () => import("@/components/risklens/experience"),
  {
    ssr: false,
    loading: () => (
      <div
        style={{ minHeight: "100vh", backgroundColor: "#061014" }}
        aria-hidden="true"
      />
    ),
  }
);

export default function LandingPage() {
  const router = useRouter();
  const [sessionChecked, setSessionChecked] = useState(false);

  // Silent session check — redirect logged-in users straight to dashboard
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const resp = await fetch(`${BASE_URL}/auth/refresh`, {
          method: "POST",
          credentials: "include",
        });
        if (!cancelled && resp.ok) {
          router.replace("/dashboard");
          return;
        }
      } catch {
        // No session — show landing page
      }
      if (!cancelled) setSessionChecked(true);
    })();
    return () => {
      cancelled = true;
    };
  }, [router]);

  // While checking session, show blank dark screen (avoids flash of marketing for returning users)
  if (!sessionChecked) {
    return (
      <div
        style={{ minHeight: "100vh", backgroundColor: "#061014" }}
        aria-hidden="true"
      />
    );
  }

  return <RiskLensExperience />;
}
