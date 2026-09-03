/** HTTP client for registry, coordinator, and aggregator. Dev server proxies /api/* in vite.config.ts. */
import type {
  AuditExport,
  AuditStatus,
  PrivacyAccountant,
  RegistryStats,
  ReviewDecision,
  ReviewTicket,
  ServiceHealth,
} from "../types";

const REGISTRY = "/api/registry";
const COORDINATOR = "/api/coordinator";
const AGGREGATOR = "/api/aggregator";

async function fetchJson<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, init);
  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || `HTTP ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export async function getRegistryHealth(): Promise<ServiceHealth> {
  return fetchJson(`${REGISTRY}/health`);
}

export async function getCoordinatorHealth(): Promise<ServiceHealth> {
  return fetchJson(`${COORDINATOR}/health`);
}

export async function getAggregatorHealth(): Promise<ServiceHealth> {
  return fetchJson(`${AGGREGATOR}/health`);
}

export async function getRegistryStats(): Promise<RegistryStats> {
  return fetchJson(`${REGISTRY}/stats`);
}

export async function getPrivacyAccountant(): Promise<PrivacyAccountant> {
  return fetchJson(`${AGGREGATOR}/accountant`);
}

export async function getReviewQueue(): Promise<ReviewTicket[]> {
  return fetchJson(`${REGISTRY}/review/queue`);
}

export async function getReviewTicket(id: string): Promise<ReviewTicket> {
  return fetchJson(`${REGISTRY}/review/${encodeURIComponent(id)}`);
}

export async function submitReviewDecision(
  id: string,
  body: {
    status: ReviewDecision;
    reviewer: string;
    notes: string;
    checklist_complete: boolean;
  }
): Promise<ReviewTicket> {
  return fetchJson(`${REGISTRY}/review/${encodeURIComponent(id)}/decision`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export async function getAuditExport(): Promise<AuditExport> {
  return fetchJson(`${REGISTRY}/audit/export`);
}

export async function getAuditStatus(): Promise<AuditStatus> {
  return fetchJson(`${REGISTRY}/audit/status`);
}

export interface DashboardSnapshot {
  registry: ServiceHealth;
  coordinator: ServiceHealth;
  aggregator: ServiceHealth;
  stats: RegistryStats;
  accountant: PrivacyAccountant;
  reviews: ReviewTicket[];
  auditStatus: AuditStatus;
}

export async function loadDashboardSnapshot(): Promise<DashboardSnapshot> {
  const [registry, coordinator, aggregator, stats, accountant, reviews, auditStatus] =
    await Promise.all([
      getRegistryHealth(),
      getCoordinatorHealth(),
      getAggregatorHealth(),
      getRegistryStats(),
      getPrivacyAccountant(),
      getReviewQueue(),
      getAuditStatus(),
    ]);
  return { registry, coordinator, aggregator, stats, accountant, reviews, auditStatus };
}
