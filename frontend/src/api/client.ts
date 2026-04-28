/**
 * summary:
 *   Centralized HTTP client.
 *
 *   CRITIQUE: a single client = a single policy for auth, errors, refresh
 *   tokens and request_id. Never call fetch directly from a component:
 *   it creates instant drift (who sets the bearer? who handles 401? who
 *   talks to the backend?).
 */
import { useAuthStore } from "../store/auth";
import type { ApiError } from "./types";

const BASE = (import.meta.env.VITE_API_BASE as string) || "/api/v1";

export class ApiException extends Error {
  status: number;
  payload: ApiError;
  constructor(status: number, payload: ApiError) {
    super(payload.message);
    this.status = status;
    this.payload = payload;
  }
}

interface RequestOpts {
  method?: string;
  body?: unknown;
  query?: Record<string, string | number | undefined>;
}

/**
 * summary:
 *   Perform an authenticated JSON request and unwrap the standard
 *   `data` envelope. Transparently refreshes the access token once on
 *   401 before giving up.
 * args:
 *   path: API path under the BASE prefix (e.g. "/tickets").
 *   opts: optional request options (method, JSON body, query).
 * return:
 *   The unwrapped response payload typed as T.
 */
export async function api<T>(path: string, opts: RequestOpts = {}): Promise<T> {
  const { method = "GET", body, query } = opts;
  const url = new URL(BASE + path, window.location.origin);
  if (query) {
    for (const [k, v] of Object.entries(query)) {
      if (v !== undefined && v !== null && v !== "") url.searchParams.set(k, String(v));
    }
  }

  const headers: Record<string, string> = { "Content-Type": "application/json" };
  const token = useAuthStore.getState().accessToken;
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const resp = await fetch(url.toString(), {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  });

  if (resp.status === 401) {
    // Single refresh attempt, then force logout.
    const refreshed = await tryRefresh();
    if (refreshed) return api<T>(path, opts);
    useAuthStore.getState().clear();
    throw new ApiException(401, { code: "AUTH_REQUIRED", message: "Session expired" });
  }

  const text = await resp.text();
  const data = text ? JSON.parse(text) : {};

  if (!resp.ok) {
    const err: ApiError = data.error || { code: "INTERNAL_ERROR", message: "Error" };
    throw new ApiException(resp.status, err);
  }

  return data.data as T;
}

let refreshing: Promise<boolean> | null = null;

/**
 * summary:
 *   Attempt to obtain a fresh access token using the stored refresh
 *   token. Concurrent callers share the same in-flight promise.
 * args:
 *   none.
 * return:
 *   True when a new access token was stored, false otherwise.
 */
async function tryRefresh(): Promise<boolean> {
  if (refreshing) return refreshing;
  refreshing = (async () => {
    const refresh = useAuthStore.getState().refreshToken;
    if (!refresh) return false;
    try {
      const resp = await fetch(BASE + "/auth/refresh", {
        method: "POST",
        headers: { Authorization: `Bearer ${refresh}` },
      });
      if (!resp.ok) return false;
      const data = await resp.json();
      useAuthStore.getState().setAccess(data.data.access_token);
      return true;
    } catch {
      return false;
    } finally {
      refreshing = null;
    }
  })();
  return refreshing;
}
