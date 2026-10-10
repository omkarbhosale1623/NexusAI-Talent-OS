"use client";

import Link from "next/link";
import Image from "next/image";
import { LogOut, ChevronDown } from "lucide-react";
import { cn } from "@/lib/utils";
import { useTheme } from "@/hooks/useTheme";
import ThemeToggle from "@/components/layout/theme-toggle";

const CANDIDATE = {
  name: "Priya Sharma",
  email: "priya.sharma@gmail.com",
  initials: "PS",
};

export default function CandidateLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const { theme } = useTheme();

  return (
    <div className="min-h-screen bg-bg flex flex-col">
      {/* Top bar */}
      <header className="bg-surface border-b border-border sticky top-0 z-40">
        <div className="mx-auto max-w-5xl px-4 sm:px-6 h-14 flex items-center justify-between">
          {/* Logo */}
          <Link href="/portal" className="flex items-center shrink-0">
            <Image
              src={theme === "dark" ? "/logo.png" : "/logo_full.png"}
              alt="Talent OS Logo"
              width={40}
              height={40}
              className="object-contain"
              priority
            />
          </Link>

          {/* Candidate info + logout */}
          <div className="flex items-center gap-3">
            <ThemeToggle />
            <div className="hidden sm:flex items-center gap-2.5">
              <div
                className={cn(
                  "h-8 w-8 rounded-full bg-brand-light border border-brand/20",
                  "flex items-center justify-center"
                )}
              >
                <span className="text-xs font-semibold text-brand">
                  {CANDIDATE.initials}
                </span>
              </div>
              <div className="flex flex-col leading-none">
                <span className="text-sm font-medium text-text-primary">
                  {CANDIDATE.name}
                </span>
                <span className="text-xs text-text-muted">
                  {CANDIDATE.email}
                </span>
              </div>
            </div>

            {/* Mobile avatar only */}
            <div className="flex sm:hidden items-center gap-2">
              <div className="h-8 w-8 rounded-full bg-brand-light border border-brand/20 flex items-center justify-center">
                <span className="text-xs font-semibold text-brand">
                  {CANDIDATE.initials}
                </span>
              </div>
            </div>

            <div className="w-px h-5 bg-border hidden sm:block" />

            <button
              className={cn(
                "flex items-center gap-1.5 text-sm text-text-muted",
                "hover:text-text-primary transition-colors px-2 py-1 rounded-md hover:bg-bg"
              )}
            >
              <LogOut className="h-4 w-4" />
              <span className="hidden sm:inline">Sign out</span>
            </button>
          </div>
        </div>
      </header>

      {/* Page content */}
      <main className="flex-1">
        <div className="mx-auto max-w-5xl px-4 sm:px-6 py-8">{children}</div>
      </main>

      {/* Footer */}
      <footer className="border-t border-border py-5 mt-auto">
        <div className="mx-auto max-w-5xl px-4 sm:px-6 flex items-center justify-between">
          <p className="text-xs text-text-muted">
            &copy; {new Date().getFullYear()} NexusAI Talent OS
          </p>
          <p className="text-xs text-text-muted">
            Powered by AI — interviews assessed with transparency
          </p>
        </div>
      </footer>
    </div>
  );
}
