import { CheckCircle2, Loader2, XCircle } from "lucide-react";
import type { ServiceHealth } from "../types";

interface ServiceHealthGridProps {
  services: { name: string; health: ServiceHealth | null; error?: string }[];
}

export function ServiceHealthGrid({ services }: ServiceHealthGridProps) {
  return (
    <div className="grid gap-4 sm:grid-cols-3">
      {services.map(({ name, health, error }) => {
        const ok = health?.status === "ok";
        return (
          <div key={name} className="card flex items-center gap-4 p-4">
            {health ? (
              ok ? (
                <CheckCircle2 className="h-8 w-8 shrink-0 text-success" />
              ) : (
                <XCircle className="h-8 w-8 shrink-0 text-danger" />
              )
            ) : (
              <Loader2 className="h-8 w-8 shrink-0 animate-spin text-slate-500" />
            )}
            <div className="min-w-0">
              <p className="font-medium capitalize text-white">{name}</p>
              <p className="truncate text-sm text-slate-400">
                {error ?? (health ? `${health.status} · ready=${health.ready ?? "—"}` : "Checking…")}
              </p>
            </div>
            <span className={`ml-auto badge ${ok ? "badge-success" : "badge-danger"}`}>
              {health?.status ?? "unknown"}
            </span>
          </div>
        );
      })}
    </div>
  );
}
