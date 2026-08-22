import React from 'react';

interface MetricCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  badgeText?: string;
  badgeVariant?: 'success' | 'warning' | 'danger' | 'info' | 'neutral';
  highlight?: boolean;
}

export const MetricCard: React.FC<MetricCardProps> = ({
  title,
  value,
  subtitle,
  badgeText,
  badgeVariant = 'neutral',
  highlight = false,
}) => {
  const getBadgeStyle = () => {
    switch (badgeVariant) {
      case 'success':
        return 'text-emerald-400 bg-emerald-500/10 border-emerald-500/20';
      case 'warning':
        return 'text-amber-400 bg-amber-500/10 border-amber-500/20';
      case 'danger':
        return 'text-rose-400 bg-rose-500/10 border-rose-500/20';
      case 'info':
        return 'text-sky-400 bg-sky-500/10 border-sky-500/20';
      default:
        return 'text-slate-400 bg-slate-800/80 border-slate-700';
    }
  };

  return (
    <div
      className={`rounded-lg border p-5 transition-colors ${
        highlight
          ? 'border-slate-700 bg-slate-900/90'
          : 'border-slate-800/80 bg-slate-900/40'
      }`}
    >
      <div className="flex items-center justify-between">
        <span className="text-xs font-medium text-slate-400 font-sans">
          {title}
        </span>
        {badgeText && (
          <span
            className={`inline-flex items-center rounded px-2 py-0.5 text-[11px] font-medium border ${getBadgeStyle()}`}
          >
            {badgeText}
          </span>
        )}
      </div>

      <div className="mt-3">
        <span className="text-2xl sm:text-3xl font-semibold tracking-tight text-white font-mono">
          {value}
        </span>
      </div>

      {subtitle && (
        <p className="mt-1.5 text-xs text-slate-500 font-sans">{subtitle}</p>
      )}
    </div>
  );
};
