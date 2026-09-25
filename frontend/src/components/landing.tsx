"use client";

import {
  ArrowRight,
  BadgeCheck,
  Ban,
  BarChart3,
  ChevronRight,
  CreditCard,
  Database,
  EyeOff,
  FileDown,
  FileX,
  Globe2,
  KeyRound,
  Layers,
  Lock,
  LockKeyhole,
  ScanText,
  ServerCog,
  ShieldCheck,
  UploadCloud,
  Zap,
} from "lucide-react";
import { useState } from "react";

import type { PagePack, Plan } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { DOCUMENT_TYPES } from "@/lib/documents";
import { fill } from "@/lib/fill";
import { useI18n } from "@/lib/i18n";
import { formatPages } from "@/lib/plans";

import { HeroVisual } from "./hero-visual";
import { ModeToggle, PackPicker, PlanCards, type PricingMode } from "./pricing";
import { Reveal } from "./reveal";
import { SiteFooter } from "./site-footer";
import { SiteHeader } from "./site-header";
import { ButtonLink, SectionTitle } from "./ui";
import { WindParticles } from "./wind-particles";

const FEATURE_ICONS = [Layers, Globe2, BarChart3, Zap, Lock, ShieldCheck];
const STEP_ICONS = [UploadCloud, ScanText, FileDown];
const SECURITY_ICONS = [Ban, LockKeyhole, FileX, Database, CreditCard, EyeOff, KeyRound, ServerCog];

function Hero() {
  const { m } = useI18n();
  return (
    // Phones: flex-1 inside the first-screen wrapper (see Landing), so the hero plus the steps fill
    // exactly one screen; the invoice preview moves below that screen.
    <section className="relative isolate flex flex-1 items-center overflow-hidden lg:block">
      <div className="bg-dots absolute inset-0 -z-10 [mask-image:radial-gradient(ellipse_at_top,black,transparent_70%)]" />
      <div className="absolute top-[-12rem] left-1/2 -z-10 size-[38rem] -translate-x-1/2 rotate-45 bg-gradient-to-br from-emerald-400/15 via-cyan-400/10 to-brand-500/20 blur-3xl" />
      <WindParticles className="-z-10" />
      <div className="mx-auto grid w-full max-w-6xl items-center gap-14 px-4 py-8 sm:px-6 sm:py-14 lg:grid-cols-[1fr_1.05fr] lg:pt-20 lg:pb-20">
        <div className="animate-fade-up text-center lg:text-left">
          <h1 className="text-[2.1rem] leading-[1.05] font-bold tracking-tight text-balance sm:text-5xl lg:text-6xl">
            {m.hero.title} <span className="text-gradient">{m.hero.highlight}</span>
          </h1>
          <p className="mx-auto mt-4 max-w-xl text-base text-pretty text-slate-600 sm:mt-6 sm:text-lg lg:mx-0 dark:text-slate-400">{m.hero.subtitle}</p>
          <div className="mt-6 flex flex-col justify-center gap-3 sm:mt-8 sm:flex-row lg:justify-start">
            <ButtonLink href="/register" size="lg" icon={<ArrowRight className="size-5" />} className="flex-row-reverse">
              {m.hero.cta}
            </ButtonLink>
            <ButtonLink href="/pricing" size="lg" variant="outline">
              {m.hero.secondary}
            </ButtonLink>
          </div>
          <p className="mt-4 text-xs text-slate-500 sm:text-sm">{m.hero.note}</p>
        </div>
        <div className="hidden animate-fade-up [animation-delay:150ms] lg:block">
          <HeroVisual />
        </div>
      </div>
    </section>
  );
}

function Steps() {
  const { m } = useI18n();
  return (
    <section id="how-it-works" className="scroll-mt-20 border-y border-slate-200/70 bg-slate-50/80 dark:border-slate-800/70 dark:bg-slate-900/40">
      <div className="mx-auto max-w-6xl px-4 sm:px-6">
        <p className="flex items-center justify-center gap-2 pt-3 text-[11px] font-bold tracking-[0.2em] text-slate-500 uppercase sm:pt-5 dark:text-slate-400">
          {m.steps.title}
        </p>
        <ol className="grid grid-cols-3 py-3 sm:py-4">
          {m.steps.items.map(({ title, text }, index) => {
            const Icon = STEP_ICONS[index] ?? UploadCloud;
            return (
              <li
                key={title}
                style={{ animationDelay: `${300 + index * 120}ms` }}
                className="group flex animate-fade-up flex-col items-center gap-1.5 text-center sm:flex-row sm:justify-center sm:gap-3 sm:text-left"
              >
                <span className="bg-signature grid size-9 shrink-0 place-items-center text-white transition-all duration-500 ease-out group-hover:rotate-90 group-hover:rounded-[10px]">
                  <Icon className="size-4 transition duration-500 ease-out group-hover:-rotate-90" />
                </span>
                <p className="text-sm leading-tight">
                  <span className="font-semibold">{title}</span>
                  <span className="hidden text-xs text-slate-500 sm:block dark:text-slate-400">{text}</span>
                </p>
                {index < m.steps.items.length - 1 && (
                  <ChevronRight className="ml-auto hidden size-4 text-slate-300 sm:ml-6 sm:block dark:text-slate-600" />
                )}
              </li>
            );
          })}
        </ol>
        <div className="bg-signature animate-grow-x h-px origin-left opacity-60" />
        <dl className="grid grid-cols-4 py-3">
          {m.steps.stats.map(({ value, label }, index) => (
            <div key={label} style={{ animationDelay: `${500 + index * 90}ms` }} className="animate-fade-up text-center">
              <dt className="text-base font-bold tracking-tight tabular-nums sm:text-lg">{value}</dt>
              <dd className="text-[10px] leading-tight text-slate-500 sm:text-[11px] dark:text-slate-400">{label}</dd>
            </div>
          ))}
        </dl>
      </div>
    </section>
  );
}

function Features() {
  const { m } = useI18n();
  return (
    <section id="features" className="relative scroll-mt-20 overflow-hidden py-20 sm:py-28">
      <div className="bg-dots absolute inset-0 -z-10 opacity-60 [mask-image:linear-gradient(to_bottom,transparent,black_30%,black_70%,transparent)]" />
      <div className="mx-auto max-w-6xl px-4 sm:px-6">
        <Reveal>
          <SectionTitle center title={m.features.title} subtitle={m.features.subtitle} />
        </Reveal>
        <div className="mt-14 grid gap-px bg-slate-200/80 sm:grid-cols-2 lg:grid-cols-3 dark:bg-slate-800">
          {m.features.items.map(({ title, text }, index) => {
            const Icon = FEATURE_ICONS[index] ?? Layers;
            return (
              <Reveal
                key={title}
                delay={(index % 3) * 110}
                className="group relative isolate overflow-hidden bg-white px-6 py-9 text-center [perspective:700px] sm:px-8 sm:py-11 dark:bg-slate-950"
              >
                {/* A wash of color rises from the bottom on hover. */}
                <span
                  aria-hidden
                  className="absolute inset-0 -z-10 origin-bottom scale-y-0 bg-gradient-to-t from-brand-50 via-emerald-50/40 to-transparent transition-transform duration-700 ease-out group-hover:scale-y-100 dark:from-brand-500/10 dark:via-emerald-500/5"
                />
                {/* The icon lifts toward the viewer like a card picked up from the table. */}
                <div className="relative mx-auto size-12 transition-transform duration-700 ease-out [transform-style:preserve-3d] group-hover:[transform:translateY(-10px)_rotateX(22deg)_scale(1.12)]">
                  <span
                    aria-hidden
                    className="absolute inset-0 translate-x-1.5 translate-y-1.5 border border-brand-200 transition-all duration-700 ease-out group-hover:translate-x-3.5 group-hover:translate-y-4 group-hover:border-accent group-hover:bg-accent/15 group-hover:shadow-[0_14px_24px_-8px_rgb(250_204_21/0.6)] dark:border-brand-500/40"
                  />
                  <span className="bg-signature animate-pan relative grid size-12 place-items-center text-white transition-shadow duration-700 ease-out group-hover:shadow-[0_20px_32px_-10px_rgb(31_87_214/0.65)]">
                    <Icon className="size-5" />
                  </span>
                </div>
                <h3 className="mt-7 text-lg font-semibold">{title}</h3>
                <p className="mx-auto mt-2 max-w-xs text-sm leading-relaxed text-slate-600 dark:text-slate-400">{text}</p>
                <span aria-hidden className="bg-signature mx-auto mt-5 block h-0.5 w-20 scale-x-0 transition-transform duration-700 ease-out group-hover:scale-x-100" />
              </Reveal>
            );
          })}
        </div>
      </div>
    </section>
  );
}

function DocumentTypes() {
  const { m } = useI18n();
  const d = m.documentTypes;
  return (
    <section id="document-types" className="relative scroll-mt-20 overflow-hidden bg-slate-950 py-20 text-white sm:py-24">
      <div className="absolute -right-40 -bottom-40 size-[32rem] rotate-12 bg-gradient-to-tr from-brand-600/25 via-cyan-500/10 to-emerald-500/20 blur-3xl" />
      <div className="relative mx-auto max-w-6xl px-4 text-center sm:px-6">
        <Reveal className="mx-auto max-w-2xl">
          <p className="flex items-center justify-center gap-2 text-sm font-semibold tracking-wide text-emerald-300 uppercase">
            <span className="size-2 bg-accent" /> {d.eyebrow}
          </p>
          <h2 className="mt-2 text-3xl font-bold tracking-tight text-balance sm:text-4xl">{d.title}</h2>
          <p className="mt-4 text-lg text-slate-400">{d.subtitle}</p>
        </Reveal>
        <ul className="mt-14 grid grid-cols-2 gap-x-6 gap-y-10 sm:grid-cols-3 lg:grid-cols-5">
          {Object.entries(DOCUMENT_TYPES).map(([id, { icon: Icon, color }], index) => {
            const text = d.types[id as keyof typeof d.types];
            return (
              <Reveal as="li" key={id} delay={(index % 5) * 70} className="group flex flex-col items-center">
                <Icon className="size-7 transition duration-500 ease-out group-hover:-translate-y-1 group-hover:scale-110" style={{ color }} />
                <span aria-hidden className="mt-3 block h-0.5 w-6 transition-all duration-700 ease-out group-hover:w-24" style={{ backgroundColor: color }} />
                <p className="mt-3 font-semibold">{text.label}</p>
                <p className="mt-1 text-xs text-slate-400">{text.examples}</p>
              </Reveal>
            );
          })}
        </ul>
      </div>
    </section>
  );
}

// A shield with rounded corners and a slightly pointed base (the outline of lucide's shield icon,
// drawn in a 24 x 24 box). Filled with the brand gradient it becomes the badge itself.
const SHIELD =
  "M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.67-.01C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.24-2.72a1.17 1.17 0 0 1 1.52 0C14.51 3.81 17 5 19 5a1 1 0 0 1 1 1z";

/** The security badge: a gradient shield with a check mark, and shield outlines pulsing out of it. */
function ShieldBadge() {
  const pulse = "absolute inset-0 size-full animate-ping text-emerald-400/50 [animation-duration:2.6s]";
  return (
    <div className="relative mx-auto grid size-28 place-items-center">
      {/* Two outlines of the same shield grow and fade out, one after the other. */}
      <svg viewBox="0 0 24 24" className={pulse} aria-hidden>
        <path d={SHIELD} fill="none" stroke="currentColor" strokeWidth="0.6" strokeLinejoin="round" />
      </svg>
      <svg viewBox="0 0 24 24" className={`${pulse} text-brand-400/50 [animation-delay:1.3s]`} aria-hidden>
        <path d={SHIELD} fill="none" stroke="currentColor" strokeWidth="0.6" strokeLinejoin="round" />
      </svg>
      <svg viewBox="0 0 24 24" className="relative size-24 drop-shadow-[0_0_24px_rgb(16_185_129/0.55)]" aria-hidden>
        <defs>
          <linearGradient id="shield-fill" x1="4" y1="2" x2="20" y2="22" gradientUnits="userSpaceOnUse">
            <stop stopColor="#10b981" />
            <stop offset="0.5" stopColor="#0891b2" />
            <stop offset="1" stopColor="#1f57d6" />
          </linearGradient>
        </defs>
        {/* The stroke in the same gradient, with round joins, softens the corners a little more. */}
        <path d={SHIELD} fill="url(#shield-fill)" stroke="url(#shield-fill)" strokeWidth="1.2" strokeLinejoin="round" />
        <path d="m9 12 2 2 4-4" fill="none" stroke="#fff" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    </div>
  );
}

function Security() {
  const { m } = useI18n();
  const s = m.security;
  return (
    <section id="security" className="relative scroll-mt-20 overflow-hidden bg-slate-950 py-20 text-white sm:py-28">
      <div className="bg-grid-light absolute inset-0 opacity-50 [mask-image:radial-gradient(ellipse_at_top,black,transparent_70%)]" />
      <div className="bg-signature animate-grow-x absolute inset-x-0 top-0 h-1 origin-left" />
      <div className="relative mx-auto max-w-6xl px-4 sm:px-6">
        <Reveal className="mx-auto max-w-3xl text-center">
          <ShieldBadge />
          <p className="mt-6 text-sm font-semibold tracking-wide text-emerald-300 uppercase">{s.eyebrow}</p>
          <h2 className="mt-2 text-3xl font-bold tracking-tight text-balance sm:text-5xl">{s.title}</h2>
          <p className="mt-4 text-lg text-slate-400">{s.subtitle}</p>
        </Reveal>

        <div className="mt-14 grid gap-px bg-white/10 sm:grid-cols-2 lg:grid-cols-4">
          {s.items.map(({ title, text }, index) => {
            const Icon = SECURITY_ICONS[index] ?? ShieldCheck;
            return (
              <Reveal key={title} delay={(index % 4) * 90} className="group relative overflow-hidden bg-slate-950 p-6 text-center">
                <span
                  aria-hidden
                  className="absolute inset-0 origin-left scale-x-0 bg-gradient-to-r from-emerald-500/10 via-cyan-500/5 to-transparent transition-transform duration-700 ease-out group-hover:scale-x-100"
                />
                <Icon className="relative mx-auto size-6 text-emerald-300 transition duration-500 ease-out group-hover:-translate-y-0.5 group-hover:text-accent" />
                <h3 className="relative mt-4 font-semibold">{title}</h3>
                <p className="relative mt-1.5 text-sm leading-relaxed text-slate-400">{text}</p>
              </Reveal>
            );
          })}
        </div>

        <Reveal className="mt-12">
          <p className="text-center text-xs font-bold tracking-[0.2em] text-slate-500 uppercase">{s.standardsTitle}</p>
          <div className="mt-5 grid grid-cols-2 gap-3 lg:grid-cols-4">
            {s.standards.map(({ name, text }) => (
              <div key={name} className="group border border-white/10 p-4 text-center transition-colors duration-500 ease-out hover:border-emerald-400/50 hover:bg-white/[0.03]">
                <span className="mx-auto grid size-9 place-items-center" aria-hidden>
                  <BadgeCheck className="size-6 text-accent transition-transform duration-500 ease-out will-change-transform group-hover:scale-125" />
                </span>
                <p className="mt-1 font-bold tracking-tight">{name}</p>
                <p className="mt-1 text-xs text-slate-400">{text}</p>
              </div>
            ))}
          </div>
          <p className="mx-auto mt-6 max-w-2xl text-center text-xs text-slate-500">{s.disclaimer}</p>
        </Reveal>
      </div>
    </section>
  );
}

function Pricing() {
  const { m, locale } = useI18n();
  const { user } = useAuth();
  const [mode, setMode] = useState<PricingMode>("payg");
  const [pack, setPack] = useState("p1000");
  const signUpThen = (next: string) => (user ? next : `/register?next=${encodeURIComponent(next)}`);

  const packAction = (selected: PagePack) => (
    <ButtonLink
      href={signUpThen(`/pricing?pack=${selected.id}`)}
      variant="light"
      className="w-full"
      icon={<ArrowRight className="size-4" />}
    >
      {fill(m.pricing.buy, { pages: formatPages(selected.pages, locale) })}
    </ButtonLink>
  );
  const planAction = (plan: Plan) => (
    <ButtonLink
      href={plan.id === "free" ? "/register" : signUpThen(`/pricing?plan=${plan.id}`)}
      variant={plan.highlight ? "primary" : "outline"}
      className="w-full"
    >
      {plan.id === "free" ? m.pricing.startFree : fill(m.pricing.get, { plan: plan.name })}
    </ButtonLink>
  );

  return (
    <section id="pricing" className="scroll-mt-20 bg-slate-50/70 py-20 sm:py-24 dark:bg-slate-900/40">
      <div className="mx-auto max-w-6xl px-4 sm:px-6">
        <Reveal>
          <SectionTitle center title={m.pricing.title} subtitle={m.pricing.subtitle} />
        </Reveal>
        <Reveal className="mt-10" delay={80}>
          <ModeToggle mode={mode} onChange={setMode} />
        </Reveal>
        <Reveal className="mt-10" delay={140}>
          {mode === "payg" ? <PackPicker selected={pack} onSelect={setPack} action={packAction} /> : <PlanCards action={planAction} />}
        </Reveal>
      </div>
    </section>
  );
}

function Faq() {
  const { m } = useI18n();
  return (
    <section id="faq" className="mx-auto max-w-3xl scroll-mt-20 px-4 py-20 sm:px-6 sm:py-24">
      <Reveal>
        <SectionTitle center title={m.faq.title} />
      </Reveal>
      <div className="mt-12 divide-y divide-slate-200 border-y border-slate-200 dark:divide-slate-800 dark:border-slate-800">
        {m.faq.items.map(({ q, a }, index) => (
          <Reveal as="details" key={q} delay={index * 60} className="group py-4">
            <summary className="flex cursor-pointer list-none items-center justify-between gap-4 font-semibold transition duration-300 ease-out select-none hover:text-brand-600 dark:hover:text-brand-400 [&::-webkit-details-marker]:hidden">
              {q}
              <span aria-hidden className="grid size-7 shrink-0 place-items-center bg-slate-100 text-lg leading-none transition duration-500 ease-out select-none group-open:rotate-45 group-open:bg-accent group-open:text-slate-900 dark:bg-slate-800">
                +
              </span>
            </summary>
            <p className="mt-3 pr-10 text-sm leading-relaxed text-slate-600 dark:text-slate-400">{a}</p>
          </Reveal>
        ))}
      </div>
    </section>
  );
}

function FinalCta() {
  const { m } = useI18n();
  return (
    <section className="px-4 pb-20 sm:px-6">
      <Reveal className="bg-signature animate-pan relative mx-auto max-w-5xl overflow-hidden px-6 py-14 text-center text-white shadow-2xl shadow-brand-900/30 sm:px-12">
        <div className="bg-grid-light absolute inset-0 [mask-image:radial-gradient(ellipse_at_center,black,transparent_75%)]" />
        <span aria-hidden className="absolute top-0 left-0 h-1 w-24 bg-accent" />
        <span aria-hidden className="absolute right-0 bottom-0 size-3 bg-accent" />
        <h2 className="relative text-3xl font-bold tracking-tight text-balance sm:text-4xl">{m.cta.title}</h2>
        <p className="relative mx-auto mt-4 max-w-xl text-lg text-white/85">{m.cta.subtitle}</p>
        <div className="relative mt-8 flex justify-center">
          <ButtonLink href="/register" size="lg" variant="light">
            {m.cta.button} <ArrowRight className="size-5" />
          </ButtonLink>
        </div>
      </Reveal>
    </section>
  );
}

export function Landing() {
  return (
    <>
      <SiteHeader />
      <main>
        {/* One full screen on phones (svh: the height with the browser bars shown); normal flow on desktop. */}
        <div className="flex min-h-[calc(100svh-4rem)] flex-col lg:block lg:min-h-0">
          <Hero />
          <Steps />
        </div>
        <section className="overflow-hidden px-6 py-12 lg:hidden" aria-hidden>
          <HeroVisual />
        </section>
        <Features />
        <DocumentTypes />
        <Security />
        <Pricing />
        <Faq />
        <FinalCta />
      </main>
      <SiteFooter />
    </>
  );
}
