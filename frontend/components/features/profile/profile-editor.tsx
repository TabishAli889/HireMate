"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { FileText, Info } from "lucide-react";
import { toast } from "sonner";
import { BasicsSection } from "@/components/features/profile/basics-section";
import { CompletenessMeter } from "@/components/features/profile/completeness-meter";
import { EducationSection } from "@/components/features/profile/education-section";
import { ExperienceSection } from "@/components/features/profile/experience-section";
import { ProjectsSection } from "@/components/features/profile/projects-section";
import { ResumeDropzone } from "@/components/features/profile/resume-dropzone";
import { SaveBar } from "@/components/features/profile/save-bar";
import { SkillsSection } from "@/components/features/profile/skills-section";
import { Card } from "@/components/ui/card";
import { ApiError } from "@/lib/api";
import { profileCompleteness, toProfileData } from "@/lib/profile";
import type { Profile, ProfileData } from "@/types/profile";

interface ProfileEditorProps {
  profile: Profile;
  onSave: (data: ProfileData) => Promise<Profile>;
  onReplaced: (profile: Profile) => void;
}

/** Editable Profile Vault. Holds a local draft; mount with `key` so a new upload resets it. */
export function ProfileEditor({ profile, onSave, onReplaced }: ProfileEditorProps) {
  const saved = useMemo(() => toProfileData(profile), [profile]);
  const [draft, setDraft] = useState<ProfileData>(saved);
  const [saving, setSaving] = useState(false);

  const dirty = useMemo(() => JSON.stringify(draft) !== JSON.stringify(saved), [draft, saved]);
  const completeness = useMemo(() => profileCompleteness(draft), [draft]);

  const patch = useCallback((changes: Partial<ProfileData>) => setDraft((d) => ({ ...d, ...changes })), []);

  useEffect(() => {
    if (!dirty) return;
    const warn = (event: BeforeUnloadEvent) => {
      event.preventDefault();
      event.returnValue = "";
    };
    window.addEventListener("beforeunload", warn);
    return () => window.removeEventListener("beforeunload", warn);
  }, [dirty]);

  const save = async () => {
    setSaving(true);
    try {
      const updated = await onSave(draft);
      setDraft(toProfileData(updated));
      toast.success("Profile saved");
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Could not save your profile.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="flex flex-col gap-6">
      {profile.is_demo && (
        <Card role="note" className="flex items-start gap-3 border-primary/30 p-4">
          <Info className="mt-0.5 size-5 shrink-0 text-primary" aria-hidden />
          <p className="text-sm">
            <span className="font-semibold">This is demo data.</span>{" "}
            <span className="text-muted-foreground">Upload your own resume to replace it. Nothing here is about you yet.</span>
          </p>
        </Card>
      )}

      <div className="grid gap-6 lg:grid-cols-[1.4fr_1fr]">
        <CompletenessMeter {...completeness} />
        <div className="flex flex-col gap-2">
          <ResumeDropzone compact onUploaded={onReplaced} />
          {profile.source_filename && (
            <p className="inline-flex items-center gap-1.5 px-1 text-xs text-muted-foreground">
              <FileText className="size-3.5" aria-hidden />
              Extracted from <span className="truncate font-medium">{profile.source_filename}</span>
            </p>
          )}
        </div>
      </div>

      <BasicsSection value={draft} onChange={patch} />
      <SkillsSection skills={draft.skills} onChange={(skills) => patch({ skills })} />
      <ExperienceSection items={draft.experience} onChange={(experience) => patch({ experience })} />
      <ProjectsSection items={draft.projects} onChange={(projects) => patch({ projects })} />
      <EducationSection items={draft.education} onChange={(education) => patch({ education })} />

      <SaveBar visible={dirty} saving={saving} onSave={() => void save()} onDiscard={() => setDraft(saved)} />
    </div>
  );
}
