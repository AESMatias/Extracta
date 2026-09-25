"use client";

import { BadgeCheck, Crown, KeyRound, LogOut, Mail, Receipt } from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { AppPage } from "@/components/app-header";
import { SecurityCard } from "@/components/security-card";
import { subscriptionIsLive, SubscriptionPanel } from "@/components/subscription-panel";
import { Badge, Button, ButtonLink, Card, PageLoader } from "@/components/ui";
import { UsageCard } from "@/components/usage-card";
import { VerifyEmailBanner } from "@/components/verify-email-banner";
import { api, type Payment } from "@/lib/api";
import { useAuth, useRequireUser } from "@/lib/auth";
import { formatDate } from "@/lib/documents";
import { planFeatures } from "@/lib/plans";

const STATUS_TONE = { active: "green", pending: "amber", rejected: "red", suspended: "red" } as const;
const PAYMENT_TONE: Record<string, "green" | "amber" | "red"> = { COMPLETED: "green", REFUNDED: "red", REVERSED: "red" };

export default function AccountPage() {
  const { user, loading } = useRequireUser();
  const { logout } = useAuth();
  const router = useRouter();
  const [payments, setPayments] = useState<Payment[] | null>(null);

  useEffect(() => {
    if (user) api.payments().then((r) => setPayments(r.payments), () => setPayments([]));
  }, [user]);

  if (loading || !user) {
    return (
      <AppPage>
        <PageLoader />
      </AppPage>
    );
  }

  async function signOut() {
    await logout();
    router.push("/");
  }

  return (
    <AppPage>
      <h1 className="text-2xl font-bold tracking-tight sm:text-3xl">Account</h1>
      {!user.email_verified && (
        <div className="mt-4">
          <VerifyEmailBanner user={user} />
        </div>
      )}

      <div className="mt-6 grid gap-6 lg:grid-cols-[1fr_1.2fr]">
        <div className="space-y-6">
          <Card className="p-6">
            <div className="flex items-center gap-4">
              <div className="grid size-14 place-items-center rounded-2xl bg-gradient-to-br from-brand-500 to-fuchsia-500 text-xl font-bold text-white">
                {(user.name ?? user.email).charAt(0).toUpperCase()}
              </div>
              <div className="min-w-0">
                <p className="truncate text-lg font-semibold">{user.name ?? "No name"}</p>
                <p className="flex items-center gap-1.5 truncate text-sm text-slate-500">
                  <Mail className="size-3.5" /> {user.email}
                </p>
              </div>
            </div>
            <dl className="mt-6 space-y-3 text-sm">
              <div className="flex justify-between gap-4">
                <dt className="text-slate-500">Email</dt>
                <dd>
                  {user.email_verified ? (
                    <Badge tone="green">
                      <BadgeCheck className="size-3" /> Verified
                    </Badge>
                  ) : (
                    <Badge tone="amber">Not verified</Badge>
                  )}
                </dd>
              </div>
              <div className="flex justify-between gap-4">
                <dt className="text-slate-500">Status</dt>
                <dd>
                  <Badge tone={STATUS_TONE[user.status]}>{user.status}</Badge>
                </dd>
              </div>
              <div className="flex justify-between gap-4">
                <dt className="text-slate-500">Sign-in methods</dt>
                <dd className="flex gap-1.5">
                  {user.has_password && (
                    <Badge tone="slate">
                      <KeyRound className="size-3" /> Password
                    </Badge>
                  )}
                  {user.has_google && <Badge tone="slate">Google</Badge>}
                </dd>
              </div>
              <div className="flex justify-between gap-4">
                <dt className="text-slate-500">Member since</dt>
                <dd>{formatDate(user.created_at)}</dd>
              </div>
            </dl>
            <Button variant="outline" className="mt-6 w-full" onClick={signOut} icon={<LogOut className="size-4" />}>
              Sign out
            </Button>
          </Card>
          <SecurityCard user={user} />
          <UsageCard user={user} />
        </div>

        <div className="space-y-6">
          <Card className="p-6">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <h2 className="flex items-center gap-2 text-lg font-semibold">
                <Crown className="size-5 text-violet-500" /> {user.plan.name} plan
              </h2>
              {!subscriptionIsLive(user.subscription) && (
                <ButtonLink href="/pricing" size="sm" variant={user.plan.id === "free" ? "primary" : "outline"}>
                  {user.plan.id === "free" ? "Upgrade" : "Extend or change"}
                </ButtonLink>
              )}
            </div>
            <p className="mt-1 text-sm text-slate-500">
              {subscriptionIsLive(user.subscription)
                ? user.plan.tagline
                : user.plan_expires_at
                  ? `Active until ${formatDate(user.plan_expires_at, true)}, then back to Free.`
                  : user.plan.tagline}
            </p>
            <SubscriptionPanel user={user} />
            <h3 className="mt-6 text-sm font-semibold">Your privileges</h3>
            <ul className="mt-3 grid gap-2 sm:grid-cols-2">
              {planFeatures(user.plan).map((feature) => (
                <li
                  key={feature.label}
                  className={`rounded-xl border px-3 py-2 text-sm ${
                    feature.included
                      ? "border-slate-200 dark:border-slate-800"
                      : "border-dashed border-slate-200 text-slate-400 line-through dark:border-slate-800"
                  }`}
                >
                  {feature.label}
                </li>
              ))}
              {user.daily_limit !== user.plan.privileges.docs_per_24h && (
                <li className="rounded-xl border border-violet-200 bg-violet-50 px-3 py-2 text-sm text-violet-800 sm:col-span-2 dark:border-violet-500/30 dark:bg-violet-500/10 dark:text-violet-200">
                  Custom limit set by the administrator: {user.daily_limit} PDFs every 24 hours
                </li>
              )}
            </ul>
          </Card>

          <Card className="p-6">
            <h2 className="flex items-center gap-2 text-lg font-semibold">
              <Receipt className="size-5 text-brand-500" /> Payments
            </h2>
            {payments === null ? (
              <div className="skeleton mt-4 h-16" />
            ) : payments.length === 0 ? (
              <p className="mt-3 text-sm text-slate-500">No payments yet.</p>
            ) : (
              <ul className="mt-4 divide-y divide-slate-100 dark:divide-slate-800">
                {payments.map((payment) => (
                  <li key={payment.created_at} className="flex items-center justify-between gap-3 py-3 text-sm">
                    <div>
                      <p className="font-medium capitalize">
                        {payment.plan} · {payment.kind === "subscription" ? "monthly subscription" : "30-day pass"}
                      </p>
                      <p className="text-xs text-slate-500">{formatDate(payment.created_at, true)}</p>
                    </div>
                    <div className="text-right">
                      <p className="font-semibold">
                        ${payment.amount} {payment.currency}
                      </p>
                      <Badge tone={PAYMENT_TONE[payment.status] ?? "amber"}>{payment.status.toLowerCase()}</Badge>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </Card>
        </div>
      </div>
    </AppPage>
  );
}
