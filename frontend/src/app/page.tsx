import {
  ArrowRight,
  BarChart3,
  ChevronRight,
  FileDown,
  Globe2,
  Layers,
  Lock,
  ScanText,
  ShieldCheck,
  UploadCloud,
  Zap,
} from "lucide-react";
import type { Metadata } from "next";

import { HeroVisual } from "@/components/hero-visual";
import { PlanCard, PlanGrid } from "@/components/pricing";
import { Reveal } from "@/components/reveal";
import { SiteFooter } from "@/components/site-footer";
import { SiteHeader } from "@/components/site-header";
import { ButtonLink, SectionTitle } from "@/components/ui";
import { DOCUMENT_TYPES } from "@/lib/documents";
import { PLANS } from "@/lib/plans";

export const metadata: Metadata = { title: { absolute: "Extracta · Turn PDFs into structured data" } };

const FEATURES = [
  { icon: Layers, title: "10 document types", text: "Invoices, receipts, orders, quotes, bank statements, contracts, payslips, resumes, reports and more." },
  { icon: Globe2, title: "Any language", text: "Spanish, English, Portuguese… Dates, amounts and currencies always come back in one clean format." },
  { icon: BarChart3, title: "Live charts", text: "Watch totals by currency and documents by type build up while your batch is processed." },
  { icon: Zap, title: "Batch processing", text: "Drop dozens of PDFs at once. They are queued and processed one by one, reliably." },
  { icon: Lock, title: "Private by design", text: "Process-only mode never stores your data. Bank accounts keep just the last 4 digits." },
  { icon: ShieldCheck, title: "Validated output", text: "Every result is checked against a strict schema before it reaches you. No broken data." },
];

const STEPS = [
  { icon: UploadCloud, title: "Upload", text: "Drop one PDF or dozens" },
  { icon: ScanText, title: "AI reads", text: "Classified and extracted" },
  { icon: FileDown, title: "Export", text: "Excel, CSV or JSON" },
];

const STATS = [
  ["10", "document types"],
  ["3", "export formats"],
  ["Any", "language"],
  ["< 10 s", "per document"],
];

const FAQ = [
  {
    q: "Which PDFs work?",
    a: "Digital PDFs with a text layer: those created by accounting systems, banks, e-invoicing or exported from Word. Scanned images are not supported yet.",
  },
  {
    q: "What does the free plan include?",
    a: "2 PDFs every 24 hours with all features except saving to your history. No credit card needed.",
  },
  {
    q: "Do you keep my documents?",
    a: "The PDF file is deleted right after processing. In process-only mode the extracted data lives for 1 hour and is never written to a database. Paid plans can choose to save results to their history.",
  },
  {
    q: "How do payments work?",
    a: "Through PayPal, your choice: a monthly subscription you can cancel anytime from your account (you keep the plan until the period ends), or a single 30-day pass that never renews.",
  },
  {
    q: "How accurate is it?",
    a: "Very accurate on well-structured documents, but it is AI: always review important figures before using them.",
  },
];

export default function HomePage() {
  return (
    <>
      <SiteHeader />
      <main>
        {/* ------------------------------------------------ hero */}
        <section className="relative overflow-hidden">
          <div className="bg-dots absolute inset-0 -z-10 [mask-image:radial-gradient(ellipse_at_top,black,transparent_70%)]" />
          <div className="absolute top-[-12rem] left-1/2 -z-10 size-[38rem] -translate-x-1/2 rotate-45 bg-gradient-to-br from-emerald-400/15 via-cyan-400/10 to-brand-500/20 blur-3xl" />
          <div className="mx-auto grid max-w-6xl items-center gap-14 px-4 pt-12 pb-16 sm:px-6 sm:pt-20 lg:grid-cols-[1.05fr_1fr] lg:pb-20">
            <div className="animate-fade-up text-center lg:text-left">
              <span className="inline-flex items-center gap-2 border border-brand-200 bg-white/80 px-3 py-1 text-xs font-semibold text-brand-700 dark:border-brand-500/30 dark:bg-brand-500/10 dark:text-brand-300">
                <span className="size-1.5 animate-blink bg-accent" /> AI document extraction, powered by Gemini
              </span>
              <h1 className="mt-6 text-4xl leading-[1.05] font-bold tracking-tight text-balance sm:text-5xl lg:text-6xl">
                Turn any PDF into <span className="text-gradient">clean, structured data</span>
              </h1>
              <p className="mx-auto mt-6 max-w-xl text-lg text-pretty text-slate-600 lg:mx-0 dark:text-slate-400">
                Drop your invoices, receipts, contracts or bank statements. Extracta reads them with AI and hands you tidy tables,
                live charts and one-click Excel, CSV or JSON exports.
              </p>
              <div className="mt-8 flex flex-col justify-center gap-3 sm:flex-row lg:justify-start">
                <ButtonLink href="/register" size="lg" icon={<ArrowRight className="size-5" />} className="flex-row-reverse">
                  Start free — 2 PDFs a day
                </ButtonLink>
                <ButtonLink href="/pricing" size="lg" variant="outline">
                  See plans
                </ButtonLink>
              </div>
              <p className="mt-4 text-sm text-slate-500">No credit card required · Paid plans from $1.99</p>
            </div>
            <div className="animate-fade-up [animation-delay:150ms]">
              <HeroVisual />
            </div>
          </div>
        </section>

        {/* ------------------------------------------------ how it works (compact) + numbers */}
        <section id="how-it-works" className="scroll-mt-20 border-y border-slate-200/70 bg-slate-50/70 dark:border-slate-800/70 dark:bg-slate-900/40">
          <div className="mx-auto max-w-6xl px-4 sm:px-6">
            <ol className="grid gap-2 py-5 sm:grid-cols-3 sm:gap-0">
              {STEPS.map(({ icon: Icon, title, text }, index) => (
                <Reveal as="li" key={title} delay={index * 120} className="group flex items-center gap-3 sm:justify-center">
                  <span className="grid size-9 shrink-0 place-items-center bg-signature text-white transition duration-300 group-hover:rotate-90">
                    <Icon className="size-4 transition duration-300 group-hover:-rotate-90" />
                  </span>
                  <p className="text-sm leading-tight">
                    <span className="font-mono text-[11px] text-slate-400">0{index + 1}</span>{" "}
                    <span className="font-semibold">{title}</span>
                    <span className="block text-xs text-slate-500 dark:text-slate-400">{text}</span>
                  </p>
                  {index < STEPS.length - 1 && <ChevronRight className="ml-auto hidden size-4 text-slate-300 sm:ml-6 sm:block dark:text-slate-600" />}
                </Reveal>
              ))}
            </ol>
            <div className="bg-signature animate-grow-x h-px origin-left opacity-60" />
            <dl className="grid grid-cols-4 py-4">
              {STATS.map(([value, label], index) => (
                <Reveal key={label} delay={index * 90} className="text-center">
                  <dt className="text-lg font-bold tracking-tight tabular-nums sm:text-xl">{value}</dt>
                  <dd className="text-[11px] text-slate-500 sm:text-xs dark:text-slate-400">{label}</dd>
                </Reveal>
              ))}
            </dl>
          </div>
        </section>

        {/* ------------------------------------------------ features */}
        <section id="features" className="relative scroll-mt-20 overflow-hidden py-20 sm:py-28">
          <div className="bg-dots absolute inset-0 -z-10 opacity-60 [mask-image:linear-gradient(to_bottom,transparent,black_30%,black_70%,transparent)]" />
          <div className="mx-auto max-w-6xl px-4 sm:px-6">
            <Reveal>
              <SectionTitle
                center
                eyebrow="Features"
                title="Everything you need to get data out of PDFs"
                subtitle="Built for freelancers, accountants and teams that are tired of copying numbers by hand."
              />
            </Reveal>
            <div className="mt-14 grid gap-px bg-slate-200/80 sm:grid-cols-2 lg:grid-cols-3 dark:bg-slate-800">
              {FEATURES.map(({ icon: Icon, title, text }, index) => (
                <Reveal
                  key={title}
                  delay={(index % 3) * 110}
                  className="group relative isolate overflow-hidden bg-white px-6 py-8 text-center sm:px-8 sm:py-10 dark:bg-slate-950"
                >
                  {/* A wash of color rises from the bottom on hover. */}
                  <span
                    aria-hidden
                    className="absolute inset-0 -z-10 origin-bottom scale-y-0 bg-gradient-to-t from-brand-50 via-emerald-50/40 to-transparent transition-transform duration-500 group-hover:scale-y-100 dark:from-brand-500/10 dark:via-emerald-500/5"
                  />
                  <p className="font-mono text-[11px] tracking-[0.25em] text-slate-400">{String(index + 1).padStart(2, "0")}</p>
                  <div className="relative mx-auto mt-5 size-12">
                    <span
                      aria-hidden
                      className="absolute inset-0 translate-x-1.5 translate-y-1.5 border border-brand-200 transition-all duration-300 group-hover:translate-x-2.5 group-hover:translate-y-2.5 group-hover:border-accent dark:border-brand-500/40"
                    />
                    <span className="bg-signature animate-pan relative grid size-12 place-items-center text-white">
                      <Icon className="size-5 transition duration-500 group-hover:scale-110" />
                    </span>
                  </div>
                  <h3 className="mt-6 text-lg font-semibold">{title}</h3>
                  <p className="mx-auto mt-2 max-w-xs text-sm leading-relaxed text-slate-600 dark:text-slate-400">{text}</p>
                  <span aria-hidden className="bg-signature mx-auto mt-5 block h-0.5 w-10 scale-x-0 transition-transform duration-500 group-hover:scale-x-100" />
                </Reveal>
              ))}
            </div>
          </div>
        </section>

        {/* ------------------------------------------------ document types */}
        <section id="document-types" className="relative scroll-mt-20 overflow-hidden bg-slate-950 py-20 text-white sm:py-24">
          <div className="absolute -right-40 -bottom-40 size-[32rem] rotate-12 bg-gradient-to-tr from-brand-600/25 via-cyan-500/10 to-emerald-500/20 blur-3xl" />
          <div className="relative mx-auto max-w-6xl px-4 sm:px-6">
            <Reveal className="max-w-2xl">
              <p className="flex items-center gap-2 text-sm font-semibold tracking-wide text-emerald-300 uppercase">
                <span className="size-2 bg-accent" /> Document types
              </p>
              <h2 className="mt-2 text-3xl font-bold tracking-tight text-balance sm:text-4xl">It knows what it is reading</h2>
              <p className="mt-4 text-lg text-slate-400">
                Each PDF is classified first, then the fields that matter for that type are extracted: totals and line items for an
                invoice, parties and renewal terms for a contract, balances for a statement.
              </p>
            </Reveal>
            <ul className="mt-14 grid grid-cols-2 gap-x-6 gap-y-10 sm:grid-cols-3 lg:grid-cols-5">
              {Object.entries(DOCUMENT_TYPES).map(([id, { label, icon: Icon, color, examples }], index) => (
                <Reveal as="li" key={id} delay={(index % 5) * 70} className="group">
                  <Icon className="size-7 transition duration-300 group-hover:-translate-y-1" style={{ color }} />
                  <span
                    aria-hidden
                    className="mt-3 block h-0.5 w-6 transition-all duration-500 group-hover:w-full"
                    style={{ backgroundColor: color }}
                  />
                  <p className="mt-3 font-semibold">{label}</p>
                  <p className="mt-1 text-xs text-slate-400">{examples}</p>
                </Reveal>
              ))}
            </ul>
          </div>
        </section>

        {/* ------------------------------------------------ pricing */}
        <section id="pricing" className="scroll-mt-20 bg-slate-50/70 py-20 sm:py-24 dark:bg-slate-900/40">
          <div className="mx-auto max-w-6xl px-4 sm:px-6">
            <Reveal>
              <SectionTitle
                center
                eyebrow="Pricing"
                title="Simple, tiny prices"
                subtitle="Start free. Subscribe monthly and cancel anytime, or buy a single 30-day pass — no surprises."
              />
            </Reveal>
            <Reveal className="mt-10" delay={100}>
              <PlanGrid>
                {PLANS.map((plan) => (
                  <PlanCard
                    key={plan.id}
                    plan={plan}
                    period="/ month"
                    action={
                      <ButtonLink
                        href={plan.id === "free" ? "/register" : `/pricing?plan=${plan.id}`}
                        variant={plan.highlight ? "primary" : "outline"}
                        className="w-full"
                      >
                        {plan.id === "free" ? "Start free" : `Get ${plan.name}`}
                      </ButtonLink>
                    }
                  />
                ))}
              </PlanGrid>
            </Reveal>
          </div>
        </section>

        {/* ------------------------------------------------ FAQ */}
        <section id="faq" className="mx-auto max-w-3xl scroll-mt-20 px-4 py-20 sm:px-6 sm:py-24">
          <Reveal>
            <SectionTitle center eyebrow="FAQ" title="Questions, answered" />
          </Reveal>
          <div className="mt-12 divide-y divide-slate-200 border-y border-slate-200 dark:divide-slate-800 dark:border-slate-800">
            {FAQ.map(({ q, a }, index) => (
              <Reveal as="details" key={q} delay={index * 60} className="group py-4">
                <summary className="flex cursor-pointer list-none items-center justify-between gap-4 font-semibold transition hover:text-brand-600 dark:hover:text-brand-400">
                  {q}
                  <span className="grid size-7 shrink-0 place-items-center bg-slate-100 text-lg leading-none transition duration-300 group-open:rotate-45 group-open:bg-accent group-open:text-slate-900 dark:bg-slate-800">
                    +
                  </span>
                </summary>
                <p className="mt-3 pr-10 text-sm leading-relaxed text-slate-600 dark:text-slate-400">{a}</p>
              </Reveal>
            ))}
          </div>
        </section>

        {/* ------------------------------------------------ final CTA */}
        <section className="px-4 pb-20 sm:px-6">
          <Reveal className="bg-signature animate-pan relative mx-auto max-w-5xl overflow-hidden px-6 py-14 text-center text-white shadow-2xl shadow-brand-900/30 sm:px-12">
            <div className="bg-grid-light absolute inset-0 [mask-image:radial-gradient(ellipse_at_center,black,transparent_75%)]" />
            <span aria-hidden className="absolute top-0 left-0 h-1 w-24 bg-accent" />
            <span aria-hidden className="absolute right-0 bottom-0 size-3 bg-accent" />
            <h2 className="relative text-3xl font-bold tracking-tight text-balance sm:text-4xl">Stop copying numbers by hand</h2>
            <p className="relative mx-auto mt-4 max-w-xl text-lg text-white/85">Create your free account and extract your first PDFs in under a minute.</p>
            <div className="relative mt-8 flex justify-center">
              <ButtonLink href="/register" size="lg" variant="secondary" className="bg-white! text-slate-900! hover:bg-accent!">
                Create free account <ArrowRight className="size-5" />
              </ButtonLink>
            </div>
          </Reveal>
        </section>
      </main>
      <SiteFooter />
    </>
  );
}
