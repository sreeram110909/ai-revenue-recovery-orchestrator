import React from 'react';
import { RecoveryCase } from '../types/api';
import { StatusBadge } from './StatusBadge';
import { RefreshCw } from 'lucide-react';

interface DecisionTimelineProps {
  caseData: RecoveryCase;
  activeStepKey?: string | null;
  completedStepKeys?: string[];
  isStreaming?: boolean;
}

export const DecisionTimeline: React.FC<DecisionTimelineProps> = ({
  caseData,
  activeStepKey,
  completedStepKeys = [],
  isStreaming = false,
}) => {
  const isDiagnosed = !!caseData.recommended_strategy || caseData.current_status !== 'DETECTED';
  const isPolicyChecked = !!caseData.policy_evaluation;
  const isExecuted = !!caseData.executed_action;
  const isVerified = !!caseData.verification_outcome;

  const policyOutcome = caseData.policy_evaluation?.outcome;
  const approvedStrategy = caseData.policy_evaluation?.approved_strategy;
  const isNoFinancialAction =
    policyOutcome === 'BLOCK' ||
    policyOutcome === 'ESCALATE' ||
    policyOutcome === 'STOP' ||
    approvedStrategy === 'HUMAN_ESCALATION' ||
    approvedStrategy === 'STOP';

  // Derive meaningful Action Dispatch description
  const getActionDesc = () => {
    if (caseData.executed_action) {
      const actionType =
        (caseData.executed_action as any).action_type ||
        (caseData.executed_action as any).strategy ||
        caseData.policy_evaluation?.approved_strategy;
      const status = caseData.executed_action.status || 'SUCCESS';

      if (actionType === 'SMART_RETRY') return `Retry Scheduled (${status})`;
      if (actionType === 'PAYMENT_LINK') return `Payment Link Created (${status})`;
      if (actionType === 'SUBSCRIPTION_RETRY') return `Subscription Retry Scheduled (${status})`;
      if (actionType === 'UPDATE_PAYMENT_METHOD') return `Payment Method Update Requested (${status})`;
      if (actionType === 'HUMAN_ESCALATION') return `Escalated to Operations`;
      if (actionType === 'STOP') return `Recovery Stopped`;
      if (actionType) return `Action Dispatched: ${actionType} (${status})`;
      return `Action Succeeded (${status})`;
    }
    if (approvedStrategy === 'HUMAN_ESCALATION') return 'Escalated to Operations (No Financial Action)';
    if (approvedStrategy === 'STOP') return 'Recovery Stopped (No Financial Action)';
    if (policyOutcome === 'BLOCK') return 'Blocked by Policy (No Financial Action)';
    if (policyOutcome === 'ESCALATE') return 'Escalated to Operations (No Financial Action)';
    if (policyOutcome === 'STOP') return 'Stopped by Policy (No Financial Action)';
    return 'Action Pending Authorization';
  };

  // Derive meaningful Gateway Verification description
  const getVerificationDesc = () => {
    if (isNoFinancialAction) {
      return 'No financial action dispatched (₹0.00 recovered)';
    }
    if (caseData.verification_outcome) {
      const status = caseData.verification_outcome.status;
      if (status === 'PAID' || status === 'CAPTURED') {
        return `Verified Paid (₹${caseData.verified_recovered_amount.toLocaleString()} recovered)`;
      }
      return `Pending Settlement / Unpaid (₹0.00 recovered)`;
    }
    return 'Independent verification pending';
  };

  const steps = [
    {
      key: 'detect_and_load',
      title: '1. Ingestion & Detection',
      desc: `Failure code ${caseData.failure_code} (${caseData.failure_category.replace(/_/g, ' ')})`,
      staticDone: true,
      sub: `₹${caseData.amount.toLocaleString()} • Attempts: ${caseData.attempts_count}/${caseData.max_attempts_allowed}`,
    },
    {
      key: 'extract_evidence',
      title: '2. Evidence Scrubbing',
      desc: 'PII masked, zero server secrets exposed',
      staticDone: isDiagnosed || isPolicyChecked || isExecuted || isVerified,
      sub: `${caseData.masked_customer_email} • Segment: ${caseData.customer_segment}`,
    },
    {
      key: 'diagnose',
      title: '3. Gemini Diagnosis',
      desc: caseData.strategy_rationale || 'Bounded failure categorization',
      staticDone: isDiagnosed,
      sub: `Category: ${caseData.failure_category.replace(/_/g, ' ')}`,
    },
    {
      key: 'score_strategy',
      title: '4. Strategy Scoring',
      desc: `Deterministic ranking across locked actions`,
      staticDone: !!caseData.recommended_strategy,
      sub: caseData.recommended_strategy
        ? `Top strategy: ${caseData.recommended_strategy}`
        : 'Strategy ranking pending',
    },
    {
      key: 'evaluate_policy',
      title: '5. Policy Engine Evaluation',
      desc: caseData.policy_evaluation
        ? `Outcome: ${caseData.policy_evaluation.outcome} → Approved: ${caseData.policy_evaluation.approved_strategy}`
        : 'Policy check pending',
      staticDone: isPolicyChecked,
      sub: caseData.policy_evaluation?.reasons?.[0] || 'Awaiting policy validation',
    },
    {
      key: 'execute_action',
      title: '6. Action Dispatch',
      desc: getActionDesc(),
      staticDone: isExecuted || isNoFinancialAction,
      sub: caseData.executed_action?.gateway_reference_id
        ? `Ref: ${caseData.executed_action.gateway_reference_id}`
        : isNoFinancialAction
        ? 'Financial execution skipped by policy'
        : undefined,
    },
    {
      key: 'verify_outcome',
      title: '7. Gateway Verification',
      desc: getVerificationDesc(),
      staticDone: isVerified || isNoFinancialAction,
      sub: `Final Status: ${caseData.current_status}`,
    },
  ];

  return (
    <div className="rounded-lg border border-slate-800 bg-slate-900/30 p-5 space-y-4">
      <div className="flex items-center justify-between border-b border-slate-800 pb-3">
        <h4 className="text-xs font-semibold text-white uppercase tracking-wider font-sans">
          Decision Flow (LangGraph State Machine)
        </h4>
        <StatusBadge status={caseData.current_status} size="sm" />
      </div>

      <div className="space-y-4 pl-4 border-l border-slate-800 relative">
        {steps.map((step, idx) => {
          const isDone = isStreaming
            ? completedStepKeys.includes(step.key)
            : step.staticDone;
          const inProgress = isStreaming && activeStepKey === step.key && !isDone;

          return (
            <div key={idx} className="relative space-y-0.5 transition-all duration-300">
              <span
                className={`absolute -left-[21px] top-1 h-2.5 w-2.5 rounded-full border transition-all duration-300 ${
                  inProgress
                    ? 'bg-sky-400 border-sky-300 ring-4 ring-sky-500/30 animate-pulse'
                    : isDone
                    ? 'bg-emerald-500 border-emerald-400 ring-2 ring-slate-950'
                    : 'bg-slate-800 border-slate-700 ring-2 ring-slate-950'
                }`}
              />
              <div className="flex items-center justify-between">
                <span
                  className={`text-xs font-medium transition-colors ${
                    inProgress
                      ? 'text-sky-300 font-semibold'
                      : isDone
                      ? 'text-slate-200'
                      : 'text-slate-500'
                  }`}
                >
                  {step.title}
                </span>

                {inProgress ? (
                  <span className="text-[11px] text-sky-400 font-sans flex items-center gap-1">
                    <RefreshCw className="w-2.5 h-2.5 animate-spin" /> In Progress...
                  </span>
                ) : isDone ? (
                  <span className="text-[11px] text-emerald-400/90 font-sans">Completed</span>
                ) : (
                  <span className="text-[11px] text-slate-600 font-sans">Pending</span>
                )}
              </div>
              <p className={`text-xs transition-colors ${isDone || inProgress ? 'text-slate-400' : 'text-slate-600'}`}>
                {step.desc}
              </p>
              {step.sub && (
                <p className={`text-[11px] font-mono transition-colors ${isDone || inProgress ? 'text-slate-500' : 'text-slate-700'}`}>
                  {step.sub}
                </p>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};
