/**
 * api-client.ts — Thin fetch wrapper with Bearer token attachment and
 * silent refresh-on-401 interceptor.
 *
 * Usage:
 *   import { apiClient } from "@/lib/api-client";
 *   const data = await apiClient.get("/portfolios/123");
 *   const result = await apiClient.post("/simulations", { portfolio_id: "..." });
 */

import { useAuthStore } from "@/store/auth-store";

const BASE_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

// ── Token refresh ──────────────────────────────────────────────────────────

/** Ongoing refresh promise — prevents concurrent refresh races. */
let refreshPromise: Promise<string | null> | null = null;

async function silentRefresh(): Promise<string | null> {
  if (refreshPromise) return refreshPromise;

  refreshPromise = (async () => {
    try {
      const resp = await fetch(`${BASE_URL}/auth/refresh`, {
        method: "POST",
        credentials: "include", // sends the httpOnly refresh cookie
      });

      if (!resp.ok) {
        // Refresh failed — clear auth state and signal the interceptor
        useAuthStore.getState().clear();
        return null;
      }

      const data: { access_token: string } = await resp.json();
      useAuthStore.getState().setAccessToken(data.access_token);
      return data.access_token;
    } catch {
      useAuthStore.getState().clear();
      return null;
    } finally {
      refreshPromise = null;
    }
  })();

  return refreshPromise;
}

// ── Core fetch wrapper ─────────────────────────────────────────────────────

type HttpMethod = "GET" | "POST" | "PUT" | "PATCH" | "DELETE";

interface RequestOptions {
  /** Additional headers to merge. */
  headers?: Record<string, string>;
  /** Arbitrary options forwarded to fetch (e.g. signal for abort). */
  fetchOptions?: RequestInit;
}

async function request<T>(
  method: HttpMethod,
  path: string,
  body?: unknown,
  options: RequestOptions = {}
): Promise<T> {
  const doRequest = async (token: string | null): Promise<Response> => {
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
      ...options.headers,
    };
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }

    return fetch(`${BASE_URL}${path}`, {
      method,
      credentials: "include",
      headers,
      body: body !== undefined ? JSON.stringify(body) : undefined,
      ...options.fetchOptions,
    });
  };

  const token = useAuthStore.getState().accessToken;
  let resp = await doRequest(token);

  // Silent refresh on 401 — try once
  if (resp.status === 401) {
    const newToken = await silentRefresh();
    if (newToken) {
      resp = await doRequest(newToken);
    }
  }

  // After second attempt, if still 401 → redirect to login
  if (resp.status === 401) {
    if (typeof window !== "undefined") {
      window.location.href = "/login";
    }
    throw new Error("Unauthorized");
  }

  if (!resp.ok) {
    let detail = `HTTP ${resp.status}`;
    try {
      const err = await resp.json();
      detail = err?.detail ?? detail;
    } catch {
      /* ignore parse errors */
    }
    throw new Error(detail);
  }

  // 204 No Content — return empty object cast as T
  if (resp.status === 204) return {} as T;

  return resp.json() as Promise<T>;
}

// ── Public API ─────────────────────────────────────────────────────────────

export const apiClient = {
  get: <T>(path: string, opts?: RequestOptions) =>
    request<T>("GET", path, undefined, opts),

  post: <T>(path: string, body?: unknown, opts?: RequestOptions) =>
    request<T>("POST", path, body, opts),

  put: <T>(path: string, body?: unknown, opts?: RequestOptions) =>
    request<T>("PUT", path, body, opts),

  patch: <T>(path: string, body?: unknown, opts?: RequestOptions) =>
    request<T>("PATCH", path, body, opts),

  delete: <T>(path: string, opts?: RequestOptions) =>
    request<T>("DELETE", path, undefined, opts),
};

// ── Auth-specific helpers ──────────────────────────────────────────────────

export interface TokenResponse {
  access_token: string;
  token_type: string;
}

export async function authRegister(
  email: string,
  password: string
): Promise<TokenResponse> {
  const resp = await fetch(`${BASE_URL}/auth/register`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  if (!resp.ok) {
    const err = await resp.json().catch(() => ({}));
    throw Object.assign(new Error(err?.detail ?? "Registration failed"), {
      status: resp.status,
    });
  }
  return resp.json();
}

export async function authLogin(
  email: string,
  password: string
): Promise<TokenResponse> {
  const resp = await fetch(`${BASE_URL}/auth/login`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  if (!resp.ok) {
    const err = await resp.json().catch(() => ({}));
    throw Object.assign(new Error(err?.detail ?? "Login failed"), {
      status: resp.status,
    });
  }
  return resp.json();
}

export async function authLogout(): Promise<void> {
  await fetch(`${BASE_URL}/auth/logout`, {
    method: "POST",
    credentials: "include",
  });
  useAuthStore.getState().clear();
}
