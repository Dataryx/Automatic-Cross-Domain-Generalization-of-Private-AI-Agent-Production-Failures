import type { AuditEvent } from "../types";

interface AuditTableProps {
  events: AuditEvent[];
}

export function AuditTable({ events }: AuditTableProps) {
  if (events.length === 0) {
    return (
      <div className="card p-12 text-center text-slate-400">
        No audit events recorded yet.
      </div>
    );
  }

  const rows = [...events].reverse().slice(0, 100);

  return (
    <div className="card overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full text-left text-sm">
          <thead>
            <tr className="border-b border-surface-border bg-surface/50 text-xs uppercase tracking-wider text-slate-500">
              <th className="px-5 py-3 font-medium">Time</th>
              <th className="px-5 py-3 font-medium">Actor</th>
              <th className="px-5 py-3 font-medium">Action</th>
              <th className="px-5 py-3 font-medium">Resource</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-surface-border">
            {rows.map((event, idx) => (
              <tr key={`${event.resource_id}-${idx}`} className="hover:bg-surface-border/20">
                <td className="px-5 py-3 font-mono text-xs text-slate-500">
                  {event.timestamp ? new Date(event.timestamp).toLocaleString() : "—"}
                </td>
                <td className="px-5 py-3 text-slate-300">{event.actor ?? "—"}</td>
                <td className="px-5 py-3">
                  <span className="badge-neutral">{event.action ?? "—"}</span>
                </td>
                <td className="px-5 py-3 font-mono text-xs text-accent-glow">
                  {event.resource_id ?? "—"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
