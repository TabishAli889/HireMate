import type { HTMLAttributes } from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const badgeVariants = cva("inline-flex items-center gap-1 whitespace-nowrap rounded-lg px-2.5 py-1 text-xs font-medium", {
  variants: {
    variant: {
      default: "bg-accent text-accent-foreground",
      success: "bg-success-soft text-success",
      warning: "bg-warning-soft text-warning",
      muted: "bg-muted text-muted-foreground",
      outline: "border border-border text-muted-foreground",
    },
  },
  defaultVariants: { variant: "default" },
});

export interface BadgeProps extends HTMLAttributes<HTMLSpanElement>, VariantProps<typeof badgeVariants> {}

export function Badge({ className, variant, ...props }: BadgeProps) {
  return <span className={cn(badgeVariants({ variant }), className)} {...props} />;
}
