"use client";

import { useMounted } from "@/hooks/use-mounted";

function partOfDay(hour: number): string {
  if (hour < 12) return "Good morning";
  if (hour < 17) return "Good afternoon";
  return "Good evening";
}

/** Time-of-day greeting computed in the user's own timezone (client-side). */
export function Greeting({ name }: { name?: string }) {
  const mounted = useMounted();
  const salutation = mounted ? partOfDay(new Date().getHours()) : "Welcome";
  return (
    <>
      {salutation}
      {name ? (
        <>
          , <span className="text-gradient">{name}</span>
        </>
      ) : null}
    </>
  );
}
