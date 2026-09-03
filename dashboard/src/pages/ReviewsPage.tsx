import { useCallback, useEffect, useState } from "react";
import { getReviewQueue } from "../api/client";
import type { ReviewTicket } from "../types";
import { ReviewQueueTable } from "../components/ReviewQueueTable";

export function ReviewsPage() {
  const [tickets, setTickets] = useState<ReviewTicket[]>([]);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      setError(null);
      setTickets(await getReviewQueue());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load review queue");
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-semibold text-white">Human review queue</h2>
        <p className="mt-1 text-sm text-slate-400">
          Approve, reject, or request generalization before lifecycle promotion. Complete all 12
          release-gate items before approval.
        </p>
      </div>
      {error && <p className="text-sm text-danger">{error}</p>}
      <ReviewQueueTable tickets={tickets} onUpdated={refresh} />
    </div>
  );
}
