import type { ReactNode } from "react";
import type { LucideIcon } from "lucide-react";
import { Card } from "@/components/ui/card";

interface SectionCardProps {
  icon: LucideIcon;
  title: string;
  description?: string;
  /** Right-aligned header action, e.g. an "Add" button. */
  action?: ReactNode;
  children: ReactNode;
}

/** Card wrapper for one Profile Vault section. */
export function SectionCard({ icon: Icon, title, description, action, children }: SectionCardProps) {
  const headingId = `section-${title.toLowerCase().replace(/\W+/g, "-")}`;
  return (
    <Card role="region" aria-labelledby={headingId} className="p-5 sm:p-6">
      <div className="mb-5 flex items-start justify-between gap-4">
        <div className="flex items-start gap-3">
          <span className="grid size-10 shrink-0 place-items-center rounded-xl bg-accent text-accent-foreground">
            <Icon className="size-5" aria-hidden />
          </span>
          <div>
            <h2 id={headingId} className="text-base font-semibold">
              {title}
            </h2>
            {description && <p className="mt-0.5 text-sm text-muted-foreground">{description}</p>}
          </div>
        </div>
        {action}
      </div>
      {children}
    </Card>
  );
}
