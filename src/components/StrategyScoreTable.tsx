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
    <div className="rounded-lg border border-slate-800 bg-slate-900/30 p-5 space-y-4">
      <div className="flex items-center justify-between border-b border-slate-800 pb-3">
        <div>
          <h4 className="text-xs font-semibold text-white uppercase tracking-wider font-sans">
            Strategy Ranking
          </h4>
          <p className="text-xs text-slate-500 mt-0.5">
            Deterministic scoring across locked action space
          </p>
        </div>
        {recommendedStrategy && (
          <span className="text-xs font-mono text-emerald-400 font-medium">
            Top: {recommendedStrategy}
          </span>
        )}
      </div>

      {rationale && (
        <p className="text-xs text-slate-400 p-3 rounded bg-slate-950/60 border border-slate-800/80">
          <span className="text-slate-500 font-medium">Diagnostic rationale: </span>
          {rationale}
        </p>
      )}

      <div className="rounded border border-slate-800 overflow-hidden divide-y divide-slate-800/60">
        {allowedStrategies.map((s) => {
          const isTop = s.name === recommendedStrategy;
          return (
            <div
              key={s.name}
              className={`flex items-center justify-between p-3 text-xs ${
                isTop ? 'bg-slate-800/40 text-white' : 'bg-slate-950/30 text-slate-400'
              }`}
            >
              <div>
                <span className={`font-mono font-medium ${isTop ? 'text-emerald-400' : 'text-slate-300'}`}>
                  {s.name}
                </span>
                <p className="text-[11px] text-slate-500 mt-0.5">{s.desc}</p>
              </div>

              <div>
                {isTop ? (
                  <span className="text-[11px] text-emerald-400 font-medium">Selected</span>
                ) : (
                  <span className="text-[11px] text-slate-600">—</span>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
