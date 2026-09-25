"use client";

import clsx from "clsx";
import { ArrowLeft, CalendarClock, Check, RefreshCw, ShieldCheck } from "lucide-react";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useCallback, useEffect, useRef } from "react";

import { PayPalCheckout } from "@/components/paypal-checkout";
import { PlanCard, PlanGrid } from "@/components/pricing";
import { SiteFooter } from "@/components/site-footer";
import { SiteHeader } from "@/components/site-header";
import { subscriptionIsLive } from "@/components/subscription-panel";
import { useToast } from "@/components/toast";
import { Alert, Button, ButtonLink, Card, SectionTitle } from "@/components/ui";
import { useVerificationRequired, VerifyEmailBanner } from "@/components/verify-email-banner";
import type { BillingMode, PlanId, User } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { formatDate } from "@/lib/documents";
import { planFeatures, PLANS } from "@/lib/plans";

function BillingToggle({ mode, onChange }: { mode: BillingMode; onChange: (mode: BillingMode) => void }) {
  const options: { id: BillingMode; label: string; hint: string }[] = [
    { id: "monthly", label: "Monthly", hint: "renews automatically" },
    { id: "once", label: "30-day pass", hint: "pay once" },
  ];
  return (
    <div role="radiogroup" aria-label="Billing" className="mx-auto mt-10 grid w-full max-w-md grid-cols-2 gap-1 border border-slate-200 bg-white/80 p-1 shadow-sm backdrop-blur dark:border-slate-800 dark:bg-slate-900/70">
      {options.map((option) => (
        <button
          key={option.id}
          role="radio"
          aria-checked={mode === option.id}
          onClick={() => onChange(option.id)}
          className={clsx(
            "cursor-pointer px-3 py-2.5 text-center transition",
            mode === option.id
              ? "bg-signature text-white shadow-md shadow-brand-600/25"
              : "text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800",
          )}
        >
          <span className="block text-sm font-semibold">{option.label}</span>
          <span className={clsx("block text-xs", mode === option.id ? "text-white/80" : "text-slate-500")}>{option.hint}</span>
        </button>
      ))}
    </div>
  );
}

function checkoutNote(user: User, planId: PlanId, planName: string, price: string, mode: BillingMode): string {
  const paidUntil = user.plan_expires_at;
  const samePlan = user.plan.id === planId && paidUntil;
  if (mode === "monthly") {
    if (samePlan) return `You already paid for ${planName} until ${formatDate(paidUntil)}. The first charge happens on that date, so you lose no days.`;
    if (user.plan.id !== "free" && paidUntil) return `Your current ${user.plan.name} plan is replaced by ${planName} today.`;
    return `PayPal charges $${price} today and then every month. Cancel anytime from your account and keep the plan until the period ends.`;
  }
  if (samePlan) return `You already have ${planName} until ${formatDate(paidUntil)}. Buying again adds 30 more days.`;
  if (user.plan.id !== "free" && paidUntil) return `This replaces your current ${user.plan.name} plan starting today.`;
  return "Pay once with PayPal or a card. Your plan activates immediately and nothing renews.";
}

function Checkout({ planId, mode }: { planId: PlanId; mode: BillingMode }) {
  const plan = PLANS.find((p) => p.id === planId);
  const { user, setUser } = useAuth();
  const { toast } = useToast();
  const router = useRouter();
  const verificationRequired = useVerificationRequired();

  const onPaid = useCallback(
    (updated: User, activating: boolean) => {
      setUser(updated);
      if (activating) toast("info", "Almost there", "PayPal is confirming your first payment. Your plan activates in a minute.");
      else if (mode === "monthly")
        toast("success", `Welcome to ${updated.plan.name}!`, `Your subscription renews on ${formatDate(updated.subscription?.next_billing_at ?? null)}.`);
      else toast("success", `Welcome to ${updated.plan.name}!`, `Your plan is active until ${formatDate(updated.plan_expires_at)}.`);
      router.push("/app");
    },
    [setUser, toast, router, mode],
  );

  if (!plan || plan.id === "free" || !user || subscriptionIsLive(user.subscription)) return null;
  const monthly = mode === "monthly";

  return (
    <Card className="mx-auto mt-12 max-w-3xl overflow-hidden">
      <div className="grid md:grid-cols-2">
        <div className="bg-signature animate-pan p-6 text-white sm:p-8">
          <p className="text-sm font-medium text-white/70">{monthly ? "You are subscribing to" : "You are buying"}</p>
          <h2 className="mt-1 text-2xl font-bold">Extracta {plan.name}</h2>
          <p className="mt-4 flex items-baseline gap-1">
            <span className="text-5xl font-bold">${plan.price_usd}</span>
            <span className="text-white/70">USD{monthly ? " / month" : ""}</span>
          </p>
          <p className="mt-2 flex items-center gap-2 text-sm text-white/80">
            {monthly ? (
              <>
                <RefreshCw className="size-4" /> Renews every month · cancel anytime
              </>
            ) : (
              <>
                <CalendarClock className="size-4" /> 30 days · no automatic renewal
              </>
            )}
          </p>
          <ul className="mt-6 space-y-2 text-sm">
            {planFeatures(plan)
              .filter((f) => f.included)
              .map((f) => (
                <li key={f.label} className="flex items-center gap-2">
                  <Check className="size-4 text-white/80" /> {f.label}
                </li>
              ))}
          </ul>
        </div>
        <div className="p-6 sm:p-8">
          <p className="text-sm text-slate-600 dark:text-slate-400">{checkoutNote(user, plan.id, plan.name, plan.price_usd, mode)}</p>
          <div className="mt-6">
            {!user.email_verified && verificationRequired ? (
              <VerifyEmailBanner user={user} />
            ) : (
              <PayPalCheckout key={mode} plan={plan} mode={mode} onPaid={onPaid} />
            )}
          </div>
        </div>
      </div>
    </Card>
  );
}

function PricingContent() {
  const params = useSearchParams();
  const router = useRouter();
  const { user } = useAuth();
  const selected = (params.get("plan") as PlanId | null) ?? null;
  const mode: BillingMode = params.get("billing") === "once" ? "once" : "monthly";
  const checkoutRef = useRef<HTMLDivElement>(null);
  const subscribed = subscriptionIsLive(user?.subscription);

  useEffect(() => {
    if (selected && user) checkoutRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
  }, [selected, user]);

  function go(plan: PlanId | null, billing: BillingMode) {
    const query = new URLSearchParams({ ...(plan ? { plan } : {}), ...(billing === "once" ? { billing } : {}) });
    router.replace(`/pricing${query.size ? `?${query}` : ""}`, { scroll: false });
  }

  return (
    <>
      <SectionTitle
        center
        eyebrow="Pricing"
        title={
          <>
            Plans for every volume, <span className="text-gradient">from $1.99</span>
          </>
        }
        subtitle="Start free. Subscribe monthly and cancel anytime, or buy a single 30-day pass that never renews."
      />

      <BillingToggle mode={mode} onChange={(billing) => go(selected, billing)} />

      {subscribed && user?.subscription && (
        <div className="mx-auto mt-8 max-w-3xl">
          <Alert
            tone="brand"
            title={`You have a monthly ${PLANS.find((p) => p.id === user.subscription?.plan)?.name ?? ""} subscription`}
            action={
              <ButtonLink href="/account" size="sm" variant="outline">
                Manage
              </ButtonLink>
            }
          >
            To change plans, cancel it in your account first. You keep your plan until the period you paid for ends.
          </Alert>
        </div>
      )}

      <div className="mt-10">
        <PlanGrid>
        {PLANS.map((plan) => {
          const current = user?.plan.id === plan.id;
          let action;
          if (plan.id === "free") {
            action = user ? (
              <Button variant="outline" className="w-full" disabled>
                {current ? "Your current plan" : "Included"}
              </Button>
            ) : (
              <ButtonLink href="/register" variant="outline" className="w-full">
                Start free
              </ButtonLink>
            );
          } else if (user && subscribed) {
            action = (
              <Button variant="outline" className="w-full" disabled>
                {user.subscription?.plan === plan.id ? "Your subscription" : "Cancel yours first"}
              </Button>
            );
          } else if (user) {
            action = (
              <Button variant={plan.highlight ? "primary" : "outline"} className="w-full" onClick={() => go(plan.id, mode)}>
                {mode === "monthly" ? `Subscribe to ${plan.name}` : current ? "Add 30 days" : `Buy ${plan.name}`}
              </Button>
            );
          } else {
            const next = `/pricing?plan=${plan.id}${mode === "once" ? "&billing=once" : ""}`;
            action = (
              <ButtonLink href={`/register?next=${encodeURIComponent(next)}`} variant={plan.highlight ? "primary" : "outline"} className="w-full">
                Get {plan.name}
              </ButtonLink>
            );
          }
          return <PlanCard key={plan.id} plan={plan} action={action} current={current} period={mode === "monthly" ? "/ month" : "/ 30 days"} />;
        })}
        </PlanGrid>
      </div>

      <div ref={checkoutRef} className="scroll-mt-24">
        {selected && user && <Checkout planId={selected} mode={mode} />}
        {selected && user && (
          <div className="mt-4 text-center">
            <Button variant="ghost" size="sm" onClick={() => go(null, mode)} icon={<ArrowLeft className="size-4" />}>
              Back to all plans
            </Button>
          </div>
        )}
      </div>

      <p className="mt-12 flex items-center justify-center gap-2 text-center text-sm text-slate-500">
        <ShieldCheck className="size-4" /> Payments are processed by PayPal. Prices in USD; taxes may apply in your country.
      </p>
    </>
  );
}

export default function PricingPage() {
  return (
    <>
      <SiteHeader />
      <main className="relative mx-auto max-w-7xl px-4 py-14 sm:px-6 sm:py-20">
        <div className="bg-dots absolute inset-0 -z-10 [mask-image:radial-gradient(ellipse_at_top,black,transparent_60%)]" />
        <Suspense>
          <PricingContent />
        </Suspense>
      </main>
      <SiteFooter />
    </>
  );
}
