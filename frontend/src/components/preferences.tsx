"use client";

import clsx from "clsx";
import { Moon, Sun } from "lucide-react";
import { useEffect, useState } from "react";

import { useI18n } from "@/lib/i18n";
import { currentTheme, LOCALES, saveTheme, type Theme } from "@/lib/preferences";

/** Light by default; the choice is remembered in this browser. */
export function ThemeToggle({ className }: { className?: string }) {
  const { m } = useI18n();
  const [theme, setTheme] = useState<Theme>("light");

  useEffect(() => {
    // Reading the theme the head script applied is the purpose of this effect.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setTheme(currentTheme());
  }, []);

  const next = theme === "dark" ? "light" : "dark";
  return (
    <button
      type="button"
      onClick={() => {
        saveTheme(next);
        setTheme(next);
      }}
      className={clsx(
        "group relative grid size-9 cursor-pointer place-items-center overflow-hidden text-slate-600 transition duration-300 ease-out hover:bg-slate-900 hover:text-white dark:text-slate-300 dark:hover:bg-white dark:hover:text-slate-900",
        className,
      )}
      aria-label={`${m.prefs.theme}: ${next === "dark" ? m.prefs.dark : m.prefs.light}`}
      title={next === "dark" ? m.prefs.dark : m.prefs.light}
    >
      <Sun className={clsx("absolute size-[18px] transition duration-500 ease-out", theme === "dark" ? "rotate-0 opacity-100" : "rotate-90 opacity-0")} />
      <Moon className={clsx("absolute size-[18px] transition duration-500 ease-out", theme === "dark" ? "-rotate-90 opacity-0" : "rotate-0 opacity-100")} />
    </button>
  );
}

export function LanguageSwitch({ className }: { className?: string }) {
  const { locale, setLocale, m } = useI18n();
  return (
    <div role="radiogroup" aria-label={m.prefs.language} className={clsx("inline-flex border border-slate-200 p-0.5 dark:border-slate-700", className)}>
      {LOCALES.map((option) => (
        <button
          key={option}
          type="button"
          role="radio"
          aria-checked={locale === option}
          onClick={() => setLocale(option)}
          className={clsx(
            "cursor-pointer px-2.5 py-1 text-xs font-bold tracking-wide uppercase transition duration-300 ease-out",
            locale === option
              ? "bg-slate-900 text-white dark:bg-white dark:text-slate-900"
              : "text-slate-500 hover:text-slate-900 dark:hover:text-white",
          )}
        >
          {option === "en" ? "English" : "Español"}
        </button>
      ))}
    </div>
  );
}

export function GitHubMark({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" className={className} aria-hidden fill="currentColor">
      <path d="M12 .5a11.5 11.5 0 0 0-3.64 22.41c.58.1.79-.25.79-.56v-2c-3.2.7-3.88-1.37-3.88-1.37-.52-1.33-1.28-1.69-1.28-1.69-1.04-.71.08-.7.08-.7 1.15.08 1.76 1.19 1.76 1.19 1.03 1.76 2.7 1.25 3.36.96.1-.75.4-1.25.73-1.54-2.56-.29-5.25-1.28-5.25-5.7 0-1.26.45-2.29 1.19-3.1-.12-.29-.52-1.46.11-3.05 0 0 .97-.31 3.17 1.18a11 11 0 0 1 5.77 0c2.2-1.49 3.17-1.18 3.17-1.18.63 1.59.23 2.76.11 3.05.74.81 1.19 1.84 1.19 3.1 0 4.43-2.7 5.4-5.27 5.69.41.36.78 1.06.78 2.14v3.17c0 .31.21.67.8.56A11.5 11.5 0 0 0 12 .5Z" />
    </svg>
  );
}

/** "by AESMatias" with the GitHub mark, linking to the author's profile. */
export function Byline({ className }: { className?: string }) {
  const { m } = useI18n();
  return (
    <a
      href="https://github.com/AESMatias"
      target="_blank"
      rel="noopener noreferrer"
      className={clsx("group inline-flex items-center gap-2 text-slate-500 transition duration-300 ease-out hover:text-slate-900 dark:text-slate-400 dark:hover:text-white", className)}
    >
      <span className="grid size-7 place-items-center bg-slate-900 text-white transition duration-300 ease-out group-hover:rotate-[-8deg] dark:bg-white dark:text-slate-900">
        <GitHubMark className="size-4" />
      </span>
      <span className="text-left text-[11px] leading-tight">
        {m.prefs.byAuthor}
        <span className="block font-semibold text-slate-700 dark:text-slate-200">AESMatias</span>
      </span>
    </a>
  );
}
