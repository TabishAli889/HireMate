import Link from "next/link";
import { Compass } from "lucide-react";
import { EmptyIllustration } from "@/components/features/empty-illustration";
import { Button } from "@/components/ui/button";

export default function NotFound() {
  return (
    <main className="grid min-h-dvh place-items-center px-6">
      <div className="flex flex-col items-center text-center">
        <EmptyIllustration icon={Compass} />
        <p className="mt-6 font-heading text-sm font-semibold text-primary">404</p>
        <h1 className="mt-1 text-2xl font-bold">This page doesn’t exist</h1>
        <p className="mt-2 max-w-sm text-sm text-muted-foreground">The link may be broken or the page was moved.</p>
        <Button asChild className="mt-6">
          <Link href="/">Back to dashboard</Link>
        </Button>
      </div>
    </main>
  );
}
