"use client";

import { Coins, Crown, Gauge, Timer } from "lucide-react";

import type { User } from "@/lib/api";
import { formatDate, timeUntil } from "@/lib/documents";
import { fill, useI18n } from "@/lib/i18n";
import { formatPages } from "@/lib/plans";

import { Badge, ButtonLink, Card, Progress } from "./ui";

export function UsageCard({ user }: { user: User }) {
  const { m, locale } = useI18n();
  const u = m.usage;
  const usage = user.usage ?? {
    used: 0,
    limit: user.page_limit,
    remaining: user.page_limit,
    credits: user.page_credits,
    available: user.page_limit + user.page_credits,
    window_hours: user.privileges.window_hours,
    next_slot_at: null,
  };
  const percent = usage.limit ? (usage.used / usage.limit) * 100 : 100;
  const free = user.plan.id === "free";
  const pages = (value: number) => formatPages(value, locale);

  return (
    <Card className="relative overflow-hidden p-5 sm:p-6">
      <div className="absolute -top-16 -right-16 size-48 bg-gradient-to-br from-brand-500/20 to-emerald-500/20 blur-2xl" />
      <div className="relative flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="flex items-center gap-2 text-sm font-medium text-slate-500 dark:text-slate-400">
            <Gauge className="size-4" /> {usage.window_hours <= 24 ? u.title24 : u.title30}
          </p>
          <p className="mt-2 text-4xl font-bold tracking-tight tabular-nums">
            {pages(usage.used)}
            <span className="text-xl font-semibold text-slate-400"> / {pages(usage.limit)}</span>
          </p>
        </div>
        <div className="text-right">
          <Badge tone={free ? "slate" : "violet"}>
            {!free && <Crown className="size-3" />} {fill(u.plan, { plan: user.plan.name })}
          </Badge>
          {user.plan_expires_at && <p className="mt-2 text-xs text-slate-500">{fill(u.until, { date: formatDate(user.plan_expires_at) })}</p>}
        </div>
      </div>
      <Progress value={percent} tone={usage.remaining === 0 ? "red" : percent >= 75 ? "amber" : "brand"} className="relative mt-5" />
      <div className="relative mt-3 flex flex-wrap items-center justify-between gap-2 text-sm text-slate-600 dark:text-slate-400">
        {usage.remaining === 0 && usage.next_slot_at ? (
          <p className="flex items-center gap-1.5">
            <Timer className="size-4" /> {fill(u.comeBack, { time: timeUntil(usage.next_slot_at) })}
          </p>
        ) : (
          <p>
            <span className="font-semibold text-slate-900 dark:text-white">{fill(u.left, { count: pages(usage.remaining) })}</span> ·{" "}
            {fill(u.maxPages, { pages: user.privileges.max_pages_per_pdf })}
          </p>
        )}
      </div>

      <div className="relative mt-4 flex items-center justify-between gap-3 border-t border-slate-100 pt-4 dark:border-slate-800">
        <div className="flex items-center gap-3">
          <span className="bg-signature grid size-9 place-items-center text-white">
            <Coins className="size-4" />
          </span>
          <div>
            <p className="text-sm font-semibold">
              {u.prepaid}: <span className="tabular-nums">{pages(usage.credits)}</span>
            </p>
            <p className="text-xs text-slate-500">{u.prepaidHint}</p>
          </div>
        </div>
        <ButtonLink href="/pricing" size="sm" variant={usage.available === 0 ? "primary" : "outline"}>
          {usage.credits === 0 && free ? u.buyPages : u.getMore}
        </ButtonLink>
      </div>
    </Card>
  );
}
