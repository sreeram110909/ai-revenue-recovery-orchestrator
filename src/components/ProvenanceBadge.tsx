import React from 'react';
import { TruthProvenance } from '../types/api';

interface ProvenanceBadgeProps {
  provenance: TruthProvenance | string;
  showIcon?: boolean;
}

export const ProvenanceBadge: React.FC<ProvenanceBadgeProps> = ({
  provenance,
}) => {
  switch (provenance) {
    case 'LIVE_TEST_MODE_API_RESULT':
      return (
        <span className="inline-flex items-center text-xs font-sans text-amber-400/90 font-medium">
          Razorpay Test Mode
        </span>
      );
    case 'MOCKED_TEST_RESULT':
      return (
        <span className="inline-flex items-center text-xs font-sans text-slate-400">
          Mocked Gateway
        </span>
      );
    case 'SYNTHETIC_DATA_RESULT':
    default:
      return (
        <span className="inline-flex items-center text-xs font-sans text-slate-400">
          Synthetic Benchmark
        </span>
      );
  }
};
