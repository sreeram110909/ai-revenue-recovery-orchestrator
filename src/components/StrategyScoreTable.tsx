import React from 'react';
import { RecoveryStrategy, CaseType } from '../types/api';

interface StrategyScoreTableProps {
  caseType: CaseType;
  recommendedStrategy?: RecoveryStrategy | null;
  confidence?: number | null;
  rationale?: string | null;
}

export const StrategyScoreTable: React.FC<StrategyScoreTableProps> = ({
  caseType,
  recommendedStrategy,
  confidence,
  rationale,
}) => {
  const primaryStrategies: { name: RecoveryStrategy; desc: string }[] = [
    { name: 'PAYMENT_LINK', desc: 'Generate hosted Razorpay payment link' },
    { name: 'SMART_RETRY', desc: 'Schedule dynamic merchant orchestration retry' },
    { name: 'HUMAN_ESCALATION', desc: 'Route high-value or policy-sensitive case to human review' },
    { name: 'STOP', desc: 'Cease further recovery attempts' },
  ];

  const secondaryStrategies: { name: RecoveryStrategy; desc: string }[] = [
    { name: 'SUBSCRIPTION_RETRY', desc: 'Observe native Razorpay subscription retry lifecycle' },
    { name: 'UPDATE_PAYMENT_METHOD', desc: 'Request updated payment instrument / UPI mandate' },
    { name: 'HUMAN_ESCALATION', desc: 'Route critical subscription failure to support' },
    { name: 'STOP', desc: 'Cancel subscription recovery workflow' },
  ];

  const allowedStrategies = caseType === 'SUBSCRIPTION_RECURRING' ? secondaryStrategies : primaryStrategies;

  return (
    <div className="rounded-lg border border-[#262B33] bg-[#14171C]/80 p-5 space-y-4">
      <div className="flex items-center justify-between border-b border-[#262B33] pb-3">
        <div>
          <h4 className="text-xs font-semibold text-[#ECEFF3] uppercase tracking-wider font-heading">
            Strategy Ranking
          </h4>
          <p className="text-xs text-[#8B93A1] mt-0.5">
            Deterministic scoring across locked action space
          </p>
        </div>
        {recommendedStrategy ? (
          <span className="text-xs font-mono text-[#2DBE8F] font-medium">
            Top: {recommendedStrategy}
          </span>
        ) : (
          <span className="text-xs text-[#8B93A1] italic">
            Pending diagnosis
          </span>
        )}
      </div>

      {rationale && (
        <p className="text-xs text-[#8B93A1] p-3 rounded bg-[#0B0D10]/60 border border-[#262B33]">
          <span className="text-[#8B93A1] font-medium">Diagnostic rationale: </span>
          {rationale}
        </p>
      )}

      <div className="rounded border border-[#262B33] overflow-hidden divide-y divide-[#262B33]/60">
        {allowedStrategies.map((s) => {
          const isTop = s.name === recommendedStrategy;
          return (
            <div
              key={s.name}
              className={`flex items-center justify-between p-3 text-xs ${
                isTop ? 'bg-[#14171C] text-[#ECEFF3]' : 'bg-[#0B0D10]/30 text-[#8B93A1]'
              }`}
            >
              <div>
                <span className={`font-mono font-medium ${isTop ? 'text-[#2DBE8F]' : 'text-[#ECEFF3]/70'}`}>
                  {s.name}
                </span>
                <p className="text-[11px] text-[#8B93A1] mt-0.5">{s.desc}</p>
              </div>

              <div>
                {isTop ? (
                  <span className="text-[11px] text-[#2DBE8F] font-medium">Selected</span>
                ) : (
                  <span className="text-[11px] text-[#8B93A1]/40">—</span>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
