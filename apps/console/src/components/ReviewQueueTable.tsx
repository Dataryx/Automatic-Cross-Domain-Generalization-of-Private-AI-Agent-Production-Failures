import { Fragment, useState } from "react";
import { Check, X, AlertTriangle } from "lucide-react";
import type { ReviewDecision, ReviewTicket } from "../types";
import { submitReviewDecision } from "../api/client";

interface ReviewQueueTableProps {
  tickets: ReviewTicket[];
  onUpdated: () => void;
}

const CHECKLIST = [
  "Local immutable evidence preserved",
  "Expected outcome supported",
  "Counterfactual interventions safe and repeated",
  "Graph elements justified",
  "Exact identifiers removed",
  "Source inference assessed",
  "Reconstruction attack assessed",
  "No executable exploit disclosure",
  "Negative controls sufficient",
  "Legal/privacy/security/domain review",
  "Disclosure tier and expiration explicit",
  "Schema, compiler, digest, attestations, signature present",
];

export function ReviewQueueTable({ tickets, onUpdated }: ReviewQueueTableProps) {
  const [busy, setBusy] = useState<string | null>(null);
  const [expanded, setExpanded] = useState<string | null>(null);

  async function decide(id: string, status: ReviewDecision) {
    const reviewer = window.prompt("Reviewer email:", "reviewer@org");
    if (!reviewer) return;
    const notes = window.prompt("Notes:", "") ?? "";
    const checklist_complete = window.confirm(
      "Confirm all 12 release-gate checklist items are complete?"
    );
    setBusy(id);
    try {
      await submitReviewDecision(id, { status, reviewer, notes, checklist_complete });
      onUpdated();
    } catch (err) {
      window.alert(err instanceof Error ? err.message : "Decision failed");
    } finally {
      setBusy(null);
    }
  }

  if (tickets.length === 0) {
    return (
      <div className="card p-12 text-center">
        <p className="text-slate-400">No pending reviews in the queue.</p>
        <p className="mt-2 text-sm text-slate-500">
          Publish a CFI with <code className="font-mono text-accent-glow">cfi-contribute publish</code>
        </p>
      </div>
    );
  }

  return (
    <div className="card overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full text-left text-sm">
          <thead>
            <tr className="border-b border-surface-border bg-surface/50 text-xs uppercase tracking-wider text-slate-500">
              <th className="px-5 py-3 font-medium">Invariant ID</th>
              <th className="px-5 py-3 font-medium">Status</th>
              <th className="px-5 py-3 font-medium">Adversary scores</th>
              <th className="px-5 py-3 font-medium">Updated</th>
              <th className="px-5 py-3 font-medium text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-surface-border">
            {tickets.map((ticket) => (
              <Fragment key={ticket.invariant_id}>
                <tr className="hover:bg-surface-border/20">
                  <td className="px-5 py-4">
                    <button
                      type="button"
                      className="font-mono text-sm text-accent-glow hover:underline"
                      onClick={() =>
                        setExpanded(expanded === ticket.invariant_id ? null : ticket.invariant_id)
                      }
                    >
                      {ticket.invariant_id}
                    </button>
                  </td>
                  <td className="px-5 py-4">
                    <span className="badge-warning">{ticket.status}</span>
                  </td>
                  <td className="px-5 py-4 text-slate-400">
                    {Object.entries(ticket.adversary_scores)
                      .map(([k, v]) => `${k}: ${v.toFixed(2)}`)
                      .join(" · ") || "—"}
                  </td>
                  <td className="px-5 py-4 text-slate-500">
                    {new Date(ticket.updated_at).toLocaleString()}
                  </td>
                  <td className="px-5 py-4">
                    <div className="flex justify-end gap-2">
                      <button
                        type="button"
                        className="btn-primary py-1.5 px-3 text-xs"
                        disabled={busy === ticket.invariant_id}
                        onClick={() => decide(ticket.invariant_id, "approved")}
                      >
                        <Check className="h-3.5 w-3.5" />
                        Approve
                      </button>
                      <button
                        type="button"
                        className="btn-ghost py-1.5 px-3 text-xs"
                        disabled={busy === ticket.invariant_id}
                        onClick={() => decide(ticket.invariant_id, "needs_generalization")}
                      >
                        <AlertTriangle className="h-3.5 w-3.5" />
                        Generalize
                      </button>
                      <button
                        type="button"
                        className="btn-danger py-1.5 px-3 text-xs"
                        disabled={busy === ticket.invariant_id}
                        onClick={() => decide(ticket.invariant_id, "rejected")}
                      >
                        <X className="h-3.5 w-3.5" />
                        Reject
                      </button>
                    </div>
                  </td>
                </tr>
                {expanded === ticket.invariant_id && (
                  <tr>
                    <td colSpan={5} className="bg-surface/40 px-5 py-4">
                      <p className="mb-2 text-xs font-medium uppercase text-slate-500">
                        Release gate checklist
                      </p>
                      <ol className="grid gap-1 text-sm text-slate-400 sm:grid-cols-2">
                        {CHECKLIST.map((item, i) => (
                          <li key={item}>
                            {i + 1}. {item}
                          </li>
                        ))}
                      </ol>
                    </td>
                  </tr>
                )}
              </Fragment>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
