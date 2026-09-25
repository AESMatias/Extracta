"use client";

import { BadgeCheck, Crown, KeyRound, LogOut, Mail, Receipt } from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { AppPage } from "@/components/app-header";
import { DeleteAccountCard } from "@/components/delete-account-card";
import { SecurityCard } from "@/components/security-card";
import { subscriptionIsLive, SubscriptionPanel } from "@/components/subscription-panel";
import { Badge, Button, ButtonLink, Card, PageLoader } from "@/components/ui";
import { UsageCard } from "@/components/usage-card";
import { VerifyEmailBanner } from "@/components/verify-email-banner";
import { api, type Payment } from "@/lib/api";
import { useAuth, useRequireUser } from "@/lib/auth";
import { formatDate } from "@/lib/documents";
import { fill, useI18n } from "@/lib/i18n";
import { formatPages, PACKS, planFeatures, PLANS } from "@/lib/plans";

const STATUS_TONE = { active: "green", pending: "amber", rejected: "red", suspended: "red", deleted: "slate" } as const;
const PAYMENT_TONE: Record<string, "green" | "amber" | "red"> = { COMPLETED: "green", REFUNDED: "red", REVERSED: "red" };
type PaymentStatus = keyof typeof import("@/lib/messages/en").en.account.paymentStatus;

export default function AccountPage() {
  const { user, loading } = useRequireUser();
  const { logout } = useAuth();
  const router = useRouter();
  const [payments, setPayments] = useState<Payment[] | null>(null);
  const { m, locale } = useI18n();
  const a = m.account;

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
      <h1 className="text-2xl font-bold tracking-tight sm:text-3xl">{a.title}</h1>
      {!user.email_verified && (
        <div className="mt-4">
          <VerifyEmailBanner user={user} />
        </div>
      )}

      <div className="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.2fr)]">
        <div className="space-y-6">
          <Card className="p-6">
            <div className="flex items-center gap-4">
              <div className="grid size-14 shrink-0 place-items-center rounded-full bg-signature text-xl font-bold text-white">
                {(user.name ?? user.email).charAt(0).toUpperCase()}
              </div>
              <div className="min-w-0">
                <p className="truncate text-lg font-semibold">{user.name ?? a.noName}</p>
                <p className="flex items-center gap-1.5 truncate text-sm text-slate-500">
                  <Mail className="size-3.5" /> {user.email}
                </p>
              </div>
            </div>
            <dl className="mt-6 space-y-3 text-sm">
              <div className="flex justify-between gap-4">
                <dt className="text-slate-500">{a.email}</dt>
                <dd>
                  {user.email_verified ? (
                    <Badge tone="green">
                      <BadgeCheck className="size-3" /> {a.verified}
                    </Badge>
                  ) : (
                    <Badge tone="amber">{a.notVerified}</Badge>
                  )}
                </dd>
              </div>
              <div className="flex justify-between gap-4">
                <dt className="text-slate-500">{a.status}</dt>
                <dd>
                  <Badge tone={STATUS_TONE[user.status]}>{a.statuses[user.status]}</Badge>
                </dd>
              </div>
              <div className="flex justify-between gap-4">
                <dt className="text-slate-500">{a.methods}</dt>
                <dd className="flex gap-1.5">
                  {user.has_password && (
                    <Badge tone="slate">
                      <KeyRound className="size-3" /> {m.auth.password}
                    </Badge>
                  )}
                  {user.has_google && <Badge tone="slate">Google</Badge>}
                </dd>
              </div>
              <div className="flex justify-between gap-4">
                <dt className="text-slate-500">{a.memberSince}</dt>
                <dd>{formatDate(user.created_at)}</dd>
              </div>
            </dl>
            <Button variant="outline" className="mt-6 w-full" onClick={signOut} icon={<LogOut className="size-4" />}>
              {m.common.signOut}
            </Button>
          </Card>
          <SecurityCard user={user} />
          <UsageCard user={user} />
          <DeleteAccountCard user={user} />
        </div>

        <div className="space-y-6">
          <Card className="p-6">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <h2 className="flex items-center gap-2 text-lg font-semibold">
                <Crown className="size-5 text-teal-500" /> {fill(a.planTitle, { plan: user.plan.name })}
              </h2>
              {!subscriptionIsLive(user.subscription) && (
                <ButtonLink href="/pricing" size="sm" variant={user.plan.id === "free" ? "primary" : "outline"}>
                  {user.plan.id === "free" ? a.upgrade : a.change}
                </ButtonLink>
              )}
            </div>
            <p className="mt-1 text-sm text-slate-500">
              {subscriptionIsLive(user.subscription)
                ? user.plan.tagline
                : user.plan_expires_at
                  ? fill(a.activeUntil, { date: formatDate(user.plan_expires_at, true) })
                  : user.plan.tagline}
            </p>
            <SubscriptionPanel user={user} />
            <h3 className="mt-6 text-sm font-semibold">{a.privileges}</h3>
            <ul className="mt-3 grid grid-cols-1 gap-2 sm:grid-cols-2">
              {planFeatures(user.privileges, m, locale).map((feature) => (
                <li
                  key={feature.label}
                  className={` border px-3 py-2 text-sm ${
                    feature.included
                      ? "border-slate-200 dark:border-slate-800"
                      : "border-dashed border-slate-200 text-slate-400 line-through dark:border-slate-800"
                  }`}
                >
                  {feature.label}
                </li>
              ))}
              {user.page_limit !== user.plan.privileges.pages && (
                <li className="border border-teal-200 bg-teal-50 px-3 py-2 text-sm text-teal-800 sm:col-span-2 dark:border-teal-500/30 dark:bg-teal-500/10 dark:text-teal-200">
                  {fill(a.customLimit, { pages: formatPages(user.page_limit, locale) })}
                </li>
              )}
            </ul>
          </Card>

          <Card className="p-6">
            <h2 className="flex items-center gap-2 text-lg font-semibold">
              <Receipt className="size-5 text-brand-500" /> {a.payments}
            </h2>
            {payments === null ? (
              <div className="skeleton mt-4 h-16" />
            ) : payments.length === 0 ? (
              <p className="mt-3 text-sm text-slate-500">{a.noPayments}</p>
            ) : (
              <ul className="mt-4 divide-y divide-slate-100 dark:divide-slate-800">
                {payments.map((payment) => (
                  <li key={payment.created_at} className="flex items-center justify-between gap-3 py-3 text-sm">
                    <div>
                      <p className="font-medium">
                        {payment.kind === "pages"
                          ? fill(a.packPayment, { pages: formatPages(payment.pages ?? PACKS.find((p) => p.id === payment.plan)?.pages ?? 0, locale) })
                          : fill(payment.kind === "subscription" ? a.subscriptionPayment : a.passPayment, {
                              plan: PLANS.find((p) => p.id === payment.plan)?.name ?? payment.plan,
                            })}
                      </p>
                      <p className="text-xs text-slate-500">{formatDate(payment.created_at, true)}</p>
                    </div>
                    <div className="text-right">
                      <p className="font-semibold">
                        ${payment.amount} {payment.currency}
                      </p>
                      <Badge tone={PAYMENT_TONE[payment.status] ?? "amber"}>{a.paymentStatus[payment.status as PaymentStatus] ?? payment.status.toLowerCase()}</Badge>
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
