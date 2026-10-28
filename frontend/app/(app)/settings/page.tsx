import type { Metadata } from "next";
import { ApiStatusCard } from "@/components/features/settings/api-status-card";
import { ThemeSelector } from "@/components/features/settings/theme-selector";
import { PageHeader } from "@/components/layout/page-header";

export const metadata: Metadata = { title: "Settings" };

export default function SettingsPage() {
  return (
    <>
      <PageHeader title="Settings" description="Appearance and connection status." />
      <div className="grid gap-6 lg:grid-cols-2">
        <ThemeSelector />
        <ApiStatusCard />
      </div>
    </>
  );
}
