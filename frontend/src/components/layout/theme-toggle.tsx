"use client";

import { useTheme } from "@/hooks/useTheme";
import { Sun, Moon } from "lucide-react";

export default function ThemeToggle() {
  const { theme, toggleTheme } = useTheme();

  return (
    <button
      onClick={toggleTheme}
      type="button"
      className="p-2.5 rounded-full text-text-muted hover:text-text-primary hover:bg-bg/80 dark:hover:bg-surface/50 border border-transparent hover:border-border/50 transition-all duration-150 cursor-pointer focus:outline-none focus:ring-2 focus:ring-brand/20 shrink-0"
      title={theme === "light" ? "Switch to Dark Theme" : "Switch to Light Theme"}
      aria-label="Toggle Theme"
    >
      {theme === "light" ? (
        <Moon className="h-5 w-5 transition-transform duration-200 hover:rotate-12" />
      ) : (
        <Sun className="h-5 w-5 text-amber-500 transition-transform duration-200 hover:scale-110" />
      )}
    </button>
  );
}
