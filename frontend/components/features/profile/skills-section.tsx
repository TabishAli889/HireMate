"use client";

import { Wrench } from "lucide-react";
import { ChipInput } from "@/components/features/profile/chip-input";
import { SectionCard } from "@/components/features/profile/section-card";

interface SkillsSectionProps {
  skills: string[];
  onChange: (skills: string[]) => void;
}

export function SkillsSection({ skills, onChange }: SkillsSectionProps) {
  return (
    <SectionCard
      icon={Wrench}
      title="Skills"
      description="Only skills you can honestly talk about in an interview. Matching uses this list."
      action={<span className="text-sm font-medium text-muted-foreground">{skills.length}</span>}
    >
      <ChipInput label="Skills" values={skills} onChange={onChange} placeholder="Add a skill (comma or Enter)" />
    </SectionCard>
  );
}
