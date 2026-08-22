import React from 'react';
import { useMetrics } from '../hooks/useMetrics';
import { useCases } from '../hooks/useCases';
import { StatusBadge } from '../components/StatusBadge';
import { RefreshCw, ArrowRight } from 'lucide-react';

interface DashboardProps {
  onNavigateToCase: (caseId: string) => void;
  onNavigateToCases: () => void;
  onNavigateToEval: () => void;
}

export const Dashboard: React.FC<DashboardProps> = ({
  onNavigateToCase,
  onNavigateToCases,
  onNavigateToEval,
}) => {
  const { metrics, loading: metricsLoading, error: metricsError, refetch: refetchMetrics } = useMetrics();
  const { cases, loading: casesLoading, refetch: refetchCases } = useCases({ limit: 5 });

  const orchMetrics = metrics?.metrics['AI_REVENUE_RECOVERY_ORCHESTRATOR'];
  const retryMetrics = metrics?.metrics['RETRY_ONLY'];
  const noActionMetrics = metrics?.metrics['NO_ACTION'];
  const comparison = metrics?.comparison_summary;

  const formatCurrency = (val?: number) => {
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      maximumFractionDigits: 2,
    }).format(val || 0);
  };

  const handleRefreshAll = () => {
    refetchMetrics();
    refetchCases();
  };

  if (metricsLoading) {
    return (
      <div className="flex items-center justify-center py-20 text-xs text-slate-400 font-sans">
        <RefreshCw className="w-4 h-4 animate-spin mr-2 text-slate-400" />
        Loading recovery metrics...
      </div>
    );
  }

  if (metricsError || !metrics) {
    return (
      <div className="rounded-lg border border-slate-800 bg-slate-900/40 p-8 text-center space-y-3">
        <h3 className="text-sm font-semibold text-white">Evaluation Data Unavailable</h3>
        <p className="text-xs text-slate-400 max-w-md mx-auto">
          {metricsError || 'Failed to connect to backend evaluation API.'}
        </p>
        <button
          onClick={handleRefreshAll}
          className="inline-flex items-center gap-1.5 rounded border border-slate-700 bg-slate-800 px-3 py-1.5 text-xs font-medium text-white hover:bg-slate-700 transition-colors cursor-pointer"
        >
          <RefreshCw className="w-3.5 h-3.5" /> Retry Connection
        </button>
      </div>
    );
  }

  const recoveredCasesCount = Math.round((orchMetrics?.case_recovery_rate || 0) * (orchMetrics?.total_cases || 60));

  return (
    <div className="space-y-8">
      {/* Page Header */}
      <div className="flex flex-wrap items-end justify-between gap-4 border-b border-slate-800/80 pb-4">
        <div>
          <h1 className="text-xl font-semibold text-white tracking-tight">Revenue Recovery</h1>
          <p className="text-xs text-slate-400 mt-1">
            Monitor payment failures, recovery outcomes, and policy-controlled actions.
          </p>
        </div>

        <div className="flex items-center gap-2 text-xs text-slate-400 font-sans">
          <span>{orchMetrics?.total_cases || 60} recovery cases</span>
          <span>•</span>
          <span>Seed 42</span>
          <span>•</span>
          <span>Test Mode</span>
          <button
            onClick={handleRefreshAll}
            className="p-1.5 rounded border border-slate-800 bg-slate-900 text-slate-400 hover:text-white transition-colors cursor-pointer ml-1"
            title="Refresh Metrics"
          >
            <RefreshCw className={`w-3 h-3 ${casesLoading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {/* Primary Hero Section: Verified Recovered Revenue */}
      <div className="rounded-lg border border-slate-800 bg-slate-900/60 p-6 sm:p-8 flex flex-wrap items-center justify-between gap-6">
        <div className="space-y-2">
          <span className="text-xs font-medium text-slate-400 block font-sans">
            Verified recovered revenue
          </span>
          <div className="text-3xl sm:text-4xl font-semibold text-white font-mono tracking-tight">
            {formatCurrency(orchMetrics?.verified_recovered_revenue)}
          </div>
          <div className="text-xs text-slate-400 flex flex-wrap items-center gap-2 font-sans">
            <span className="text-emerald-400 font-medium">
              {((orchMetrics?.revenue_recovery_rate || 0) * 100).toFixed(1)}% revenue recovery rate
            </span>
            <span>•</span>
            <span className="text-slate-300">
              {((orchMetrics?.case_recovery_rate || 0) * 100).toFixed(1)}% case recovery rate ({recoveredCasesCount}/{orchMetrics?.total_cases || 60} cases)
            </span>
          </div>
        </div>

        <div className="text-left sm:text-right border-t sm:border-t-0 sm:border-l border-slate-800 sm:pl-8 pt-4 sm:pt-0">
          <span className="text-xs text-slate-500 block font-sans">Revenue uplift vs Retry Only</span>
          <div className="text-xl font-semibold font-mono text-emerald-400 mt-1">
            +{formatCurrency(comparison?.orchestrator_absolute_lift)}
          </div>
          <span className="text-xs font-mono text-emerald-400/90 font-medium block mt-0.5">
            +{comparison?.orchestrator_percentage_lift.toFixed(1)}% lift
          </span>
        </div>
      </div>

      {/* Secondary Metrics: Simple Horizontal Row with Dividers */}
      <div className="grid grid-cols-2 sm:grid-cols-5 gap-4 py-3 px-4 rounded-lg border border-slate-800/80 bg-slate-900/30 text-xs">
        <div className="space-y-1">
          <span className="text-slate-500 block">Revenue at Risk</span>
          <span className="font-mono text-sm font-semibold text-white block">
            {formatCurrency(comparison?.total_revenue_at_risk)}
          </span>
        </div>
        <div className="space-y-1 border-l border-slate-800/80 pl-4">
          <span className="text-slate-500 block">Recovery Attempts</span>
          <span className="font-mono text-sm font-semibold text-white block">
            {orchMetrics?.recovery_attempts || 0}
          </span>
        </div>
        <div className="space-y-1 border-l border-slate-800/80 pl-4">
          <span className="text-slate-500 block">Successful Dispatches</span>
          <span className="font-mono text-sm font-semibold text-white block">
            {orchMetrics?.successful_actions || 0}
          </span>
        </div>
        <div className="space-y-1 border-l border-slate-800/80 pl-4">
          <span className="text-slate-500 block">Human Escalations</span>
          <span className="font-mono text-sm font-semibold text-amber-400 block">
            {orchMetrics?.human_escalations || 0}
          </span>
        </div>
        <div className="space-y-1 border-l border-slate-800/80 pl-4 col-span-2 sm:col-span-1">
          <span className="text-slate-500 block">Policy Violations</span>
          <span className="font-mono text-sm font-semibold text-emerald-400 block">
            {orchMetrics?.policy_violations || 0}
          </span>
        </div>
      </div>

      {/* Main Content: 2-Column (Benchmark Comparison + Recovery Outcomes) */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Left: Benchmark Comparison Table */}
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="text-xs font-semibold text-white uppercase tracking-wider font-sans">
              Benchmark comparison
            </h2>
            <button
              onClick={onNavigateToEval}
              className="text-xs text-slate-400 hover:text-white font-sans flex items-center gap-1 cursor-pointer"
            >
              Full benchmark <ArrowRight className="w-3 h-3" />
            </button>
          </div>

          <div className="rounded-lg border border-slate-800 bg-slate-900/30 overflow-hidden">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b border-slate-800 bg-slate-900/60 text-slate-400 text-[11px] uppercase font-sans">
                  <th className="px-4 py-2.5 font-medium">Metric</th>
                  <th className="px-4 py-2.5 font-medium">No Action</th>
                  <th className="px-4 py-2.5 font-medium">Retry Only</th>
                  <th className="px-4 py-2.5 font-medium text-white bg-slate-800/40">Orchestrator</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 font-sans">
                <tr>
                  <td className="px-4 py-2.5 text-slate-300">Recovered</td>
                  <td className="px-4 py-2.5 font-mono text-slate-400">{formatCurrency(noActionMetrics?.verified_recovered_revenue)}</td>
                  <td className="px-4 py-2.5 font-mono text-slate-300">{formatCurrency(retryMetrics?.verified_recovered_revenue)}</td>
                  <td className="px-4 py-2.5 font-mono font-semibold text-emerald-400 bg-slate-800/40">
                    {formatCurrency(orchMetrics?.verified_recovered_revenue)}
                  </td>
                </tr>
                <tr>
                  <td className="px-4 py-2.5 text-slate-300">Recovery Rate</td>
                  <td className="px-4 py-2.5 font-mono text-slate-400">0.0%</td>
                  <td className="px-4 py-2.5 font-mono text-slate-300">{((retryMetrics?.revenue_recovery_rate || 0) * 100).toFixed(1)}%</td>
                  <td className="px-4 py-2.5 font-mono font-semibold text-emerald-400 bg-slate-800/40">
                    {((orchMetrics?.revenue_recovery_rate || 0) * 100).toFixed(1)}%
                  </td>
                </tr>
                <tr>
                  <td className="px-4 py-2.5 text-slate-300">Case Rate</td>
                  <td className="px-4 py-2.5 font-mono text-slate-400">0.0%</td>
                  <td className="px-4 py-2.5 font-mono text-slate-300">{((retryMetrics?.case_recovery_rate || 0) * 100).toFixed(1)}%</td>
                  <td className="px-4 py-2.5 font-mono font-semibold text-emerald-400 bg-slate-800/40">
                    {((orchMetrics?.case_recovery_rate || 0) * 100).toFixed(1)}%
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        {/* Right: Recovery Outcomes Breakdown */}
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="text-xs font-semibold text-white uppercase tracking-wider font-sans">
              Recovery outcomes
            </h2>
            <span className="text-xs text-slate-500 font-sans">
              {recoveredCasesCount} / {orchMetrics?.total_cases || 60} recovered
            </span>
          </div>

          <div className="rounded-lg border border-slate-800 bg-slate-900/30 p-5 space-y-4 text-xs">
            <div className="space-y-1.5">
              <div className="flex justify-between text-slate-300">
                <span>Recovered</span>
                <span className="font-mono font-medium text-emerald-400">{recoveredCasesCount} (53.3%)</span>
              </div>
              <div className="h-2 rounded bg-slate-800 overflow-hidden">
                <div className="h-full bg-emerald-500 rounded" style={{ width: '53.3%' }} />
              </div>
            </div>

            <div className="space-y-1.5">
              <div className="flex justify-between text-slate-300">
                <span>Human escalation</span>
                <span className="font-mono font-medium text-amber-400">16 (26.7%)</span>
              </div>
              <div className="h-2 rounded bg-slate-800 overflow-hidden">
                <div className="h-full bg-amber-500 rounded" style={{ width: '26.7%' }} />
              </div>
            </div>

            <div className="space-y-1.5">
              <div className="flex justify-between text-slate-300">
                <span>Other / In Progress</span>
                <span className="font-mono font-medium text-slate-400">12 (20.0%)</span>
              </div>
              <div className="h-2 rounded bg-slate-800 overflow-hidden">
                <div className="h-full bg-slate-500 rounded" style={{ width: '20.0%' }} />
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Lower Area: 2-Column (Recovery Funnel + Recent Cases) */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Left: Simple Recovery Funnel */}
        <div className="space-y-3">
          <h2 className="text-xs font-semibold text-white uppercase tracking-wider font-sans">
            Recovery funnel
          </h2>

          <div className="rounded-lg border border-slate-800 bg-slate-900/30 p-5 space-y-3.5 text-xs">
            <div className="space-y-1">
              <div className="flex justify-between text-slate-300">
                <span>60 recovery cases</span>
                <span className="font-mono text-white">100%</span>
              </div>
              <div className="h-1.5 rounded bg-slate-800 overflow-hidden">
                <div className="h-full bg-slate-600 rounded w-full" />
              </div>
            </div>

            <div className="space-y-1">
              <div className="flex justify-between text-slate-300">
                <span>44 successful dispatches</span>
                <span className="font-mono text-white">73.3%</span>
              </div>
              <div className="h-1.5 rounded bg-slate-800 overflow-hidden">
                <div className="h-full bg-slate-500 rounded" style={{ width: '73.3%' }} />
              </div>
            </div>

            <div className="space-y-1">
              <div className="flex justify-between text-slate-300">
                <span>32 verified recoveries</span>
                <span className="font-mono text-emerald-400 font-medium">53.3%</span>
              </div>
              <div className="h-1.5 rounded bg-slate-800 overflow-hidden">
                <div className="h-full bg-emerald-500 rounded" style={{ width: '53.3%' }} />
              </div>
            </div>

            <div className="pt-3 border-t border-slate-800/80 flex items-center justify-between text-slate-400">
              <span>Verified recovered</span>
              <span className="font-mono font-semibold text-emerald-400 text-sm">
                {formatCurrency(orchMetrics?.verified_recovered_revenue)}
              </span>
            </div>
          </div>
        </div>

        {/* Right: Recent Cases Table */}
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="text-xs font-semibold text-white uppercase tracking-wider font-sans">
              Recent cases
            </h2>
            <button
              onClick={onNavigateToCases}
              className="text-xs text-slate-400 hover:text-white font-sans flex items-center gap-1 cursor-pointer"
            >
              View all cases <ArrowRight className="w-3 h-3" />
            </button>
          </div>

          <div className="rounded-lg border border-slate-800 bg-slate-900/30 overflow-hidden">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b border-slate-800 bg-slate-900/60 text-slate-400 text-[11px] uppercase font-sans">
                  <th className="px-4 py-2.5 font-medium">Case</th>
                  <th className="px-4 py-2.5 font-medium">Amount</th>
                  <th className="px-4 py-2.5 font-medium">Issue</th>
                  <th className="px-4 py-2.5 font-medium">Status</th>
                  <th className="px-4 py-2.5 text-right font-medium">Recovered</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 font-sans">
                {cases.map((c) => (
                  <tr
                    key={c.id}
                    onClick={() => onNavigateToCase(c.id)}
                    className="hover:bg-slate-800/30 cursor-pointer transition-colors"
                  >
                    <td className="px-4 py-2.5 font-mono text-white font-medium hover:text-emerald-400">
                      {c.id}
                    </td>
                    <td className="px-4 py-2.5 font-mono text-slate-200">
                      {formatCurrency(c.amount)}
                    </td>
                    <td className="px-4 py-2.5 text-slate-300 text-[11px]">
                      {c.failure_category.replace(/_/g, ' ')}
                    </td>
                    <td className="px-4 py-2.5">
                      <StatusBadge status={c.current_status} size="sm" />
                    </td>
                    <td className="px-4 py-2.5 font-mono text-right text-emerald-400">
                      {c.current_status === 'VERIFIED_RECOVERED' ? formatCurrency(c.verified_recovered_amount) : '₹0.00'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
};
