/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 *
 * Core Domain Types & Enums for the AI Revenue Recovery Orchestrator
 * Locked Scope: Failed Payment Recovery (Primary) & Recurring Subscription Recovery (Secondary)
 */

export type CaseType = 'ONE_TIME_PAYMENT' | 'SUBSCRIPTION_RECURRING';

export type FailureCategory =
  | 'INSUFFICIENT_FUNDS'
  | 'EXPIRED_INSTRUMENT'
  | 'BANK_TIMEOUT_NETWORK'
  | 'AUTHENTICATION_OTP_FAILURE'
  | 'RISK_SECURITY_BLOCK'
  | 'MANDATE_EXPIRED_INVALID'
  | 'GENERAL_TECHNICAL_ERROR';

/**
 * Locked Recovery Action Space
 * Primary: SMART_RETRY | PAYMENT_LINK | HUMAN_ESCALATION | STOP
 * Secondary: SUBSCRIPTION_RETRY | UPDATE_PAYMENT_METHOD | HUMAN_ESCALATION | STOP
 */
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

/**
 * Policy Configuration Interface
 * NOTE: All values are demonstration safety/merchant policies.
 * They are NOT universal regulatory mandates. Production thresholds must be determined
 * by applicable payment methods, merchant risk tolerance, and current regulations.
 */
export interface PolicyConfig {
  /** Maximum automated retries per case before mandatory escalation or stop */
  maxRetryAttempts: number;
  /** Minimum hours required between automated retries */
  retryCooldownHours: number;
  /** Maximum amount (in INR) for automated actions without mandatory human review */
  automatedRecoveryAmountLimit: number;
  /** Categories where automated retries are strictly blocked */
  nonRetryableCategories: FailureCategory[];
  /** Allowed hours window (0-23) for sending customer notifications */
  contactWindowStartHour: number;
  contactWindowEndHour: number;
  /** Whether cases with invalid/expired mandate can auto-retry subscription debit */
  allowInvalidMandateAutoRetry: boolean;
}

export interface RuleEvaluationDetail {
  ruleId: string;
  ruleName: string;
  passed: boolean;
  reason: string;
  suggestedOutcome?: PolicyOutcome;
}

export interface PolicyCheckResult {
  outcome: PolicyOutcome;
  passed: boolean;
  proposedStrategy: RecoveryStrategy;
  approvedStrategy: RecoveryStrategy;
  evaluations: RuleEvaluationDetail[];
  reasons: string[];
  downgradeReason?: string;
  escalationReason?: string;
  evaluatedAt: string;
  configSnapshot: PolicyConfig;
}

export interface SubscriptionMetadata {
  subscriptionId: string;
  planName: string;
  billingInterval: 'MONTHLY' | 'YEARLY';
  mandateStatus: 'ACTIVE' | 'EXPIRED' | 'REVOKED' | 'INVALID' | 'SUSPENDED';
  mandateExpiryDate?: string;
  requiresAfa: boolean;
}

export interface RecoveryCase {
  id: string;
  caseType: CaseType;
  customerId: string;
  // Masked contact references for privacy
  maskedCustomerEmail: string;
  maskedCustomerPhone: string;
  customerSegment: 'STANDARD' | 'PREMIUM' | 'ENTERPRISE';
  amount: number;
  currency: string;
  gatewayReferenceId: string;
  failureCode: string;
  failureDescription: string;
  failureCategory: FailureCategory;
  attemptsCount: number;
  maxAttemptsAllowed: number;
  lastAttemptAt?: string;
  nextAllowedAttemptAt?: string;
  subscriptionDetails?: SubscriptionMetadata;
  currentStatus: CaseStatus;
  recommendedStrategy?: RecoveryStrategy;
  strategyConfidence?: number;
  strategyRationale?: string;
  policyEvaluation?: PolicyCheckResult;
  executedAction?: ActionExecutionRecord;
  verificationOutcome?: VerificationRecord;
  verifiedRecoveredAmount: number;
  isEscalated: boolean;
  escalationReason?: string;
  provenance: TruthProvenance;
  createdAt: string;
  updatedAt: string;
}

export interface ActionExecutionRecord {
  actionId: string;
  actionType: RecoveryStrategy;
  status: 'PENDING' | 'SUCCESS' | 'FAILED';
  executedAt: string;
  payload: Record<string, unknown>;
  gatewayResponse?: Record<string, unknown>;
  paymentLinkUrl?: string;
  notificationLog?: {
    channel: 'EMAIL' | 'TRANSACTIONAL_NOTICE';
    recipientMasked: string;
    content: string;
    timestamp: string;
  };
  provenance: TruthProvenance;
}

export interface VerificationRecord {
  verified: boolean;
  status: 'PAID' | 'FAILED' | 'PENDING' | 'EXPIRED';
  verifiedAt: string;
  recoveredAmount: number;
  verificationMethod: 'GATEWAY_API_CHECK' | 'WEBHOOK_EVENT' | 'TEST_SIMULATION';
  details: string;
  provenance: TruthProvenance;
}

export interface AuditLogEntry {
  id: string;
  caseId: string;
  timestamp: string;
  eventType:
    | 'CASE_INGESTED'
    | 'DIAGNOSIS_COMPLETED'
    | 'STRATEGY_RECOMMENDED'
    | 'POLICY_EVALUATION'
    | 'ACTION_DISPATCHED'
    | 'VERIFICATION_RECEIVED'
    | 'CASE_RECOVERED'
    | 'CASE_ESCALATED'
    | 'CASE_STOPPED';
  actor:
    | 'SYSTEM_INGESTOR'
    | 'AI_DIAGNOSTICIAN'
    | 'POLICY_ENGINE'
    | 'EXECUTION_SERVICE'
    | 'VERIFICATION_SERVICE'
    | 'HUMAN_OPERATOR';
  summary: string;
  policyOutcome?: PolicyOutcome;
  details: Record<string, unknown>;
}

export interface BatchMetrics {
  totalCases: number;
  revenueAtRisk: number;
  eligibleCases: number;
  recoveryAttempts: number;
  successfulActions: number;
  verifiedRecoveredRevenue: number;
  recoveryRatePercentage: number;
  policyBlockedActions: number;
  humanEscalations: number;
  stoppedCases: number;
  failures: number;
  provenance: TruthProvenance;
}
