"use client";

import { GraduationCap, Plus } from "lucide-react";
import { EntryCard } from "@/components/features/profile/entry-card";
import { SectionCard } from "@/components/features/profile/section-card";
import { Button } from "@/components/ui/button";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { newEducation, removeAt, updateAt } from "@/lib/profile";
import type { EducationItem } from "@/types/profile";

interface EducationSectionProps {
  items: EducationItem[];
  onChange: (items: EducationItem[]) => void;
}

export function EducationSection({ items, onChange }: EducationSectionProps) {
  const set = (index: number, patch: Partial<EducationItem>) => onChange(updateAt(items, index, patch));

  return (
    <SectionCard
      icon={GraduationCap}
      title="Education"
      description="Degrees, diplomas and certifications."
      action={
        <Button type="button" variant="outline" size="sm" onClick={() => onChange([...items, newEducation()])}>
          <Plus aria-hidden />
          Add
        </Button>
      }
    >
      {items.length === 0 ? (
        <p className="text-sm text-muted-foreground">No education added yet.</p>
      ) : (
        <ul className="flex flex-col gap-4">
          {items.map((item, index) => (
            <EntryCard
              key={index}
              title={item.degree || item.institution || `Education ${index + 1}`}
              onRemove={() => onChange(removeAt(items, index))}
            >
              <div className="grid gap-4 sm:grid-cols-2">
                <Field label="Institution">
                  {(id) => <Input id={id} value={item.institution} onChange={(e) => set(index, { institution: e.target.value })} />}
                </Field>
                <Field label="Degree">
                  {(id) => <Input id={id} value={item.degree} onChange={(e) => set(index, { degree: e.target.value })} placeholder="BS Computer Science" />}
                </Field>
                <Field label="Field of study">
                  {(id) => <Input id={id} value={item.field_of_study} onChange={(e) => set(index, { field_of_study: e.target.value })} />}
                </Field>
                <div className="grid grid-cols-2 gap-3">
                  <Field label="Start">{(id) => <Input id={id} value={item.start_date} onChange={(e) => set(index, { start_date: e.target.value })} />}</Field>
                  <Field label="End">{(id) => <Input id={id} value={item.end_date} onChange={(e) => set(index, { end_date: e.target.value })} />}</Field>
                </div>
                <Field label="Details" className="sm:col-span-2" hint="Grades, coursework or honours, as on your resume.">
                  {(id) => <Textarea id={id} rows={2} value={item.details} onChange={(e) => set(index, { details: e.target.value })} />}
                </Field>
              </div>
            </EntryCard>
          ))}
        </ul>
      )}
    </SectionCard>
  );
}
