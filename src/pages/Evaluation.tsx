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
      <div className="flex items-center justify-center py-20 text-xs text-slate-400 font-sans">
        <RefreshCw className="w-4 h-4 animate-spin mr-2" />
        Loading benchmark results...
      </div>
    );
  }

  if (error || !metrics) {
    return (
      <div className="rounded-lg border border-slate-800 bg-slate-900/40 p-8 text-center space-y-3">
        <h3 className="text-sm font-semibold text-white">Benchmark Data Unavailable</h3>
        <p className="text-xs text-slate-400 max-w-md mx-auto">
          {error || 'Unable to retrieve evaluation results from backend.'}
        </p>
        <button
          onClick={() => refetch()}
          className="inline-flex items-center gap-1.5 rounded border border-slate-700 bg-slate-800 px-3 py-1.5 text-xs font-medium text-white hover:bg-slate-700 transition-colors cursor-pointer"
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
      <div className="flex flex-wrap items-end justify-between gap-4 border-b border-slate-800/80 pb-4">
        <div>
          <h1 className="text-xl font-semibold text-white tracking-tight">Benchmark</h1>
          <p className="text-xs text-slate-400 mt-1">
            {metrics.metadata?.total_cases || totalCases} recovery cases · Seed {metrics.metadata?.random_seed ?? 42} · Synthetic evaluation
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowConfig(!showConfig)}
            className="inline-flex items-center gap-1.5 rounded border border-slate-800 bg-slate-900 px-3 py-1.5 text-xs font-medium text-slate-300 hover:text-white transition-colors cursor-pointer"
          >
            <Sliders className="w-3.5 h-3.5" />
            {showConfig ? 'Hide config' : 'Configure benchmark'}
          </button>
          <button
            onClick={handleRerunStandardBenchmark}
            disabled={running}
            className="inline-flex items-center gap-1.5 rounded border border-slate-700 bg-slate-800 px-3 py-1.5 text-xs font-medium text-white hover:bg-slate-700 disabled:opacity-50 transition-colors cursor-pointer"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${running ? 'animate-spin' : ''}`} />
            {running ? 'Running...' : 'Re-run benchmark'}
          </button>
        </div>
      </div>

      {/* Benchmark Success Banner */}
      {benchmarkNotification && (
        <div className="p-3 rounded-lg border border-emerald-500/30 bg-emerald-500/10 text-xs text-emerald-300 flex items-center justify-between animate-fade-in">
          <div className="flex items-center gap-2">
            <Check className="w-4 h-4 text-emerald-400 shrink-0" />
            <span>{benchmarkNotification}</span>
          </div>
          <button
            onClick={() => setBenchmarkNotification(null)}
            className="text-[11px] text-emerald-400 hover:text-white cursor-pointer"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Config Drawer */}
      {showConfig && (
        <div className="rounded-lg border border-slate-800 bg-slate-900/60 p-4 space-y-3">
          <span className="text-xs font-semibold text-slate-300 font-sans block">
            Configure benchmark run
          </span>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs">
            <div>
              <label className="text-slate-400 block mb-1">Random seed</label>
              <input
                type="number"
                value={seed}
                onChange={(e) => setSeed(parseInt(e.target.value) || 42)}
                className="w-full rounded border border-slate-800 bg-slate-950 px-2.5 py-1.5 text-white font-mono text-xs focus:outline-none"
              />
            </div>
            <div>
              <label className="text-slate-400 block mb-1">Dataset size</label>
              <input
                type="number"
                value={count}
                min={50}
                max={200}
                onChange={(e) => setCount(parseInt(e.target.value) || 60)}
                className="w-full rounded border border-slate-800 bg-slate-950 px-2.5 py-1.5 text-white font-mono text-xs focus:outline-none"
              />
            </div>
            <div className="flex items-end">
              <button
                onClick={handleRunCustomBenchmark}
                disabled={running}
                className="w-full rounded border border-slate-700 bg-slate-800 px-3 py-1.5 text-xs font-medium text-white hover:bg-slate-700 disabled:opacity-50 transition-colors cursor-pointer"
              >
                {running ? 'Executing...' : 'Run with settings'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Primary Result Banner */}
      <div className="rounded-lg border border-slate-800 bg-slate-900/60 p-6 sm:p-8 flex flex-wrap items-center justify-between gap-6">
        <div className="space-y-1.5">
          <span className="text-xs font-medium text-slate-400 block font-sans">
            Measured recovered revenue
          </span>
          <div className="text-3xl sm:text-4xl font-semibold text-white font-mono tracking-tight">
            {formatCurrency(orchMetrics?.verified_recovered_revenue)}
          </div>
          <div className="text-xs text-slate-400 flex items-center gap-2 font-sans">
            <span className="text-emerald-400 font-medium">
              {((orchMetrics?.revenue_recovery_rate || 0) * 100).toFixed(1)}% revenue recovery
            </span>
            <span>•</span>
            <span className="text-slate-300">
              {((orchMetrics?.case_recovery_rate || 0) * 100).toFixed(1)}% case recovery ({recoveredCasesCount} of {totalCases} cases)
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

      {/* Benchmark Comparison (Left) & Recovery Funnel (Right) */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Left: Clean 3-Way Comparison Table */}
        <div className="space-y-3">
          <h2 className="text-xs font-semibold text-white uppercase tracking-wider font-sans">
            Benchmark results
          </h2>

          <div className="rounded-lg border border-slate-800 bg-slate-900/30 overflow-hidden">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b border-slate-800 bg-slate-900/60 text-slate-400 text-[11px] uppercase font-sans">
                  <th className="px-4 py-2.5 font-medium">Strategy</th>
                  <th className="px-4 py-2.5 font-medium">Recovered</th>
                  <th className="px-4 py-2.5 font-medium">Recovery Rate</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 font-sans">
                <tr>
                  <td className="px-4 py-2.5 text-slate-400">No Action</td>
                  <td className="px-4 py-2.5 font-mono text-slate-400">{formatCurrency(noActionMetrics?.verified_recovered_revenue)}</td>
                  <td className="px-4 py-2.5 font-mono text-slate-400">0.0%</td>
                </tr>
                <tr>
                  <td className="px-4 py-2.5 text-slate-300">Retry Only</td>
                  <td className="px-4 py-2.5 font-mono text-slate-300">{formatCurrency(retryMetrics?.verified_recovered_revenue)}</td>
                  <td className="px-4 py-2.5 font-mono text-slate-300">{((retryMetrics?.revenue_recovery_rate || 0) * 100).toFixed(1)}%</td>
                </tr>
                <tr className="bg-slate-800/40">
                  <td className="px-4 py-2.5 font-medium text-white">Orchestrator</td>
                  <td className="px-4 py-2.5 font-mono font-semibold text-emerald-400">
                    {formatCurrency(orchMetrics?.verified_recovered_revenue)}
                  </td>
                  <td className="px-4 py-2.5 font-mono font-semibold text-emerald-400">
                    {((orchMetrics?.revenue_recovery_rate || 0) * 100).toFixed(1)}%
                  </td>
                </tr>
              </tbody>
            </table>

            <div className="grid grid-cols-3 gap-2 p-3 border-t border-slate-800/80 text-[11px] text-slate-400 bg-slate-950/30 font-sans">
              <div>
                <span className="text-slate-500 block">Case Rate</span>
                <span className="font-mono text-slate-200">{((orchMetrics?.case_recovery_rate || 0) * 100).toFixed(1)}%</span>
              </div>
              <div>
                <span className="text-slate-500 block">Human Reviews</span>
                <span className="font-mono text-amber-400">{orchMetrics?.human_escalations || 0}</span>
              </div>
              <div>
                <span className="text-slate-500 block">Policy Violations</span>
                <span className="font-mono text-emerald-400">{orchMetrics?.policy_violations || 0}</span>
              </div>
            </div>
          </div>
        </div>

        {/* Right: Dynamic Data-Driven Recovery Funnel */}
        <div className="space-y-3">
          <h2 className="text-xs font-semibold text-white uppercase tracking-wider font-sans">
            Recovery funnel
          </h2>

          <div className="rounded-lg border border-slate-800 bg-slate-900/30 p-5 space-y-3.5 text-xs">
            <div className="space-y-1">
              <div className="flex justify-between text-slate-300">
                <span>{totalCases} cases evaluated</span>
                <span className="font-mono text-white">100%</span>
              </div>
              <div className="h-1.5 rounded bg-slate-800 overflow-hidden">
                <div className="h-full bg-slate-600 rounded w-full" />
              </div>
            </div>

            <div className="space-y-1">
              <div className="flex justify-between text-slate-300">
                <span>{successfulDispatches} successful dispatches</span>
                <span className="font-mono text-white">{dispatchesPct}%</span>
              </div>
              <div className="h-1.5 rounded bg-slate-800 overflow-hidden">
                <div className="h-full bg-slate-500 rounded transition-all duration-500" style={{ width: `${dispatchesPct}%` }} />
              </div>
            </div>

            <div className="space-y-1">
              <div className="flex justify-between text-slate-300">
                <span>{recoveredCasesCount} verified recoveries</span>
                <span className="font-mono text-emerald-400 font-medium">{caseRatePct}%</span>
              </div>
              <div className="h-1.5 rounded bg-slate-800 overflow-hidden">
                <div className="h-full bg-emerald-500 rounded transition-all duration-500" style={{ width: `${caseRatePct}%` }} />
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
      </div>

      {/* Expandable Benchmark Details */}
      <div className="rounded-lg border border-slate-800 bg-slate-900/30 overflow-hidden">
        <button
          onClick={() => setShowMetadata(!showMetadata)}
          className="w-full flex items-center justify-between p-4 text-xs font-medium text-slate-300 hover:text-white hover:bg-slate-900/50 transition-colors cursor-pointer font-sans"
        >
          <span>{showMetadata ? 'Hide benchmark details' : 'View benchmark details'}</span>
          {showMetadata ? <ChevronUp className="w-4 h-4 text-slate-400" /> : <ChevronDown className="w-4 h-4 text-slate-400" />}
        </button>

        {showMetadata && (
          <div className="border-t border-slate-800 p-4 grid grid-cols-2 sm:grid-cols-5 gap-4 text-xs">
            <div>
              <span className="text-slate-500 block">Batch ID</span>
              <span className="font-mono text-slate-300">{metrics.metadata.batch_id}</span>
            </div>
            <div>
              <span className="text-slate-500 block">Dataset</span>
              <span className="font-mono text-slate-300">{metrics.metadata.dataset_version}</span>
            </div>
            <div>
              <span className="text-slate-500 block">Seed</span>
              <span className="font-mono text-slate-300">{metrics.metadata.random_seed}</span>
            </div>
            <div>
              <span className="text-slate-500 block">Policy version</span>
              <span className="font-mono text-slate-300">{metrics.metadata.policy_config_version}</span>
            </div>
            <div>
              <span className="text-slate-500 block">Execution mode</span>
              <span className="text-emerald-400 font-medium">Offline (0 live API calls)</span>
            </div>
          </div>
        )}
      </div>

      {/* Collapsible Case-Level Results Section */}
      <div className="rounded-lg border border-slate-800 bg-slate-900/30 overflow-hidden">
        <button
          onClick={() => setShowCaseResults(!showCaseResults)}
          className="w-full flex items-center justify-between p-4 text-xs font-medium text-slate-300 hover:text-white hover:bg-slate-900/50 transition-colors cursor-pointer font-sans"
        >
          <span>
            {showCaseResults ? 'Hide case-level results' : `View ${caseResultsCount} case-level results`}
          </span>
          {showCaseResults ? <ChevronUp className="w-4 h-4 text-slate-400" /> : <ChevronDown className="w-4 h-4 text-slate-400" />}
        </button>

        {showCaseResults && (
          caseResultsCount > 0 ? (
            <div className="border-t border-slate-800 overflow-x-auto max-h-96">
              <table className="w-full text-left text-xs">
                <thead className="sticky top-0 bg-slate-950 border-b border-slate-800 text-[11px] text-slate-400 uppercase font-sans">
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
                <tbody className="divide-y divide-slate-800/60 font-sans">
                  {metrics.case_results.map((cr, idx) => (
                    <tr key={`${cr.case_id}_${cr.strategy_type}_${idx}`} className="hover:bg-slate-800/20">
                      <td className="py-2 px-3 font-mono font-medium text-white">{cr.case_id}</td>
                      <td className="py-2 px-3 text-slate-400 text-[11px]">
                        {cr.strategy_type === 'AI_REVENUE_RECOVERY_ORCHESTRATOR' ? 'Orchestrator' : cr.strategy_type === 'RETRY_ONLY' ? 'Retry Only' : 'No Action'}
                      </td>
                      <td className="py-2 px-3 text-slate-400 text-[11px]">{cr.workflow_type === 'ONE_TIME_PAYMENT' ? 'One-Time' : 'Subscription'}</td>
                      <td className="py-2 px-3 text-slate-300">{cr.failure_category.replace(/_/g, ' ')}</td>
                      <td className="py-2 px-3 font-mono text-slate-300 text-[11px]">{cr.selected_strategy || '—'}</td>
                      <td className="py-2 px-3">
                        {cr.policy_outcome ? <StatusBadge status={cr.policy_outcome} size="sm" /> : '—'}
                      </td>
                      <td className="py-2 px-3">
                        <StatusBadge status={cr.final_status} size="sm" />
                      </td>
                      <td className="py-2 px-3 font-mono text-right text-emerald-400">
                        {cr.verified_recovered_amount > 0 ? formatCurrency(cr.verified_recovered_amount) : '₹0.00'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="border-t border-slate-800 p-6 text-center text-xs text-slate-500 font-sans">
              No case-level results available for this benchmark run.
            </div>
          )
        )}
      </div>
    </div>
  );
};
