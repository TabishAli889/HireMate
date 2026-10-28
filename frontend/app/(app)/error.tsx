"use client";

import { useEffect } from "react";
import { RotateCcw, TriangleAlert } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";

/** Route-level error boundary with a retry button. */
export default function RouteError({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <Card role="alert" className="mx-auto flex max-w-lg flex-col items-center px-6 py-12 text-center">
      <span className="grid size-14 place-items-center rounded-2xl bg-warning-soft text-warning">
        <TriangleAlert className="size-7" aria-hidden />
      </span>
      <h1 className="mt-5 text-xl font-semibold">Something went wrong</h1>
      <p className="mt-2 text-sm text-muted-foreground">
        This page hit an unexpected error. Your data is safe — try again, and if it keeps happening, check that the API is online.
      </p>
      <Button className="mt-6" onClick={reset}>
        <RotateCcw aria-hidden />
        Try again
      </Button>
    </Card>
  );
}
