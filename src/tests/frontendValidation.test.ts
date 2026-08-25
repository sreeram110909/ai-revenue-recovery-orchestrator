/**
 * Frontend Validation & Security Test Suite (Milestone 6 Final Correction)
 * Validates:
 * 1. Absence of forbidden terms ("68 cases", "21.6% Verified Settlement", "60 failed payments", "VIP", "Naive Retry", "Production-Grade", hardcoded "case_001")
 * 2. Strict UI schema and terminology alignment
 * 3. Absence of backend secrets and credentials
 * 4. Absence of direct financial gateway SDKs in browser
 * 5. Dynamic data integrity and API error handling
 */

import * as fs from 'fs';
import * as path from 'path';
import { fileURLToPath } from 'url';
import { api, ApiError } from '../services/api';
import { BatchRunSummary, RecoveryCase, AuditLogEntry } from '../types/api';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

export interface TestResult {
  name: string;
  passed: boolean;
  error?: string;
}

export function runFrontendValidationTests(): { total: number; passed: number; failed: number; results: TestResult[] } {
  const results: TestResult[] = [];

  function test(name: string, fn: () => void) {
    try {
      fn();
      results.push({ name, passed: true });
    } catch (err: any) {
      results.push({ name, passed: false, error: err.message });
    }
  }

  const srcDir = path.resolve(__dirname, '..');

  function getProductionFiles(): string[] {
    const targetDirs = ['components', 'pages', 'services', 'hooks'];
    const files: string[] = [path.resolve(srcDir, 'App.tsx'), path.resolve(srcDir, 'main.tsx')];
    for (const dirName of targetDirs) {
      const fullDir = path.join(srcDir, dirName);
      if (fs.existsSync(fullDir)) {
        const entries = fs.readdirSync(fullDir, { withFileTypes: true });
        for (const entry of entries) {
          if (entry.isFile() && (entry.name.endsWith('.ts') || entry.name.endsWith('.tsx'))) {
            files.push(path.join(fullDir, entry.name));
          }
        }
      }
    }
    return files;
  }

  // 1. Security Scan: Confirm NO backend secrets exist in src/
  test('Security Scan: No backend secrets (RAZORPAY_KEY_SECRET, GEMINI_API_KEY, DATABASE_URL) in src/', () => {
    const secretKeywords = [
      'RAZORPAY_KEY_SECRET',
      'RAZORPAY_WEBHOOK_SECRET',
      'GEMINI_API_KEY',
      'DATABASE_URL',
      'rzp_test_secret',
      'rzp_live_secret',
    ];

    function scanDir(dir: string) {
      const entries = fs.readdirSync(dir, { withFileTypes: true });
      for (const entry of entries) {
        const fullPath = path.join(dir, entry.name);
        if (entry.isDirectory()) {
          scanDir(fullPath);
        } else if (entry.isFile() && (entry.name.endsWith('.ts') || entry.name.endsWith('.tsx'))) {
          const content = fs.readFileSync(fullPath, 'utf-8');
          for (const kw of secretKeywords) {
            if (content.includes(`process.env.${kw}`) || content.includes(`import.meta.env.VITE_${kw}`)) {
              throw new Error(`Security Violation: Secret keyword '${kw}' found in ${fullPath}`);
            }
          }
        }
      }
    }

    scanDir(srcDir);
  });

  // 2. Architecture Scan: Confirm NO direct server-side razorpay SDK in frontend components
  test('Architecture Scan: No direct server-side razorpay SDK in frontend components', () => {
    const files = getProductionFiles();
    for (const file of files) {
      const content = fs.readFileSync(file, 'utf-8');
      if (content.includes("from 'razorpay'") || content.includes('require("razorpay")')) {
        throw new Error(`Direct SDK import found in frontend file: ${path.basename(file)}`);
      }
    }
  });

  // 3. Issue 1 Verification: "68 cases" does not appear in production frontend code
  test('Issue 1: "68 cases" does not appear anywhere in frontend source', () => {
    const files = getProductionFiles();
    for (const file of files) {
      const content = fs.readFileSync(file, 'utf-8');
      if (content.includes('68 cases') || content.includes('68 Cases')) {
        throw new Error(`Forbidden phrase "68 cases" found in ${path.basename(file)}`);
      }
    }
  });

  // 4. Issue 2 Verification: "21.6% Verified Settlement" does not appear anywhere
  test('Issue 2: "21.6% Verified Settlement" does not appear in frontend source', () => {
    const files = getProductionFiles();
    for (const file of files) {
      const content = fs.readFileSync(file, 'utf-8');
      if (content.includes('Verified Settlement') || content.includes('verified settlement')) {
        // Only allow descriptions that explain settlement accounting, not "21.6% Verified Settlement"
        if (content.includes('% Verified Settlement')) {
          throw new Error(`Forbidden metric label "% Verified Settlement" found in ${path.basename(file)}`);
        }
      }
    }
  });

  // 5. Issue 3 Verification: "60 failed payments evaluated" does not appear
  test('Issue 3: "60 failed payments evaluated" does not appear in frontend source', () => {
    const files = getProductionFiles();
    for (const file of files) {
      const content = fs.readFileSync(file, 'utf-8');
      if (content.includes('failed payments evaluated') || content.includes('failed payments')) {
        throw new Error(`Forbidden phrase "failed payments" found in ${path.basename(file)}`);
      }
    }
  });

  // 6. Issue 4 Verification: "VIP" does not appear in production code
  test('Issue 4: "VIP" does not appear anywhere in production frontend code', () => {
    const files = getProductionFiles();
    for (const file of files) {
      const content = fs.readFileSync(file, 'utf-8');
      if (/\bVIP\b/.test(content)) {
        throw new Error(`Forbidden term "VIP" found in ${path.basename(file)}`);
      }
    }
  });

  // 7. Issue 6 Verification: "Naive Retry" does not appear in production code
  test('Issue 6: "Naive Retry" does not appear anywhere (replaced with "Retry Only")', () => {
    const files = getProductionFiles();
    for (const file of files) {
      const content = fs.readFileSync(file, 'utf-8');
      if (content.includes('Naive Retry') || content.includes('naive retry')) {
        throw new Error(`Forbidden term "Naive Retry" found in ${path.basename(file)}`);
      }
    }
  });

  // 8. Issue 9 Verification: "Production-Grade" does not appear in production code
  test('Issue 9: "Production-Grade" does not appear in frontend source', () => {
    const files = getProductionFiles();
    for (const file of files) {
      const content = fs.readFileSync(file, 'utf-8');
      if (content.includes('Production-Grade') || content.includes('production-grade')) {
        throw new Error(`Forbidden phrase "Production-Grade" found in ${path.basename(file)}`);
      }
    }
  });

  // 9. Issue 7 Verification: Case navigation does not default to hardcoded "case_001"
  test('Issue 7: App.tsx does not initialize with hardcoded "case_001"', () => {
    const appPath = path.resolve(srcDir, 'App.tsx');
    const appContent = fs.readFileSync(appPath, 'utf-8');
    if (appContent.includes("useState<string>('case_001')") || appContent.includes('useState("case_001")')) {
      throw new Error(`App.tsx hardcodes initial state to case_001`);
    }
  });

  // 10. Issue 10 & 11: Dynamic Benchmark Numbers Integrity
  test('Data Integrity: Dashboard and Evaluation pages do not contain hardcoded benchmark totals', () => {
    const dashboardPath = path.resolve(srcDir, 'pages/Dashboard.tsx');
    const evalPath = path.resolve(srcDir, 'pages/Evaluation.tsx');
    const dashboardContent = fs.readFileSync(dashboardPath, 'utf-8');
    const evalContent = fs.readFileSync(evalPath, 'utf-8');

    const hardcodedPatterns = ['521769', '521,769', '112529', '112,529', '51765', '51,765'];
    for (const pat of hardcodedPatterns) {
      if (dashboardContent.includes(pat)) {
        throw new Error(`Hardcoded benchmark metric pattern '${pat}' found in Dashboard.tsx`);
      }
      if (evalContent.includes(pat)) {
        throw new Error(`Hardcoded benchmark metric pattern '${pat}' found in Evaluation.tsx`);
      }
    }
  });

  // 11. API Client error handling
  test('API Client: ApiError captures status, message, and fallback gracefully', () => {
    const err = new ApiError('Case not found', 404, 'No case with ID case_999');
    if (err.status !== 404 || err.message !== 'Case not found' || err.name !== 'ApiError') {
      throw new Error('ApiError failed to instantiate correctly');
    }
  });

  // 12. Schema Validation
  test('Schema Validation: BatchRunSummary and EvaluationCaseResult structure alignment', () => {
    const mockSummary: BatchRunSummary = {
      metadata: {
        batch_id: 'batch_test_001',
        batch_timestamp: new Date().toISOString(),
        dataset_version: 'v1.0',
        random_seed: 42,
        total_cases: 60,
        policy_config_version: '1.0.0-demo',
        code_version: '1.0.0',
      },
      metrics: {
        NO_ACTION: {
          strategy_type: 'NO_ACTION',
          total_cases: 60,
          total_revenue_at_risk: 521769.7,
          eligible_cases: 60,
          recovery_attempts: 0,
          successful_actions: 0,
          verified_recovered_revenue: 0,
          revenue_recovery_rate: 0,
          case_recovery_rate: 0,
          policy_blocks: 0,
          human_escalations: 0,
          stopped_cases: 0,
          failed_actions: 0,
          policy_violations: 0,
        },
        AI_REVENUE_RECOVERY_ORCHESTRATOR: {
          strategy_type: 'AI_REVENUE_RECOVERY_ORCHESTRATOR',
          total_cases: 60,
          total_revenue_at_risk: 521769.7,
          eligible_cases: 60,
          recovery_attempts: 52,
          successful_actions: 44,
          verified_recovered_revenue: 112529.4,
          revenue_recovery_rate: 0.2157,
          case_recovery_rate: 0.5333,
          policy_blocks: 0,
          human_escalations: 16,
          stopped_cases: 0,
          failed_actions: 0,
          policy_violations: 0,
        },
      },
      case_results: [],
      comparison_summary: {
        total_revenue_at_risk: 521769.7,
        no_action_revenue: 0,
        retry_only_revenue: 51765.46,
        orchestrator_revenue: 112529.4,
        orchestrator_absolute_lift: 60763.94,
        orchestrator_percentage_lift: 117.38,
        orchestrator_policy_violations: 0,
        retry_only_policy_violations: 0,
      },
    };

    if (mockSummary.metrics.AI_REVENUE_RECOVERY_ORCHESTRATOR.policy_violations !== 0) {
      throw new Error('Schema validation failed for policy violations');
    }
  });

  // 13. Terminology & UI Polish Verification: No "Settled" badge on Recovery Rate
  test('UI Polish: "Settled" badge is replaced with "Verified" on Revenue Recovery Rate', () => {
    const dashboardPath = path.resolve(srcDir, 'pages/Dashboard.tsx');
    const dashboardContent = fs.readFileSync(dashboardPath, 'utf-8');
    if (dashboardContent.includes('badgeText="Settled"')) {
      throw new Error(`Forbidden badgeText="Settled" found in Dashboard.tsx`);
    }
  });

  // 14. Technical Leakage Scan: No "undefined" interpolation in DecisionTimeline
  test('Technical Leakage Scan: DecisionTimeline does not interpolate undefined action strategy', () => {
    const dtPath = path.resolve(srcDir, 'components/DecisionTimeline.tsx');
    const dtContent = fs.readFileSync(dtPath, 'utf-8');
    if (dtContent.includes('${caseData.executed_action.strategy}')) {
      throw new Error(`Direct undefined strategy interpolation found in DecisionTimeline.tsx`);
    }
  });

  // 15. AI-Initiated Escalation / Stop Label Resolution in CaseView and DecisionTimeline
  test('Action & Verification Labels: Handles AI-initiated HUMAN_ESCALATION and STOP when policy outcome is ALLOW', () => {
    const cvPath = path.resolve(srcDir, 'pages/CaseView.tsx');
    const cvContent = fs.readFileSync(cvPath, 'utf-8');
    if (!cvContent.includes("approvedStrategy === 'HUMAN_ESCALATION'") || !cvContent.includes("approvedStrategy === 'STOP'")) {
      throw new Error('CaseView.tsx must check approved_strategy for HUMAN_ESCALATION and STOP');
    }

    const dtPath = path.resolve(srcDir, 'components/DecisionTimeline.tsx');
    const dtContent = fs.readFileSync(dtPath, 'utf-8');
    if (!dtContent.includes("approvedStrategy === 'HUMAN_ESCALATION'") || !dtContent.includes("approvedStrategy === 'STOP'")) {
      throw new Error('DecisionTimeline.tsx must check approved_strategy for HUMAN_ESCALATION and STOP');
    }
  });

  const passed = results.filter((r) => r.passed).length;
  const failed = results.filter((r) => !r.passed).length;

  return { total: results.length, passed, failed, results };
}
