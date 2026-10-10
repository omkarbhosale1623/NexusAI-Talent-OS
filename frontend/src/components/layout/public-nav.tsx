"use client";

import { useState } from "react";
import Link from "next/link";
import Image from "next/image";
import { Menu, X } from "lucide-react";
import { cn } from "@/lib/utils";
import { useTheme } from "@/hooks/useTheme";
import ThemeToggle from "@/components/layout/theme-toggle";

const NAV_LINKS = [
  { label: "Features", href: "#features" },
  { label: "How It Works", href: "#how-it-works" },
  { label: "Pricing", href: "#pricing" },
];

export default function PublicNav() {
  const [mobileOpen, setMobileOpen] = useState(false);

  const handleNavClick = (href: string) => {
    setMobileOpen(false);
    const id = href.replace("#", "");
    const el = document.getElementById(id);
    if (el) {
      el.scrollIntoView({ behavior: "smooth" });
    }
  };

  const { theme } = useTheme();

  return (
    <header className="sticky top-0 z-50 bg-surface border-b border-border">
      <nav className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="flex h-16 items-center justify-between">
          {/* Logo */}
          <Link href="/" className="flex items-center shrink-0">
            <Image
              src={theme === "dark" ? "/logo.png" : "/logo_full.png"}
              alt="Talent OS Logo"
              width={48}
              height={48}
              className="object-contain"
              priority
            />
          </Link>

          {/* Desktop nav links */}
          <ul className="hidden md:flex items-center gap-1">
            {NAV_LINKS.map((link) => (
              <li key={link.href}>
                <button
                  onClick={() => handleNavClick(link.href)}
                  className="px-4 py-2 text-sm font-medium text-text-muted hover:text-text-primary transition-colors duration-100 rounded-full hover:bg-bg cursor-pointer"
                >
                  {link.label}
                </button>
              </li>
            ))}
          </ul>

          {/* Desktop CTA */}
          <div className="hidden md:flex items-center gap-3">
            <ThemeToggle />
            <Link
              href="/login"
              className="text-sm font-medium text-text-muted hover:text-text-primary transition-colors duration-100"
            >
              Sign In
            </Link>
            <Link
              href="/signup"
              className="inline-flex items-center justify-center rounded-full bg-brand px-5 py-2 text-sm font-semibold text-white hover:bg-brand-hover transition-colors duration-100"
            >
              Get Started
            </Link>
          </div>

          {/* Mobile hamburger */}
          <button
            onClick={() => setMobileOpen((prev) => !prev)}
            className="md:hidden p-2 rounded-lg text-text-muted hover:text-text-primary hover:bg-bg transition-colors duration-100"
            aria-label="Toggle menu"
          >
            {mobileOpen ? (
              <X className="h-5 w-5" />
            ) : (
              <Menu className="h-5 w-5" />
            )}
          </button>
        </div>

        {/* Mobile slide-down menu */}
        <div
          className={cn(
            "md:hidden overflow-hidden transition-all duration-200",
            mobileOpen ? "max-h-80 pb-4" : "max-h-0"
          )}
        >
          <ul className="flex flex-col gap-1 pt-2">
            {NAV_LINKS.map((link) => (
              <li key={link.href}>
                <button
                  onClick={() => handleNavClick(link.href)}
                  className="w-full text-left px-3 py-2.5 text-sm font-medium text-text-muted hover:text-text-primary hover:bg-bg rounded-lg transition-colors duration-100 cursor-pointer"
                >
                  {link.label}
                </button>
              </li>
            ))}
          </ul>
          <div className="flex flex-col gap-2 pt-3 border-t border-border mt-2">
            <div className="flex items-center justify-between px-3 py-1 bg-bg/50 rounded-lg">
              <span className="text-sm font-medium text-text-muted">Theme</span>
              <ThemeToggle />
            </div>
            <Link
              href="/login"
              onClick={() => setMobileOpen(false)}
              className="px-3 py-2.5 text-sm font-medium text-text-muted hover:text-text-primary transition-colors duration-100"
            >
              Sign In
            </Link>
            <Link
              href="/signup"
              onClick={() => setMobileOpen(false)}
              className="inline-flex items-center justify-center rounded-full bg-brand px-5 py-2.5 text-sm font-semibold text-white hover:bg-brand-hover transition-colors duration-100"
            >
              Get Started
            </Link>
          </div>
        </div>
      </nav>
    </header>
  );
}
