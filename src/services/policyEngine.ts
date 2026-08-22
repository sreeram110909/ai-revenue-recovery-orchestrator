/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 *
 * Deterministic Policy Engine for AI Revenue Recovery Orchestrator
 *
 * CRITICAL ARCHITECTURAL CONSTRAINTS:
 * 1. 100% Deterministic: Given the exact same case state and configuration,
 *    it MUST produce the exact same outcome.
 * 2. Zero AI / Zero LLM: This module never calls an LLM or external network services.
 * 3. Authority: The Policy Engine has absolute authority to ALLOW, BLOCK,
 *    DOWNGRADE, ESCALATE, or STOP any candidate action.
 *
 * NOTE ON POLICY CONFIGURATION:
 * Thresholds such as amount limits (e.g., ₹15,000), retry caps (e.g., 3), and cooldowns (e.g., 4h)
 * are configurable DEMONSTRATION POLICIES for the buildathon. Production thresholds must be
 * determined from the applicable payment method, merchant risk policy, and verified current regulations.
 */

import {
  PolicyCheckResult,
  PolicyConfig,
  PolicyOutcome,
  RecoveryCase,
  RecoveryStrategy,
  RuleEvaluationDetail,
} from '../types/recovery.ts';

/**
 * Default Demonstration Policy Configuration
 * NOTE: These are demonstration values, not hard-coded regulatory claims.
 */
export const DEFAULT_DEMO_POLICY_CONFIG: PolicyConfig = {
  // Demonstration Safety Policy: Cap retries per case to prevent endless loops
  maxRetryAttempts: 3,
  // Demonstration Safety Policy: Minimum hours between automated retry attempts
  retryCooldownHours: 4,
  // Demonstration Safety Policy: Automated actions above this value require human sign-off
  automatedRecoveryAmountLimit: 15000,
  // Demonstration Safety Policy: Non-retryable root causes
  nonRetryableCategories: [
    'RISK_SECURITY_BLOCK',
    'EXPIRED_INSTRUMENT',
    'MANDATE_EXPIRED_INVALID',
  ],
  // Demonstration Safety Policy: Permitted contact notification hours (09:00 to 20:00)
  contactWindowStartHour: 9,
  contactWindowEndHour: 20,
  // Demonstration Safety Policy: Disallow automated charge on invalid/expired mandates
  allowInvalidMandateAutoRetry: false,
};

export class PolicyEngine {
  private config: PolicyConfig;

  constructor(customConfig?: Partial<PolicyConfig>) {
    this.config = {
      ...DEFAULT_DEMO_POLICY_CONFIG,
      ...customConfig,
    };
  }

  /**
   * Update policy configuration at runtime (e.g., for merchant customization or test scenarios)
   */
  public updateConfig(newConfig: Partial<PolicyConfig>): void {
    this.config = {
      ...this.config,
      ...newConfig,
    };
  }

  /**
   * Get active policy configuration snapshot
   */
  public getConfig(): PolicyConfig {
    return { ...this.config };
  }

  /**
   * Primary Evaluation Method
   * Validates a proposed recovery strategy against the recovery case state and active policies.
   */
  public evaluate(
    recoveryCase: RecoveryCase,
    proposedStrategy: RecoveryStrategy,
    evaluationTimestamp: Date = new Date()
  ): PolicyCheckResult {
    const evaluations: RuleEvaluationDetail[] = [];
    const reasons: string[] = [];

    // Rule 1: Case Status Integrity (Cannot execute automated action on already escalated or stopped cases)
    const statusCheck = this.evaluateStatusIntegrity(recoveryCase, proposedStrategy);
    evaluations.push(statusCheck);
    if (!statusCheck.passed) {
      return this.buildResult(
        'STOP',
        false,
        proposedStrategy,
        'STOP',
        evaluations,
        [statusCheck.reason],
        evaluationTimestamp
      );
    }

    // Rule 2: Amount Automation Threshold Policy
    const amountCheck = this.evaluateAmountThreshold(recoveryCase, proposedStrategy);
    evaluations.push(amountCheck);
    if (!amountCheck.passed) {
      return this.buildResult(
        'ESCALATE',
        false,
        proposedStrategy,
        'HUMAN_ESCALATION',
        evaluations,
        [amountCheck.reason],
        evaluationTimestamp,
        undefined,
        amountCheck.reason
      );
    }

    // Rule 3: Non-Retryable Failure Category Guardrail
    const failureCategoryCheck = this.evaluateFailureCategory(recoveryCase, proposedStrategy);
    evaluations.push(failureCategoryCheck);
    if (!failureCategoryCheck.passed) {
      // If card is expired on one-time payment, downgrade from SMART_RETRY to PAYMENT_LINK
      if (
        recoveryCase.caseType === 'ONE_TIME_PAYMENT' &&
        recoveryCase.failureCategory === 'EXPIRED_INSTRUMENT' &&
        proposedStrategy === 'SMART_RETRY'
      ) {
        return this.buildResult(
          'DOWNGRADE',
          true,
          proposedStrategy,
          'PAYMENT_LINK',
          evaluations,
          [failureCategoryCheck.reason, 'Downgraded to PAYMENT_LINK to allow customer to provide a new payment instrument.'],
          evaluationTimestamp,
          'Card is expired. Retrying the same instrument will fail. Downgraded to customer PAYMENT_LINK.'
        );
      }

      // If mandate is expired/invalid on recurring subscription, downgrade from SUBSCRIPTION_RETRY to UPDATE_PAYMENT_METHOD
      if (
        recoveryCase.caseType === 'SUBSCRIPTION_RECURRING' &&
        recoveryCase.failureCategory === 'MANDATE_EXPIRED_INVALID' &&
        proposedStrategy === 'SUBSCRIPTION_RETRY'
      ) {
        return this.buildResult(
          'DOWNGRADE',
          true,
          proposedStrategy,
          'UPDATE_PAYMENT_METHOD',
          evaluations,
          [failureCategoryCheck.reason, 'Downgraded to UPDATE_PAYMENT_METHOD to request updated mandate/instrument.'],
          evaluationTimestamp,
          'Mandate is invalid or expired. Auto-retry blocked. Downgraded to UPDATE_PAYMENT_METHOD link.'
        );
      }

      return this.buildResult(
        'BLOCK',
        false,
        proposedStrategy,
        'HUMAN_ESCALATION',
        evaluations,
        [failureCategoryCheck.reason],
        evaluationTimestamp,
        undefined,
        'Non-retryable root cause requires human review.'
      );
    }

    // Rule 4: Maximum Retry Cap Policy
    const retryCapCheck = this.evaluateRetryCap(recoveryCase, proposedStrategy);
    evaluations.push(retryCapCheck);
    if (!retryCapCheck.passed) {
      // If retry cap reached for automated retry, downgrade to alternative or escalate
      if (proposedStrategy === 'SMART_RETRY') {
        return this.buildResult(
          'DOWNGRADE',
          true,
          proposedStrategy,
          'PAYMENT_LINK',
          evaluations,
          [retryCapCheck.reason, 'Exceeded automated retry cap. Downgraded to PAYMENT_LINK.'],
          evaluationTimestamp,
          'Maximum automated gateway retries reached. Downgraded to customer-driven PAYMENT_LINK.'
        );
      }
      if (proposedStrategy === 'SUBSCRIPTION_RETRY') {
        return this.buildResult(
          'DOWNGRADE',
          true,
          proposedStrategy,
          'UPDATE_PAYMENT_METHOD',
          evaluations,
          [retryCapCheck.reason, 'Exceeded mandate retry cap. Downgraded to UPDATE_PAYMENT_METHOD.'],
          evaluationTimestamp,
          'Maximum subscription debit attempts reached. Downgraded to UPDATE_PAYMENT_METHOD link.'
        );
      }

      return this.buildResult(
        'ESCALATE',
        false,
        proposedStrategy,
        'HUMAN_ESCALATION',
        evaluations,
        [retryCapCheck.reason],
        evaluationTimestamp,
        undefined,
        'Attempts limit reached. Escalating to human operator.'
      );
    }

    // Rule 5: Retry Cooldown Duration Policy
    const cooldownCheck = this.evaluateCooldown(recoveryCase, proposedStrategy, evaluationTimestamp);
    evaluations.push(cooldownCheck);
    if (!cooldownCheck.passed) {
      return this.buildResult(
        'BLOCK',
        false,
        proposedStrategy,
        'STOP',
        evaluations,
        [cooldownCheck.reason],
        evaluationTimestamp
      );
    }

    // Rule 6: Recurring Mandate Integrity Policy (Secondary Workflow)
    if (recoveryCase.caseType === 'SUBSCRIPTION_RECURRING') {
      const mandateCheck = this.evaluateMandateIntegrity(recoveryCase, proposedStrategy);
      evaluations.push(mandateCheck);
      if (!mandateCheck.passed) {
        if (proposedStrategy === 'SUBSCRIPTION_RETRY') {
          return this.buildResult(
            'DOWNGRADE',
            true,
            proposedStrategy,
            'UPDATE_PAYMENT_METHOD',
            evaluations,
            [mandateCheck.reason, 'Downgraded to UPDATE_PAYMENT_METHOD.'],
            evaluationTimestamp,
            'Mandate is invalid or expired. Auto-retry blocked. Downgraded to UPDATE_PAYMENT_METHOD.'
          );
        }
        return this.buildResult(
          'ESCALATE',
          false,
          proposedStrategy,
          'HUMAN_ESCALATION',
          evaluations,
          [mandateCheck.reason],
          evaluationTimestamp,
          undefined,
          'Mandate issue cannot be automatically resolved.'
        );
      }
    }

    // All policy rules passed
    reasons.push(`Action ${proposedStrategy} complies with all active demonstration policies.`);
    return this.buildResult(
      'ALLOW',
      true,
      proposedStrategy,
      proposedStrategy,
      evaluations,
      reasons,
      evaluationTimestamp
    );
  }

  // --- Private Deterministic Evaluation Rules ---

  private evaluateStatusIntegrity(
    recoveryCase: RecoveryCase,
    proposedStrategy: RecoveryStrategy
  ): RuleEvaluationDetail {
    const isFrozen =
      recoveryCase.currentStatus === 'ESCALATED' ||
      recoveryCase.currentStatus === 'STOPPED' ||
      recoveryCase.currentStatus === 'CLOSED_UNRECOVERABLE' ||
      recoveryCase.currentStatus === 'VERIFIED_RECOVERED';

    if (isFrozen && proposedStrategy !== 'STOP' && proposedStrategy !== 'HUMAN_ESCALATION') {
      return {
        ruleId: 'POL-01-STATUS-FREEZE',
        ruleName: 'Case State Freeze Guardrail',
        passed: false,
        reason: `Case is in terminal/frozen status '${recoveryCase.currentStatus}'. Automated action '${proposedStrategy}' is strictly forbidden.`,
        suggestedOutcome: 'STOP',
      };
    }

    return {
      ruleId: 'POL-01-STATUS-FREEZE',
      ruleName: 'Case State Freeze Guardrail',
      passed: true,
      reason: `Case status '${recoveryCase.currentStatus}' is eligible for evaluation.`,
    };
  }

  private evaluateAmountThreshold(
    recoveryCase: RecoveryCase,
    proposedStrategy: RecoveryStrategy
  ): RuleEvaluationDetail {
    // Demonstration Policy: Any automated financial action on high-value transactions (> ₹15,000)
    // requires human verification rather than blind autonomous execution.
    if (
      recoveryCase.amount > this.config.automatedRecoveryAmountLimit &&
      proposedStrategy !== 'HUMAN_ESCALATION' &&
      proposedStrategy !== 'STOP'
    ) {
      return {
        ruleId: 'POL-02-AMOUNT-CEILING',
        ruleName: 'Automated Recovery Value Ceiling Policy (Demo Configuration)',
        passed: false,
        reason: `Case amount ₹${recoveryCase.amount} exceeds demo automation limit of ₹${this.config.automatedRecoveryAmountLimit}. Mandatory human escalation required.`,
        suggestedOutcome: 'ESCALATE',
      };
    }

    return {
      ruleId: 'POL-02-AMOUNT-CEILING',
      ruleName: 'Automated Recovery Value Ceiling Policy (Demo Configuration)',
      passed: true,
      reason: `Case amount ₹${recoveryCase.amount} is within the demo automation limit of ₹${this.config.automatedRecoveryAmountLimit}.`,
    };
  }

  private evaluateFailureCategory(
    recoveryCase: RecoveryCase,
    proposedStrategy: RecoveryStrategy
  ): RuleEvaluationDetail {
    const isNonRetryable = this.config.nonRetryableCategories.includes(recoveryCase.failureCategory);
    const isRetryAction =
      proposedStrategy === 'SMART_RETRY' || proposedStrategy === 'SUBSCRIPTION_RETRY';

    if (isNonRetryable && isRetryAction) {
      return {
        ruleId: 'POL-03-NON-RETRYABLE-FAILURES',
        ruleName: 'Non-Retryable Root Cause Guardrail',
        passed: false,
        reason: `Failure category '${recoveryCase.failureCategory}' is non-retryable. Automated retry would fail or trigger fraud blocks.`,
        suggestedOutcome: 'BLOCK',
      };
    }

    return {
      ruleId: 'POL-03-NON-RETRYABLE-FAILURES',
      ruleName: 'Non-Retryable Root Cause Guardrail',
      passed: true,
      reason: `Failure category '${recoveryCase.failureCategory}' is permitted for action '${proposedStrategy}'.`,
    };
  }

  private evaluateRetryCap(
    recoveryCase: RecoveryCase,
    proposedStrategy: RecoveryStrategy
  ): RuleEvaluationDetail {
    const isRetryAction =
      proposedStrategy === 'SMART_RETRY' || proposedStrategy === 'SUBSCRIPTION_RETRY';

    if (isRetryAction && recoveryCase.attemptsCount >= this.config.maxRetryAttempts) {
      return {
        ruleId: 'POL-04-MAX-RETRY-CAP',
        ruleName: 'Maximum Automated Retry Cap Policy (Demo Configuration)',
        passed: false,
        reason: `Case has exhausted ${recoveryCase.attemptsCount} attempts (max allowed: ${this.config.maxRetryAttempts}). Further automated retries blocked.`,
        suggestedOutcome: 'DOWNGRADE',
      };
    }

    return {
      ruleId: 'POL-04-MAX-RETRY-CAP',
      ruleName: 'Maximum Automated Retry Cap Policy (Demo Configuration)',
      passed: true,
      reason: `Attempts count (${recoveryCase.attemptsCount}/${this.config.maxRetryAttempts}) is within policy limits.`,
    };
  }

  private evaluateCooldown(
    recoveryCase: RecoveryCase,
    proposedStrategy: RecoveryStrategy,
    now: Date
  ): RuleEvaluationDetail {
    const isRetryAction =
      proposedStrategy === 'SMART_RETRY' || proposedStrategy === 'SUBSCRIPTION_RETRY';

    if (isRetryAction && recoveryCase.lastAttemptAt) {
      const lastAttemptTime = new Date(recoveryCase.lastAttemptAt).getTime();
      const elapsedHours = (now.getTime() - lastAttemptTime) / (1000 * 60 * 60);

      if (elapsedHours < this.config.retryCooldownHours) {
        const remainingMin = Math.ceil(
          (this.config.retryCooldownHours - elapsedHours) * 60
        );
        return {
          ruleId: 'POL-05-RETRY-COOLDOWN',
          ruleName: 'Mandatory Retry Cooldown Policy (Demo Configuration)',
          passed: false,
          reason: `Only ${elapsedHours.toFixed(1)}h elapsed since last attempt at ${recoveryCase.lastAttemptAt}. Required cooldown is ${this.config.retryCooldownHours}h (${remainingMin}m remaining).`,
          suggestedOutcome: 'BLOCK',
        };
      }
    }

    return {
      ruleId: 'POL-05-RETRY-COOLDOWN',
      ruleName: 'Mandatory Retry Cooldown Policy (Demo Configuration)',
      passed: true,
      reason: `Cooldown requirements satisfied.`,
    };
  }

  private evaluateMandateIntegrity(
    recoveryCase: RecoveryCase,
    proposedStrategy: RecoveryStrategy
  ): RuleEvaluationDetail {
    const sub = recoveryCase.subscriptionDetails;
    if (!sub) {
      return {
        ruleId: 'POL-06-MANDATE-INTEGRITY',
        ruleName: 'Recurring Mandate Integrity Policy',
        passed: false,
        reason: 'Subscription metadata missing for recurring payment case.',
        suggestedOutcome: 'ESCALATE',
      };
    }

    const isMandateInvalid =
      sub.mandateStatus === 'EXPIRED' ||
      sub.mandateStatus === 'REVOKED' ||
      sub.mandateStatus === 'INVALID';

    if (isMandateInvalid && proposedStrategy === 'SUBSCRIPTION_RETRY') {
      return {
        ruleId: 'POL-06-MANDATE-INTEGRITY',
        ruleName: 'Recurring Mandate Integrity Policy',
        passed: false,
        reason: `Mandate status is '${sub.mandateStatus}'. Automated subscription debit cannot succeed without customer updating payment method.`,
        suggestedOutcome: 'DOWNGRADE',
      };
    }

    return {
      ruleId: 'POL-06-MANDATE-INTEGRITY',
      ruleName: 'Recurring Mandate Integrity Policy',
      passed: true,
      reason: `Mandate status is '${sub.mandateStatus}'. Complies with recurring debit policy.`,
    };
  }

  private buildResult(
    outcome: PolicyOutcome,
    passed: boolean,
    proposedStrategy: RecoveryStrategy,
    approvedStrategy: RecoveryStrategy,
    evaluations: RuleEvaluationDetail[],
    reasons: string[],
    evaluatedAt: Date,
    downgradeReason?: string,
    escalationReason?: string
  ): PolicyCheckResult {
    return {
      outcome,
      passed,
      proposedStrategy,
      approvedStrategy,
      evaluations,
      reasons,
      downgradeReason,
      escalationReason,
      evaluatedAt: evaluatedAt.toISOString(),
      configSnapshot: this.getConfig(),
    };
  }
}
