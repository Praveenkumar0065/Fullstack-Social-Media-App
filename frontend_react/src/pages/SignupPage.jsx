import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useSearchParams } from "react-router-dom";
import { useAuth } from "../state/AuthContext";

export default function SignupPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { signup } = useAuth();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const referralCode = String(searchParams.get("code") || "").trim().toUpperCase();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError("");
    try {
      await signup(name, email, password, referralCode);
      navigate("/onboarding", { replace: true });
    } catch (err) {
      setError(
        err?.response?.data?.detail ||
          (err?.request ? "Cannot reach server. Please check deployment API settings." : "Signup failed.")
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
        <aside className="auth-pane auth-pane-cta">
          <h2 className="auth-pane-cta-title">Already with us?</h2>
          <p className="auth-pane-cta-subtitle">Sign in and continue sharing with your network.</p>
          <Link to="/login" className="auth-secondary-action">SIGN IN</Link>
        </aside>

        <form onSubmit={handleSubmit} className="auth-pane auth-pane-form auth-pane-form-centered">
          <h1 className="auth-pane-title">Create account</h1>
          <p className="auth-pane-subtitle">or create your profile</p>
          <div className="auth-divider" aria-hidden="true" />
          {referralCode ? <p className="auth-inline-note">Invite applied: {referralCode}</p> : null}
          {error && <p className="auth-inline-error">{error}</p>}

          <div className="mt-5 space-y-3">
            <label className="auth-input-row" aria-label="Name">
              <span className="auth-input-icon" aria-hidden="true">N</span>
              <input
                required
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Name"
                className="auth-neo-input"
              />
            </label>
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

          <button type="submit" disabled={loading} className="auth-primary-action auth-primary-action-compact mt-5 disabled:opacity-60">
            {loading ? "CREATING..." : "SIGN UP"}
          </button>
        </form>
      </div>
    </div>
  );
}
