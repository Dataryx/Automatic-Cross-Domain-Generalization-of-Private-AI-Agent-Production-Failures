import { useEffect, useState } from "react";
import { getPrivacyAccountant } from "../api/client";
import type { PrivacyAccountant } from "../types";
import { PrivacyGauge } from "../components/PrivacyGauge";

export function PrivacyPage() {
  const [accountant, setAccountant] = useState<PrivacyAccountant | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getPrivacyAccountant()
      .then(setAccountant)
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load"));
  }, []);

  if (error) {
    return <p className="text-danger">{error}</p>;
  }

  if (!accountant) {
    return <p className="text-slate-400">Loading privacy accountant…</p>;
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-semibold text-white">Privacy budget</h2>
        <p className="mt-1 text-sm text-slate-400">
          Aggregator differential privacy accountant snapshot. Monitor remaining ε before cohort
          releases.
        </p>
      </div>
      <PrivacyGauge accountant={accountant} />
      <div className="card p-5 text-sm text-slate-400">
        <p className="font-medium text-slate-300">Assumptions</p>
        <ul className="mt-2 list-inside list-disc space-y-1">
          <li>ε budget is consortium-wide, not per-tenant.</li>
          <li>Clipped contributions only; raw incidents never reach aggregator.</li>
          <li>Statistical guarantees require honest minimum cohort k.</li>
        </ul>
      </div>
    </div>
  );
}
