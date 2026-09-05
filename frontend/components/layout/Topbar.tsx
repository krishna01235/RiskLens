/**
 * Topbar.tsx — App-level topbar with portfolio name, connection status,
 * theme toggle, and user menu (email + logout).
 *
 * Spec §4.5: Portfolio switcher + user menu + ConnectionStatusDot.
 */

"use client";

import { useRouter } from "next/navigation";
import { useAuthStore } from "@/store/auth-store";
import { apiClient } from "@/lib/api-client";
import ThemeToggle from "./ThemeToggle";
import { useState } from "react";

interface TopbarProps {
  /** Width of the sidebar so topbar content is offset correctly */
  sidebarWidth: number;
  /** Whether the WebSocket is connected */
  wsConnected?: boolean;
}

export default function Topbar({ sidebarWidth, wsConnected = true }: TopbarProps) {
  const router = useRouter();
  const user = useAuthStore((s) => s.user);
  const clear = useAuthStore((s) => s.clear);
  const [userMenuOpen, setUserMenuOpen] = useState(false);

  async function handleLogout() {
    try {
      await apiClient.post("/auth/logout");
    } catch {
      // ignore errors — log out locally regardless
    }
    clear();
    router.push("/login");
  }

  return (
    <header
      className="fixed top-0 right-0 z-30 flex items-center justify-between border-b border-brand-border bg-brand-elevated px-4"
      style={{
        left: sidebarWidth,
        height: "var(--topbar-height)",
      }}
    >
      {/* Left: portfolio label */}
      <p className="text-sm text-brand-secondary">
        <span className="text-brand-tertiary mr-1.5">Portfolio</span>
        <span className="font-medium text-brand-primary">My Portfolio</span>
      </p>

      {/* Right: connection dot, theme toggle, user menu */}
      <div className="flex items-center gap-2">
        {/* Connection status dot */}
        <div
          title={wsConnected ? "Live" : "Reconnecting…"}
          className="flex items-center gap-1.5"
          aria-label={wsConnected ? "Market data: live" : "Market data: reconnecting"}
        >
          <span
            className={`h-2 w-2 rounded-full ${
              wsConnected ? "bg-brand-safe" : "bg-brand-tertiary animate-pulse"
            }`}
          />
          <span className="hidden sm:inline text-xs text-brand-tertiary">
            {wsConnected ? "Live" : "Reconnecting…"}
          </span>
        </div>

        <div className="h-4 w-px bg-brand-border" aria-hidden="true" />

        <ThemeToggle />

        <div className="h-4 w-px bg-brand-border" aria-hidden="true" />

        {/* User menu */}
        <div className="relative">
          <button
            onClick={() => setUserMenuOpen((o) => !o)}
            aria-expanded={userMenuOpen}
            aria-haspopup="menu"
            aria-label="User menu"
            className="flex h-8 items-center gap-2 rounded-md px-2 text-brand-secondary hover:text-brand-primary hover:bg-brand-hover transition-colors duration-fast focus-visible:outline focus-visible:outline-2 focus-visible:outline-[var(--color-accent)]"
          >
            <div className="flex h-6 w-6 items-center justify-center rounded-full bg-brand-accent/20 text-xs font-medium text-brand-accent">
              {user?.email?.[0]?.toUpperCase() ?? "U"}
            </div>
            <span className="hidden sm:inline text-xs font-medium max-w-[140px] truncate">
              {user?.email ?? "Account"}
            </span>
            <svg width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden="true">
              <path d="M3 4.5L6 7.5L9 4.5" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </button>

          {userMenuOpen && (
            <>
              {/* Backdrop */}
              <div
                className="fixed inset-0 z-10"
                onClick={() => setUserMenuOpen(false)}
                aria-hidden="true"
              />
              <div
                role="menu"
                className="absolute right-0 top-full mt-1 z-20 w-48 rounded-lg border border-brand-border bg-brand-elevated shadow-lg py-1"
              >
                <p className="px-3 py-2 text-xs text-brand-tertiary truncate border-b border-brand-border mb-1">
                  {user?.email}
                </p>
                <button
                  role="menuitem"
                  onClick={handleLogout}
                  className="w-full text-left px-3 py-2 text-sm text-brand-secondary hover:text-brand-primary hover:bg-brand-hover transition-colors duration-fast focus-visible:outline focus-visible:outline-2 focus-visible:outline-[var(--color-accent)]"
                >
                  Sign out
                </button>
              </div>
            </>
          )}
        </div>
      </div>
    </header>
  );
}
