import * as React from 'react';
import { cva, type VariantProps } from 'class-variance-authority';
import { cn } from '../../lib/utils';

export const badgeVariants = cva(
  'inline-flex items-center gap-1.5 font-sans font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-[#262B33] focus:ring-offset-2',
  {
    variants: {
      variant: {
        default: 'border-transparent bg-[#14171C] text-[#ECEFF3]',
        secondary: 'border-transparent bg-[#0B0D10] text-[#8B93A1]',
        outline: 'border border-[#262B33] bg-transparent text-[#8B93A1]',
        emerald: 'border border-[#2DBE8F]/20 bg-[#2DBE8F]/10 text-[#2DBE8F]',
        amber: 'border border-[#E8A33D]/20 bg-[#E8A33D]/10 text-[#E8A33D]',
        rose: 'border border-[#C24C4C]/20 bg-[#C24C4C]/10 text-[#D4605F]',
        indigo: 'border border-indigo-500/20 bg-indigo-500/10 text-indigo-300',
        sky: 'border border-sky-500/20 bg-sky-500/10 text-sky-300',
        slate: 'border border-[#262B33] bg-[#14171C] text-[#8B93A1]',
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
