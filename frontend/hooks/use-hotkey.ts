"use client";

import { useEffect, useRef } from "react";

interface HotkeyOptions {
  /** Require Ctrl (Windows/Linux) or ⌘ (macOS). Default true. */
  withModifier?: boolean;
  /** Fire even while typing in an input/textarea. Default true. */
  allowInInputs?: boolean;
}

function isTypingTarget(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) return false;
  return target.isContentEditable || ["INPUT", "TEXTAREA", "SELECT"].includes(target.tagName);
}

/** Registers a global keyboard shortcut such as Ctrl/⌘+K. */
export function useHotkey(key: string, handler: (event: KeyboardEvent) => void, options: HotkeyOptions = {}): void {
  const { withModifier = true, allowInInputs = true } = options;
  const handlerRef = useRef(handler);

  useEffect(() => {
    handlerRef.current = handler;
  });

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key.toLowerCase() !== key.toLowerCase()) return;
      if (withModifier && !(event.metaKey || event.ctrlKey)) return;
      if (!allowInInputs && isTypingTarget(event.target)) return;
      event.preventDefault();
      handlerRef.current(event);
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [key, withModifier, allowInInputs]);
}
