/**
 * AppShell.tsx — Authenticated layout wrapper.
 *
 * Combines Sidebar + Topbar and provides the scrollable content area with
 * correct left-offset depending on sidebar collapsed state.
 *
 * Auth pages (login / register / onboarding) do NOT use AppShell — they
 * render their own full-screen layouts.
 */

"use client";

import { ReactNode, useState } from "react";
import Sidebar from "./Sidebar";
import Topbar from "./Topbar";

interface AppShellProps {
  children: ReactNode;
  wsConnected?: boolean;
}

const SIDEBAR_FULL = 240;
const SIDEBAR_COLLAPSED = 64;

export default function AppShell({ children, wsConnected = true }: AppShellProps) {
  const [collapsed, setCollapsed] = useState(false);

  const sw = collapsed ? SIDEBAR_COLLAPSED : SIDEBAR_FULL;

  return (
    <div className="min-h-screen bg-brand-bg">
      <Sidebar collapsed={collapsed} onToggle={() => setCollapsed((c) => !c)} />
      <Topbar sidebarWidth={sw} wsConnected={wsConnected} />

      {/* Content area — offset by sidebar (desktop) and topbar */}
      <main
        className="transition-[padding-left] duration-normal ease-out-expo"
        style={{
          paddingTop: "var(--topbar-height)",
          // On desktop we offset by sidebar width; mobile uses full width (sidebar is bottom nav)
        }}
      >
        <div
          className="md:ml-0"
          style={{ marginLeft: typeof window !== "undefined" && window.innerWidth >= 768 ? sw : 0 }}
        >
          {/* On mobile: extra bottom padding so content clears the bottom nav */}
          <div className="pb-16 md:pb-0 px-4 md:px-6 py-6 md:py-8 max-w-[1440px] mx-auto">
            {children}
          </div>
        </div>
      </main>
    </div>
  );
}
