"use client";

import clsx from "clsx";
import { Check, Minus, Sparkles } from "lucide-react";
import type { ReactNode } from "react";

import type { Plan } from "@/lib/api";
import { planFeatures } from "@/lib/plans";

export function PlanCard({ plan, action, current }: { plan: Plan; action: ReactNode; current?: boolean }) {
  const free = plan.id === "free";
  return (
    <div
      className={clsx(
        "relative flex flex-col rounded-3xl border p-6 transition duration-300 hover:-translate-y-1",
        plan.highlight
          ? "border-transparent bg-slate-900 text-white shadow-2xl shadow-brand-600/30 ring-2 ring-brand-500 dark:bg-slate-900"
          : "border-slate-200 bg-white shadow-sm hover:shadow-lg dark:border-slate-800 dark:bg-slate-900/60",
      )}
    >
      {plan.highlight && (
        <span className="absolute -top-3 left-1/2 inline-flex -translate-x-1/2 items-center gap-1 whitespace-nowrap rounded-full bg-gradient-to-r from-brand-500 to-fuchsia-500 px-3 py-1 text-xs font-semibold text-white shadow-lg">
          <Sparkles className="size-3.5" /> Most popular
        </span>
      )}
      <div className="flex items-center justify-between gap-2">
        <h3 className="text-lg font-semibold">{plan.name}</h3>
        {current && (
          <span className={clsx("rounded-full px-2 py-0.5 text-xs font-semibold", plan.highlight ? "bg-white/15" : "bg-brand-50 text-brand-700 dark:bg-brand-500/15 dark:text-brand-300")}>
            Current
          </span>
        )}
      </div>
      <p className={clsx("mt-1 min-h-[2.5rem] text-sm text-pretty", plan.highlight ? "text-slate-300" : "text-slate-600 dark:text-slate-400")}>{plan.tagline}</p>
      <p className="mt-5 flex items-baseline gap-1 whitespace-nowrap">
        <span className="text-4xl font-bold tracking-tight">{free ? "$0" : `$${plan.price_usd}`}</span>
        <span className={clsx("text-sm", plan.highlight ? "text-slate-400" : "text-slate-500")}>{free ? "forever" : "/ 30 days"}</span>
      </p>
      <div className="mt-6">{action}</div>
      <ul className="mt-6 space-y-3 text-sm">
        {planFeatures(plan).map((feature) => (
          <li key={feature.label} className={clsx("flex items-start gap-2.5", !feature.included && "opacity-50")}>
            {feature.included ? (
              <Check className={clsx("mt-0.5 size-4 shrink-0", plan.highlight ? "text-brand-300" : "text-brand-600 dark:text-brand-400")} />
            ) : (
              <Minus className="mt-0.5 size-4 shrink-0" />
            )}
            <span>{feature.label}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
