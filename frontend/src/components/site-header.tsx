"use client";

import clsx from "clsx";
import { LayoutDashboard, LogOut, Menu, UserRound, X } from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { useAuth } from "@/lib/auth";
import { useI18n } from "@/lib/i18n";

import { Logo } from "./logo";
import { Byline, LanguageSwitch, ThemeToggle } from "./preferences";
import { Button, ButtonLink } from "./ui";

/** A link whose hover slides a slanted block behind it and flips its color. */
export function SlantLink({ href, children, onClick }: { href: string; children: React.ReactNode; onClick?: () => void }) {
  return (
    <Link
      href={href}
      onClick={onClick}
      className="group relative isolate px-3.5 py-2 text-sm font-medium text-slate-600 transition-colors duration-300 ease-out hover:text-white dark:text-slate-300 dark:hover:text-slate-900"
    >
      <span
        aria-hidden
        className="absolute inset-y-0.5 -inset-x-1 -z-10 origin-center -skew-x-12 scale-x-0 bg-slate-900 transition-transform duration-300 ease-out group-hover:scale-x-100 dark:bg-white"
      />
      {children}
    </Link>
  );
}

export function SiteHeader() {
  const { user, loading, logout } = useAuth();
  const { m } = useI18n();
  const links = [
    { href: "/#features", label: m.nav.features },
    { href: "/#security", label: m.nav.security },
    { href: "/pricing", label: m.nav.pricing },
    { href: "/#faq", label: m.nav.faq },
  ];
  const [open, setOpen] = useState(false);
  const [scrolled, setScrolled] = useState(false);
  const pathname = usePathname();
  const router = useRouter();

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 8);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  useEffect(() => {
    // Close the mobile menu after navigating.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setOpen(false);
  }, [pathname]);

  useEffect(() => {
    document.body.style.overflow = open ? "hidden" : "";
  }, [open]);

  async function signOut() {
    await logout();
    router.push("/");
  }

  return (
    <header
      className={clsx(
        "sticky top-0 z-50 transition-all duration-300",
        scrolled || open
          ? "border-b border-slate-200/70 bg-white/80 backdrop-blur-xl dark:border-slate-800/70 dark:bg-slate-950/75"
          : "border-b border-transparent",
      )}
    >
      <nav className="mx-auto flex h-16 max-w-6xl items-center justify-between gap-4 px-4 sm:px-6" aria-label="Main">
        <div className="flex items-center gap-4">
          <Logo travel />
          <span className="hidden h-7 w-px bg-slate-200 lg:block dark:bg-slate-800" aria-hidden />
          <Byline className="hidden lg:inline-flex" />
        </div>

        <div className="hidden items-center gap-0.5 md:flex">
          {links.map((link) => (
            <SlantLink key={link.href} href={link.href}>
              {link.label}
            </SlantLink>
          ))}
        </div>

        <div className="hidden items-center gap-2 md:flex">
          <ThemeToggle />
          {loading ? (
            <div className="skeleton h-9 w-40" />
          ) : user ? (
            <>
              <ButtonLink href="/account" variant="ghost" size="md" icon={<UserRound className="size-4" />}>
                {m.common.account}
              </ButtonLink>
              <ButtonLink href="/app" size="md" icon={<LayoutDashboard className="size-4" />}>
                {m.common.dashboard}
              </ButtonLink>
            </>
          ) : (
            <>
              <ButtonLink href="/login" variant="ghost">
                {m.common.signIn}
              </ButtonLink>
              <ButtonLink href="/register">{m.common.getStarted}</ButtonLink>
            </>
          )}
        </div>

        <div className="-mr-2 flex items-center gap-1 md:hidden">
          <ThemeToggle />
          <button
            className="p-2 text-slate-700 transition hover:bg-slate-100 dark:text-slate-200 dark:hover:bg-slate-800"
            onClick={() => setOpen((value) => !value)}
            aria-expanded={open}
            aria-controls="mobile-menu"
            aria-label={open ? m.nav.closeMenu : m.nav.openMenu}
          >
            {open ? <X className="size-6" /> : <Menu className="size-6" />}
          </button>
        </div>
      </nav>

      {open && (
        <div id="mobile-menu" className="h-[calc(100dvh-4rem)] overflow-y-auto border-t border-slate-200/70 px-4 pt-4 pb-8 md:hidden dark:border-slate-800">
          <div className="flex flex-col gap-1 text-center">
            {links.map((link) => (
              <Link
                key={link.href}
                href={link.href}
                onClick={() => setOpen(false)}
                className="px-3 py-3 text-base font-medium text-slate-700 hover:bg-slate-100 dark:text-slate-200 dark:hover:bg-slate-800"
              >
                {link.label}
              </Link>
            ))}
          </div>
          <div className="mt-6 flex flex-col gap-3">
            {user ? (
              <>
                <ButtonLink href="/app" size="lg" icon={<LayoutDashboard className="size-5" />}>
                  {m.common.dashboard}
                </ButtonLink>
                <ButtonLink href="/account" variant="outline" size="lg" icon={<UserRound className="size-5" />}>
                  {m.common.account}
                </ButtonLink>
                <Button variant="ghost" size="lg" onClick={signOut} icon={<LogOut className="size-5" />}>
                  {m.common.signOut}
                </Button>
              </>
            ) : (
              <>
                <ButtonLink href="/register" size="lg">
                  {m.common.getStarted}
                </ButtonLink>
                <ButtonLink href="/login" variant="outline" size="lg">
                  {m.common.signIn}
                </ButtonLink>
              </>
            )}
          </div>
          <div className="mt-8 flex flex-col items-center gap-4 border-t border-slate-200/70 pt-6 dark:border-slate-800">
            <Byline />
            <LanguageSwitch />
          </div>
        </div>
      )}
    </header>
  );
}
