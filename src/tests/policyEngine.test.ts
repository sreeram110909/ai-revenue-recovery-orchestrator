/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 *
 * Comprehensive Unit Test Suite for Policy Engine
 * Verifies all 10 mandated policy rules in complete isolation (0 LLM, 0 network).
 */

import { PolicyEngine } from '../services/policyEngine.ts';
import { RecoveryCase } from '../types/recovery.ts';

export function runPolicyEngineTests(): {
  total: number;
  passed: number;
  failed: number;
  results: { testName: string; passed: boolean; message?: string }[];
} {
  const engine = new PolicyEngine({
    maxRetryAttempts: 3,
    retryCooldownHours: 4,
    automatedRecoveryAmountLimit: 15000,
    nonRetryableCategories: [
      'RISK_SECURITY_BLOCK',
      'EXPIRED_INSTRUMENT',
      'MANDATE_EXPIRED_INVALID',
    ],
    allowInvalidMandateAutoRetry: false,
  });

  const results: { testName: string; passed: boolean; message?: string }[] = [];

  function assert(condition: boolean, testName: string, failureMessage: string) {
    if (condition) {
      results.push({ testName, passed: true });
    } else {
      results.push({ testName, passed: false, message: failureMessage });
    }
  }

  // Base sample mock case
  const createBaseCase = (overrides?: Partial<RecoveryCase>): RecoveryCase => ({
    id: 'case_test_001',
    caseType: 'ONE_TIME_PAYMENT',
    customerId: 'cust_101',
    maskedCustomerEmail: 'u***@example.com',
    maskedCustomerPhone: '+91 98*** **123',
    customerSegment: 'STANDARD',
    amount: 4999,
    currency: 'INR',
    gatewayReferenceId: 'pay_test_ref_01',
    failureCode: 'PAYMENT_FAILED_BANK_TIMEOUT',
    failureDescription: 'Bank gateway timeout during 3DS OTP verification',
    failureCategory: 'BANK_TIMEOUT_NETWORK',
    attemptsCount: 1,
    maxAttemptsAllowed: 3,
    lastAttemptAt: new Date(Date.now() - 5 * 3600 * 1000).toISOString(), // 5 hours ago
    currentStatus: 'DIAGNOSED',
    verifiedRecoveredAmount: 0,
    isEscalated: false,
    provenance: 'SYNTHETIC_DATA_RESULT',
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
    ...overrides,
  });

  // Test 1: Valid retry is allowed
  {
    const testCase = createBaseCase({
      attemptsCount: 1,
      amount: 4500,
      failureCategory: 'BANK_TIMEOUT_NETWORK',
      lastAttemptAt: new Date(Date.now() - 6 * 3600 * 1000).toISOString(),
    });
    const result = engine.evaluate(testCase, 'SMART_RETRY');
    assert(
      result.outcome === 'ALLOW' &&
        result.approvedStrategy === 'SMART_RETRY' &&
        result.passed === true,
      'Test 1: Valid retry is allowed',
      `Expected ALLOW with SMART_RETRY, got ${result.outcome} (${result.approvedStrategy})`
    );
  }

  // Test 2: Retry limit is reached (Downgrades SMART_RETRY to PAYMENT_LINK)
  {
    const testCase = createBaseCase({
      attemptsCount: 3,
      maxAttemptsAllowed: 3,
    });
    const result = engine.evaluate(testCase, 'SMART_RETRY');
    assert(
      result.outcome === 'DOWNGRADE' &&
        result.approvedStrategy === 'PAYMENT_LINK',
      'Test 2: Retry limit reached forces downgrade to PAYMENT_LINK',
      `Expected DOWNGRADE to PAYMENT_LINK, got ${result.outcome} -> ${result.approvedStrategy}`
    );
  }

  // Test 3: Cooldown has not elapsed (Blocks immediate retry)
  {
    const testCase = createBaseCase({
      attemptsCount: 1,
      // Attempt was made only 1 hour ago (requires 4 hours)
      lastAttemptAt: new Date(Date.now() - 1 * 3600 * 1000).toISOString(),
    });
    const result = engine.evaluate(testCase, 'SMART_RETRY');
    assert(
      result.outcome === 'BLOCK' && result.passed === false,
      'Test 3: Cooldown violation blocks immediate retry',
      `Expected BLOCK due to cooldown, got ${result.outcome}`
    );
  }

  // Test 4: Amount exceeds configured demonstration automation threshold (₹15,000)
  {
    const testCase = createBaseCase({
      amount: 25000, // Above limit of ₹15,000
      attemptsCount: 0,
      lastAttemptAt: undefined,
    });
    const result = engine.evaluate(testCase, 'SMART_RETRY');
    assert(
      result.outcome === 'ESCALATE' &&
        result.approvedStrategy === 'HUMAN_ESCALATION',
      'Test 4: High-value case (>₹15,000) requires human escalation',
      `Expected ESCALATE to HUMAN_ESCALATION, got ${result.outcome} -> ${result.approvedStrategy}`
    );
  }

  // Test 5: Non-retryable failure blocks retry
  {
    const testCase = createBaseCase({
      failureCategory: 'RISK_SECURITY_BLOCK',
      failureCode: 'GATEWAY_FRAUD_BLOCK',
      amount: 3000,
    });
    const result = engine.evaluate(testCase, 'SMART_RETRY');
    assert(
      result.outcome === 'BLOCK' &&
        result.approvedStrategy === 'HUMAN_ESCALATION' &&
        result.passed === false,
      'Test 5: Non-retryable failure (RISK_SECURITY_BLOCK) blocks retry',
      `Expected BLOCK with HUMAN_ESCALATION, got ${result.outcome} -> ${result.approvedStrategy}`
    );
  }

  // Test 6: Escalated case cannot receive automated action (Status Freeze)
  {
    const testCase = createBaseCase({
      currentStatus: 'ESCALATED',
      isEscalated: true,
      amount: 3000,
    });
    const result = engine.evaluate(testCase, 'SMART_RETRY');
    assert(
      result.outcome === 'STOP' && result.passed === false,
      'Test 6: Case in ESCALATED state rejects automated action',
      `Expected STOP on frozen case, got ${result.outcome}`
    );
  }

  // Test 7: Stopped case cannot receive automated action (Status Freeze)
  {
    const testCase = createBaseCase({
      currentStatus: 'STOPPED',
      amount: 3000,
    });
    const result = engine.evaluate(testCase, 'PAYMENT_LINK');
    assert(
      result.outcome === 'STOP' && result.passed === false,
      'Test 7: Case in STOPPED state rejects automated action',
      `Expected STOP on stopped case, got ${result.outcome}`
    );
  }

  // Test 8: Invalid/expired mandate blocks subscription retry
  {
    const testCase = createBaseCase({
      caseType: 'SUBSCRIPTION_RECURRING',
      failureCategory: 'MANDATE_EXPIRED_INVALID',
      amount: 1999,
      subscriptionDetails: {
        subscriptionId: 'sub_test_999',
        planName: 'Pro Monthly SaaS',
        billingInterval: 'MONTHLY',
        mandateStatus: 'EXPIRED',
        requiresAfa: false,
      },
    });
    const result = engine.evaluate(testCase, 'SUBSCRIPTION_RETRY');
    assert(
      (result.outcome === 'DOWNGRADE' || result.outcome === 'BLOCK') &&
        result.approvedStrategy === 'UPDATE_PAYMENT_METHOD',
      'Test 8: Expired recurring mandate blocks SUBSCRIPTION_RETRY and downgrades to UPDATE_PAYMENT_METHOD',
      `Expected downgrade to UPDATE_PAYMENT_METHOD, got ${result.outcome} -> ${result.approvedStrategy}`
    );
  }

  // Test 9: Expired card instrument on one-time payment downgrades retry to payment link
  {
    const testCase = createBaseCase({
      caseType: 'ONE_TIME_PAYMENT',
      failureCategory: 'EXPIRED_INSTRUMENT',
      amount: 2500,
    });
    const result = engine.evaluate(testCase, 'SMART_RETRY');
    assert(
      result.outcome === 'DOWNGRADE' &&
        result.approvedStrategy === 'PAYMENT_LINK',
      'Test 9: Expired card instrument downgrades retry to PAYMENT_LINK',
      `Expected DOWNGRADE to PAYMENT_LINK, got ${result.outcome} -> ${result.approvedStrategy}`
    );
  }

  // Test 10: Policy result is 100% deterministic and reproducible for identical inputs
  {
    const testCase = createBaseCase({
      amount: 8999,
      attemptsCount: 2,
      lastAttemptAt: new Date('2026-08-20T10:00:00Z').toISOString(),
    });
    const evalDate = new Date('2026-08-20T16:00:00Z');

    const result1 = engine.evaluate(testCase, 'PAYMENT_LINK', evalDate);
    const result2 = engine.evaluate(testCase, 'PAYMENT_LINK', evalDate);

    const matches =
      result1.outcome === result2.outcome &&
      result1.approvedStrategy === result2.approvedStrategy &&
      JSON.stringify(result1.evaluations) === JSON.stringify(result2.evaluations);

    assert(
      matches,
      'Test 10: Policy engine evaluation is completely deterministic',
      'Evaluation results differed between consecutive identical calls'
    );
  }

  const total = results.length;
  const passed = results.filter((r) => r.passed).length;
  const failed = total - passed;

  return { total, passed, failed, results };
}
