"use client";

import { UserRound } from "lucide-react";
import { ChipInput } from "@/components/features/profile/chip-input";
import { SectionCard } from "@/components/features/profile/section-card";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import type { ProfileData } from "@/types/profile";

type Basics = Pick<ProfileData, "full_name" | "headline" | "email" | "phone" | "location" | "links" | "summary">;

interface BasicsSectionProps {
  value: Basics;
  onChange: (patch: Partial<Basics>) => void;
}

/** Name, contact details, links and summary. */
export function BasicsSection({ value, onChange }: BasicsSectionProps) {
  return (
    <SectionCard icon={UserRound} title="Basics" description="How employers see and reach you.">
      <div className="grid gap-4 sm:grid-cols-2">
        <Field label="Full name">
          {(id) => <Input id={id} value={value.full_name} onChange={(e) => onChange({ full_name: e.target.value })} autoComplete="name" />}
        </Field>
        <Field label="Headline">
          {(id) => (
            <Input
              id={id}
              value={value.headline}
              onChange={(e) => onChange({ headline: e.target.value })}
              placeholder="e.g. CS student · AI developer"
            />
          )}
        </Field>
        <Field label="Email">
          {(id) => (
            <Input id={id} type="email" value={value.email} onChange={(e) => onChange({ email: e.target.value })} autoComplete="email" />
          )}
        </Field>
        <Field label="Phone">
          {(id) => <Input id={id} type="tel" value={value.phone} onChange={(e) => onChange({ phone: e.target.value })} autoComplete="tel" />}
        </Field>
        <Field label="Location" className="sm:col-span-2">
          {(id) => <Input id={id} value={value.location} onChange={(e) => onChange({ location: e.target.value })} />}
        </Field>
        <div className="flex flex-col gap-1.5 sm:col-span-2">
          <span className="text-xs font-medium text-muted-foreground">Links</span>
          <ChipInput
            label="Links"
            values={value.links}
            onChange={(links) => onChange({ links })}
            placeholder="Paste a GitHub, LinkedIn or portfolio URL and press Enter"
          />
        </div>
        <Field label="Summary" className="sm:col-span-2" hint={`${value.summary.length} characters · 2–3 sentences works best`}>
          {(id) => <Textarea id={id} rows={4} value={value.summary} onChange={(e) => onChange({ summary: e.target.value })} />}
        </Field>
      </div>
    </SectionCard>
  );
}
