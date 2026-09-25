"use client";

import clsx from "clsx";
import { CreditCard, LayoutDashboard, LogOut, UserRound } from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";

import { useAuth } from "@/lib/auth";
import { useI18n } from "@/lib/i18n";

import { Logo } from "./logo";
import { ThemeToggle } from "./preferences";

/** Header for signed-in pages. On phones the links move to a bottom tab bar. */
export function AppHeader() {
  const pathname = usePathname();
  const router = useRouter();
  const { user, logout } = useAuth();
  const { m } = useI18n();
  const LINKS = [
    { href: "/app", label: m.common.dashboard, icon: LayoutDashboard },
    { href: "/pricing", label: m.common.plans, icon: CreditCard },
    { href: "/account", label: m.common.account, icon: UserRound },
  ];

  async function signOut() {
    await logout();
    router.push("/");
  }

  return (
    <>
      <header className="sticky top-0 z-40 border-b border-slate-200/70 bg-white/80 backdrop-blur-xl dark:border-slate-800/70 dark:bg-slate-950/75">
        <div className="mx-auto flex h-16 max-w-6xl items-center justify-between gap-4 px-4 sm:px-6">
          <Logo travel />
          <nav className="hidden items-center gap-1 sm:flex" aria-label="App">
            {LINKS.map(({ href, label, icon: Icon }) => (
              <Link
                key={href}
                href={href}
                className={clsx(
                  "inline-flex items-center gap-2 px-3 py-2 text-sm font-medium transition",
                  pathname === href
                    ? "bg-brand-50 text-brand-700 dark:bg-brand-500/15 dark:text-brand-300"
                    : "text-slate-600 hover:bg-slate-100 hover:text-slate-900 dark:text-slate-400 dark:hover:bg-slate-800 dark:hover:text-white",
                )}
              >
                <Icon className="size-4" /> {label}
              </Link>
            ))}
          </nav>
          <div className="flex items-center gap-2">
            <ThemeToggle />
            {user && (
              <span className="hidden max-w-48 truncate text-sm text-slate-500 lg:block dark:text-slate-400" title={user.email}>
                {user.email}
              </span>
            )}
            <button
              onClick={signOut}
              className="inline-flex items-center gap-2 px-3 py-2 text-sm font-medium text-slate-600 transition hover:bg-slate-100 hover:text-slate-900 dark:text-slate-400 dark:hover:bg-slate-800 dark:hover:text-white"
            >
              <LogOut className="size-4" /> <span className="hidden sm:inline">{m.common.signOut}</span>
            </button>
          </div>
        </div>
      </header>

      <nav
        className="fixed inset-x-0 bottom-0 z-40 grid grid-cols-3 border-t border-slate-200/70 bg-white/90 pb-[env(safe-area-inset-bottom)] backdrop-blur-xl sm:hidden dark:border-slate-800/70 dark:bg-slate-950/90"
        aria-label="App"
      >
        {LINKS.map(({ href, label, icon: Icon }) => (
          <Link
            key={href}
            href={href}
            className={clsx(
              "flex flex-col items-center gap-1 py-2.5 text-[11px] font-medium",
              pathname === href ? "text-brand-600 dark:text-brand-400" : "text-slate-500",
            )}
          >
            <Icon className="size-5" />
            {label}
          </Link>
        ))}
      </nav>
    </>
  );
}

export function AppPage({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-dvh bg-slate-50/70 dark:bg-slate-950">
      <AppHeader />
      <main className="mx-auto max-w-6xl px-4 pt-6 pb-28 sm:px-6 sm:pt-10 sm:pb-16">{children}</main>
    </div>
  );
}
