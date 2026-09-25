"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";

import { en, type Messages } from "./messages/en";
import { es } from "./messages/es";
import { saveLocale, type Locale } from "./preferences";

const CATALOG: Record<Locale, Messages> = { en, es };

interface I18nState {
  locale: Locale;
  m: Messages; // every text of the site in the current language, fully typed
  setLocale: (locale: Locale) => void;
}

const I18nContext = createContext<I18nState | null>(null);

export function I18nProvider({ children }: { children: ReactNode }) {
  // The static HTML is English; the head script already chose the visitor's language.
  const [locale, setLocaleState] = useState<Locale>("en");

  useEffect(() => {
    const chosen = document.documentElement.lang === "es" ? "es" : "en";
    // Adopting the language picked before hydration is the purpose of this effect.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setLocaleState(chosen);
    requestAnimationFrame(() => document.documentElement.classList.remove("i18n-pending"));
  }, []);

  const setLocale = useCallback((next: Locale) => {
    saveLocale(next);
    setLocaleState(next);
  }, []);

  const value = useMemo(() => ({ locale, m: CATALOG[locale], setLocale }), [locale, setLocale]);
  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>;
}

export function useI18n(): I18nState {
  const context = useContext(I18nContext);
  if (!context) throw new Error("useI18n must be used inside <I18nProvider>");
  return context;
}

export { fill } from "./fill";
