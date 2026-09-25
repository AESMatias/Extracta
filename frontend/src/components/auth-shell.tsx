"use client";

import { CheckCircle2 } from "lucide-react";
import type { ReactNode } from "react";

import { useI18n } from "@/lib/i18n";

import { Logo } from "./logo";
import { Byline, LanguageSwitch, ThemeToggle } from "./preferences";

export function AuthShell({ title, subtitle, children }: { title: string; subtitle: ReactNode; children: ReactNode }) {
  const { m } = useI18n();
  return (
    <div className="grid min-h-dvh lg:grid-cols-[1fr_1.1fr]">
      <aside className="relative hidden overflow-hidden bg-slate-950 p-12 text-white lg:flex lg:flex-col lg:justify-between">
        <div className="bg-dots absolute inset-0 opacity-40" />
        <div className="absolute -top-40 -left-40 size-[30rem] bg-brand-600/40 blur-3xl" />
        <div className="absolute -right-32 -bottom-40 size-[28rem] bg-emerald-600/30 blur-3xl" />
        <div className="relative">
          <Logo />
        </div>
        <div className="relative">
          <h2 className="text-4xl leading-tight font-bold tracking-tight text-balance">
            {m.auth.shellTitle1} <span className="text-gradient">{m.auth.shellTitle2}</span> {m.auth.shellTitle3}
          </h2>
          <ul className="mt-8 space-y-3">
            {m.auth.shellPoints.map((point) => (
              <li key={point} className="flex items-center gap-3 text-slate-300">
                <CheckCircle2 className="size-5 text-brand-400" /> {point}
              </li>
            ))}
          </ul>
        </div>
        <div className="relative flex items-end justify-between gap-4">
          <p className="max-w-xs text-sm text-slate-500">{m.auth.shellNote}</p>
          <Byline className="text-slate-400 hover:text-white [&_.block]:text-slate-200" />
        </div>
      </aside>

      <main className="relative flex flex-col px-4 py-8 sm:px-6">
        <div className="bg-dots absolute inset-0 -z-10 opacity-60 [mask-image:radial-gradient(ellipse_at_top,black,transparent_60%)] lg:hidden" />
        <div className="flex items-center justify-between gap-3">
          <span className="lg:invisible">
            <Logo />
          </span>
          <ThemeToggle />
        </div>
        <div className="mx-auto flex w-full max-w-sm flex-1 flex-col justify-center py-10">
          <h1 className="text-3xl font-bold tracking-tight">{title}</h1>
          <p className="mt-2 text-slate-600 dark:text-slate-400">{subtitle}</p>
          <div className="mt-8">{children}</div>
        </div>
        <div className="flex justify-center">
          <LanguageSwitch />
        </div>
      </main>
    </div>
  );
}

export function GoogleButton({ label }: { label: string }) {
  return (
    // A plain link: the API redirects to Google and back (/api/auth/google/callback).
    <a
      href="/api/auth/google/login"
      className="flex h-11 w-full items-center justify-center gap-3 border border-slate-300 bg-white text-sm font-semibold text-slate-800 shadow-sm transition hover:border-slate-400 hover:bg-slate-50 active:scale-[0.99] dark:border-slate-700 dark:bg-slate-900 dark:text-slate-100 dark:hover:bg-slate-800"
    >
      <svg viewBox="0 0 24 24" className="size-5" aria-hidden>
        <path fill="#4285F4" d="M23.5 12.3c0-.8-.1-1.6-.2-2.3H12v4.4h6.5a5.6 5.6 0 0 1-2.4 3.6v3h3.9c2.3-2.1 3.5-5.2 3.5-8.7Z" />
        <path fill="#34A853" d="M12 24c3.2 0 6-1.1 8-2.9l-3.9-3c-1.1.7-2.5 1.2-4.1 1.2-3.1 0-5.8-2.1-6.7-5H1.3v3.1A12 12 0 0 0 12 24Z" />
        <path fill="#FBBC05" d="M5.3 14.3a7.2 7.2 0 0 1 0-4.6V6.6H1.3a12 12 0 0 0 0 10.8l4-3.1Z" />
        <path fill="#EA4335" d="M12 4.8c1.7 0 3.3.6 4.6 1.8l3.4-3.4A12 12 0 0 0 1.3 6.6l4 3.1c.9-2.9 3.6-4.9 6.7-4.9Z" />
      </svg>
      {label}
    </a>
  );
}

export function Divider({ label }: { label: string }) {
  return (
    <div className="my-6 flex items-center gap-3 text-xs font-medium text-slate-400 uppercase">
      <span className="h-px flex-1 bg-slate-200 dark:bg-slate-800" />
      {label}
      <span className="h-px flex-1 bg-slate-200 dark:bg-slate-800" />
    </div>
  );
}
