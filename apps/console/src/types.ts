export interface ServiceHealth {
  status: string;
  service: string;
  ready?: string;
}

export interface RegistryStats {
  registered_cfis: number;
  pending_reviews: number;
  active_cfis: number;
  cohort_manifests: number;
}

export interface PrivacyAccountant {
  total_epsilon: number;
  spent_epsilon: number;
  remaining_epsilon: number;
  release_count: number;
}

export interface ReviewTicket {
  invariant_id: string;
  status: string;
  adversary_scores: Record<string, number>;
  checklist_complete: boolean;
  reviewer: string | null;
  notes: string;
  created_at: string;
  updated_at: string;
  lifecycle_state?: string;
  checklist?: { id: number; item: string }[];
}

export interface AuditEvent {
  timestamp?: string;
  actor?: string;
  action?: string;
  resource_id?: string;
  details?: Record<string, unknown>;
}

export interface AuditExport {
  events: AuditEvent[];
  assumptions?: string[];
}

export interface AuditStatus {
  cursor?: number;
  pending_export?: number;
  assumptions?: string[];
}

export type ReviewDecision = "approved" | "rejected" | "needs_generalization";
