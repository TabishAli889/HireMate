"use client";

import { FolderGit2, Plus } from "lucide-react";
import { BulletListEditor } from "@/components/features/profile/bullet-list-editor";
import { ChipInput } from "@/components/features/profile/chip-input";
import { EntryCard } from "@/components/features/profile/entry-card";
import { SectionCard } from "@/components/features/profile/section-card";
import { Button } from "@/components/ui/button";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { newProject, removeAt, updateAt } from "@/lib/profile";
import type { ProjectItem } from "@/types/profile";

interface ProjectsSectionProps {
  items: ProjectItem[];
  onChange: (items: ProjectItem[]) => void;
}

export function ProjectsSection({ items, onChange }: ProjectsSectionProps) {
  const set = (index: number, patch: Partial<ProjectItem>) => onChange(updateAt(items, index, patch));

  return (
    <SectionCard
      icon={FolderGit2}
      title="Projects"
      description="For students, projects often matter as much as experience."
      action={
        <Button type="button" variant="outline" size="sm" onClick={() => onChange([...items, newProject()])}>
          <Plus aria-hidden />
          Add
        </Button>
      }
    >
      {items.length === 0 ? (
        <p className="text-sm text-muted-foreground">No projects yet. Course projects, FYPs and side projects all count.</p>
      ) : (
        <ul className="flex flex-col gap-4">
          {items.map((item, index) => {
            const title = item.name || `Project ${index + 1}`;
            return (
              <EntryCard key={index} title={title} onRemove={() => onChange(removeAt(items, index))}>
                <div className="grid gap-4 sm:grid-cols-2">
                  <Field label="Project name">{(id) => <Input id={id} value={item.name} onChange={(e) => set(index, { name: e.target.value })} />}</Field>
                  <Field label="Link">
                    {(id) => <Input id={id} type="url" value={item.link} onChange={(e) => set(index, { link: e.target.value })} placeholder="https://github.com/…" />}
                  </Field>
                  <Field label="Description" className="sm:col-span-2">
                    {(id) => <Textarea id={id} rows={2} value={item.description} onChange={(e) => set(index, { description: e.target.value })} />}
                  </Field>
                  <div className="flex flex-col gap-1.5 sm:col-span-2">
                    <span className="text-xs font-medium text-muted-foreground">Tech stack</span>
                    <ChipInput
                      label={`Tech stack for ${title}`}
                      values={item.tech_stack}
                      onChange={(tech_stack) => set(index, { tech_stack })}
                      placeholder="Add a technology"
                    />
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
