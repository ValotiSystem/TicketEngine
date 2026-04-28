/**
 * summary:
 *   Persisted auth store (zustand).
 *
 *   CRITIQUE: tokens are kept in localStorage for simplicity. This is
 *   XSS-sensitive. In high-trust enterprise contexts consider httpOnly
 *   cookies + CSRF, or sessionStorage with strict CSP. The right choice
 *   depends on the threat model.
 */
import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { Me } from "../api/types";

interface AuthState {
  accessToken: string | null;
  refreshToken: string | null;
  me: Me | null;
  setTokens: (a: string, r: string) => void;
  setAccess: (a: string) => void;
  setMe: (m: Me) => void;
  clear: () => void;
  hasPermission: (code: string) => boolean;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      accessToken: null,
      refreshToken: null,
      me: null,
      setTokens: (a, r) => set({ accessToken: a, refreshToken: r }),
      setAccess: (a) => set({ accessToken: a }),
      setMe: (m) => set({ me: m }),
      clear: () => set({ accessToken: null, refreshToken: null, me: null }),
      hasPermission: (code) => !!get().me?.permissions.includes(code),
    }),
    { name: "tp-auth" }
  )
);
