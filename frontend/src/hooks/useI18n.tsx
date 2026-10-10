"use client";

import React, { createContext, useContext, useEffect, useState } from "react";
import { api } from "@/lib/api";

type Bundle = Record<string, string>;

interface I18nContextType {
  locale: string;
  setLocale: (l: string) => void;
  t: (key: string, fallback?: string) => string;
  bundle: Bundle;
  locales: string[];
}

const I18nContext = createContext<I18nContextType | undefined>(undefined);

async function fetchBundle(locale: string): Promise<Bundle> {
  try {
    const data = await api.getLocaleBundle(locale);
    return (data as Bundle) || {};
  } catch {
    return {};
  }
}

export function I18nProvider({ children }: { children: React.ReactNode }) {
  const [locale, setLocaleState] = useState<string>("en");
  const [bundle, setBundle] = useState<Bundle>({});
  const [locales, setLocales] = useState<string[]>(["en"]);

  // Load the list of available locales once on mount.
  useEffect(() => {
    let active = true;
    (async () => {
      try {
        const data = await api.listLocales();
        if (active && data?.locales?.length) {
          setLocales(data.locales as string[]);
        }
      } catch {
        if (active) setLocales(["en"]);
      }
    })();
    return () => {
      active = false;
    };
  }, []);

  // On mount, read the persisted locale and load its bundle.
  useEffect(() => {
    let active = true;
    const saved = localStorage.getItem("locale") || "en";
    (async () => {
      const b = await fetchBundle(saved);
      if (!active) return;
      setLocaleState(saved);
      setBundle(b);
      document.documentElement.lang = saved;
    })();
    return () => {
      active = false;
    };
  }, []);

  const setLocale = (l: string) => {
    setLocaleState(l);
    localStorage.setItem("locale", l);
    document.documentElement.lang = l;
    (async () => {
      const b = await fetchBundle(l);
      setBundle(b);
    })();
  };

  const t = (key: string, fallback?: string): string =>
    bundle[key] ?? fallback ?? key;

  return (
    <I18nContext.Provider value={{ locale, setLocale, t, bundle, locales }}>
      {children}
    </I18nContext.Provider>
  );
}

export function useI18n() {
  const context = useContext(I18nContext);
  if (context === undefined) {
    throw new Error("useI18n must be used within an I18nProvider");
  }
  return context;
}
