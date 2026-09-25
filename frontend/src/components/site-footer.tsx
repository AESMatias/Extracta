"use client";

import Link from "next/link";

import { useI18n } from "@/lib/i18n";

import { Logo } from "./logo";
import { Byline, LanguageSwitch } from "./preferences";

export function SiteFooter() {
  const { m } = useI18n();
  const columns = [
    {
      title: m.footer.product,
      links: [
        { href: "/#features", label: m.nav.features },
        { href: "/#document-types", label: m.footer.documentTypes },
        { href: "/#security", label: m.nav.security },
        { href: "/pricing", label: m.nav.pricing },
      ],
    },
    {
      title: m.footer.accountTitle,
      links: [
        { href: "/register", label: m.common.createAccount },
        { href: "/login", label: m.common.signIn },
        { href: "/app", label: m.common.dashboard },
      ],
    },
    {
      title: m.footer.legal,
      links: [
        { href: "/terms", label: m.footer.terms },
        { href: "/privacy", label: m.footer.privacy },
        { href: "/#faq", label: m.nav.faq },
      ],
    },
  ];

  return (
    <footer className="border-t border-slate-200/70 dark:border-slate-800/70">
      <div className="mx-auto grid max-w-6xl gap-10 px-4 py-12 sm:px-6 md:grid-cols-[1.4fr_repeat(3,1fr)]">
        <div>
          <Logo />
          <p className="mt-4 max-w-xs text-sm text-slate-600 dark:text-slate-400">{m.footer.tagline}</p>
          <Byline className="mt-5" />
        </div>
        {columns.map((column) => (
          <div key={column.title}>
            <p className="text-sm font-semibold">{column.title}</p>
            <ul className="mt-3 space-y-2">
              {column.links.map((link) => (
                <li key={link.href}>
                  <Link
                    href={link.href}
                    className="text-sm text-slate-600 transition duration-300 ease-out hover:text-brand-600 dark:text-slate-400 dark:hover:text-brand-300"
                  >
                    {link.label}
                  </Link>
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>
      <div className="border-t border-slate-200/70 dark:border-slate-800/70">
        <div className="mx-auto flex max-w-6xl flex-col items-center justify-between gap-4 px-4 py-6 sm:flex-row sm:px-6">
          <p className="text-center text-xs text-slate-500 sm:text-left">
            © {new Date().getFullYear()} Extracta. {m.footer.note}
          </p>
          <LanguageSwitch />
        </div>
      </div>
    </footer>
  );
}
