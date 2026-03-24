import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../state/AuthContext";

export default function SignupPage() {
  const navigate = useNavigate();
  const { signup } = useAuth();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError("");
    try {
      await signup(name, email, password);
      navigate("/feed", { replace: true });
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

      <form onSubmit={handleSubmit} className="auth-card card-enter">
        <h1 className="text-3xl font-bold tracking-tight">Create Account</h1>
        <p className="mt-1 text-sm text-slate-600">Join the network and start sharing instantly.</p>
        {error && <p className="mt-3 rounded-lg bg-rose-100 px-3 py-2 text-sm text-rose-700">{error}</p>}

        <div className="mt-4 space-y-3">
          <input
            required
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Name"
            className="field-input"
          />
          <input
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="Email"
            className="field-input"
          />
          <input
            type="password"
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="Password"
            className="field-input"
          />
        </div>

        <button
          type="submit"
          disabled={loading}
          className="brand-button mt-4 w-full disabled:opacity-60"
        >
          {loading ? "Creating..." : "Create Account"}
        </button>

        <p className="mt-4 text-center text-sm text-slate-600">
          Already have an account? <Link to="/login" className="font-bold text-emerald-700">Sign in</Link>
        </p>
      </form>
    </div>
  );
}
