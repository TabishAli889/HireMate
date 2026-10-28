import type { Metadata } from "next";
import { ProfileVault } from "@/components/features/profile/profile-vault";
import { PageHeader } from "@/components/layout/page-header";

export const metadata: Metadata = { title: "Profile" };

export default function ProfilePage() {
  return (
    <>
      <PageHeader
        title="Profile Vault"
        description="Your structured resume: the single source of truth every tailored bullet and cover letter is built from."
      />
      <ProfileVault />
    </>
  );
}
