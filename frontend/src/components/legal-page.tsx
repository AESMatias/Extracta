"use client";

import Link from "next/link";

import { CONTACT_EMAIL, LEGAL, LEGAL_UPDATED } from "@/lib/legal";
import { fill, useI18n } from "@/lib/i18n";

import { Reveal } from "./reveal";
import { SiteFooter } from "./site-footer";
import { SiteHeader } from "./site-header";

export function LegalPage({ kind }: { kind: keyof typeof LEGAL }) {
  const { m, locale } = useI18n();
  const doc = LEGAL[kind][locale];
  const date = new Intl.DateTimeFormat(locale === "es" ? "es-CL" : "en-US", { dateStyle: "long" }).format(new Date(`${LEGAL_UPDATED}T12:00:00Z`));
  return (
    <>
      <SiteHeader />
      <main className="relative">
        <div className="bg-dots absolute inset-x-0 top-0 -z-10 h-72 [mask-image:linear-gradient(to_bottom,black,transparent)]" />
        <article className="mx-auto max-w-3xl px-4 py-14 sm:px-6 sm:py-20">
          <p className="flex items-center gap-2 text-xs font-bold tracking-[0.2em] text-slate-500 uppercase">
            <span className="size-1.5 bg-accent" aria-hidden /> {fill(m.legal.updated, { date })}
          </p>
          <h1 className="mt-3 text-3xl font-bold tracking-tight sm:text-4xl">{doc.title}</h1>
          <div className="bg-signature animate-grow-x mt-5 h-1 w-24 origin-left" />
          <p className="mt-6 text-lg leading-relaxed text-slate-600 dark:text-slate-300">{doc.intro}</p>
          <div className="mt-10 space-y-10">
            {doc.sections.map((section) => (
              <Reveal as="section" key={section.title} id={section.id} className="scroll-mt-24">
                <h2 className="text-lg font-semibold">{section.title}</h2>
                <div className="mt-3 space-y-3 text-[15px] leading-relaxed text-slate-600 dark:text-slate-400">
                  {section.paragraphs.map((paragraph) => (
                    <p key={paragraph.slice(0, 40)}>{paragraph}</p>
                  ))}
                  {section.bullets && (
                    <ul className="space-y-2">
                      {section.bullets.map((bullet) => (
                        <li key={bullet.slice(0, 40)} className="flex gap-3">
                          <span className="mt-2.5 size-1.5 shrink-0 bg-brand-500" aria-hidden />
                          <span>{bullet}</span>
                        </li>
                      ))}
                    </ul>
                  )}
                  {section.after?.map((paragraph) => (
                    <p key={paragraph.slice(0, 40)}>{paragraph}</p>
                  ))}
                </div>
              </Reveal>
            ))}
          </div>
          <div className="mt-14 space-y-2 border-t border-slate-200 pt-6 text-sm text-slate-600 dark:border-slate-800 dark:text-slate-400">
            <p>
              {m.legal.contact}{" "}
              <a href={`mailto:${CONTACT_EMAIL}`} className="font-semibold text-brand-600 hover:underline dark:text-brand-400">
                {CONTACT_EMAIL}
              </a>
            </p>
            <p>
              {m.legal.seeAlso}{" "}
              <Link href={kind === "terms" ? "/privacy" : "/terms"} className="font-semibold text-brand-600 hover:underline dark:text-brand-400">
                {LEGAL[kind === "terms" ? "privacy" : "terms"][locale].title}
              </Link>
              .
            </p>
          </div>
        </article>
      </main>
      <SiteFooter />
    </>
  );
}
