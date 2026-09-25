"use client";

import clsx from "clsx";
import { Check, Minus, Sparkles } from "lucide-react";
import type { ReactNode } from "react";

import type { Plan } from "@/lib/api";
import { planFeatures } from "@/lib/plans";

/**
 * The five plans side by side. Phones: a horizontal row that snaps card by card (the next card
 * peeks in, inviting a swipe). Tablets: 2-3 columns. Desktop: all five in one row.
 */
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

export function PlanCard({
  plan,
  action,
  current,
  period = "/ 30 days",
}: {
  plan: Plan;
  action: ReactNode;
  current?: boolean;
  period?: string;
}) {
  const free = plan.id === "free";
  return (
    <div
      className={clsx(
        "group relative flex flex-col p-5 transition duration-300 hover:-translate-y-1",
        plan.highlight
          ? "bg-slate-900 text-white shadow-2xl shadow-brand-900/30 ring-1 ring-brand-500/50 dark:bg-slate-900"
          : "border border-slate-200 bg-white hover:border-brand-300 hover:shadow-lg hover:shadow-brand-900/5 dark:border-slate-800 dark:bg-slate-900/60 dark:hover:border-brand-500/50",
      )}
    >
      {/* Signature bar: always on the recommended plan, drawn on hover on the others. */}
      <span
        aria-hidden
        className={clsx(
          "bg-signature animate-pan absolute inset-x-0 top-0 h-1 origin-left transition-transform duration-500",
          plan.highlight ? "scale-x-100" : "scale-x-0 group-hover:scale-x-100",
        )}
      />
      {plan.highlight && (
        <span className="absolute -top-3 right-4 inline-flex items-center gap-1 bg-accent px-2 py-0.5 text-[11px] font-bold tracking-wide text-slate-900 uppercase shadow-md">
          <Sparkles className="size-3" /> Popular
        </span>
      )}
      <div className="flex items-center justify-between gap-2">
        <h3 className="font-semibold">{plan.name}</h3>
        {current && (
          <span className={clsx("px-1.5 py-0.5 text-[11px] font-semibold", plan.highlight ? "bg-white/15" : "bg-brand-50 text-brand-700 dark:bg-brand-500/15 dark:text-brand-300")}>
            Current
          </span>
        )}
      </div>
      <p className={clsx("mt-1 min-h-[2.25rem] text-xs leading-snug text-pretty", plan.highlight ? "text-slate-300" : "text-slate-600 dark:text-slate-400")}>
        {plan.tagline}
      </p>
      <p className="mt-3 flex items-baseline gap-1 whitespace-nowrap">
        <span className="text-3xl font-bold tracking-tight tabular-nums">{free ? "$0" : `$${plan.price_usd}`}</span>
        <span className={clsx("text-xs", plan.highlight ? "text-slate-400" : "text-slate-500")}>{free ? "forever" : period}</span>
      </p>
      <div className="mt-4 *:h-9 *:text-sm">{action}</div>
      <ul className="mt-4 space-y-2 text-[13px]">
        {planFeatures(plan).map((feature) => (
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
