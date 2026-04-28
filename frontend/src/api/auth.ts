/**
 * summary:
 *   Auth API client.
 */
import { api } from "./client";
import type { Me } from "./types";

export const authApi = {
  /**
   * summary:
   *   Exchange credentials for an access + refresh token pair.
   * args:
   *   tenant_slug: tenant short identifier.
   *   email: user email.
   *   password: plaintext password.
   * return:
   *   Promise resolving to an object with access_token and refresh_token.
   */
  login: (tenant_slug: string, email: string, password: string) =>
    api<{ access_token: string; refresh_token: string }>("/auth/login", {
      method: "POST",
      body: { tenant_slug, email, password },
    }),

  /**
   * summary:
   *   Fetch the current user profile and effective permissions.
   * args:
   *   none.
   * return:
   *   Promise resolving to a Me object.
   */
  me: () => api<Me>("/auth/me"),

  /**
   * summary:
   *   Best-effort logout (audit only on the backend).
   * args:
   *   none.
   * return:
   *   Promise resolving to { ok: true }.
   */
  logout: () => api<{ ok: boolean }>("/auth/logout", { method: "POST" }),
};
