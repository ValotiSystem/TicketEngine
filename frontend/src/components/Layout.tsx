/**
 * summary:
 *   Authenticated app shell: top bar with navigation links and a logout
 *   button, plus the routed content area.
 */
import { Link, Outlet, useNavigate } from "react-router-dom";
import { useAuthStore } from "../store/auth";
import { authApi } from "../api/auth";

export function Layout() {
  const me = useAuthStore((s) => s.me);
  const clear = useAuthStore((s) => s.clear);
  const hasPermission = useAuthStore((s) => s.hasPermission);
  const nav = useNavigate();

  /**
   * summary:
   *   Best-effort logout: notify the backend, drop local tokens, redirect
   *   to /login.
   * args:
   *   none.
   * return:
   *   Promise that resolves once navigation has been requested.
   */
  async function logout() {
    try { await authApi.logout(); } catch { /* best-effort */ }
    clear();
    nav("/login");
  }

  return (
    <div className="app-shell">
      <header className="topbar">
        <Link to="/" className="brand">TicketPortal</Link>
        <Link to="/tickets">Tickets</Link>
        <Link to="/tickets/new">New</Link>
        {hasPermission("admin.config") && <Link to="/admin">Admin</Link>}
        <span style={{ marginLeft: "auto" }}>{me?.email}</span>
        <button className="btn btn-secondary" onClick={logout}>Sign out</button>
      </header>
      <main className="main">
        <Outlet />
      </main>
    </div>
  );
}
