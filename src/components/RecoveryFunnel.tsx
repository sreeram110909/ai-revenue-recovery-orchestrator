import React from 'react';
import { BatchMetrics } from '../types/api';

interface RecoveryFunnelProps {
  metrics: BatchMetrics;
  totalAtRisk: number;
}

export const RecoveryFunnel: React.FC<RecoveryFunnelProps> = ({
  metrics,
}) => {
  const formatCurrency = (val: number) => {
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      maximumFractionDigits: 2,
    }).format(val);
  };

  const recoveredCasesCount = Math.round(metrics.case_recovery_rate * metrics.total_cases);

  const steps = [
    {
      label: 'Recovery Cases',
      value: `${metrics.total_cases}`,
      barWidth: '100%',
      color: 'bg-slate-600',
    },
    {
      label: 'Successful Action Dispatches',
      value: `${metrics.successful_actions}`,
      barWidth: `${Math.round((metrics.successful_actions / metrics.total_cases) * 100)}%`,
      color: 'bg-slate-500',
    },
    {
      label: 'Verified Recoveries',
      value: `${recoveredCasesCount}`,
      barWidth: `${Math.round((recoveredCasesCount / metrics.total_cases) * 100)}%`,
      color: 'bg-emerald-600',
    },
    {
      label: 'Verified Recovered Revenue',
      value: formatCurrency(metrics.verified_recovered_revenue),
      barWidth: `${Math.round(metrics.revenue_recovery_rate * 100)}%`,
      color: 'bg-emerald-500',
    },
  ];

  return (
    <div className="rounded-lg border border-slate-800 bg-slate-900/30 p-5 space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-xs font-semibold text-white uppercase tracking-wider font-sans">
          Orchestrator Recovery Funnel
        </h3>
        <span className="text-xs font-mono text-emerald-400 font-medium">
          {(metrics.revenue_recovery_rate * 100).toFixed(1)}% Revenue Recovery
        </span>
      </div>

      <div className="space-y-3">
        {steps.map((step, idx) => (
          <div key={idx} className="space-y-1">
            <div className="flex items-center justify-between text-xs font-sans">
              <span className="text-slate-300">{step.label}</span>
              <span className="font-mono font-medium text-white">{step.value}</span>
            </div>
            <div className="h-2 w-full rounded bg-slate-800/80 overflow-hidden">
              <div
                className={`h-full rounded transition-all duration-300 ${step.color}`}
                style={{ width: step.barWidth }}
              />
            </div>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-2 gap-3 pt-3 border-t border-slate-800/60 text-xs">
        <div>
          <span className="text-slate-500 block">Revenue Recovery Rate</span>
          <span className="font-mono text-sm font-semibold text-emerald-400">
            {(metrics.revenue_recovery_rate * 100).toFixed(1)}%
          </span>
        </div>
        <div>
          <span className="text-slate-500 block">Case Recovery Rate</span>
          <span className="font-mono text-sm font-semibold text-slate-200">
            {(metrics.case_recovery_rate * 100).toFixed(1)}% ({recoveredCasesCount}/{metrics.total_cases})
          </span>
        </div>
      </div>
    </div>
  );
};
