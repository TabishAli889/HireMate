import { cn } from "@/lib/utils";

interface ProgressProps {
  /** 0-100, or null for an indeterminate (working…) bar. */
  value: number | null;
  label: string;
  className?: string;
}

export function Progress({ value, label, className }: ProgressProps) {
  const indeterminate = value === null;
  return (
    <div
      role="progressbar"
      aria-label={label}
      aria-valuemin={0}
      aria-valuemax={100}
      aria-valuenow={value ?? undefined}
      className={cn("relative h-2 w-full overflow-hidden rounded-full bg-muted", className)}
    >
      <div
        className={cn(
          "absolute inset-y-0 left-0 rounded-full bg-brand transition-[width] duration-300",
          indeterminate && "animate-indeterminate w-1/3",
        )}
        style={indeterminate ? undefined : { width: `${value}%` }}
      />
    </div>
  );
}
