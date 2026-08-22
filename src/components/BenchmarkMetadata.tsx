import React from 'react';
import { BatchRunMetadata } from '../types/api';
import { RefreshCw } from 'lucide-react';

interface BenchmarkMetadataProps {
  metadata: BatchRunMetadata;
  onRefresh?: () => void;
  running?: boolean;
}

export const BenchmarkMetadata: React.FC<BenchmarkMetadataProps> = ({
  metadata,
  onRefresh,
  running = false,
}) => {
  return (
    <div className="flex flex-wrap items-center justify-between gap-4 p-4 rounded-lg border border-slate-800 bg-slate-900/40 text-xs">
      <div className="flex flex-wrap items-center gap-6">
        <div>
          <span className="text-slate-500 block">Batch ID</span>
          <span className="font-mono text-slate-200 font-medium">{metadata.batch_id}</span>
        </div>
        <div>
          <span className="text-slate-500 block">Dataset</span>
          <span className="font-mono text-slate-200">{metadata.dataset_version} ({metadata.total_cases} cases)</span>
        </div>
        <div>
          <span className="text-slate-500 block">Random Seed</span>
          <span className="font-mono text-slate-200">{metadata.random_seed} (Deterministic)</span>
        </div>
        <div>
          <span className="text-slate-500 block">Policy Config</span>
          <span className="font-mono text-slate-200">{metadata.policy_config_version}</span>
        </div>
        <div>
          <span className="text-slate-500 block">Execution Mode</span>
          <span className="text-emerald-400 font-medium">Offline (0 Live API Calls)</span>
        </div>
      </div>

      {onRefresh && (
        <button
          onClick={onRefresh}
          disabled={running}
          className="inline-flex items-center gap-1.5 rounded border border-slate-700 bg-slate-800 px-3 py-1.5 text-xs font-medium text-white hover:bg-slate-700 disabled:opacity-50 transition-colors cursor-pointer"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${running ? 'animate-spin' : ''}`} />
          {running ? 'Running...' : 'Run Benchmark'}
        </button>
      )}
    </div>
  );
};
