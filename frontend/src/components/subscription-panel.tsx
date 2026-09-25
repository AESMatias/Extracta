"use client";

import { CalendarClock, RefreshCw, XCircle } from "lucide-react";
import { useState } from "react";

import { api, type Subscription, type SubscriptionStatus, type User } from "@/lib/api";
import { errorText } from "@/lib/errors";
import { fill, useI18n } from "@/lib/i18n";
import { useAuth } from "@/lib/auth";
import { formatDate } from "@/lib/documents";
import { PLANS } from "@/lib/plans";

import { useToast } from "./toast";
import { Alert, Badge, Button } from "./ui";

const TONE: Record<SubscriptionStatus, "green" | "amber" | "red" | "slate"> = {
  APPROVAL_PENDING: "amber",
  APPROVED: "amber",
  ACTIVE: "green",
  SUSPENDED: "red",
  CANCELLED: "slate",
  EXPIRED: "slate",
};

export function subscriptionIsLive(subscription: Subscription | null | undefined): boolean {
  return Boolean(subscription && ["APPROVED", "ACTIVE", "SUSPENDED"].includes(subscription.status));
}

/** The monthly subscription inside the plan card: status, next charge and cancellation. */
export function SubscriptionPanel({ user }: { user: User }) {
  const { setUser } = useAuth();
  const { toast } = useToast();
  const { m, locale } = useI18n();
  const s = m.subscription;
  const [confirming, setConfirming] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const subscription = user.subscription;
  if (!subscription) return null;

  const plan = PLANS.find((p) => p.id === subscription.plan);
  const live = subscriptionIsLive(subscription);
  const tone = TONE[subscription.status];
  const statusLabel = s.status[subscription.status];

  async function cancel() {
    setLoading(true);
    setError(null);
    try {
      const { user: updated } = await api.cancelSubscription();
      setUser(updated);
      setConfirming(false);
      toast("success", s.cancelled, s.cancelledText);
    } catch (err) {
      setError(errorText(err, locale, s.cancelFailed));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="mt-5 border border-slate-200 bg-slate-50/60 p-4 dark:border-slate-800 dark:bg-slate-900/40">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="flex items-center gap-2 text-sm font-semibold">
          <RefreshCw className="size-4 text-brand-500" /> {fill(s.title, { plan: plan?.name ?? subscription.plan })}
          {plan && <span className="font-normal text-slate-500">{fill(s.perMonth, { price: plan.price_usd })}</span>}
        </p>
        <Badge tone={tone}>{statusLabel}</Badge>
      </div>

      <p className="mt-2 flex items-start gap-2 text-sm text-slate-600 dark:text-slate-400">
        <CalendarClock className="mt-0.5 size-4 shrink-0" />
        {subscription.status === "ACTIVE" && subscription.next_billing_at
          ? fill(s.renews, { date: formatDate(subscription.next_billing_at, true) })
          : subscription.status === "SUSPENDED"
            ? s.suspended
            : subscription.status === "APPROVED"
              ? s.approved
              : user.plan_expires_at
                ? fill(s.endsOn, { date: formatDate(user.plan_expires_at, true) })
                : s.noCharges}
      </p>

      {error && (
        <div className="mt-3">
          <Alert>{error}</Alert>
        </div>
      )}

      {live &&
        (confirming ? (
          <div className="mt-4 border border-rose-200 bg-rose-50 p-3 text-sm text-rose-900 dark:border-rose-500/30 dark:bg-rose-500/10 dark:text-rose-100">
            <p className="font-semibold">{s.confirmTitle}</p>
            <p className="mt-1 opacity-90">{fill(s.confirmText, { plan: plan?.name ?? subscription.plan })}</p>
            <div className="mt-3 flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
              <Button size="sm" variant="ghost" onClick={() => setConfirming(false)}>
                {s.keep}
              </Button>
              <Button size="sm" variant="danger" onClick={cancel} loading={loading} icon={<XCircle className="size-3.5" />}>
                {s.yesCancel}
              </Button>
            </div>
          </div>
        ) : (
          <Button size="sm" variant="ghost" className="mt-3 text-rose-600 dark:text-rose-400" onClick={() => setConfirming(true)}>
            {s.cancel}
          </Button>
        ))}
    </div>
  );
}
