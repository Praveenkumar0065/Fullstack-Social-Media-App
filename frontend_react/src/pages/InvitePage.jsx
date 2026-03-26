import { Link, useSearchParams } from "react-router-dom";

export default function InvitePage() {
  const [searchParams] = useSearchParams();
  const code = String(searchParams.get("code") || "").trim().toUpperCase();

  return (
    <div className="auth-bg auth-shell page-enter">
      <div className="auth-orb auth-orb-teal" />
      <div className="auth-orb auth-orb-amber" />

      <div className="auth-card card-enter space-y-4">
        <h1 className="text-3xl font-bold tracking-tight dark:text-white">You are Invited</h1>
        <p className="page-subtle-text">
          Join Pulsegram and start building your network.
        </p>

        {code ? (
          <p className="rounded-lg bg-teal-50 px-3 py-2 text-sm font-semibold text-teal-700 dark:bg-teal-950/50 dark:text-teal-300">
            Invite code: {code}
          </p>
        ) : (
          <p className="rounded-lg bg-amber-50 px-3 py-2 text-sm text-amber-700 dark:bg-amber-950/50 dark:text-amber-300">
            Invite code missing. You can still create an account.
          </p>
        )}

        <Link
          to={code ? `/signup?code=${encodeURIComponent(code)}` : "/signup"}
          className="brand-button inline-flex w-full items-center justify-center"
        >
          Create Account
        </Link>

        <p className="text-center text-sm text-slate-600 dark:text-slate-400">
          Already have an account? <Link to="/login" className="font-bold text-emerald-700">Sign in</Link>
        </p>
      </div>
    </div>
  );
}
