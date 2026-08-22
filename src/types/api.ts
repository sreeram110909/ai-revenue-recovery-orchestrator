/**
 * TypeScript API Schema Definitions
 * Strictly aligned with FastAPI backend Pydantic models.
 */

export type CaseType = 'ONE_TIME_PAYMENT' | 'SUBSCRIPTION_RECURRING';

export type FailureCategory =
  | 'BANK_TIMEOUT_NETWORK'
  | 'EXPIRED_CARD_INSTRUMENT'
  | 'INSUFFICIENT_FUNDS_TRANSIENT'
  | 'INSUFFICIENT_FUNDS_CHRONIC'
  | 'INVALID_MANDATE_SUBSCRIPTION'
  | 'SECURITY_BLOCK_FRAUD'
  | 'AUTHENTICATION_FAILED'
  | 'GENERAL_TECHNICAL_ERROR';

export type RecoveryStrategy =
  | 'SMART_RETRY'
  | 'PAYMENT_LINK'
  | 'SUBSCRIPTION_RETRY'
  | 'UPDATE_PAYMENT_METHOD'
  | 'HUMAN_ESCALATION'
  | 'STOP';

export type CaseStatus =
  | 'DETECTED'
  | 'DIAGNOSED'
  | 'POLICY_EVALUATED'
  | 'ACTION_IN_PROGRESS'
  | 'ACTION_COMPLETED'
  | 'VERIFIED_RECOVERED'
  | 'RETRY_SCHEDULED'
  | 'ESCALATED'
  | 'STOPPED'
  | 'CLOSED_UNRECOVERABLE';

export type PolicyOutcome = 'ALLOW' | 'BLOCK' | 'DOWNGRADE' | 'ESCALATE' | 'STOP';

export type TruthProvenance =
  | 'LIVE_TEST_MODE_API_RESULT'
  | 'MOCKED_TEST_RESULT'
  | 'SYNTHETIC_DATA_RESULT';

export type BaselineStrategyType =
  | 'NO_ACTION'
  | 'RETRY_ONLY'
  | 'AI_REVENUE_RECOVERY_ORCHESTRATOR';

export interface SubscriptionDetails {
  subscription_id: string;
  plan_name: string;
  billing_cycle: string;
  mandate_status: string;
  current_cycle_number: number;
  consecutive_failures: number;
}

export interface PolicyCheckResult {
  passed: boolean;
  outcome: PolicyOutcome;
  proposed_strategy: RecoveryStrategy;
  approved_strategy: RecoveryStrategy;
  reasons: string[];
  cooldown_expires_at?: string | null;
  rule_checks?: Record<string, boolean>;
}

export interface ActionExecutionRecord {
  strategy: RecoveryStrategy;
  executed_at: string;
  status: string;
  gateway_reference_id?: string | null;
  details?: string | null;
  truth_provenance: TruthProvenance;
}

export interface VerificationRecord {
  verified: boolean;
  status: string;
  verified_at: string;
  recovered_amount: number;
  verification_method: string;
  details?: string | null;
  truth_provenance: TruthProvenance;
}

export interface RecoveryCase {
  id: string;
  case_type: CaseType;
  customer_id: string;
  masked_customer_email: string;
  masked_customer_phone: string;
  customer_segment: string;
  amount: number;
  currency: string;
  gateway_reference_id?: string | null;
  failure_code: string;
  failure_description?: string | null;
  failure_category: FailureCategory;
  attempts_count: number;
  max_attempts_allowed: number;
  last_attempt_at?: string | null;
  subscription_details?: SubscriptionDetails | null;
  current_status: CaseStatus;
  recommended_strategy?: RecoveryStrategy | null;
  strategy_confidence?: number | null;
  strategy_rationale?: string | null;
  policy_evaluation?: PolicyCheckResult | null;
  executed_action?: ActionExecutionRecord | null;
  verification_outcome?: VerificationRecord | null;
  verified_recovered_amount: number;
  is_escalated: boolean;
  escalation_reason?: string | null;
  provenance: TruthProvenance;
  created_at: string;
  updated_at: string;
}

export interface AuditLogEntry {
  id: string;
  case_id: string;
  event_type: string;
  event_timestamp: string;
  actor: string;
  previous_status?: string | null;
  new_status?: string | null;
  policy_outcome?: string | null;
  strategy?: string | null;
  details?: Record<string, any> | null;
  provenance: TruthProvenance;
}

export interface CaseDetailResponse {
  case: RecoveryCase;
  audit_trail: AuditLogEntry[];
}

export interface CaseListResponse {
  total: number;
  limit: number;
  offset: number;
  cases: RecoveryCase[];
}

export interface BatchMetrics {
  strategy_type: BaselineStrategyType;
  total_cases: number;
  total_revenue_at_risk: number;
  eligible_cases: number;
  recovery_attempts: number;
  successful_actions: number;
  verified_recovered_revenue: number;
  revenue_recovery_rate: number;
  case_recovery_rate: number;
  policy_blocks: number;
  human_escalations: number;
  stopped_cases: number;
  failed_actions: number;
  policy_violations: number;
}

export interface EvaluationCaseResult {
  case_id: string;
  batch_id: string;
  strategy_type: BaselineStrategyType;
  workflow_type: CaseType;
  failure_category: FailureCategory;
  amount: number;
  selected_strategy?: RecoveryStrategy | null;
  policy_outcome?: PolicyOutcome | null;
  execution_status: string;
  verification_status: string;
  verified_recovered_amount: number;
  final_status: CaseStatus;
  is_escalated: boolean;
  is_stopped: boolean;
  policy_violation: boolean;
  violation_details?: string | null;
  truth_provenance: TruthProvenance;
  audit_event_count: number;
  executed_at: string;
}

export interface BatchRunMetadata {
  batch_id: string;
  batch_timestamp: string;
  dataset_version: string;
  random_seed: number;
  total_cases: number;
  policy_config_version: string;
  code_version: string;
}

export interface ComparisonSummary {
  total_revenue_at_risk: number;
  no_action_revenue: number;
  retry_only_revenue: number;
  orchestrator_revenue: number;
  orchestrator_absolute_lift: number;
  orchestrator_percentage_lift: number;
  orchestrator_policy_violations: number;
  retry_only_policy_violations: number;
}

export interface BatchRunSummary {
  metadata: BatchRunMetadata;
  metrics: Record<string, BatchMetrics>;
  case_results: EvaluationCaseResult[];
  comparison_summary: ComparisonSummary;
  generated_artifacts?: Record<string, string>;
}

export interface HealthCheckResponse {
  status: string;
  service: string;
  version: string;
}
