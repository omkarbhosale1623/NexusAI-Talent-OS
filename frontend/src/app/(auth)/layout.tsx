"use client";

import Link from "next/link";
import Image from "next/image";
import { useTheme } from "@/hooks/useTheme";
import ThemeToggle from "@/components/layout/theme-toggle";

export default function AuthLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const { theme } = useTheme();

  return (
    <div className="min-h-screen bg-bg flex flex-col items-center justify-center px-4 py-12 relative">
      {/* Floating Theme Toggle */}
      <div className="absolute top-4 right-4 z-50">
        <ThemeToggle />
      </div>

      {/* Logo */}
      <Link href="/" className="flex flex-col items-center mb-6">
        <Image
          src={theme === "dark" ? "/logo.png" : "/logo_full.png"}
          alt="Talent OS Logo"
          width={140}
          height={140}
          className="object-contain"
          priority
        />
      </Link>

      {/* Card slot */}
      <div className="w-full max-w-md">{children}</div>

      {/* Footer */}
      <p className="mt-8 text-xs text-text-muted text-center">
        &copy; {new Date().getFullYear()} NexusAI Talent OS. All rights reserved.
      </p>
    </div>
  );
}
