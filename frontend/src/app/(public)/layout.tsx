"use client";

import PublicNav from "@/components/layout/public-nav";
import Link from "next/link";
import Image from "next/image";
import { useTheme } from "@/hooks/useTheme";

export default function PublicLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const { theme } = useTheme();

  return (
    <div className="min-h-screen bg-bg flex flex-col">
      <PublicNav />

      <main className="flex-1">{children}</main>

      {/* Footer */}
      <footer className="border-t border-border bg-surface mt-16">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-10">
          <div className="flex flex-col sm:flex-row items-center justify-between gap-4">
            <Link href="/" className="flex items-center shrink-0">
              <Image
                src={theme === "dark" ? "/logo.png" : "/logo_full.png"}
                alt="Talent OS Logo"
                width={64}
                height={64}
                className="object-contain"
              />
            </Link>

            <div className="flex items-center gap-6">
              <Link
                href="/jobs"
                className="text-sm text-text-muted hover:text-text-primary transition-colors"
              >
                Open Positions
              </Link>
              <Link
                href="/login"
                className="text-sm text-text-muted hover:text-text-primary transition-colors"
              >
                Sign In
              </Link>
              <Link
                href="/signup"
                className="text-sm text-text-muted hover:text-text-primary transition-colors"
              >
                Sign Up
              </Link>
            </div>

            <p className="text-xs text-text-muted">
              &copy; {new Date().getFullYear()} NexusAI Talent OS. All rights reserved.
            </p>
          </div>
        </div>
      </footer>
    </div>
  );
}
