"use client";

import { Crown, Gauge, Timer } from "lucide-react";

import type { User } from "@/lib/api";
import { formatDate, timeUntil } from "@/lib/documents";

import { Badge, ButtonLink, Card, Progress } from "./ui";

export function UsageCard({ user }: { user: User }) {
  const usage = user.usage ?? { used: 0, limit: user.daily_limit, remaining: user.daily_limit, next_slot_at: null };
  const percent = usage.limit ? (usage.used / usage.limit) * 100 : 100;
  const free = user.plan.id === "free";

  return (
    <Card className="relative overflow-hidden p-5 sm:p-6">
      <div className="absolute -top-16 -right-16 size-48 rounded-full bg-gradient-to-br from-brand-500/20 to-fuchsia-500/20 blur-2xl" />
      <div className="relative flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="flex items-center gap-2 text-sm font-medium text-slate-500 dark:text-slate-400">
            <Gauge className="size-4" /> PDFs in the last 24 hours
          </p>
          <p className="mt-2 text-4xl font-bold tracking-tight">
            {usage.used}
            <span className="text-xl font-semibold text-slate-400"> / {usage.limit}</span>
          </p>
        </div>
        <div className="text-right">
          <Badge tone={free ? "slate" : "violet"}>
            {!free && <Crown className="size-3" />} {user.plan.name} plan
          </Badge>
          {user.plan_expires_at && <p className="mt-2 text-xs text-slate-500">Until {formatDate(user.plan_expires_at)}</p>}
        </div>
      </div>
      <Progress value={percent} tone={usage.remaining === 0 ? "red" : percent >= 75 ? "amber" : "brand"} className="relative mt-5" />
      <div className="relative mt-4 flex flex-wrap items-center justify-between gap-3 text-sm">
        {usage.remaining === 0 && usage.next_slot_at ? (
          <p className="flex items-center gap-1.5 text-slate-600 dark:text-slate-400">
            <Timer className="size-4" /> Next PDF available in {timeUntil(usage.next_slot_at)}
          </p>
        ) : (
          <p className="text-slate-600 dark:text-slate-400">
            <span className="font-semibold text-slate-900 dark:text-white">{usage.remaining}</span> left today ·{" "}
            {user.plan.privileges.max_file_mb} MB per file
          </p>
        )}
        {user.plan.id !== "ultra" && (
          <ButtonLink href="/pricing" size="sm" variant={usage.remaining === 0 ? "primary" : "outline"}>
            {free ? "Upgrade from $1.99" : "Get more"}
          </ButtonLink>
        )}
      </div>
    </Card>
  );
}
