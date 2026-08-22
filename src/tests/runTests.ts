/**
 * Standalone Test Runner for Frontend Verification & Security Invariants
 */

import { runPolicyEngineTests } from './policyEngine.test.ts';
import { runFrontendValidationTests } from './frontendValidation.test.ts';

console.log('==================================================');
console.log('  FRONTEND VALIDATION & SECURITY TEST RUNNER       ');
console.log('==================================================\n');

let totalFailed = 0;

// 1. Policy Engine Deterministic Tests
console.log('--- 1. Policy Engine Deterministic Rules ---');
const policySuite = runPolicyEngineTests();
for (const result of policySuite.results) {
  if (result.passed) {
    console.log(`  ✓ [PASS] ${result.testName}`);
  } else {
    console.error(`  ✗ [FAIL] ${result.testName}: ${result.message}`);
  }
}
totalFailed += policySuite.failed;

// 2. Frontend Security & Presentation Invariants
console.log('\n--- 2. Frontend Security & Architecture Invariants ---');
const frontendSuite = runFrontendValidationTests();
for (const result of frontendSuite.results) {
  if (result.passed) {
    console.log(`  ✓ [PASS] ${result.name}`);
  } else {
    console.error(`  ✗ [FAIL] ${result.name}: ${result.error}`);
  }
}
totalFailed += frontendSuite.failed;

console.log('\n--------------------------------------------------');
const totalTests = policySuite.total + frontendSuite.total;
const totalPassed = policySuite.passed + frontendSuite.passed;
console.log(`Summary: ${totalPassed}/${totalTests} passed (${totalFailed} failed)`);
console.log('--------------------------------------------------');

if (totalFailed > 0) {
  process.exit(1);
} else {
  console.log('All Frontend validation & security tests passed successfully.\n');
  process.exit(0);
}
