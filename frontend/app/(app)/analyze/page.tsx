import { Suspense } from "react";
import type { Metadata } from "next";
import { AnalyzeSkeleton, AnalyzeWorkspace } from "@/components/features/analyze/analyze-workspace";
import { PageHeader } from "@/components/layout/page-header";

export const metadata: Metadata = { title: "Analyze Job" };

export default function AnalyzePage() {
  return (
    <>
      <PageHeader
        title="Analyze a job"
        description="Paste a job posting or a link. The agent extracts the requirements, scores your match with evidence, and plans your skill gaps."
      />
      {/* useSearchParams needs a Suspense boundary in the App Router */}
      <Suspense fallback={<AnalyzeSkeleton />}>
        <AnalyzeWorkspace />
      </Suspense>
    </>
  );
}
