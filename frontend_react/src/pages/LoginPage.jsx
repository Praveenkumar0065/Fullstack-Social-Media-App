import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../state/AuthContext";

export default function LoginPage() {
  const navigate = useNavigate();
  const { login } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError("");
    try {
      await login(email, password);
      navigate("/feed", { replace: true });
    } catch (err) {
      setError(
        err?.response?.data?.detail ||
          (err?.request ? "Cannot reach server. Please check deployment API settings." : "Login failed.")
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-bg auth-shell page-enter">
      <div className="auth-orb auth-orb-teal" />
      <div className="auth-orb auth-orb-amber" />

      <div className="auth-split-card card-enter">
        <form onSubmit={handleSubmit} className="auth-pane auth-pane-form auth-pane-form-centered">
          <h1 className="auth-pane-title">Sign in</h1>
          <p className="auth-pane-subtitle">or use your account</p>
          <div className="auth-divider" aria-hidden="true" />
          {error && <p className="auth-inline-error">{error}</p>}

          <div className="mt-5 space-y-3">
            <label className="auth-input-row" aria-label="E-mail">
              <span className="auth-input-icon" aria-hidden="true">@</span>
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="E-mail"
                className="auth-neo-input"
              />
            </label>
            <label className="auth-input-row" aria-label="Password">
              <span className="auth-input-icon" aria-hidden="true">*</span>
              <input
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Password"
                className="auth-neo-input"
              />
            </label>
          </div>

          <p className="mt-3 text-center text-xs text-slate-400">Forgot your password?</p>

          <button type="submit" disabled={loading} className="auth-primary-action auth-primary-action-compact mt-3 disabled:opacity-60">
            {loading ? "SIGNING IN..." : "SIGN IN"}
          </button>
        </form>

        <aside className="auth-pane auth-pane-cta">
          <h2 className="auth-pane-cta-title">New here ?</h2>
          <p className="auth-pane-cta-subtitle">Enter your personal details and start your journey with us.</p>
          <Link to="/signup" className="auth-secondary-action">SIGN UP</Link>
        </aside>
      </div>
    </div>
  );
}
