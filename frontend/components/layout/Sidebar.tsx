/**
 * Sidebar.tsx — Fixed 240 px sidebar with collapsible icon rail (64 px).
 *
 * Spec (§4.5):
 * - Icon + label nav items
 * - Active item: 2 px left accent bar + subtly elevated background
 * - Under 768 px: collapses to a bottom tab bar (via CSS media query)
 */

"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";

interface NavItem {
  label: string;
  href: string;
  icon: React.ReactNode;
}

const NAV_ITEMS: NavItem[] = [
  {
    label: "Dashboard",
    href: "/dashboard",
    icon: (
      <svg width="18" height="18" viewBox="0 0 18 18" fill="none" aria-hidden="true">
        <rect x="2" y="2" width="6" height="6" rx="1.5" stroke="currentColor" strokeWidth="1.4" />
        <rect x="10" y="2" width="6" height="6" rx="1.5" stroke="currentColor" strokeWidth="1.4" />
        <rect x="2" y="10" width="6" height="6" rx="1.5" stroke="currentColor" strokeWidth="1.4" />
        <rect x="10" y="10" width="6" height="6" rx="1.5" stroke="currentColor" strokeWidth="1.4" />
      </svg>
    ),
  },
  {
    label: "Simulate",
    href: "/dashboard/simulate",
    icon: (
      <svg width="18" height="18" viewBox="0 0 18 18" fill="none" aria-hidden="true">
        <path d="M2 14 L5 9 L8 11 L11 6 L14 8 L16 4" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round" />
        <circle cx="14" cy="14" r="2.5" stroke="currentColor" strokeWidth="1.4" />
        <path d="M14 12v4M12 14h4" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" />
      </svg>
    ),
  },
  {
    label: "Replay",
    href: "/dashboard/replay",
    icon: (
      <svg width="18" height="18" viewBox="0 0 18 18" fill="none" aria-hidden="true">
        <path d="M3 9a6 6 0 106-6H7" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" />
        <path d="M7 6L4 9l3 3" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    ),
  },
];

interface SidebarProps {
  collapsed: boolean;
  onToggle: () => void;
}

export default function Sidebar({ collapsed, onToggle }: SidebarProps) {
  const pathname = usePathname();

  function isActive(href: string) {
    if (href === "/dashboard") return pathname === "/dashboard";
    return pathname.startsWith(href);
  }

  return (
    <>
      {/* ── Desktop sidebar ───────────────────────────────────────────── */}
      <aside
        style={{ width: collapsed ? "var(--sidebar-collapsed-width)" : "var(--sidebar-width)" }}
        className="hidden md:flex fixed top-0 left-0 h-full flex-col border-r border-brand-border bg-brand-elevated z-40 transition-[width] duration-normal ease-out-expo overflow-hidden"
        aria-label="Primary navigation"
      >
        {/* Logo */}
        <div className="flex h-[var(--topbar-height)] items-center gap-3 px-4 border-b border-brand-border shrink-0">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-brand-accent/10 shrink-0">
            <svg width="18" height="18" viewBox="0 0 18 18" fill="none" aria-hidden="true">
              <path d="M3 14 L6.5 8 L10 11 L13.5 5 L16 7" stroke="var(--color-accent)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </div>
          {!collapsed && (
            <span className="font-semibold text-brand-primary text-sm tracking-tight whitespace-nowrap">
              RiskLens
            </span>
          )}
        </div>

        {/* Nav links */}
        <nav className="flex-1 py-3 space-y-0.5 px-2">
          {NAV_ITEMS.map((item) => {
            const active = isActive(item.href);
            return (
              <Link
                key={item.href}
                href={item.href}
                title={collapsed ? item.label : undefined}
                aria-current={active ? "page" : undefined}
                className={`relative flex items-center gap-3 rounded-md px-3 py-2 text-sm transition-colors duration-fast focus-visible:outline focus-visible:outline-2 focus-visible:outline-[var(--color-accent)] ${
                  active
                    ? "bg-brand-hover text-brand-primary"
                    : "text-brand-secondary hover:text-brand-primary hover:bg-brand-hover"
                }`}
              >
                {/* Active indicator bar */}
                {active && (
                  <span
                    aria-hidden="true"
                    className="absolute left-0 top-1 bottom-1 w-0.5 rounded-full bg-brand-accent"
                  />
                )}
                <span className="shrink-0">{item.icon}</span>
                {!collapsed && (
                  <span className="whitespace-nowrap">{item.label}</span>
                )}
              </Link>
            );
          })}
        </nav>

        {/* Collapse toggle */}
        <div className="border-t border-brand-border p-2">
          <button
            onClick={onToggle}
            aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
            title={collapsed ? "Expand" : "Collapse"}
            className="flex w-full items-center justify-center rounded-md p-2 text-brand-tertiary hover:text-brand-primary hover:bg-brand-hover transition-colors duration-fast focus-visible:outline focus-visible:outline-2 focus-visible:outline-[var(--color-accent)]"
          >
            <svg
              width="16"
              height="16"
              viewBox="0 0 16 16"
              fill="none"
              aria-hidden="true"
              className={`transition-transform duration-normal ${collapsed ? "rotate-180" : ""}`}
            >
              <path d="M10 4L6 8l4 4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </button>
        </div>
      </aside>

      {/* ── Mobile bottom nav bar ─────────────────────────────────────── */}
      <nav
        className="md:hidden fixed bottom-0 left-0 right-0 z-40 flex items-center justify-around border-t border-brand-border bg-brand-elevated h-14 px-2"
        aria-label="Primary navigation"
      >
        {NAV_ITEMS.map((item) => {
          const active = isActive(item.href);
          return (
            <Link
              key={item.href}
              href={item.href}
              aria-current={active ? "page" : undefined}
              className={`flex flex-col items-center gap-0.5 px-4 py-1 rounded-md text-xs transition-colors duration-fast focus-visible:outline focus-visible:outline-2 focus-visible:outline-[var(--color-accent)] ${
                active
                  ? "text-brand-accent"
                  : "text-brand-tertiary hover:text-brand-secondary"
              }`}
            >
              {item.icon}
              <span>{item.label}</span>
            </Link>
          );
        })}
      </nav>
    </>
  );
}
