import React from 'react';
import { CaseStatus, PolicyOutcome } from '../types/api';
import { Badge, type BadgeVariantProps } from './ui/badge';
import { cn } from '../lib/utils';

export interface StatusBadgeProps {
  status: CaseStatus | PolicyOutcome | string;
  size?: 'sm' | 'md';
  className?: string;
}

interface StatusConfig {
  variant: NonNullable<BadgeVariantProps['variant']>;
  dot: string;
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({
  status,
  size = 'sm',
  className,
}) => {
  const getStatusConfig = (s: string): StatusConfig => {
    switch (s) {
      case 'VERIFIED_RECOVERED':
      case 'ALLOW':
      case 'PAID':
      case 'CAPTURED':
      case 'SUCCESS':
        return {
          variant: 'emerald',
          dot: 'bg-emerald-500',
        };
      case 'ESCALATED':
      case 'ESCALATE':
      case 'HUMAN_ESCALATION':
        return {
          variant: 'amber',
          dot: 'bg-amber-500',
        };
      case 'BLOCK':
      case 'STOPPED':
      case 'STOP':
      case 'FAILED':
      case 'CLOSED_UNRECOVERABLE':
        return {
          variant: 'rose',
          dot: 'bg-rose-500',
        };
      case 'DOWNGRADE':
      case 'UPDATE_PAYMENT_METHOD':
      case 'RETRY_SCHEDULED':
        return {
          variant: 'indigo',
          dot: 'bg-indigo-400',
        };
      case 'ACTION_IN_PROGRESS':
      case 'DETECTED':
      case 'DIAGNOSED':
      case 'POLICY_EVALUATED':
      case 'CREATED':
        return {
          variant: 'sky',
          dot: 'bg-sky-400',
        };
      default:
        return {
          variant: 'slate',
          dot: 'bg-slate-400',
        };
    }
  };

  const formatText = (text: string) => {
    return text.replace(/_/g, ' ');
  };

  const config = getStatusConfig(status);

  return (
    <Badge
      variant={config.variant}
      size={size}
      className={cn('shrink-0', className)}
    >
      <span className={cn('h-1.5 w-1.5 rounded-full', config.dot)} />
      <span className="capitalize">{formatText(status.toLowerCase())}</span>
    </Badge>
  );
};
