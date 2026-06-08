export type Role = "ADMIN" | "MANAGER" | "ANALYST" | "VIEWER";
export type Severity = "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
export type Status = "NEW" | "PROCESSING" | "RESOLVED" | "FAILED";

export interface User {
  id: string;
  name: string;
  email: string;
  role: Role;
  is_active: boolean;
  created_at?: string;
}

export interface AuthResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  user: User;
}

export interface MeResponse {
  user: User;
}

export interface EventActivity {
  id: string;
  event_id: string;
  activity_type: string;
  actor_id: string | null;
  tenant_id: string | null;
  details: Record<string, unknown>;
  created_at: string;
}

export interface Event {
  id: string;
  title: string;
  description: string | null;
  event_type: string;
  severity: Severity;
  status: Status;
  source: string;
  tenant_id: string | null;
  metadata: Record<string, unknown>;
  created_by?: string;
  created_at?: string;
  updated_at?: string;
  timeline?: EventActivity[];
}

export interface EventCreate {
  title: string;
  description?: string | null;
  event_type: string;
  severity: Severity;
  status?: Status;
  source: string;
  tenant_id?: string | null;
  metadata: Record<string, unknown>;
}

export interface EventUpdate {
  title?: string;
  description?: string | null;
  event_type?: string;
  severity?: Severity;
  status?: Status;
  source?: string;
  tenant_id?: string | null;
  metadata?: Record<string, unknown>;
}

export interface EventListParams {
  page?: number;
  page_size?: number;
  search?: string;
  severity?: Severity | Severity[];
  status?: Status | Status[];
  event_type?: string | string[];
  tenant_id?: string;
  sort_by?: "created_at" | "updated_at" | "severity" | "status" | "event_type" | "title";
  sort_order?: "asc" | "desc";
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}

export interface ObservationResult {
  summary: string;
  detected_type: string;
  priority: string;
  risk_indicators: string[];
  confidence: number;
}

export interface InvestigationResult {
  root_cause: string;
  impact: string;
  evidence: string[];
  confidence: number;
}

export interface PredictionResult {
  revenue_risk: number;
  delay_probability: number;
  churn_probability: number;
  severity_score: number;
  confidence: number;
}

export interface StrategyItem {
  title: string;
  description: string;
  estimated_savings: number;
  effort: string;
  risk_reduction: number;
  confidence: number;
}

export interface DecisionResult {
  selected_action: StrategyItem;
  decision_reason: string;
  expected_savings: number;
  confidence: number;
  requires_human_approval: boolean;
}

export interface ReportResult {
  executive_summary: string;
  technical_summary: string;
  recommended_action: string;
  estimated_savings: number;
  confidence: number;
}

export interface AgentWorkflowResponse {
  event_id: string;
  event_status: string;
  observation: ObservationResult;
  investigation: InvestigationResult;
  prediction: PredictionResult;
  strategies: StrategyItem[];
  decision: DecisionResult;
  report: ReportResult;
  confidence_score: number;
  started_at: string;
  completed_at: string;
  errors: string[];
}

export interface ApiError {
  message: string;
  status: number;
  data?: unknown;
}
