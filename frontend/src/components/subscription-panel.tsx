"use client";

import { CalendarClock, RefreshCw, XCircle } from "lucide-react";
import { useState } from "react";

import { api, ApiError, type Subscription, type SubscriptionStatus, type User } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { formatDate } from "@/lib/documents";
import { PLANS } from "@/lib/plans";

import { useToast } from "./toast";
import { Alert, Badge, Button } from "./ui";

const STATUS: Record<SubscriptionStatus, { label: string; tone: "green" | "amber" | "red" | "slate" }> = {
  APPROVAL_PENDING: { label: "Waiting for PayPal", tone: "amber" },
  APPROVED: { label: "Activating", tone: "amber" },
  ACTIVE: { label: "Active", tone: "green" },
  SUSPENDED: { label: "Payment failed", tone: "red" },
  CANCELLED: { label: "Cancelled", tone: "slate" },
  EXPIRED: { label: "Ended", tone: "slate" },
};

export function subscriptionIsLive(subscription: Subscription | null | undefined): boolean {
  return Boolean(subscription && ["APPROVED", "ACTIVE", "SUSPENDED"].includes(subscription.status));
}

/** The monthly subscription inside the plan card: status, next charge and cancellation. */
export function SubscriptionPanel({ user }: { user: User }) {
  const { setUser } = useAuth();
  const { toast } = useToast();
  const [confirming, setConfirming] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const subscription = user.subscription;
  if (!subscription) return null;

  const plan = PLANS.find((p) => p.id === subscription.plan);
  const live = subscriptionIsLive(subscription);
  const status = STATUS[subscription.status];

  async function cancel() {
    setLoading(true);
    setError(null);
    try {
      const { user: updated } = await api.cancelSubscription();
      setUser(updated);
      setConfirming(false);
      toast("success", "Subscription cancelled", "You keep your plan until the end of the period you paid for.");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "The subscription could not be cancelled. Try again.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="mt-5 border border-slate-200 bg-slate-50/60 p-4 dark:border-slate-800 dark:bg-slate-900/40">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="flex items-center gap-2 text-sm font-semibold">
          <RefreshCw className="size-4 text-brand-500" /> Monthly subscription · {plan?.name ?? subscription.plan}
          {plan && <span className="font-normal text-slate-500">${plan.price_usd}/month</span>}
        </p>
        <Badge tone={status.tone}>{status.label}</Badge>
      </div>

      <p className="mt-2 flex items-start gap-2 text-sm text-slate-600 dark:text-slate-400">
        <CalendarClock className="mt-0.5 size-4 shrink-0" />
        {subscription.status === "ACTIVE" && subscription.next_billing_at
          ? `Renews automatically on ${formatDate(subscription.next_billing_at, true)}.`
          : subscription.status === "SUSPENDED"
            ? "PayPal could not charge the last payment. Update your payment method in PayPal to keep the plan."
            : subscription.status === "APPROVED"
              ? "PayPal is confirming the first payment. The plan activates in a minute."
              : user.plan_expires_at
                ? `No more charges. Your plan stays active until ${formatDate(user.plan_expires_at, true)}.`
                : "No more charges."}
      </p>

      {error && (
        <div className="mt-3">
          <Alert>{error}</Alert>
        </div>
      )}

      {live &&
        (confirming ? (
          <div className="mt-4 border border-rose-200 bg-rose-50 p-3 text-sm text-rose-900 dark:border-rose-500/30 dark:bg-rose-500/10 dark:text-rose-100">
            <p className="font-semibold">Cancel the subscription?</p>
            <p className="mt-1 opacity-90">There will be no more charges. You keep {plan?.name ?? "your plan"} until the end of the period you paid for.</p>
            <div className="mt-3 flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
              <Button size="sm" variant="ghost" onClick={() => setConfirming(false)}>
                Keep it
              </Button>
              <Button size="sm" variant="danger" onClick={cancel} loading={loading} icon={<XCircle className="size-3.5" />}>
                Yes, cancel
              </Button>
            </div>
          </div>
        ) : (
          <Button size="sm" variant="ghost" className="mt-3 text-rose-600 dark:text-rose-400" onClick={() => setConfirming(true)}>
            Cancel subscription
          </Button>
        ))}
    </div>
  );
}
