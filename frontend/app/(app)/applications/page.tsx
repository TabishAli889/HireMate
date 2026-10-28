import { Suspense } from "react";
import type { Metadata } from "next";
import { ApplicationsWorkspace, BoardSkeleton } from "@/components/features/applications/applications-workspace";
import { PageHeader } from "@/components/layout/page-header";

export const metadata: Metadata = { title: "Applications" };

export default function ApplicationsPage() {
  return (
    <>
      <PageHeader
        title="Applications"
        description="Every application on one board: Saved, Applied, Interview, Offer, Rejected."
      />
      {/* useSearchParams needs a Suspense boundary in the App Router */}
      <Suspense fallback={<BoardSkeleton />}>
        <ApplicationsWorkspace />
      </Suspense>
    </>
  );
}
