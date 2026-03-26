import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../services/api";

const STEPS = [
  {
    title: "Welcome to Pulsegram",
    description: "Set up your profile and get your first wins in the feed.",
  },
  {
    title: "Find Friends",
    description: "Open Explore, follow a few creators, and personalize your feed.",
  },
  {
    title: "Create Your First Post",
    description: "Share one short update so your profile is active from day one.",
  },
];

export default function OnboardingPage() {
  const navigate = useNavigate();
  const [step, setStep] = useState(0);
  const [busy, setBusy] = useState(false);
  const current = STEPS[step];

  const finishOnboarding = async () => {
    setBusy(true);
    try {
      await api.post("/growth/onboarding/complete");
    } catch {
      // Allow users to continue even if telemetry/save fails.
    } finally {
      setBusy(false);
      navigate("/feed", { replace: true });
    }
  };

  return (
    <section className="page-enter mx-auto max-w-2xl space-y-4 pb-20 pt-8 md:pb-4">
      <div className="page-hero">
        <h1 className="text-3xl font-bold tracking-tight dark:text-white">Quick Start</h1>
        <p className="page-subtle-text">Complete these steps to unlock your personalized experience.</p>
      </div>

      <div className="card-surface p-6">
        <p className="text-xs font-semibold uppercase tracking-wide text-teal-700 dark:text-teal-400">
          Step {step + 1} of {STEPS.length}
        </p>
        <h2 className="mt-2 text-2xl font-bold dark:text-white">{current.title}</h2>
        <p className="mt-2 text-sm text-slate-700 dark:text-slate-300">{current.description}</p>
        <div className="mt-4 h-2 overflow-hidden rounded-full bg-slate-200 dark:bg-slate-700">
          <div className="h-full rounded-full bg-gradient-to-r from-teal-600 to-emerald-500 transition-all" style={{ width: `${((step + 1) / STEPS.length) * 100}%` }} />
        </div>

        <div className="mt-6 flex gap-2">
          {step < STEPS.length - 1 ? (
            <button
              type="button"
              onClick={() => setStep((prev) => prev + 1)}
              className="brand-button"
            >
              Next
            </button>
          ) : (
            <button
              type="button"
              onClick={finishOnboarding}
              disabled={busy}
              className="brand-button disabled:opacity-60"
            >
              {busy ? "Saving..." : "Finish"}
            </button>
          )}

          <button
            type="button"
            onClick={finishOnboarding}
            disabled={busy}
            className="ui-button-secondary"
          >
            Skip
          </button>
        </div>
      </div>
    </section>
  );
}
