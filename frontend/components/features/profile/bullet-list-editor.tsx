"use client";

import { Plus, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { removeAt } from "@/lib/profile";

interface BulletListEditorProps {
  bullets: string[];
  onChange: (bullets: string[]) => void;
  /** Used in accessible labels, e.g. "AI Intern at Acme". */
  context: string;
}

/** Edit, add and remove achievement bullets. */
export function BulletListEditor({ bullets, onChange, context }: BulletListEditorProps) {
  return (
    <div className="flex flex-col gap-2">
      <span className="text-xs font-medium text-muted-foreground">Bullet points</span>
      {bullets.length === 0 && <p className="text-sm text-muted-foreground">No bullets yet.</p>}
      <ol className="flex flex-col gap-2">
        {bullets.map((bullet, index) => (
          <li key={index} className="flex items-start gap-2">
            <span className="mt-3 size-1.5 shrink-0 rounded-full bg-primary" aria-hidden />
            <Textarea
              rows={2}
              value={bullet}
              onChange={(e) => onChange(bullets.map((b, i) => (i === index ? e.target.value : b)))}
              aria-label={`Bullet ${index + 1} for ${context}`}
              className="min-h-[3.25rem]"
            />
            <Button
              type="button"
              variant="ghost"
              size="icon"
              onClick={() => onChange(removeAt(bullets, index))}
              aria-label={`Remove bullet ${index + 1} for ${context}`}
              className="shrink-0 text-muted-foreground hover:text-destructive"
            >
              <Trash2 aria-hidden />
            </Button>
          </li>
        ))}
      </ol>
      <Button type="button" variant="ghost" size="sm" className="self-start text-primary" onClick={() => onChange([...bullets, ""])}>
        <Plus aria-hidden />
        Add bullet
      </Button>
    </div>
  );
}
