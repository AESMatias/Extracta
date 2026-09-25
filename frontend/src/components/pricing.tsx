"use client";

import clsx from "clsx";
import { Check, Minus, Sparkles } from "lucide-react";
import type { ReactNode } from "react";

import type { PagePack, Plan } from "@/lib/api";
import { fill } from "@/lib/fill";
import { useI18n } from "@/lib/i18n";
import { formatPages, PACKS, planFeatures, planTagline, PLANS } from "@/lib/plans";

export type PricingMode = "payg" | "subscription";
export const DEFAULT_PACK = (PACKS[3] ?? PACKS[0]) as PagePack;

/** The five plans side by side. Phones: a row that snaps card by card. Desktop: one row of five. */
export function PlanGrid({ children }: { children: ReactNode }) {
  return (
    <div
      className={clsx(
        "-mx-4 flex snap-x snap-mandatory gap-3 overflow-x-auto px-4 pt-4 pb-4 [scrollbar-width:none] [&::-webkit-scrollbar]:hidden",
        "*:w-[72vw] *:max-w-[17rem] *:shrink-0 *:snap-center",
        "sm:mx-0 sm:grid sm:grid-cols-2 sm:overflow-visible sm:px-0 sm:*:w-auto sm:*:max-w-none",
        "lg:grid-cols-3 xl:grid-cols-5",
      )}
    >
      {children}
    </div>
  );
}

export function PlanCard({ plan, action, current }: { plan: Plan; action: ReactNode; current?: boolean }) {
  const { m, locale } = useI18n();
  const free = plan.id === "free";
  return (
    <div
      className={clsx(
        "group relative flex flex-col p-5 transition duration-500 ease-out hover:-translate-y-1",
        plan.highlight
          ? "bg-slate-900 text-white shadow-2xl shadow-brand-900/30 ring-1 ring-brand-500/50"
          : "border border-slate-200 bg-white hover:border-brand-300 hover:shadow-lg hover:shadow-brand-900/5 dark:border-slate-800 dark:bg-slate-900/60 dark:hover:border-brand-500/50",
      )}
    >
      <span
        aria-hidden
        className={clsx(
          "bg-signature animate-pan absolute inset-x-0 top-0 h-1 origin-left transition-transform duration-500 ease-out",
          plan.highlight ? "scale-x-100" : "scale-x-0 group-hover:scale-x-100",
        )}
      />
      {plan.highlight && (
        <span className="absolute -top-3 right-4 inline-flex items-center gap-1 bg-accent px-2 py-0.5 text-[11px] font-bold tracking-wide text-slate-900 uppercase shadow-md">
          <Sparkles className="size-3" /> {m.common.popular}
        </span>
      )}
      <div className="flex items-center justify-between gap-2">
        <h3 className="font-semibold">{plan.name}</h3>
        {current && (
          <span className={clsx("px-1.5 py-0.5 text-[11px] font-semibold", plan.highlight ? "bg-white/15" : "bg-brand-50 text-brand-700 dark:bg-brand-500/15 dark:text-brand-300")}>
            {m.common.current}
          </span>
        )}
      </div>
      <p className={clsx("mt-1 min-h-[2.25rem] text-xs leading-snug text-pretty", plan.highlight ? "text-slate-300" : "text-slate-600 dark:text-slate-400")}>
        {planTagline(plan, m)}
      </p>
      <p className="mt-3 flex items-baseline gap-1 whitespace-nowrap">
        <span className="text-3xl font-bold tracking-tight tabular-nums">{free ? "$0" : `$${plan.price_usd}`}</span>
        <span className={clsx("text-xs", plan.highlight ? "text-slate-400" : "text-slate-500")}>{free ? m.common.forever : m.common.perMonth}</span>
      </p>
      <div className="mt-4 *:h-9 *:text-sm">{action}</div>
      <ul className="mt-4 space-y-2 text-[13px]">
        {planFeatures(plan.privileges, m, locale).map((feature) => (
          <li key={feature.label} className={clsx("flex items-start gap-2", !feature.included && "opacity-45")}>
            {feature.included ? (
              <Check className={clsx("mt-0.5 size-3.5 shrink-0", plan.highlight ? "text-emerald-300" : "text-emerald-600 dark:text-emerald-400")} />
            ) : (
              <Minus className="mt-0.5 size-3.5 shrink-0" />
            )}
            <span>{feature.label}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

export function ModeToggle({ mode, onChange }: { mode: PricingMode; onChange: (mode: PricingMode) => void }) {
  const { m } = useI18n();
  const options: { id: PricingMode; label: string; hint: string }[] = [
    { id: "payg", label: m.pricing.payg, hint: m.pricing.paygHint },
    { id: "subscription", label: m.pricing.subscription, hint: m.pricing.subscriptionHint },
  ];
  return (
    <div
      role="radiogroup"
      aria-label={m.nav.pricing}
      className="relative mx-auto grid w-full max-w-md grid-cols-2 border border-slate-200 bg-white/80 p-1 shadow-sm backdrop-blur dark:border-slate-800 dark:bg-slate-900/70"
    >
      {/* The highlight slides between the two options. */}
      <span
        aria-hidden
        className={clsx(
          "bg-signature animate-pan absolute inset-y-1 left-1 w-[calc(50%-0.25rem)] shadow-md shadow-brand-600/25 transition-transform duration-500 ease-out",
          mode === "subscription" && "translate-x-full",
        )}
      />
      {options.map((option) => (
        <button
          key={option.id}
          type="button"
          role="radio"
          aria-checked={mode === option.id}
          onClick={() => onChange(option.id)}
          className={clsx(
            "relative cursor-pointer px-3 py-2.5 text-center transition-colors duration-300 ease-out",
            mode === option.id ? "text-white" : "text-slate-600 hover:text-slate-900 dark:text-slate-300 dark:hover:text-white",
          )}
        >
          <span className="block text-sm font-semibold">{option.label}</span>
          <span className={clsx("block text-xs", mode === option.id ? "text-white/80" : "text-slate-500")}>{option.hint}</span>
        </button>
      ))}
    </div>
  );
}

/** Pay as you go: pick an amount of pages, see the price and the price per page. */
export function PackPicker({ selected, onSelect, action }: { selected: string; onSelect: (id: string) => void; action: (pack: PagePack) => ReactNode }) {
  const { m, locale } = useI18n();
  const pack = PACKS.find((p) => p.id === selected) ?? DEFAULT_PACK;
  return (
    <div className="mx-auto grid max-w-5xl overflow-hidden border border-slate-200 bg-white shadow-xl shadow-slate-900/5 md:grid-cols-[1.25fr_1fr] dark:border-slate-800 dark:bg-slate-900/60">
      <div className="p-5 sm:p-8">
        <h3 className="text-center text-lg font-bold sm:text-xl">{m.pricing.howMany}</h3>
        <div className="mt-6 grid grid-cols-2 gap-2 sm:grid-cols-3 sm:gap-3">
          {PACKS.map((option) => (
            <button
              key={option.id}
              type="button"
              onClick={() => onSelect(option.id)}
              aria-pressed={option.id === pack.id}
              className={clsx(
                "group relative cursor-pointer border px-3 py-4 text-center transition-[background-color,border-color,box-shadow] duration-300 ease-out select-none",
                option.id === pack.id
                  ? "border-amber-400 bg-gradient-to-br from-amber-100 via-yellow-300 to-amber-400 text-slate-900 shadow-lg shadow-amber-500/30"
                  : "border-slate-200 hover:border-brand-300 hover:shadow-md dark:border-slate-700 dark:hover:border-brand-500/50",
              )}
            >
              <span className="block text-xl font-bold tabular-nums sm:text-2xl">{formatPages(option.pages, locale)}</span>
              <span className={clsx("block text-xs", option.id === pack.id ? "text-amber-900/70" : "text-slate-500")}>{m.pricing.pagesLabel}</span>
              <span className={clsx("mt-1 block text-xs font-semibold", option.id === pack.id ? "text-amber-950" : "text-brand-600 dark:text-brand-300")}>
                ${option.price_usd}
              </span>
            </button>
          ))}
        </div>
        <p className="mt-5 text-center text-xs text-slate-500">{m.pricing.freePlan}</p>
      </div>

      <div className="bg-signature animate-pan relative flex flex-col items-center justify-center overflow-hidden px-6 py-8 text-center text-white sm:px-8">
        <div className="bg-grid-light absolute inset-0 opacity-60 [mask-image:radial-gradient(ellipse_at_center,black,transparent_75%)]" />
        <p key={pack.id} className="relative animate-fade-up text-5xl font-bold tracking-tight tabular-nums">
          ${pack.price_usd}
        </p>
        <div className="relative mt-5 flex items-center gap-5 text-sm">
          <div>
            <p className="font-bold tabular-nums">{formatPages(pack.pages, locale)}</p>
            <p className="text-xs text-white/75">{m.pricing.pagesLabel}</p>
          </div>
          <span className="h-9 w-px bg-white/40" aria-hidden />
          <div>
            <p className="font-bold tabular-nums">${pack.price_per_page}</p>
            <p className="text-xs text-white/75">{m.pricing.costPerPage}</p>
          </div>
        </div>
        <div className="relative mt-6 w-full max-w-xs">{action(pack)}</div>
        <ul className="relative mt-6 space-y-1.5 text-left text-sm text-white/90">
          {m.pricing.packPoints.map((point) => (
            <li key={point} className="flex items-start gap-2">
              <Check className="mt-0.5 size-4 shrink-0 text-accent" /> {point}
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}

/** Every plan card, with the caller deciding each card's button. */
export function PlanCards({ action, currentPlan }: { action: (plan: Plan) => ReactNode; currentPlan?: string }) {
  return (
    <PlanGrid>
      {PLANS.map((plan) => (
        <PlanCard key={plan.id} plan={plan} action={action(plan)} current={currentPlan === plan.id} />
      ))}
    </PlanGrid>
  );
}

export function packLabel(pack: PagePack, template: string, locale: string): string {
  return fill(template, { pages: formatPages(pack.pages, locale) });
}
