import { useCallback, useEffect, useState } from "react";
import { FileCheck, Layers, ShieldAlert, Users } from "lucide-react";
import { loadDashboardSnapshot } from "../api/client";
import type { DashboardSnapshot } from "../api/client";
import { ServiceHealthGrid } from "../components/ServiceHealthGrid";
import { StatCard } from "../components/StatCard";
import { PrivacyGauge } from "../components/PrivacyGauge";

const REFRESH_MS = 30_000;

export function OverviewPage() {
  const [data, setData] = useState<DashboardSnapshot | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    try {
      setError(null);
      const snapshot = await loadDashboardSnapshot();
      setData(snapshot);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load dashboard");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
    const timer = window.setInterval(refresh, REFRESH_MS);
    return () => window.clearInterval(timer);
  }, [refresh]);

  if (loading && !data) {
    return <p className="text-slate-400">Loading federation status…</p>;
  }

  if (error && !data) {
    return (
      <div className="card border-danger/30 bg-danger/10 p-6 text-danger">
        <p className="font-medium">Cannot reach CFI-Fed services</p>
        <p className="mt-2 text-sm opacity-90">{error}</p>
        <p className="mt-4 text-sm text-slate-400">
          Start the stack: <code className="font-mono">docker compose up -d</code> then{" "}
          <code className="font-mono">npm run dev</code> in <code className="font-mono">dashboard/</code>
        </p>
        <button type="button" className="btn-primary mt-4" onClick={refresh}>
          Retry
        </button>
      </div>
    );
  }

  if (!data) return null;

  return (
    <div className="space-y-8">
      <ServiceHealthGrid
        services={[
          { name: "registry", health: data.registry },
          { name: "coordinator", health: data.coordinator },
          { name: "aggregator", health: data.aggregator },
        ]}
      />

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard
          label="Registered CFIs"
          value={data.stats.registered_cfis}
          icon={<Layers className="h-5 w-5" />}
        />
        <StatCard
          label="Pending reviews"
          value={data.stats.pending_reviews}
          hint="Requires human authorization"
          icon={<FileCheck className="h-5 w-5" />}
        />
        <StatCard
          label="Active CFIs"
          value={data.stats.active_cfis}
          icon={<ShieldAlert className="h-5 w-5" />}
        />
        <StatCard
          label="Cohort manifests"
          value={data.stats.cohort_manifests}
          icon={<Users className="h-5 w-5" />}
        />
      </div>

      <PrivacyGauge accountant={data.accountant} />

      {error && (
        <p className="text-sm text-warning">Last refresh failed: {error}</p>
      )}
    </div>
  );
}
