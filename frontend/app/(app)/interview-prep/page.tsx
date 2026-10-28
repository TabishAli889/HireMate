import { Suspense } from "react";
import type { Metadata } from "next";
import { InterviewSkeleton, InterviewWorkspace } from "@/components/features/interview/interview-workspace";
import { PageHeader } from "@/components/layout/page-header";

export const metadata: Metadata = { title: "Interview Prep" };

export default function InterviewPrepPage() {
  return (
    <>
      <PageHeader
        title="Interview prep"
        description="Likely questions for each job, with answer hints drawn from your real projects."
      />
      {/* useSearchParams needs a Suspense boundary in the App Router */}
      <Suspense fallback={<InterviewSkeleton />}>
        <InterviewWorkspace />
      </Suspense>
    </>
  );
}
