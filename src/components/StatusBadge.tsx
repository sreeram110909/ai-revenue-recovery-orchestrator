import React from 'react';
import { CaseStatus, PolicyOutcome } from '../types/api';

interface StatusBadgeProps {
  status: CaseStatus | PolicyOutcome | string;
  size?: 'sm' | 'md';
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({ status, size = 'sm' }) => {
  const getStyle = () => {
    switch (status) {
      case 'VERIFIED_RECOVERED':
      case 'ALLOW':
      case 'PAID':
      case 'CAPTURED':
      case 'SUCCESS':
        return {
          dot: 'bg-emerald-500',
          text: 'text-emerald-400',
          bg: 'bg-emerald-500/10 border-emerald-500/20',
        };
      case 'ESCALATED':
      case 'ESCALATE':
      case 'HUMAN_ESCALATION':
        return {
          dot: 'bg-amber-500',
          text: 'text-amber-400',
          bg: 'bg-amber-500/10 border-amber-500/20',
        };
      case 'BLOCK':
      case 'STOPPED':
      case 'STOP':
      case 'FAILED':
      case 'CLOSED_UNRECOVERABLE':
        return {
          dot: 'bg-rose-500',
          text: 'text-rose-400',
          bg: 'bg-rose-500/10 border-rose-500/20',
        };
      case 'DOWNGRADE':
      case 'UPDATE_PAYMENT_METHOD':
      case 'RETRY_SCHEDULED':
        return {
          dot: 'bg-indigo-400',
          text: 'text-indigo-300',
          bg: 'bg-indigo-500/10 border-indigo-500/20',
        };
      case 'ACTION_IN_PROGRESS':
      case 'DETECTED':
      case 'DIAGNOSED':
      case 'POLICY_EVALUATED':
      case 'CREATED':
        return {
          dot: 'bg-sky-400',
          text: 'text-sky-300',
          bg: 'bg-sky-500/10 border-sky-500/20',
        };
      default:
        return {
          dot: 'bg-slate-400',
          text: 'text-slate-300',
          bg: 'bg-slate-800/80 border-slate-700',
        };
    }
  };

  const formatText = (text: string) => {
    return text.replace(/_/g, ' ');
  };

  const style = getStyle();

  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-xs font-sans font-medium border ${style.bg} ${style.text}`}
    >
      <span className={`h-1.5 w-1.5 rounded-full ${style.dot}`} />
      <span className="capitalize">{formatText(status.toLowerCase())}</span>
    </span>
  );
};
