"use client";

import { useEffect, useRef, useState } from "react";
import { Globe, Check, ChevronDown } from "lucide-react";
import { useI18n } from "@/hooks/useI18n";
import { cn } from "@/lib/utils";

const LANGUAGE_NAMES: Record<string, string> = {
  en: "English",
  es: "Español",
  fr: "Français",
  de: "Deutsch",
  hi: "हिन्दी",
  pt: "Português",
  ja: "日本語",
  zh: "中文",
  ar: "العربية",
};

function languageName(code: string): string {
  return LANGUAGE_NAMES[code] ?? code;
}

export default function LocaleSwitcher() {
  const { locale, setLocale, locales } = useI18n();
  const [open, setOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const onClick = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", onClick);
    return () => document.removeEventListener("mousedown", onClick);
  }, [open]);

  return (
    <div ref={containerRef} className="relative shrink-0">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="flex items-center gap-1.5 p-2.5 rounded-full text-text-muted hover:text-text-primary hover:bg-bg/80 dark:hover:bg-surface/50 border border-transparent hover:border-border/50 transition-all duration-150 cursor-pointer focus:outline-none focus:ring-2 focus:ring-brand/20"
        title="Change Language"
        aria-label="Change Language"
        aria-haspopup="listbox"
        aria-expanded={open}
      >
        <Globe className="h-5 w-5" />
        <span className="text-sm font-medium uppercase">{locale}</span>
        <ChevronDown
          className={cn("h-3.5 w-3.5 transition-transform duration-150", open && "rotate-180")}
        />
      </button>

      {open && (
        <div
          role="listbox"
          className="absolute right-0 mt-2 min-w-[10rem] py-1 rounded-xl bg-surface border border-border shadow-lg z-50"
        >
          {locales.map((code) => {
            const active = code === locale;
            return (
              <button
                key={code}
                type="button"
                role="option"
                aria-selected={active}
                onClick={() => {
                  setLocale(code);
                  setOpen(false);
                }}
                className={cn(
                  "flex w-full items-center justify-between gap-3 px-3 py-2 text-sm text-left transition-colors duration-150 cursor-pointer",
                  active ? "text-brand" : "text-text-primary hover:bg-bg"
                )}
              >
                <span className="flex items-center gap-2">
                  <span>{languageName(code)}</span>
                  <span className="text-xs text-text-muted uppercase">{code}</span>
                </span>
                {active && <Check className="h-4 w-4 shrink-0" />}
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}
