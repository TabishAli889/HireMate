"use client";

import { RotateCcw, ShieldCheck, TriangleAlert } from "lucide-react";
import { ProfileEditor } from "@/components/features/profile/profile-editor";
import { ResumeDropzone } from "@/components/features/profile/resume-dropzone";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useProfile } from "@/hooks/use-profile";

function VaultSkeleton() {
  return (
    <div role="status" aria-label="Loading your profile" className="flex flex-col gap-6">
      <div className="grid gap-6 lg:grid-cols-[1.4fr_1fr]">
        <Skeleton className="h-40 rounded-2xl" />
        <Skeleton className="h-40 rounded-2xl" />
      </div>
      <Skeleton className="h-72 rounded-2xl" />
      <Skeleton className="h-32 rounded-2xl" />
      <Skeleton className="h-56 rounded-2xl" />
    </div>
  );
}

/** Loading / empty / error / editor states for the Profile Vault. */
export function ProfileVault() {
  const { state, reload, save, replace } = useProfile();

  if (state.status === "loading") return <VaultSkeleton />;

  if (state.status === "error") {
    return (
      <Card role="alert" className="mx-auto flex max-w-lg flex-col items-center px-6 py-12 text-center">
        <span className="grid size-14 place-items-center rounded-2xl bg-warning-soft text-warning">
          <TriangleAlert className="size-7" aria-hidden />
        </span>
        <h2 className="mt-5 text-lg font-semibold">Couldn’t load your profile</h2>
        <p className="mt-2 text-sm text-muted-foreground">{state.message}</p>
        <Button className="mt-6" onClick={() => void reload()}>
          <RotateCcw aria-hidden />
          Try again
        </Button>
      </Card>
    );
  }

  if (state.status === "empty") {
    return (
      <div className="mx-auto flex max-w-2xl flex-col gap-4">
        <ResumeDropzone onUploaded={replace} />
        <p className="inline-flex items-start justify-center gap-2 text-center text-sm text-muted-foreground">
          <ShieldCheck className="mt-0.5 size-4 shrink-0 text-success" aria-hidden />
          HireMate only extracts what’s written in your resume. You can review and edit every field afterwards.
        </p>
      </div>
    );
  }

  return <ProfileEditor key={state.profile.updated_at} profile={state.profile} onSave={save} onReplaced={replace} />;
}
