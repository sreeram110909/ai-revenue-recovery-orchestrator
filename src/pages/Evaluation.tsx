import React, { useState } from 'react';
import { useMetrics } from '../hooks/useMetrics';
import { StatusBadge } from '../components/StatusBadge';
import { RefreshCw, ChevronDown, ChevronUp, Sliders, Check } from 'lucide-react';

export const Evaluation: React.FC = () => {
  const { metrics, loading, running, error, refetch, runBenchmark } = useMetrics();
  const [seed, setSeed] = useState<number>(42);
  const [count, setCount] = useState<number>(60);
  const [showConfig, setShowConfig] = useState<boolean>(false);
  const [showMetadata, setShowMetadata] = useState<boolean>(false);
  const [showCaseResults, setShowCaseResults] = useState<boolean>(false);
  const [benchmarkNotification, setBenchmarkNotification] = useState<string | null>(null);

  const formatCurrency = (val?: number) => {
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      maximumFractionDigits: 2,
    }).format(val || 0);
  };

  const handleRunCustomBenchmark = async () => {
    setBenchmarkNotification(null);
    try {
      const res = await runBenchmark({ seed, count, dataset_version: 'v1.0' });
      setShowConfig(false);
      if (res) {
        setBenchmarkNotification(`Benchmark completed: ${res.metadata.total_cases} cases evaluated (Seed: ${res.metadata.random_seed}, Batch: ${res.metadata.batch_id}).`);
      }
    } catch {
      // handled in hook
    }
  };

  const handleRerunStandardBenchmark = async () => {
    setBenchmarkNotification(null);
    try {
      const res = await runBenchmark({ seed: 42, count: 60, dataset_version: 'v1.0' });
      if (res) {
        setBenchmarkNotification(`Benchmark completed: ${res.metadata.total_cases} cases evaluated across 3 baselines (Batch: ${res.metadata.batch_id}).`);
      }
    } catch {
      // handled in hook
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20 text-xs text-[#8B93A1] font-sans">
        <RefreshCw className="w-4 h-4 animate-spin mr-2" />
        Loading benchmark results...
      </div>
    );
  }

  if (error || !metrics) {
    return (
      <div className="rounded-lg border border-[#262B33] bg-[#14171C] p-8 text-center space-y-3">
        <h3 className="text-sm font-semibold text-[#ECEFF3] font-heading">Benchmark Data Unavailable</h3>
        <p className="text-xs text-[#8B93A1] max-w-md mx-auto">
          {error || 'Unable to retrieve evaluation results from backend.'}
        </p>
        <button
          onClick={() => refetch()}
          className="inline-flex items-center gap-1.5 rounded border border-[#262B33] bg-[#14171C] px-3 py-1.5 text-xs font-medium text-[#ECEFF3] hover:bg-[#262B33]/60 transition-colors cursor-pointer"
        >
          <RefreshCw className="w-3.5 h-3.5" /> Retry
        </button>
      </div>
    );
  }

  const orchMetrics = metrics.metrics['AI_REVENUE_RECOVERY_ORCHESTRATOR'];
  const retryMetrics = metrics.metrics['RETRY_ONLY'];
  const noActionMetrics = metrics.metrics['NO_ACTION'];
  const comparison = metrics.comparison_summary;

  // Dynamic derivations based on active batch run metadata and metrics
  const totalCases = orchMetrics?.total_cases || metrics.metadata?.total_cases || 60;
  const recoveredCasesCount = Math.round((orchMetrics?.case_recovery_rate || 0) * totalCases);
  const successfulDispatches = orchMetrics?.successful_actions || 0;
  const caseRatePct = ((orchMetrics?.case_recovery_rate || 0) * 100).toFixed(1);
  const dispatchesPct = totalCases > 0 ? ((successfulDispatches / totalCases) * 100).toFixed(1) : '0.0';
  const caseResultsCount = metrics.case_results?.length || 0;

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex flex-wrap items-end justify-between gap-4 border-b border-[#262B33] pb-4">
        <div>
          <h1 className="text-xl font-semibold text-[#ECEFF3] tracking-tight font-heading">Benchmark</h1>
          <p className="text-xs text-[#8B93A1] mt-1">
            {metrics.metadata?.total_cases || totalCases} recovery cases · Seed {metrics.metadata?.random_seed ?? 42} · Synthetic evaluation
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowConfig(!showConfig)}
            className="inline-flex items-center gap-1.5 rounded border border-[#262B33] bg-[#14171C] px-3 py-1.5 text-xs font-medium text-[#8B93A1] hover:text-[#ECEFF3] transition-colors cursor-pointer"
          >
            <Sliders className="w-3.5 h-3.5" />
            {showConfig ? 'Hide config' : 'Configure benchmark'}
          </button>
          <button
            onClick={handleRerunStandardBenchmark}
            disabled={running}
            className="inline-flex items-center gap-1.5 rounded border border-[#262B33] bg-[#14171C] px-3 py-1.5 text-xs font-medium text-[#ECEFF3] hover:bg-[#262B33]/60 disabled:opacity-50 transition-colors cursor-pointer"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${running ? 'animate-spin' : ''}`} />
            {running ? 'Running...' : 'Re-run benchmark'}
          </button>
        </div>
      </div>

      {/* Benchmark Success Banner */}
      {benchmarkNotification && (
        <div className="p-3 rounded-lg border border-[#2DBE8F]/30 bg-[#2DBE8F]/10 text-xs text-[#2DBE8F] flex items-center justify-between animate-fade-in">
          <div className="flex items-center gap-2">
            <Check className="w-4 h-4 text-[#2DBE8F] shrink-0" />
            <span>{benchmarkNotification}</span>
          </div>
          <button
            onClick={() => setBenchmarkNotification(null)}
            className="text-[11px] text-[#2DBE8F] hover:text-[#ECEFF3] cursor-pointer"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Config Drawer */}
      {showConfig && (
        <div className="rounded-lg border border-[#262B33] bg-[#14171C] p-4 space-y-3">
          <span className="text-xs font-semibold text-[#ECEFF3]/80 font-sans block">
            Configure benchmark run
          </span>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs">
            <div>
              <label className="text-[#8B93A1] block mb-1">Random seed</label>
              <input
                type="number"
                value={seed}
                onChange={(e) => setSeed(parseInt(e.target.value) || 42)}
                className="w-full rounded border border-[#262B33] bg-[#0B0D10] px-2.5 py-1.5 text-[#ECEFF3] font-mono text-xs focus:outline-none"
              />
            </div>
            <div>
              <label className="text-[#8B93A1] block mb-1">Dataset size</label>
              <input
                type="number"
                value={count}
                min={50}
                max={200}
                onChange={(e) => setCount(parseInt(e.target.value) || 60)}
                className="w-full rounded border border-[#262B33] bg-[#0B0D10] px-2.5 py-1.5 text-[#ECEFF3] font-mono text-xs focus:outline-none"
              />
            </div>
            <div className="flex items-end">
              <button
                onClick={handleRunCustomBenchmark}
                disabled={running}
                className="w-full rounded border border-[#262B33] bg-[#14171C] px-3 py-1.5 text-xs font-medium text-[#ECEFF3] hover:bg-[#262B33]/60 disabled:opacity-50 transition-colors cursor-pointer"
              >
                {running ? 'Executing...' : 'Run with settings'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Primary Result Banner */}
      <div className="rounded-lg border border-[#262B33] bg-[#14171C] p-6 sm:p-8 flex flex-wrap items-center justify-between gap-6">
        <div className="space-y-1.5">
          <span className="text-xs font-medium text-[#8B93A1] block font-sans">
            Measured recovered revenue
          </span>
          <div className="text-3xl sm:text-4xl font-semibold text-[#ECEFF3] font-mono tracking-tight">
            {formatCurrency(orchMetrics?.verified_recovered_revenue)}
          </div>
          <div className="text-xs text-[#8B93A1] flex items-center gap-2 font-sans">
            <span className="text-[#2DBE8F] font-medium">
              {((orchMetrics?.revenue_recovery_rate || 0) * 100).toFixed(1)}% revenue recovery
            </span>
            <span>•</span>
            <span className="text-[#ECEFF3]/80">
              {((orchMetrics?.case_recovery_rate || 0) * 100).toFixed(1)}% case recovery ({recoveredCasesCount} of {totalCases} cases)
            </span>
          </div>
        </div>

        <div className="text-left sm:text-right border-t sm:border-t-0 sm:border-l border-[#262B33] sm:pl-8 pt-4 sm:pt-0">
          <span className="text-xs text-[#8B93A1] block font-sans">Revenue uplift vs Retry Only</span>
          <div className="text-xl font-semibold font-mono text-[#2DBE8F] mt-1">
            +{formatCurrency(comparison?.orchestrator_absolute_lift)}
          </div>
          <span className="text-xs font-mono text-[#2DBE8F]/90 font-medium block mt-0.5">
            +{comparison?.orchestrator_percentage_lift.toFixed(1)}% lift
          </span>
        </div>
      </div>

      {/* Benchmark Comparison (Left) & Recovery Funnel (Right) */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Left: Clean 3-Way Comparison Table */}
        <div className="space-y-3">
          <h2 className="text-xs font-semibold text-[#ECEFF3] uppercase tracking-wider font-heading">
            Benchmark results
          </h2>

          <div className="rounded-lg border border-[#262B33] bg-[#14171C] overflow-hidden">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b border-[#262B33] bg-[#0B0D10]/60 text-[#8B93A1] text-[11px] uppercase font-sans">
                  <th className="px-4 py-2.5 font-medium">Strategy</th>
                  <th className="px-4 py-2.5 font-medium">Recovered</th>
                  <th className="px-4 py-2.5 font-medium">Recovery Rate</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#262B33]/60 font-sans">
                <tr>
                  <td className="px-4 py-2.5 text-[#8B93A1]">No Action</td>
                  <td className="px-4 py-2.5 font-mono text-[#8B93A1]">{formatCurrency(noActionMetrics?.verified_recovered_revenue)}</td>
                  <td className="px-4 py-2.5 font-mono text-[#8B93A1]">0.0%</td>
                </tr>
                <tr>
                  <td className="px-4 py-2.5 text-[#ECEFF3]/70">Retry Only</td>
                  <td className="px-4 py-2.5 font-mono text-[#ECEFF3]/70">{formatCurrency(retryMetrics?.verified_recovered_revenue)}</td>
                  <td className="px-4 py-2.5 font-mono text-[#ECEFF3]/70">{((retryMetrics?.revenue_recovery_rate || 0) * 100).toFixed(1)}%</td>
                </tr>
                <tr className="bg-[#14171C]/60">
                  <td className="px-4 py-2.5 font-medium text-[#ECEFF3]">Orchestrator</td>
                  <td className="px-4 py-2.5 font-mono font-semibold text-[#2DBE8F]">
                    {formatCurrency(orchMetrics?.verified_recovered_revenue)}
                  </td>
                  <td className="px-4 py-2.5 font-mono font-semibold text-[#2DBE8F]">
                    {((orchMetrics?.revenue_recovery_rate || 0) * 100).toFixed(1)}%
                  </td>
                </tr>
              </tbody>
            </table>

            <div className="grid grid-cols-3 gap-2 p-3 border-t border-[#262B33] text-[11px] text-[#8B93A1] bg-[#0B0D10]/30 font-sans">
              <div>
                <span className="text-[#8B93A1] block">Case Rate</span>
                <span className="font-mono text-[#ECEFF3]/80">{((orchMetrics?.case_recovery_rate || 0) * 100).toFixed(1)}%</span>
              </div>
              <div>
                <span className="text-[#8B93A1] block">Human Reviews</span>
                <span className="font-mono text-[#E8A33D]">{orchMetrics?.human_escalations || 0}</span>
              </div>
              <div>
                <span className="text-[#8B93A1] block">Policy Violations</span>
                <span className="font-mono text-[#2DBE8F]">{orchMetrics?.policy_violations || 0}</span>
              </div>
            </div>
          </div>
        </div>

        {/* Right: Dynamic Data-Driven Recovery Funnel */}
        <div className="space-y-3">
          <h2 className="text-xs font-semibold text-[#ECEFF3] uppercase tracking-wider font-heading">
            Recovery funnel
          </h2>

          <div className="rounded-lg border border-[#262B33] bg-[#14171C] p-5 space-y-3.5 text-xs">
            <div className="space-y-1">
              <div className="flex justify-between text-[#ECEFF3]/80">
                <span>{totalCases} cases evaluated</span>
                <span className="font-mono text-[#ECEFF3]">100%</span>
              </div>
              <div className="h-1.5 rounded bg-[#262B33] overflow-hidden">
                <div className="h-full bg-[#8B93A1]/40 rounded w-full" />
              </div>
            </div>

            <div className="space-y-1">
              <div className="flex justify-between text-[#ECEFF3]/80">
                <span>{successfulDispatches} successful dispatches</span>
                <span className="font-mono text-[#ECEFF3]">{dispatchesPct}%</span>
              </div>
              <div className="h-1.5 rounded bg-[#262B33] overflow-hidden">
                <div className="h-full bg-[#8B93A1]/60 rounded transition-all duration-500" style={{ width: `${dispatchesPct}%` }} />
              </div>
            </div>

            <div className="space-y-1">
              <div className="flex justify-between text-[#ECEFF3]/80">
                <span>{recoveredCasesCount} verified recoveries</span>
                <span className="font-mono text-[#2DBE8F] font-medium">{caseRatePct}%</span>
              </div>
              <div className="h-1.5 rounded bg-[#262B33] overflow-hidden">
                <div className="h-full bg-[#2DBE8F] rounded transition-all duration-500" style={{ width: `${caseRatePct}%` }} />
              </div>
            </div>

            <div className="pt-3 border-t border-[#262B33] flex items-center justify-between text-[#8B93A1]">
              <span>Verified recovered</span>
              <span className="font-mono font-semibold text-[#2DBE8F] text-sm">
                {formatCurrency(orchMetrics?.verified_recovered_revenue)}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Expandable Benchmark Details */}
      <div className="rounded-lg border border-[#262B33] bg-[#14171C] overflow-hidden">
        <button
          onClick={() => setShowMetadata(!showMetadata)}
          className="w-full flex items-center justify-between p-4 text-xs font-medium text-[#8B93A1] hover:text-[#ECEFF3] hover:bg-[#14171C]/80 transition-colors cursor-pointer font-sans"
        >
          <span>{showMetadata ? 'Hide benchmark details' : 'View benchmark details'}</span>
          {showMetadata ? <ChevronUp className="w-4 h-4 text-[#8B93A1]" /> : <ChevronDown className="w-4 h-4 text-[#8B93A1]" />}
        </button>

        {showMetadata && (
          <div className="border-t border-[#262B33] p-4 grid grid-cols-2 sm:grid-cols-5 gap-4 text-xs">
            <div>
              <span className="text-[#8B93A1] block">Batch ID</span>
              <span className="font-mono text-[#ECEFF3]/80">{metrics.metadata.batch_id}</span>
            </div>
            <div>
              <span className="text-[#8B93A1] block">Dataset</span>
              <span className="font-mono text-[#ECEFF3]/80">{metrics.metadata.dataset_version}</span>
            </div>
            <div>
              <span className="text-[#8B93A1] block">Seed</span>
              <span className="font-mono text-[#ECEFF3]/80">{metrics.metadata.random_seed}</span>
            </div>
            <div>
              <span className="text-[#8B93A1] block">Policy version</span>
              <span className="font-mono text-[#ECEFF3]/80">{metrics.metadata.policy_config_version}</span>
            </div>
            <div>
              <span className="text-[#8B93A1] block">Execution mode</span>
              <span className="text-[#2DBE8F] font-medium">Offline (0 live API calls)</span>
            </div>
          </div>
        )}
      </div>

      {/* Collapsible Case-Level Results Section */}
      <div className="rounded-lg border border-[#262B33] bg-[#14171C] overflow-hidden">
        <button
          onClick={() => setShowCaseResults(!showCaseResults)}
          className="w-full flex items-center justify-between p-4 text-xs font-medium text-[#8B93A1] hover:text-[#ECEFF3] hover:bg-[#14171C]/80 transition-colors cursor-pointer font-sans"
        >
          <span>
            {showCaseResults ? 'Hide case-level results' : `View ${caseResultsCount} case-level results`}
          </span>
          {showCaseResults ? <ChevronUp className="w-4 h-4 text-[#8B93A1]" /> : <ChevronDown className="w-4 h-4 text-[#8B93A1]" />}
        </button>

        {showCaseResults && (
          caseResultsCount > 0 ? (
            <div className="border-t border-[#262B33] overflow-x-auto max-h-96">
              <table className="w-full text-left text-xs">
                <thead className="sticky top-0 bg-[#0B0D10] border-b border-[#262B33] text-[11px] text-[#8B93A1] uppercase font-sans">
                  <tr>
                    <th className="py-2.5 px-3">Case ID</th>
                    <th className="py-2.5 px-3">Baseline</th>
                    <th className="py-2.5 px-3">Workflow</th>
                    <th className="py-2.5 px-3">Issue</th>
                    <th className="py-2.5 px-3">Strategy</th>
                    <th className="py-2.5 px-3">Policy</th>
                    <th className="py-2.5 px-3">Status</th>
                    <th className="py-2.5 px-3 text-right">Recovered</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#262B33]/60 font-sans">
                  {metrics.case_results.map((cr, idx) => (
                    <tr key={`${cr.case_id}_${cr.strategy_type}_${idx}`} className="hover:bg-[#262B33]/20">
                      <td className="py-2 px-3 font-mono font-medium text-[#ECEFF3]">{cr.case_id}</td>
                      <td className="py-2 px-3 text-[#8B93A1] text-[11px]">
                        {cr.strategy_type === 'AI_REVENUE_RECOVERY_ORCHESTRATOR' ? 'Orchestrator' : cr.strategy_type === 'RETRY_ONLY' ? 'Retry Only' : 'No Action'}
                      </td>
                      <td className="py-2 px-3 text-[#8B93A1] text-[11px]">{cr.workflow_type === 'ONE_TIME_PAYMENT' ? 'One-Time' : 'Subscription'}</td>
                      <td className="py-2 px-3 text-[#ECEFF3]/70">{cr.failure_category.replace(/_/g, ' ')}</td>
                      <td className="py-2 px-3 font-mono text-[#ECEFF3]/70 text-[11px]">{cr.selected_strategy || '—'}</td>
                      <td className="py-2 px-3">
                        {cr.policy_outcome ? <StatusBadge status={cr.policy_outcome} size="sm" /> : '—'}
                      </td>
                      <td className="py-2 px-3">
                        <StatusBadge status={cr.final_status} size="sm" />
                      </td>
                      <td className="py-2 px-3 font-mono text-right text-[#2DBE8F]">
                        {cr.verified_recovered_amount > 0 ? formatCurrency(cr.verified_recovered_amount) : '₹0.00'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="border-t border-[#262B33] p-6 text-center text-xs text-[#8B93A1] font-sans">
              No case-level results available for this benchmark run.
            </div>
          )
        )}
      </div>
    </div>
  );
};
