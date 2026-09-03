import { useEffect, useState } from "react";
import { getAuditExport, getAuditStatus } from "../api/client";
import type { AuditEvent, AuditStatus } from "../types";
import { AuditTable } from "../components/AuditTable";

export function AuditPage() {
  const [events, setEvents] = useState<AuditEvent[]>([]);
  const [status, setStatus] = useState<AuditStatus | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([getAuditExport(), getAuditStatus()])
      .then(([audit, auditStatus]) => {
        setEvents(audit.events ?? []);
        setStatus(auditStatus);
      })
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load audit log"));
  }, []);

  if (error) {
    return <p className="text-danger">{error}</p>;
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h2 className="text-xl font-semibold text-white">Governance audit log</h2>
          <p className="mt-1 text-sm text-slate-400">
            Registry governance actions. Not a substitute for tamper-evident external logging.
          </p>
        </div>
        {status && (
          <div className="card px-4 py-2 text-sm">
            <span className="text-slate-500">Pending export: </span>
            <span className="font-mono text-white">{status.pending_export ?? 0}</span>
          </div>
        )}
      </div>
      <AuditTable events={events} />
    </div>
  );
}
