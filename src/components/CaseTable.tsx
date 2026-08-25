import React, { useState, useMemo } from 'react';
import { RecoveryCase } from '../types/api';
import { StatusBadge } from './StatusBadge';
import { Search, RefreshCw } from 'lucide-react';

interface CaseTableProps {
  cases: RecoveryCase[];
  loading?: boolean;
  onSelectCase: (caseId: string) => void;
  onRefresh?: () => void;
}

export const CaseTable: React.FC<CaseTableProps> = ({
  cases,
  loading = false,
  onSelectCase,
  onRefresh,
}) => {
  const [searchTerm, setSearchTerm] = useState<string>('');
  const [selectedWorkflow, setSelectedWorkflow] = useState<string>('ALL');
  const [selectedCategory, setSelectedCategory] = useState<string>('ALL');
  const [selectedStatus, setSelectedStatus] = useState<string>('ALL');

  const filteredCases = useMemo(() => {
    return cases.filter((c) => {
      const matchesSearch =
        c.id.toLowerCase().includes(searchTerm.toLowerCase()) ||
        c.customer_id.toLowerCase().includes(searchTerm.toLowerCase()) ||
        c.failure_code.toLowerCase().includes(searchTerm.toLowerCase()) ||
        c.masked_customer_email.toLowerCase().includes(searchTerm.toLowerCase());

      if (!matchesSearch) return false;
      if (selectedWorkflow !== 'ALL' && c.case_type !== selectedWorkflow) return false;
      if (selectedCategory !== 'ALL' && c.failure_category !== selectedCategory) return false;
      if (selectedStatus !== 'ALL' && c.current_status !== selectedStatus) return false;

      return true;
    });
  }, [cases, searchTerm, selectedWorkflow, selectedCategory, selectedStatus]);

  const formatCurrency = (val: number) => {
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      maximumFractionDigits: 2,
    }).format(val);
  };

  return (
    <div className="space-y-3">
      {/* Filter and Search Bar */}
      <div className="flex flex-wrap items-center justify-between gap-3 p-3 rounded-lg border border-[#262B33] bg-[#14171C]">
        <div className="flex flex-1 items-center gap-2 min-w-[240px]">
          <div className="relative flex-1">
            <Search className="absolute left-2.5 top-2.5 h-3.5 w-3.5 text-[#8B93A1]" />
            <input
              type="text"
              placeholder="Search by case ID, customer ID, or email..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full rounded border border-[#262B33] bg-[#0B0D10] pl-8 pr-3 py-1.5 text-xs text-[#ECEFF3] placeholder-[#8B93A1]/60 focus:border-[#8B93A1]/40 focus:outline-none font-sans"
            />
          </div>

          {onRefresh && (
            <button
              onClick={onRefresh}
              disabled={loading}
              className="p-1.5 rounded border border-[#262B33] bg-[#0B0D10] text-[#8B93A1] hover:text-[#ECEFF3] transition-colors cursor-pointer"
              title="Refresh case list"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            </button>
          )}
        </div>

        <div className="flex flex-wrap items-center gap-2 text-xs">
          <select
            value={selectedWorkflow}
            onChange={(e) => setSelectedWorkflow(e.target.value)}
            className="rounded border border-[#262B33] bg-[#0B0D10] px-2.5 py-1.5 text-[#8B93A1] focus:outline-none cursor-pointer font-sans"
          >
            <option value="ALL">All Workflows</option>
            <option value="ONE_TIME_PAYMENT">One-Time Payment</option>
            <option value="SUBSCRIPTION_RECURRING">Subscription</option>
          </select>

          <select
            value={selectedCategory}
            onChange={(e) => setSelectedCategory(e.target.value)}
            className="rounded border border-[#262B33] bg-[#0B0D10] px-2.5 py-1.5 text-[#8B93A1] focus:outline-none cursor-pointer font-sans"
          >
            <option value="ALL">All Issues</option>
            <option value="BANK_TIMEOUT_NETWORK">Bank Timeout</option>
            <option value="EXPIRED_INSTRUMENT">Expired Instrument</option>
            <option value="INSUFFICIENT_FUNDS">Insufficient Funds</option>
            <option value="MANDATE_EXPIRED_INVALID">Invalid Mandate</option>
            <option value="RISK_SECURITY_BLOCK">Security Block</option>
            <option value="AUTHENTICATION_OTP_FAILURE">Auth Failed</option>
          </select>

          <select
            value={selectedStatus}
            onChange={(e) => setSelectedStatus(e.target.value)}
            className="rounded border border-[#262B33] bg-[#0B0D10] px-2.5 py-1.5 text-[#8B93A1] focus:outline-none cursor-pointer font-sans"
          >
            <option value="ALL">All Statuses</option>
            <option value="VERIFIED_RECOVERED">Verified Recovered</option>
            <option value="ESCALATED">Human Escalation</option>
            <option value="STOPPED">Stopped</option>
            <option value="RETRY_SCHEDULED">Retry Scheduled</option>
            <option value="DIAGNOSED">Diagnosed</option>
            <option value="DETECTED">Detected</option>
          </select>
        </div>
      </div>

      {/* Clean Table */}
      <div className="rounded-lg border border-[#262B33] bg-[#14171C] overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-[#262B33] bg-[#0B0D10]/60 text-[#8B93A1] text-[11px] uppercase font-sans font-medium">
                <th className="px-4 py-2.5">Case</th>
                <th className="px-4 py-2.5">Amount</th>
                <th className="px-4 py-2.5">Issue</th>
                <th className="px-4 py-2.5">Attempts</th>
                <th className="px-4 py-2.5">Strategy</th>
                <th className="px-4 py-2.5">Status</th>
                <th className="px-4 py-2.5 text-right">Recovered</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#262B33]/60 font-sans">
              {loading ? (
                <tr>
                  <td colSpan={7} className="px-4 py-8 text-center text-[#8B93A1]">
                    <RefreshCw className="w-3.5 h-3.5 animate-spin mx-auto mb-1" />
                    Loading recovery cases...
                  </td>
                </tr>
              ) : filteredCases.length === 0 ? (
                <tr>
                  <td colSpan={7} className="px-4 py-8 text-center text-[#8B93A1]">
                    No matching recovery cases found.
                  </td>
                </tr>
              ) : (
                filteredCases.map((c) => {
                  const isRecovered = c.current_status === 'VERIFIED_RECOVERED';
                  return (
                    <tr
                      key={c.id}
                      onClick={() => onSelectCase(c.id)}
                      className="hover:bg-[#262B33]/30 cursor-pointer transition-colors"
                    >
                      <td className="px-4 py-2.5 font-mono font-medium text-[#ECEFF3] hover:text-[#2DBE8F]">
                        {c.id}
                      </td>
                      <td className="px-4 py-2.5 font-mono text-[#ECEFF3]/80">
                        {formatCurrency(c.amount)}
                      </td>
                      <td className="px-4 py-2.5 text-[#ECEFF3]/70">
                        {c.failure_category.replace(/_/g, ' ')}
                      </td>
                      <td className="px-4 py-2.5 font-mono text-[#8B93A1]">
                        {c.attempts_count}/{c.max_attempts_allowed}
                      </td>
                      <td className="px-4 py-2.5 font-mono text-[#ECEFF3]/70">
                        {c.recommended_strategy || '—'}
                      </td>
                      <td className="px-4 py-2.5">
                        <StatusBadge status={c.current_status} size="sm" />
                      </td>
                      <td className="px-4 py-2.5 font-mono text-right text-[#2DBE8F] font-medium">
                        {isRecovered ? formatCurrency(c.verified_recovered_amount) : '₹0.00'}
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>

        <div className="flex items-center justify-between border-t border-[#262B33] px-4 py-2 text-xs text-[#8B93A1] font-sans">
          <span>{filteredCases.length} of {cases.length} cases</span>
          <span>FastAPI Engine</span>
        </div>
      </div>
    </div>
  );
};
