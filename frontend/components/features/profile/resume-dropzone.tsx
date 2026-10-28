"use client";

import { useEffect, useRef, useState, type DragEvent } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { CircleAlert, FileUp, Loader2, Sparkles } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { ApiError } from "@/lib/api";
import { MAX_UPLOAD_BYTES, MAX_UPLOAD_MB } from "@/lib/profile";
import { uploadFile } from "@/lib/upload";
import { cn } from "@/lib/utils";
import type { Profile } from "@/types/profile";

type Phase = { kind: "idle" } | { kind: "uploading"; percent: number } | { kind: "parsing" } | { kind: "error"; message: string };

interface ResumeDropzoneProps {
  onUploaded: (profile: Profile) => void;
  /** Smaller variant for "replace resume" once a profile exists. */
  compact?: boolean;
}

/** Returns an error message, or null if the file is an acceptable PDF. */
function checkFile(file: File): string | null {
  const isPdf = file.type === "application/pdf" || file.name.toLowerCase().endsWith(".pdf");
  if (!isPdf) return "Only PDF files are supported.";
  if (file.size > MAX_UPLOAD_BYTES) return `That file is over ${MAX_UPLOAD_MB} MB.`;
  if (file.size === 0) return "That file is empty.";
  return null;
}

/** Drag-and-drop (or click) resume upload with progress, then AI extraction. */
export function ResumeDropzone({ onUploaded, compact = false }: ResumeDropzoneProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const abortRef = useRef<AbortController | null>(null);
  const [dragging, setDragging] = useState(false);
  const [phase, setPhase] = useState<Phase>({ kind: "idle" });
  const busy = phase.kind === "uploading" || phase.kind === "parsing";

  useEffect(() => () => abortRef.current?.abort(), []);

  const start = async (file: File) => {
    const problem = checkFile(file);
    if (problem) {
      setPhase({ kind: "error", message: problem });
      toast.error(problem);
      return;
    }
    abortRef.current = new AbortController();
    setPhase({ kind: "uploading", percent: 0 });
    try {
      const profile = await uploadFile<Profile>("/profile/upload", file, {
        signal: abortRef.current.signal,
        onProgress: (percent) => setPhase(percent >= 100 ? { kind: "parsing" } : { kind: "uploading", percent }),
      });
      setPhase({ kind: "idle" });
      toast.success("Resume extracted. Please review each section before saving changes.");
      onUploaded(profile);
    } catch (err) {
      const message = err instanceof ApiError ? err.message : "Upload failed. Please try again.";
      setPhase({ kind: "error", message });
      toast.error(message);
    } finally {
      if (inputRef.current) inputRef.current.value = "";
    }
  };

  const onDrop = (event: DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    setDragging(false);
    if (busy) return;
    const file = event.dataTransfer.files[0];
    if (file) void start(file);
  };

  return (
    <div
      onDragOver={(e) => {
        e.preventDefault();
        if (!busy) setDragging(true);
      }}
      onDragLeave={(e) => {
        if (!e.currentTarget.contains(e.relatedTarget as Node | null)) setDragging(false);
      }}
      onDrop={onDrop}
      className={cn(
        "relative flex flex-col items-center justify-center rounded-2xl border-2 border-dashed border-border bg-card/40 text-center transition-all duration-200",
        compact ? "gap-3 px-5 py-6" : "gap-4 px-6 py-14",
        dragging && "scale-[1.01] border-primary bg-accent/60",
        phase.kind === "error" && "border-warning/60",
      )}
    >
      <input
        ref={inputRef}
        type="file"
        accept="application/pdf,.pdf"
        className="sr-only"
        tabIndex={-1}
        aria-hidden
        onChange={(e) => {
          const file = e.target.files?.[0];
          if (file) void start(file);
        }}
      />

      <AnimatePresence mode="wait" initial={false}>
        {busy ? (
          <motion.div
            key="busy"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="flex w-full max-w-sm flex-col items-center gap-3"
            aria-live="polite"
          >
            <span className="grid size-12 place-items-center rounded-2xl bg-brand text-[hsl(var(--gradient-foreground))] shadow-glow">
              {phase.kind === "parsing" ? <Sparkles className="size-6 animate-pulse" aria-hidden /> : <Loader2 className="size-6 animate-spin" aria-hidden />}
            </span>
            <p className="text-sm font-medium">
              {phase.kind === "uploading" ? `Uploading… ${phase.percent}%` : "Reading your resume with AI…"}
            </p>
            <Progress
              value={phase.kind === "uploading" ? phase.percent : null}
              label={phase.kind === "uploading" ? "Upload progress" : "Extracting profile"}
            />
            {phase.kind === "parsing" && (
              <p className="text-xs text-muted-foreground">Usually 5–20 seconds. Only what’s written in your resume is extracted.</p>
            )}
          </motion.div>
        ) : (
          <motion.div
            key="idle"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className={cn("flex flex-col items-center", compact ? "gap-2" : "gap-3")}
          >
            <span
              className={cn(
                "grid place-items-center rounded-2xl",
                compact ? "size-10 bg-accent text-accent-foreground" : "size-14 bg-brand text-[hsl(var(--gradient-foreground))] shadow-glow",
                phase.kind === "error" && "bg-warning-soft text-warning shadow-none",
              )}
            >
              {phase.kind === "error" ? <CircleAlert className="size-6" aria-hidden /> : <FileUp className={compact ? "size-5" : "size-7"} aria-hidden />}
            </span>
            <div>
              <p className={cn("font-semibold", compact ? "text-sm" : "text-lg")}>
                {compact ? "Replace with a new resume" : "Drop your resume here"}
              </p>
              <p className="mt-1 text-sm text-muted-foreground">
                {phase.kind === "error" ? phase.message : `PDF only, up to ${MAX_UPLOAD_MB} MB`}
              </p>
            </div>
            <Button
              type="button"
              variant={compact ? "outline" : "default"}
              size={compact ? "sm" : "default"}
              onClick={() => inputRef.current?.click()}
            >
              {phase.kind === "error" ? "Try another file" : "Choose PDF"}
            </Button>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
