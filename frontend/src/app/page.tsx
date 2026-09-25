import {
  ArrowRight,
  BarChart3,
  Globe2,
  Layers,
  Lock,
  ScanText,
  ShieldCheck,
  Sparkles,
  UploadCloud,
  Zap,
} from "lucide-react";
import type { Metadata } from "next";

import { HeroVisual } from "@/components/hero-visual";
import { PlanCard } from "@/components/pricing";
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
  { icon: UploadCloud, title: "Upload your PDFs", text: "Drag and drop one or many digital PDFs, up to 50 MB each on paid plans." },
  { icon: ScanText, title: "AI reads them", text: "Gemini classifies each document and extracts every relevant field, in any language." },
  { icon: Sparkles, title: "Use your data", text: "Review it on screen, see charts, and download Excel, CSV or JSON in one click." },
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
    a: "Paid plans are 30-day passes paid once through PayPal. Nothing renews automatically; buy again whenever you need more time.",
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
          <div className="absolute top-[-10rem] left-1/2 -z-10 size-[40rem] -translate-x-1/2 rounded-full bg-brand-500/15 blur-3xl" />
          <div className="mx-auto grid max-w-6xl items-center gap-14 px-4 pt-12 pb-20 sm:px-6 sm:pt-20 lg:grid-cols-[1.05fr_1fr] lg:pb-28">
            <div className="animate-fade-up text-center lg:text-left">
              <span className="inline-flex items-center gap-2 rounded-full border border-brand-200 bg-brand-50/80 px-3 py-1 text-xs font-semibold text-brand-700 dark:border-brand-500/30 dark:bg-brand-500/10 dark:text-brand-300">
                <Sparkles className="size-3.5" /> AI document extraction, powered by Gemini
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

        {/* ------------------------------------------------ stats strip */}
        <section className="border-y border-slate-200/70 bg-slate-50/60 dark:border-slate-800/70 dark:bg-slate-900/40">
          <dl className="mx-auto grid max-w-6xl grid-cols-2 gap-6 px-4 py-8 sm:px-6 md:grid-cols-4">
            {[
              ["10", "document types"],
              ["3", "export formats"],
              ["Any", "language"],
              ["< 10 s", "per document"],
            ].map(([value, label]) => (
              <div key={label} className="text-center">
                <dt className="text-3xl font-bold tracking-tight">{value}</dt>
                <dd className="mt-1 text-sm text-slate-600 dark:text-slate-400">{label}</dd>
              </div>
            ))}
          </dl>
        </section>

        {/* ------------------------------------------------ features */}
        <section id="features" className="mx-auto max-w-6xl scroll-mt-20 px-4 py-20 sm:px-6 sm:py-28">
          <SectionTitle
            center
            eyebrow="Features"
            title="Everything you need to get data out of PDFs"
            subtitle="Built for freelancers, accountants and teams that are tired of copying numbers by hand."
          />
          <div className="mt-14 grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
            {FEATURES.map(({ icon: Icon, title, text }) => (
              <div
                key={title}
                className="group rounded-3xl border border-slate-200/80 bg-white p-6 transition duration-300 hover:-translate-y-1 hover:border-brand-200 hover:shadow-xl hover:shadow-brand-600/5 dark:border-slate-800 dark:bg-slate-900/50 dark:hover:border-brand-500/40"
              >
                <div className="grid size-11 place-items-center rounded-2xl bg-gradient-to-br from-brand-500 to-fuchsia-500 text-white shadow-lg shadow-brand-600/20 transition group-hover:scale-110">
                  <Icon className="size-5" />
                </div>
                <h3 className="mt-5 text-lg font-semibold">{title}</h3>
                <p className="mt-2 text-sm leading-relaxed text-slate-600 dark:text-slate-400">{text}</p>
              </div>
            ))}
          </div>
        </section>

        {/* ------------------------------------------------ document types */}
        <section id="document-types" className="scroll-mt-20 bg-slate-950 py-20 text-white sm:py-28">
          <div className="mx-auto max-w-6xl px-4 sm:px-6">
            <div className="max-w-2xl">
              <p className="text-sm font-semibold tracking-wide text-brand-300 uppercase">Document types</p>
              <h2 className="mt-2 text-3xl font-bold tracking-tight text-balance sm:text-4xl">It knows what it is reading</h2>
              <p className="mt-4 text-lg text-slate-400">
                Each PDF is classified first, then the fields that matter for that type are extracted: totals and line items for an
                invoice, parties and renewal terms for a contract, balances for a statement.
              </p>
            </div>
            <div className="mt-12 grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
              {Object.entries(DOCUMENT_TYPES).map(([id, { label, icon: Icon, color, examples }]) => (
                <div key={id} className="rounded-2xl border border-white/10 bg-white/[0.03] p-4 transition hover:border-white/25 hover:bg-white/[0.06]">
                  <Icon className="size-6" style={{ color }} />
                  <p className="mt-3 font-semibold">{label}</p>
                  <p className="mt-1 text-xs text-slate-400">{examples}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* ------------------------------------------------ how it works */}
        <section id="how-it-works" className="mx-auto max-w-6xl scroll-mt-20 px-4 py-20 sm:px-6 sm:py-28">
          <SectionTitle center eyebrow="How it works" title="From PDF to spreadsheet in three steps" />
          <ol className="mt-14 grid gap-6 md:grid-cols-3">
            {STEPS.map(({ icon: Icon, title, text }, index) => (
              <li key={title} className="relative rounded-3xl border border-slate-200/80 p-6 dark:border-slate-800">
                <span className="text-gradient text-5xl font-black">{index + 1}</span>
                <Icon className="absolute top-6 right-6 size-6 text-slate-300 dark:text-slate-600" />
                <h3 className="mt-3 text-lg font-semibold">{title}</h3>
                <p className="mt-2 text-sm leading-relaxed text-slate-600 dark:text-slate-400">{text}</p>
              </li>
            ))}
          </ol>
        </section>

        {/* ------------------------------------------------ pricing */}
        <section id="pricing" className="scroll-mt-20 bg-slate-50/70 py-20 sm:py-28 dark:bg-slate-900/40">
          <div className="mx-auto max-w-7xl px-4 sm:px-6">
            <SectionTitle
              center
              eyebrow="Pricing"
              title="Simple, tiny prices"
              subtitle="Start free. Upgrade with a 30-day pass when you need more — no subscription, no surprises."
            />
            <div className="mt-14 flex flex-wrap justify-center gap-5 *:w-full sm:*:w-[calc(50%-0.625rem)] lg:*:w-[calc(33.333%-0.834rem)] xl:*:w-[calc(20%-1rem)]">
              {PLANS.map((plan) => (
                <PlanCard
                  key={plan.id}
                  plan={plan}
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
            </div>
          </div>
        </section>

        {/* ------------------------------------------------ FAQ */}
        <section id="faq" className="mx-auto max-w-3xl scroll-mt-20 px-4 py-20 sm:px-6 sm:py-28">
          <SectionTitle center eyebrow="FAQ" title="Questions, answered" />
          <div className="mt-12 space-y-3">
            {FAQ.map(({ q, a }) => (
              <details
                key={q}
                className="group rounded-2xl border border-slate-200 bg-white px-5 py-4 transition open:shadow-lg open:shadow-slate-200/50 dark:border-slate-800 dark:bg-slate-900/50 dark:open:shadow-none"
              >
                <summary className="flex cursor-pointer list-none items-center justify-between gap-4 font-semibold">
                  {q}
                  <span className="grid size-7 shrink-0 place-items-center rounded-full bg-slate-100 text-lg leading-none transition group-open:rotate-45 dark:bg-slate-800">
                    +
                  </span>
                </summary>
                <p className="mt-3 text-sm leading-relaxed text-slate-600 dark:text-slate-400">{a}</p>
              </details>
            ))}
          </div>
        </section>

        {/* ------------------------------------------------ final CTA */}
        <section className="px-4 pb-20 sm:px-6">
          <div className="relative mx-auto max-w-5xl overflow-hidden rounded-[2rem] bg-gradient-to-br from-brand-600 via-violet-600 to-fuchsia-600 px-6 py-14 text-center text-white shadow-2xl shadow-brand-600/30 sm:px-12">
            <div className="bg-dots absolute inset-0 opacity-30" />
            <h2 className="relative text-3xl font-bold tracking-tight text-balance sm:text-4xl">Stop copying numbers by hand</h2>
            <p className="relative mx-auto mt-4 max-w-xl text-lg text-white/80">Create your free account and extract your first PDFs in under a minute.</p>
            <div className="relative mt-8 flex justify-center">
              <ButtonLink href="/register" size="lg" variant="secondary" className="bg-white! text-slate-900! hover:bg-slate-100!">
                Create free account <ArrowRight className="size-5" />
              </ButtonLink>
            </div>
          </div>
        </section>
      </main>
      <SiteFooter />
    </>
  );
}
