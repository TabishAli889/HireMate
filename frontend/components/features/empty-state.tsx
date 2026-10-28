import Link from "next/link";
import { ArrowRight, type LucideIcon } from "lucide-react";
import { EmptyIllustration } from "@/components/features/empty-illustration";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { cn } from "@/lib/utils";

interface EmptyStateProps {
  icon: LucideIcon;
  title: string;
  description: string;
  action?: { label: string; href: string };
  className?: string;
}

/** Friendly "nothing here yet" panel with an illustration and one clear next step. */
export function EmptyState({ icon, title, description, action, className }: EmptyStateProps) {
  return (
    <Card className={cn("flex flex-col items-center px-6 py-14 text-center", className)}>
      <EmptyIllustration icon={icon} />
      <h2 className="mt-6 text-xl font-semibold">{title}</h2>
      <p className="mt-2 max-w-md text-sm text-muted-foreground">{description}</p>
      {action && (
        <Button asChild className="mt-6">
          <Link href={action.href}>
            {action.label}
            <ArrowRight aria-hidden />
          </Link>
        </Button>
      )}
    </Card>
  );
}
