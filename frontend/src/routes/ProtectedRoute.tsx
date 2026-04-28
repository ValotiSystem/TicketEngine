/**
 * summary:
 *   Route guard that redirects unauthenticated users to /login and lazily
 *   loads the current user profile when missing.
 */
import { useEffect } from "react";
import { Navigate, useLocation } from "react-router-dom";
import { useAuthStore } from "../store/auth";
import { authApi } from "../api/auth";

export function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const token = useAuthStore((s) => s.accessToken);
  const me = useAuthStore((s) => s.me);
  const setMe = useAuthStore((s) => s.setMe);
  const location = useLocation();

  useEffect(() => {
    if (token && !me) {
      authApi.me().then(setMe).catch(() => {});
    }
  }, [token, me, setMe]);

  if (!token) return <Navigate to="/login" state={{ from: location }} replace />;
  return <>{children}</>;
}
