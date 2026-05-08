import * as React from 'react';
import { cva, type VariantProps } from 'class-variance-authority';
import { cn } from '@/lib/utils';

const badgeVariants = cva(
  'inline-flex items-center gap-1 border px-2 py-0.5 font-mono text-[0.65rem] uppercase tracking-[0.14em] leading-none whitespace-nowrap',
  {
    variants: {
      variant: {
        default: 'border-rule bg-bg text-ink-soft',
        ok: 'border-olive-deep bg-olive-deep/10 text-olive-deep',
        warn: 'border-[#B68E1F] bg-[#B68E1F]/10 text-[#7A5E10]',
        alert: 'border-accent bg-accent/10 text-accent',
        muted: 'border-rule bg-transparent text-ink-mute',
        outline: 'border-ink bg-transparent text-ink',
      },
    },
    defaultVariants: { variant: 'default' },
  },
);

export interface BadgeProps
  extends React.HTMLAttributes<HTMLSpanElement>,
    VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, ...props }: BadgeProps) {
  return <span className={cn(badgeVariants({ variant }), className)} {...props} />;
}

export { Badge, badgeVariants };
