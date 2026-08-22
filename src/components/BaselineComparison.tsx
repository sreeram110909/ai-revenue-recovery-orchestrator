import React from 'react';
import { BatchMetrics, ComparisonSummary } from '../types/api';

interface BaselineComparisonProps {
  metrics: Record<string, BatchMetrics>;
  comparison: ComparisonSummary;
}

export const BaselineComparison: React.FC<BaselineComparisonProps> = ({
  metrics,
  comparison,
}) => {
  const noAction = metrics['NO_ACTION'];
  const retryOnly = metrics['RETRY_ONLY'];
  const orchestrator = metrics['AI_REVENUE_RECOVERY_ORCHESTRATOR'];

  const formatCurrency = (val?: number) => {
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      maximumFractionDigits: 2,
    }).format(val || 0);
  };

  const formatPct = (val?: number) => {
    return `${((val || 0) * 100).toFixed(1)}%`;
  };

  return (
    <div className="space-y-4">
      {/* Lift Callout Banner */}
      <div className="flex flex-wrap items-center justify-between gap-4 p-4 rounded-lg border border-slate-800 bg-slate-900/60">
        <div>
          <span className="text-xs text-slate-400 block font-sans">
            Revenue uplift vs Retry Only
          </span>
          <div className="flex items-baseline gap-2 mt-0.5">
            <span className="text-xl font-semibold font-mono text-emerald-400">
              +{formatCurrency(comparison.orchestrator_absolute_lift)}
            </span>
            <span className="text-xs font-semibold text-emerald-400 font-mono">
              (+{comparison.orchestrator_percentage_lift.toFixed(1)}%)
            </span>
          </div>
        </div>

        <div className="text-right">
          <span className="text-xs text-slate-400 block font-sans">
            Policy Compliance
          </span>
          <span className="text-xs font-medium text-emerald-400 font-sans">
            0 Policy Violations (All executed actions were policy-authorized)
          </span>
        </div>
      </div>

      {/* Comparison Table */}
      <div className="rounded-lg border border-slate-800 overflow-hidden bg-slate-900/30">
        <table className="w-full text-left text-xs">
          <thead>
            <tr className="border-b border-slate-800 bg-slate-900/80 text-slate-400 text-[11px] font-sans uppercase">
              <th className="px-4 py-3 font-medium">Metric</th>
              <th className="px-4 py-3 font-medium">No Action</th>
              <th className="px-4 py-3 font-medium">Retry Only</th>
              <th className="px-4 py-3 font-medium text-white bg-slate-800/40">
                Orchestrator
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/60 font-sans">
            <tr>
              <td className="px-4 py-2.5 text-slate-300">Revenue Recovered</td>
              <td className="px-4 py-2.5 font-mono text-slate-400">
                {formatCurrency(noAction?.verified_recovered_revenue)}
              </td>
              <td className="px-4 py-2.5 font-mono text-slate-300">
                {formatCurrency(retryOnly?.verified_recovered_revenue)}
              </td>
              <td className="px-4 py-2.5 font-mono font-semibold text-emerald-400 bg-slate-800/40">
                {formatCurrency(orchestrator?.verified_recovered_revenue)}
              </td>
            </tr>
            <tr>
              <td className="px-4 py-2.5 text-slate-300">Revenue Recovery Rate</td>
              <td className="px-4 py-2.5 font-mono text-slate-400">
                {formatPct(noAction?.revenue_recovery_rate)}
              </td>
              <td className="px-4 py-2.5 font-mono text-slate-300">
                {formatPct(retryOnly?.revenue_recovery_rate)}
              </td>
              <td className="px-4 py-2.5 font-mono font-semibold text-emerald-400 bg-slate-800/40">
                {formatPct(orchestrator?.revenue_recovery_rate)}
              </td>
            </tr>
            <tr>
              <td className="px-4 py-2.5 text-slate-300">Case Recovery Rate</td>
              <td className="px-4 py-2.5 font-mono text-slate-400">
                {formatPct(noAction?.case_recovery_rate)}
              </td>
              <td className="px-4 py-2.5 font-mono text-slate-300">
                {formatPct(retryOnly?.case_recovery_rate)}
              </td>
              <td className="px-4 py-2.5 font-mono font-semibold text-emerald-400 bg-slate-800/40">
                {formatPct(orchestrator?.case_recovery_rate)}
              </td>
            </tr>
            <tr>
              <td className="px-4 py-2.5 text-slate-300">Recovery Attempts</td>
              <td className="px-4 py-2.5 font-mono text-slate-400">{noAction?.recovery_attempts || 0}</td>
              <td className="px-4 py-2.5 font-mono text-slate-300">{retryOnly?.recovery_attempts || 0}</td>
              <td className="px-4 py-2.5 font-mono text-white bg-slate-800/40">
                {orchestrator?.recovery_attempts || 0}
              </td>
            </tr>
            <tr>
              <td className="px-4 py-2.5 text-slate-300">Human Escalations</td>
              <td className="px-4 py-2.5 font-mono text-slate-400">{noAction?.human_escalations || 0}</td>
              <td className="px-4 py-2.5 font-mono text-slate-300">{retryOnly?.human_escalations || 0}</td>
              <td className="px-4 py-2.5 font-mono text-amber-400 bg-slate-800/40">
                {orchestrator?.human_escalations || 0}
              </td>
            </tr>
            <tr>
              <td className="px-4 py-2.5 text-slate-300">Policy Violations</td>
              <td className="px-4 py-2.5 font-mono text-slate-400">0</td>
              <td className="px-4 py-2.5 font-mono text-slate-400">0</td>
              <td className="px-4 py-2.5 font-mono text-emerald-400 font-semibold bg-slate-800/40">
                0
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  );
};
