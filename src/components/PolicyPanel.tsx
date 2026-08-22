import React from 'react';
import { PolicyCheckResult, RecoveryStrategy } from '../types/api';
import { StatusBadge } from './StatusBadge';
import { Check, X } from 'lucide-react';

interface PolicyPanelProps {
  policy?: PolicyCheckResult | null;
  recommendedStrategy?: RecoveryStrategy | null;
}

export const PolicyPanel: React.FC<PolicyPanelProps> = ({
  policy,
  recommendedStrategy,
}) => {
  if (!policy) {
    return (
      <div className="rounded-lg border border-slate-800 bg-slate-900/30 p-6 text-center text-slate-500 text-xs font-sans">
        Policy evaluation has not yet been executed for this case.
      </div>
    );
  }

  const isDivergent = policy.proposed_strategy !== policy.approved_strategy;

  return (
    <div className="rounded-lg border border-slate-800 bg-slate-900/30 p-5 space-y-5">
      {/* Concept Header */}
      <div className="flex items-center justify-between border-b border-slate-800 pb-3">
        <div>
          <h4 className="text-xs font-semibold text-white uppercase tracking-wider font-sans">
            Policy Engine Authorization
          </h4>
          <p className="text-xs text-slate-500 mt-0.5">
            AI recommendation is advisory. Policy Engine is authoritative.
          </p>
        </div>
        <StatusBadge status={policy.outcome} size="sm" />
      </div>

      {/* Decision Flow Line */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs">
        <div className="p-3 rounded border border-slate-800 bg-slate-950/60">
          <span className="text-slate-500 block text-[11px]">1. AI Recommendation</span>
          <span className="font-mono text-white font-medium mt-1 block">
            {policy.proposed_strategy || recommendedStrategy || 'None'}
          </span>
        </div>

        <div className="p-3 rounded border border-slate-800 bg-slate-950/60">
          <span className="text-slate-500 block text-[11px]">2. Policy Decision</span>
          <div className="mt-1">
            <StatusBadge status={policy.outcome} size="sm" />
          </div>
        </div>

        <div className="p-3 rounded border border-slate-800 bg-slate-950/60">
          <span className="text-slate-500 block text-[11px]">3. Approved Action</span>
          <span className="font-mono text-emerald-400 font-medium mt-1 block">
            {policy.approved_strategy}
          </span>
        </div>
      </div>

      {/* Divergence Notification if any */}
      {isDivergent && (
        <div className="p-3 rounded border border-indigo-500/20 bg-indigo-500/5 text-xs text-indigo-300">
          Action was modified from <span className="font-mono text-white">{policy.proposed_strategy}</span> to{' '}
          <span className="font-mono text-emerald-300">{policy.approved_strategy}</span> by Policy Rule ({policy.outcome}).
        </div>
      )}

      {/* Rule Checks List */}
      {policy.rule_checks && Object.keys(policy.rule_checks).length > 0 && (
        <div className="space-y-2">
          <span className="text-xs text-slate-400 font-medium block">
            Guardrail Rule Checks
          </span>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs">
            {Object.entries(policy.rule_checks).map(([ruleName, passed]) => (
              <div
                key={ruleName}
                className="flex items-center justify-between p-2 rounded border border-slate-800/80 bg-slate-950/40"
              >
                <span className="text-slate-300 font-mono text-[11px] truncate">
                  {ruleName.replace(/_/g, ' ')}
                </span>
                {passed ? (
                  <span className="text-emerald-400 flex items-center gap-1 text-[11px] font-medium">
                    <Check className="w-3 h-3" /> PASS
                  </span>
                ) : (
                  <span className="text-rose-400 flex items-center gap-1 text-[11px] font-medium">
                    <X className="w-3 h-3" /> BLOCKED
                  </span>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Policy Reasons */}
      {policy.reasons && policy.reasons.length > 0 && (
        <div className="space-y-1.5 text-xs">
          <span className="text-slate-400 font-medium block">Decision Reasons</span>
          <ul className="space-y-1 text-slate-300">
            {policy.reasons.map((r, i) => (
              <li key={i} className="flex items-start gap-1.5 text-slate-400">
                <span className="text-slate-600">•</span>
                <span>{r}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
};
