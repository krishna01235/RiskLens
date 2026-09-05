/**
 * ThemeToggle.tsx — Dark / light mode switch.
 *
 * Reads the current theme from localStorage and toggles the `.light`
 * class on <html>. Dark is the default per §4 ("financial-terminal convention").
 */

"use client";

import { useEffect, useState } from "react";

export default function ThemeToggle() {
  const [isDark, setIsDark] = useState(true);

  // Sync with localStorage on mount
  useEffect(() => {
    const saved = localStorage.getItem("rl-theme");
    if (saved === "light") {
      document.documentElement.classList.add("light");
      setIsDark(false);
    }
  }, []);

  function toggle() {
    const next = isDark;
    if (next) {
      // switching to light
      document.documentElement.classList.add("light");
      localStorage.setItem("rl-theme", "light");
    } else {
      document.documentElement.classList.remove("light");
      localStorage.setItem("rl-theme", "dark");
    }
    setIsDark(!next);
  }

  return (
    <button
      onClick={toggle}
      aria-label={isDark ? "Switch to light mode" : "Switch to dark mode"}
      title={isDark ? "Light mode" : "Dark mode"}
      className="flex h-8 w-8 items-center justify-center rounded-md text-brand-tertiary hover:text-brand-primary hover:bg-brand-hover transition-colors duration-fast focus-visible:outline focus-visible:outline-2 focus-visible:outline-[var(--color-accent)]"
    >
      {isDark ? (
        // Sun icon
        <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
          <circle cx="8" cy="8" r="3" stroke="currentColor" strokeWidth="1.5" />
          <path d="M8 1v1.5M8 13.5V15M1 8h1.5M13.5 8H15M3.05 3.05l1.06 1.06M11.89 11.89l1.06 1.06M11.89 4.11l1.06-1.06M3.05 12.95l1.06-1.06" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
        </svg>
      ) : (
        // Moon icon
        <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
          <path d="M13.5 9.5A6 6 0 016.5 2.5a6 6 0 100 11 6 6 0 007-4z" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      )}
    </button>
  );
}
