"use client";

import { Briefcase, Plus } from "lucide-react";
import { BulletListEditor } from "@/components/features/profile/bullet-list-editor";
import { EntryCard } from "@/components/features/profile/entry-card";
import { SectionCard } from "@/components/features/profile/section-card";
import { Button } from "@/components/ui/button";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { newExperience, removeAt, updateAt } from "@/lib/profile";
import type { ExperienceItem } from "@/types/profile";

interface ExperienceSectionProps {
  items: ExperienceItem[];
  onChange: (items: ExperienceItem[]) => void;
}

function entryTitle(item: ExperienceItem, index: number): string {
  if (item.title && item.company) return `${item.title} at ${item.company}`;
  return item.title || item.company || `Experience ${index + 1}`;
}

export function ExperienceSection({ items, onChange }: ExperienceSectionProps) {
  const set = (index: number, patch: Partial<ExperienceItem>) => onChange(updateAt(items, index, patch));

  return (
    <SectionCard
      icon={Briefcase}
      title="Experience"
      description="Jobs, internships and volunteering."
      action={
        <Button type="button" variant="outline" size="sm" onClick={() => onChange([...items, newExperience()])}>
          <Plus aria-hidden />
          Add
        </Button>
      }
    >
      {items.length === 0 ? (
        <p className="text-sm text-muted-foreground">No experience yet. Internships, part-time work and volunteering all count.</p>
      ) : (
        <ul className="flex flex-col gap-4">
          {items.map((item, index) => {
            const title = entryTitle(item, index);
            return (
              <EntryCard key={index} title={title} onRemove={() => onChange(removeAt(items, index))}>
                <div className="grid gap-4 sm:grid-cols-2">
                  <Field label="Job title">{(id) => <Input id={id} value={item.title} onChange={(e) => set(index, { title: e.target.value })} />}</Field>
                  <Field label="Company">{(id) => <Input id={id} value={item.company} onChange={(e) => set(index, { company: e.target.value })} />}</Field>
                  <Field label="Location">{(id) => <Input id={id} value={item.location} onChange={(e) => set(index, { location: e.target.value })} />}</Field>
                  <div className="grid grid-cols-2 gap-3">
                    <Field label="Start">
                      {(id) => <Input id={id} value={item.start_date} onChange={(e) => set(index, { start_date: e.target.value })} placeholder="Jul 2025" />}
                    </Field>
                    <Field label="End">
                      {(id) => <Input id={id} value={item.end_date} onChange={(e) => set(index, { end_date: e.target.value })} placeholder="Present" />}
                    </Field>
                  </div>
                </div>
                <BulletListEditor bullets={item.bullets} onChange={(bullets) => set(index, { bullets })} context={title} />
              </EntryCard>
            );
          })}
        </ul>
      )}
    </SectionCard>
  );
}
