/**
 * auth-store.ts — Zustand store for authentication state.
 *
 * Design decisions:
 * - accessToken is kept in memory only (not localStorage) to mitigate XSS.
 *   The httpOnly refresh cookie re-issues a new access token on every reload
 *   via the silent-refresh path in api-client.ts.
 * - user is persisted to sessionStorage for a better reload UX (email in nav
 *   bar doesn't blink). It contains no secret material.
 */

import { create } from "zustand";
import { persist, createJSONStorage } from "zustand/middleware";

export interface AuthUser {
  id: string;
  email: string;
  role: string;
}

interface AuthState {
  /** Bearer token — in memory only, lost on tab close / reload. */
  accessToken: string | null;
  /** Lightweight user info — persisted to sessionStorage for UX. */
  user: AuthUser | null;

  setAccessToken: (token: string) => void;
  setUser: (user: AuthUser) => void;
  clear: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      accessToken: null,
      user: null,

      setAccessToken: (token) => set({ accessToken: token }),
      setUser: (user) => set({ user }),
      clear: () => set({ accessToken: null, user: null }),
    }),
    {
      name: "risklens-auth",
      storage: createJSONStorage(() => sessionStorage),
      // Only persist user info — never the access token
      partialize: (state) => ({ user: state.user }),
    }
  )
);
