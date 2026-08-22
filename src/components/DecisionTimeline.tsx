import React from 'react';
import { RecoveryCase } from '../types/api';
import { StatusBadge } from './StatusBadge';

interface DecisionTimelineProps {
  caseData: RecoveryCase;
}

export const DecisionTimeline: React.FC<DecisionTimelineProps> = ({ caseData }) => {
  const isDiagnosed = !!caseData.recommended_strategy || caseData.current_status !== 'DETECTED';
  const isPolicyChecked = !!caseData.policy_evaluation;
  const isExecuted = !!caseData.executed_action;
  const isVerified = !!caseData.verification_outcome;

  const policyOutcome = caseData.policy_evaluation?.outcome;
  const isPolicyBlocked = policyOutcome === 'BLOCK' || policyOutcome === 'ESCALATE' || policyOutcome === 'STOP';

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
    if (policyOutcome === 'BLOCK') return 'Blocked by Policy (No Financial Action)';
    if (policyOutcome === 'ESCALATE') return 'Escalated to Operations (No Financial Action)';
    if (policyOutcome === 'STOP') return 'Stopped by Policy (No Financial Action)';
    return 'Action Pending Authorization';
  };

  // Derive meaningful Gateway Verification description
  const getVerificationDesc = () => {
    if (isPolicyBlocked) {
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
      title: '1. Ingestion & Detection',
      desc: `Failure code ${caseData.failure_code} (${caseData.failure_category.replace(/_/g, ' ')})`,
      done: true,
      sub: `₹${caseData.amount.toLocaleString()} • Attempts: ${caseData.attempts_count}/${caseData.max_attempts_allowed}`,
    },
    {
      title: '2. Evidence Scrubbing',
      desc: 'PII masked, zero server secrets exposed',
      done: isDiagnosed || isPolicyChecked || isExecuted || isVerified,
      sub: `${caseData.masked_customer_email} • Segment: ${caseData.customer_segment}`,
    },
    {
      title: '3. Gemini Diagnosis',
      desc: caseData.strategy_rationale || 'Bounded failure categorization',
      done: isDiagnosed,
      sub: `Category: ${caseData.failure_category.replace(/_/g, ' ')}`,
    },
    {
      title: '4. Strategy Scoring',
      desc: `Deterministic ranking across locked actions`,
      done: !!caseData.recommended_strategy,
      sub: `Top strategy: ${caseData.recommended_strategy || 'Evaluating...'}`,
    },
    {
      title: '5. Policy Engine Evaluation',
      desc: caseData.policy_evaluation
        ? `Outcome: ${caseData.policy_evaluation.outcome} → Approved: ${caseData.policy_evaluation.approved_strategy}`
        : 'Policy check pending',
      done: isPolicyChecked,
      sub: caseData.policy_evaluation?.reasons?.[0] || 'Awaiting policy validation',
    },
    {
      title: '6. Action Dispatch',
      desc: getActionDesc(),
      done: isExecuted || isPolicyBlocked,
      sub: caseData.executed_action?.gateway_reference_id
        ? `Ref: ${caseData.executed_action.gateway_reference_id}`
        : isPolicyBlocked
        ? 'Financial execution skipped by policy'
        : undefined,
    },
    {
      title: '7. Gateway Verification',
      desc: getVerificationDesc(),
      done: isVerified || isPolicyBlocked,
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
        {steps.map((step, idx) => (
          <div key={idx} className="relative space-y-0.5">
            <span
              className={`absolute -left-[21px] top-1 h-2.5 w-2.5 rounded-full border ${
                step.done
                  ? 'bg-emerald-500 border-emerald-400 ring-2 ring-slate-950'
                  : 'bg-slate-800 border-slate-700 ring-2 ring-slate-950'
              }`}
            />
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium text-slate-200">{step.title}</span>
              {step.done && (
                <span className="text-[11px] text-slate-500 font-sans">Completed</span>
              )}
            </div>
            <p className="text-xs text-slate-400">{step.desc}</p>
            {step.sub && (
              <p className="text-[11px] text-slate-500 font-mono">{step.sub}</p>
            )}
          </div>
        ))}
      </div>
    </div>
  );
};
