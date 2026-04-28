/**
 * summary:
 *   Login page. Takes tenant slug + email + password, exchanges them for
 *   tokens, then loads the user profile and redirects to the page the
 *   user originally tried to reach.
 */
import { useState } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { authApi } from "../api/auth";
import { useAuthStore } from "../store/auth";
import { ApiException } from "../api/client";

export function LoginPage() {
  const [tenant, setTenant] = useState("acme");
  const [email, setEmail] = useState("admin@acme.test");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const setTokens = useAuthStore((s) => s.setTokens);
  const setMe = useAuthStore((s) => s.setMe);
  const nav = useNavigate();
  const loc = useLocation();
  const from = (loc.state as { from?: { pathname: string } })?.from?.pathname || "/";

  /**
   * summary:
   *   Handle the login form submission.
   * args:
   *   e: form submit event.
   * return:
   *   Promise that resolves once the login flow has finished or failed.
   */
  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const tokens = await authApi.login(tenant, email, password);
      setTokens(tokens.access_token, tokens.refresh_token);
      const me = await authApi.me();
      setMe(me);
      nav(from, { replace: true });
    } catch (e) {
      setError(e instanceof ApiException ? e.payload.message : "Error");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div style={{ maxWidth: 400, margin: "80px auto" }}>
      <div className="card">
        <h2 style={{ marginTop: 0 }}>Sign in to TicketPortal</h2>
        <form onSubmit={submit}>
          {error && <div className="error">{error}</div>}
          <div className="field">
            <label>Tenant</label>
            <input className="input" value={tenant} onChange={(e) => setTenant(e.target.value)} required />
          </div>
          <div className="field">
            <label>Email</label>
            <input className="input" type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
          </div>
          <div className="field">
            <label>Password</label>
            <input className="input" type="password" value={password} onChange={(e) => setPassword(e.target.value)} required />
          </div>
          <button className="btn" disabled={loading} type="submit">
            {loading ? "Please wait..." : "Sign in"}
          </button>
        </form>
      </div>
    </div>
  );
}
