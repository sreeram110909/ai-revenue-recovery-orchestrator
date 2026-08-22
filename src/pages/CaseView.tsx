import React, { useState } from 'react';
import { useCase } from '../hooks/useCase';
import { useCases } from '../hooks/useCases';
import { StatusBadge } from '../components/StatusBadge';
import { DecisionTimeline } from '../components/DecisionTimeline';
import { PolicyPanel } from '../components/PolicyPanel';
import { StrategyScoreTable } from '../components/StrategyScoreTable';
import { AuditTimeline } from '../components/AuditTimeline';
import { RefreshCw, ArrowLeft, Play, ChevronDown, ChevronUp, CheckCircle2 } from 'lucide-react';

interface CaseViewProps {
  caseId: string | null;
  onBackToCases: () => void;
  onSelectCase: (caseId: string) => void;
}

export const CaseView: React.FC<CaseViewProps> = ({
  caseId,
  onBackToCases,
  onSelectCase,
}) => {
  const { caseData, auditTrail, loading, processing, error, processCase } = useCase(caseId || undefined);
  const { cases } = useCases({ limit: 100 });
  const [showTechnicalDetails, setShowTechnicalDetails] = useState<boolean>(false);
  const [showFullAuditLog, setShowFullAuditLog] = useState<boolean>(false);

  const formatCurrency = (val?: number) => {
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      maximumFractionDigits: 2,
    }).format(val || 0);
  };

  const handleProcessWorkflow = async () => {
    try {
      await processCase();
    } catch {
      // handled in hook
    }
  };

  if (!caseId) {
    return (
      <div className="rounded-lg border border-slate-800 bg-slate-900/40 p-8 text-center space-y-5">
        <div className="space-y-1.5 max-w-md mx-auto">
          <h3 className="text-base font-semibold text-white">No recovery case selected</h3>
          <p className="text-xs text-slate-400">
            Select a recovery case to review payment failure diagnosis, policy authorization, and recovery outcome.
          </p>
        </div>

        {cases.length > 0 ? (
          <div className="max-w-lg mx-auto space-y-2 pt-2">
            <span className="text-xs font-medium text-slate-400 block text-left">
              Recommended demo cases ({cases.length})
            </span>
            <div className="space-y-1.5 text-left">
              {cases.map((c) => (
                <div
                  key={c.id}
                  onClick={() => onSelectCase(c.id)}
                  className="p-3 rounded border border-slate-800 bg-slate-950/60 hover:bg-slate-900 cursor-pointer transition-colors flex items-center justify-between"
                >
                  <div>
                    <span className="font-mono text-xs font-medium text-white">{c.id}</span>
                    <p className="text-[11px] text-slate-400">
                      {c.case_type === 'ONE_TIME_PAYMENT' ? 'One-Time' : 'Subscription'} • {c.failure_code}
                    </p>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="font-mono text-xs font-medium text-white">{formatCurrency(c.amount)}</span>
                    <StatusBadge status={c.current_status} size="sm" />
                  </div>
                </div>
              ))}
            </div>
          </div>
        ) : (
          <button
            onClick={onBackToCases}
            className="inline-flex items-center gap-1.5 rounded border border-slate-700 bg-slate-800 px-3 py-1.5 text-xs font-medium text-white hover:bg-slate-700 transition-colors cursor-pointer"
          >
            <ArrowLeft className="w-3.5 h-3.5" /> Open Cases
          </button>
        )}
      </div>
    );
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20 text-xs text-slate-400 font-sans">
        <RefreshCw className="w-4 h-4 animate-spin mr-2" />
        Loading case '{caseId}'...
      </div>
    );
  }

  if (error || !caseData) {
    return (
      <div className="rounded-lg border border-slate-800 bg-slate-900/40 p-8 text-center space-y-4">
        <h3 className="text-sm font-semibold text-white">Case Not Found</h3>
        <p className="text-xs text-slate-400 max-w-md mx-auto">
          {error || `Unable to locate recovery case '${caseId}'.`}
        </p>
        <button
          onClick={onBackToCases}
          className="inline-flex items-center gap-1.5 rounded border border-slate-700 bg-slate-800 px-3 py-1.5 text-xs font-medium text-white hover:bg-slate-700 transition-colors cursor-pointer"
        >
          <ArrowLeft className="w-3.5 h-3.5" /> Back to Cases
        </button>
      </div>
    );
  }

  const isRecovered = caseData.current_status === 'VERIFIED_RECOVERED';
  const isTerminal = ['VERIFIED_RECOVERED', 'ESCALATED', 'STOPPED', 'CLOSED_UNRECOVERABLE'].includes(caseData.current_status);
  const policyOutcome = caseData.policy_evaluation?.outcome;

  // Plain English Action Label
  const getActionLabel = () => {
    if (caseData.executed_action) {
      const actionType =
        (caseData.executed_action as any).action_type ||
        (caseData.executed_action as any).strategy ||
        caseData.policy_evaluation?.approved_strategy;
      if (actionType === 'SMART_RETRY') return 'Retry scheduled';
      if (actionType === 'PAYMENT_LINK') return 'Payment Link created';
      if (actionType === 'SUBSCRIPTION_RETRY') return 'Subscription retry scheduled';
      if (actionType === 'UPDATE_PAYMENT_METHOD') return 'Payment method update requested';
      if (actionType === 'HUMAN_ESCALATION') return 'Escalated to human review';
      if (actionType === 'STOP') return 'Recovery stopped';
      return actionType ? `${actionType}` : 'Action executed';
    }
    if (policyOutcome === 'BLOCK') return 'Blocked by policy (No financial action)';
    if (policyOutcome === 'ESCALATE') return 'Escalated to operations (No financial action)';
    if (policyOutcome === 'STOP') return 'Stopped by policy (No financial action)';
    return 'Action pending';
  };

  // Plain English Verification Label
  const getVerificationLabel = () => {
    if (policyOutcome === 'BLOCK' || policyOutcome === 'ESCALATE' || policyOutcome === 'STOP') {
      return 'No financial action taken';
    }
    if (caseData.verification_outcome) {
      const status = caseData.verification_outcome.status;
      if (status === 'PAID' || status === 'CAPTURED') {
        return 'Paid & captured';
      }
      return 'Not yet recovered (Unpaid / Pending)';
    }
    return 'Pending settlement';
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-800/80 pb-4">
        <div className="flex items-center gap-3">
          <button
            onClick={onBackToCases}
            className="p-1.5 rounded border border-slate-800 bg-slate-900 text-slate-400 hover:text-white transition-colors cursor-pointer"
            title="Back to Cases"
          >
            <ArrowLeft className="w-4 h-4" />
          </button>
          <div>
            <div className="flex items-center gap-2.5">
              <h1 className="text-xl font-semibold font-mono text-white">{caseData.id}</h1>
              <StatusBadge status={caseData.current_status} size="sm" />
            </div>
            <p className="text-xs text-slate-400 mt-0.5">
              {formatCurrency(caseData.amount)} • {caseData.case_type === 'ONE_TIME_PAYMENT' ? 'One-Time Payment' : 'Subscription'} • {caseData.failure_category.replace(/_/g, ' ')}
            </p>
          </div>
        </div>

        {/* Quick Demo Case Switcher & Action */}
        <div className="flex items-center gap-2.5">
          {cases.length > 0 && (
            <select
              value={caseData.id}
              onChange={(e) => onSelectCase(e.target.value)}
              className="rounded border border-slate-800 bg-slate-900 px-2.5 py-1.5 text-xs font-mono text-slate-300 focus:outline-none cursor-pointer"
            >
              {cases.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.id} ({formatCurrency(c.amount)}) [{c.current_status}]
                </option>
              ))}
            </select>
          )}

          <button
            onClick={handleProcessWorkflow}
            disabled={processing || isTerminal}
            className={`inline-flex items-center gap-1.5 rounded px-3 py-1.5 text-xs font-medium transition-colors cursor-pointer ${
              isTerminal
                ? 'border border-slate-800 bg-slate-900 text-slate-500 cursor-not-allowed'
                : 'border border-slate-700 bg-slate-800 text-white hover:bg-slate-700'
            }`}
          >
            {processing ? (
              <>
                <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                Processing...
              </>
            ) : isTerminal ? (
              <>
                <CheckCircle2 className="w-3.5 h-3.5 text-slate-400" />
                Completed
              </>
            ) : (
              <>
                <Play className="w-3.5 h-3.5 fill-current" />
                Process with LangGraph
              </>
            )}
          </button>
        </div>
      </div>

      {/* SECTION 1: WHAT HAPPENED? (Merchant Plain Language) */}
      <div className="rounded-lg border border-slate-800 bg-slate-900/40 p-6 space-y-4">
        <h2 className="text-xs font-semibold text-white uppercase tracking-wider font-sans">
          What happened?
        </h2>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs font-sans">
          <div className="p-3.5 rounded border border-slate-800/80 bg-slate-950/60 space-y-1">
            <span className="text-slate-500 block text-[11px] font-medium">1. Issue detected</span>
            <p className="text-slate-200">
              Payment failed due to {caseData.failure_category.replace(/_/g, ' ').toLowerCase()}.
            </p>
          </div>

          <div className="p-3.5 rounded border border-slate-800/80 bg-slate-950/60 space-y-1">
            <span className="text-slate-500 block text-[11px] font-medium">2. AI suggested</span>
            <p className="font-mono text-emerald-400 font-medium">
              {caseData.recommended_strategy || 'SMART_RETRY'}
            </p>
          </div>

          <div className="p-3.5 rounded border border-slate-800/80 bg-slate-950/60 space-y-1">
            <span className="text-slate-500 block text-[11px] font-medium">3. Policy decision</span>
            <div className="flex items-center gap-2">
              <StatusBadge status={policyOutcome || 'ALLOW'} size="sm" />
              <span className="font-mono text-slate-200">
                {caseData.policy_evaluation?.approved_strategy || caseData.recommended_strategy}
              </span>
            </div>
          </div>
        </div>

        {caseData.policy_evaluation?.reasons && caseData.policy_evaluation.reasons.length > 0 && (
          <div className="p-3 rounded border border-slate-800 bg-slate-950/40 text-xs text-slate-400 font-sans">
            <span className="text-slate-500 font-medium">Policy reason: </span>
            {caseData.policy_evaluation.reasons[0]}
          </div>
        )}
      </div>

      {/* SECTION 2: RECOVERY RESULT */}
      <div className="rounded-lg border border-slate-800 bg-slate-900/30 p-5">
        <h2 className="text-xs font-semibold text-white uppercase tracking-wider font-sans mb-3">
          Recovery result
        </h2>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 text-xs">
          <div className="space-y-0.5">
            <span className="text-slate-500 block">Action taken</span>
            <span className="font-sans text-sm font-medium text-white block">
              {getActionLabel()}
            </span>
          </div>

          <div className="space-y-0.5">
            <span className="text-slate-500 block">Gateway verification</span>
            <span className="font-sans text-sm font-medium text-slate-300 block">
              {getVerificationLabel()}
            </span>
          </div>

          <div className="space-y-0.5">
            <span className="text-slate-500 block">Recovered amount</span>
            <span className="font-mono text-sm font-semibold text-emerald-400 block">
              {isRecovered ? formatCurrency(caseData.verified_recovered_amount) : '₹0.00'}
            </span>
          </div>
        </div>
      </div>

      {/* SECTION 3: TECHNICAL DETAILS (COLLAPSIBLE) */}
      <div className="rounded-lg border border-slate-800 bg-slate-900/30 overflow-hidden">
        <button
          onClick={() => setShowTechnicalDetails(!showTechnicalDetails)}
          className="w-full flex items-center justify-between p-4 text-xs font-medium text-slate-300 hover:text-white hover:bg-slate-900/50 transition-colors cursor-pointer font-sans"
        >
          <span>{showTechnicalDetails ? 'Hide decision details' : 'View decision details'}</span>
          {showTechnicalDetails ? <ChevronUp className="w-4 h-4 text-slate-400" /> : <ChevronDown className="w-4 h-4 text-slate-400" />}
        </button>

        {showTechnicalDetails && (
          <div className="border-t border-slate-800 p-5 space-y-6">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <DecisionTimeline caseData={caseData} />

              <div className="space-y-6">
                <PolicyPanel
                  policy={caseData.policy_evaluation}
                  recommendedStrategy={caseData.recommended_strategy}
                />

                <StrategyScoreTable
                  caseType={caseData.case_type}
                  recommendedStrategy={caseData.recommended_strategy}
                  confidence={caseData.strategy_confidence}
                  rationale={caseData.strategy_rationale}
                />
              </div>
            </div>
          </div>
        )}
      </div>

      {/* SECTION 4: ACTIVITY & AUDIT TRAIL */}
      <div className="rounded-lg border border-slate-800 bg-slate-900/30 overflow-hidden">
        <div className="p-4 border-b border-slate-800 flex items-center justify-between">
          <div>
            <h2 className="text-xs font-semibold text-white uppercase tracking-wider font-sans">
              Activity ({auditTrail.length} events)
            </h2>
            <p className="text-[11px] text-slate-500 mt-0.5">
              Chronological append-only recovery timeline
            </p>
          </div>

          <button
            onClick={() => setShowFullAuditLog(!showFullAuditLog)}
            className="text-xs text-slate-400 hover:text-white font-sans flex items-center gap-1 cursor-pointer"
          >
            {showFullAuditLog ? 'Collapse audit log' : 'View full audit log'}
            {showFullAuditLog ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
          </button>
        </div>

        {/* Clean Activity Summary (Always Visible) */}
        <div className="divide-y divide-slate-800/60 text-xs font-sans">
          {auditTrail.slice(0, 5).map((entry, idx) => (
            <div key={entry.id || idx} className="p-3 flex items-center justify-between hover:bg-slate-800/20">
              <div className="flex items-center gap-3">
                <span className="font-mono text-slate-500 text-[11px]">
                  {new Date(entry.event_timestamp).toLocaleTimeString()}
                </span>
                <span className="font-mono text-slate-200 font-medium">
                  {entry.event_type}
                </span>
                <span className="text-slate-400 text-[11px]">
                  by {entry.actor}
                </span>
              </div>
              <div>
                {entry.policy_outcome ? (
                  <StatusBadge status={entry.policy_outcome} size="sm" />
                ) : (
                  <span className="text-slate-400 text-[11px]">
                    {entry.new_status || '—'}
                  </span>
                )}
              </div>
            </div>
          ))}
        </div>

        {/* Full Audit Log (Expands upon request) */}
        {showFullAuditLog && (
          <div className="border-t border-slate-800">
            <AuditTimeline auditTrail={auditTrail} />
          </div>
        )}
      </div>
    </div>
  );
};
