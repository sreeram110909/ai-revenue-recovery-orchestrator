import React from 'react';
import { useCases } from '../hooks/useCases';
import { CaseTable } from '../components/CaseTable';
import { AlertCircle } from 'lucide-react';

interface CasesProps {
  onSelectCase: (caseId: string) => void;
}

export const Cases: React.FC<CasesProps> = ({ onSelectCase }) => {
  const { cases, loading, error, refetch } = useCases({ limit: 100 });

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-wrap items-end justify-between gap-4 border-b border-[#262B33] pb-4">
        <div>
          <h1 className="text-xl font-semibold text-[#ECEFF3] tracking-tight font-heading">Recovery cases</h1>
          <p className="text-xs text-[#8B93A1] mt-1">
            Review payment failures and recovery outcomes.
          </p>
        </div>

        <div className="text-xs text-[#8B93A1] font-sans">
          <span>{cases.length} persisted recovery cases</span>
        </div>
      </div>

      {error && (
        <div className="rounded border border-[#C24C4C]/20 bg-[#C24C4C]/5 p-3 text-xs text-[#D4605F] flex items-center justify-between">
          <div className="flex items-center gap-2">
            <AlertCircle className="w-4 h-4 text-[#D4605F] shrink-0" />
            <span>{error}</span>
          </div>
          <button
            onClick={() => refetch()}
            className="text-xs font-semibold text-[#D4605F] hover:underline cursor-pointer"
          >
            Retry
          </button>
        </div>
      )}

      {/* Case Table */}
      <CaseTable
        cases={cases}
        loading={loading}
        onSelectCase={onSelectCase}
        onRefresh={refetch}
      />
    </div>
  );
};
