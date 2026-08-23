import * as React from 'react';
import { cva, type VariantProps } from 'class-variance-authority';
import { cn } from '../../lib/utils';

export const badgeVariants = cva(
  'inline-flex items-center gap-1.5 font-sans font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-slate-400 focus:ring-offset-2',
  {
    variants: {
      variant: {
        default: 'border-transparent bg-slate-800 text-slate-100',
        secondary: 'border-transparent bg-slate-900 text-slate-300',
        outline: 'border border-slate-700 bg-transparent text-slate-300',
        emerald: 'border border-emerald-500/20 bg-emerald-500/10 text-emerald-400',
        amber: 'border border-amber-500/20 bg-amber-500/10 text-amber-400',
        rose: 'border border-rose-500/20 bg-rose-500/10 text-rose-400',
        indigo: 'border border-indigo-500/20 bg-indigo-500/10 text-indigo-300',
        sky: 'border border-sky-500/20 bg-sky-500/10 text-sky-300',
        slate: 'border border-slate-700 bg-slate-800/80 text-slate-300',
      },
      size: {
        sm: 'px-2 py-0.5 rounded text-xs',
        md: 'px-2.5 py-1 rounded-md text-xs',
        lg: 'px-3 py-1.5 rounded-md text-sm',
      },
    },
    defaultVariants: {
      variant: 'default',
      size: 'sm',
    },
  }
);

export type BadgeVariantProps = VariantProps<typeof badgeVariants>;

export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    BadgeVariantProps {}

export const Badge: React.FC<BadgeProps> = ({
  className,
  variant,
  size,
  children,
  ...props
}) => {
  return (
    <div
      className={cn(badgeVariants({ variant, size }), className)}
      {...props}
    >
      {children}
    </div>
  );
};
