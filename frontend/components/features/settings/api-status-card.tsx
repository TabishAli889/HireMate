"use client";

import { useState } from "react";
import { CheckCircle2, CircleAlert, RefreshCw } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useBackendHealth } from "@/hooks/use-backend-health";
import { cn } from "@/lib/utils";

function Row({ label, ok, value }: { label: string; ok: boolean; value: string }) {
  const Icon = ok ? CheckCircle2 : CircleAlert;
  return (
    <div className="flex items-center justify-between gap-4 py-3">
      <dt className="text-sm text-muted-foreground">{label}</dt>
      <dd className={cn("inline-flex items-center gap-1.5 text-sm font-medium", ok ? "text-success" : "text-warning")}>
        <Icon className="size-4" aria-hidden />
        {value}
      </dd>
    </div>
  );
}

/** Shows backend reachability and whether a Groq API key is configured (never the key itself). */
export function ApiStatusCard() {
  const { status, data, refresh } = useBackendHealth();
  const [refreshing, setRefreshing] = useState(false);

  const onRefresh = async () => {
    setRefreshing(true);
    const ok = await refresh();
    setRefreshing(false);
    if (ok) toast.success("Backend is reachable");
    else toast.error("Backend is not reachable. Is uvicorn running on BACKEND_URL?");
  };

  return (
    <Card>
      <CardHeader className="flex-row items-start justify-between gap-4 space-y-0">
        <div className="space-y-1.5">
          <CardTitle>API status</CardTitle>
          <CardDescription>Connection to the HireMate backend and the LLM provider.</CardDescription>
        </div>
        <Button variant="outline" size="sm" onClick={onRefresh} disabled={refreshing}>
          <RefreshCw className={cn(refreshing && "animate-spin")} aria-hidden />
          Recheck
        </Button>
      </CardHeader>
      <CardContent>
        {status === "checking" ? (
          <div className="space-y-3" aria-label="Loading API status">
            <Skeleton className="h-6" />
            <Skeleton className="h-6" />
            <Skeleton className="h-6" />
          </div>
        ) : (
          <dl className="divide-y divide-border">
            <Row label="Backend" ok={status === "online"} value={status === "online" ? `Online · v${data?.version ?? "?"}` : "Offline"} />
            <Row
              label="Groq API key"
              ok={Boolean(data?.llm_configured)}
              value={data ? (data.llm_configured ? "Configured" : "Not set") : "Unknown"}
            />
            <Row label="Model" ok={Boolean(data)} value={data?.llm_model ?? "Unknown"} />
          </dl>
        )}
      </CardContent>
    </Card>
  );
}
