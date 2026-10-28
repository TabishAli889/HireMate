"use client";

import { AnimatePresence, motion } from "framer-motion";
import { Loader2, Save, Undo2 } from "lucide-react";
import { Button } from "@/components/ui/button";

interface SaveBarProps {
  visible: boolean;
  saving: boolean;
  onSave: () => void;
  onDiscard: () => void;
}

/** Floating "unsaved changes" bar; sits above the mobile tab bar. */
export function SaveBar({ visible, saving, onSave, onDiscard }: SaveBarProps) {
  return (
    <AnimatePresence>
      {visible && (
        <motion.div
          initial={{ y: 24, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          exit={{ y: 24, opacity: 0 }}
          transition={{ type: "spring", stiffness: 380, damping: 32 }}
          className="sticky bottom-[calc(var(--tabbar-height)+1rem)] z-20 mt-6 md:bottom-6"
        >
          <div role="status" className="glass mx-auto flex max-w-xl items-center justify-between gap-3 rounded-2xl px-4 py-3">
            <p className="text-sm font-medium">You have unsaved changes</p>
            <div className="flex items-center gap-2">
              <Button variant="ghost" size="sm" onClick={onDiscard} disabled={saving}>
                <Undo2 aria-hidden />
                Discard
              </Button>
              <Button size="sm" onClick={onSave} disabled={saving}>
                {saving ? <Loader2 className="animate-spin" aria-hidden /> : <Save aria-hidden />}
                {saving ? "Saving…" : "Save"}
              </Button>
            </div>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
