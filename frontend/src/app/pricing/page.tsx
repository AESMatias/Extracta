"use client";

import { ArrowLeft, CalendarClock, Check, ShieldCheck } from "lucide-react";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useCallback, useEffect, useRef } from "react";

import { PayPalCheckout } from "@/components/paypal-checkout";
import { PlanCard } from "@/components/pricing";
import { SiteFooter } from "@/components/site-footer";
import { SiteHeader } from "@/components/site-header";
import { useToast } from "@/components/toast";
import { Button, ButtonLink, Card, SectionTitle } from "@/components/ui";
import type { PlanId, User } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { formatDate } from "@/lib/documents";
import { planFeatures, PLANS } from "@/lib/plans";

function Checkout({ planId }: { planId: PlanId }) {
  const plan = PLANS.find((p) => p.id === planId);
  const { user, setUser } = useAuth();
  const { toast } = useToast();
  const router = useRouter();

  const onPaid = useCallback(
    (updated: User) => {
      setUser(updated);
      toast("success", `Welcome to ${updated.plan.name}!`, `Your plan is active until ${formatDate(updated.plan_expires_at)}.`);
      router.push("/app");
    },
    [setUser, toast, router],
  );

  if (!plan || plan.id === "free" || !user) return null;
  const sameActivePlan = user.plan.id === plan.id && user.plan_expires_at;

  return (
    <Card className="mx-auto mt-12 max-w-3xl overflow-hidden">
      <div className="grid md:grid-cols-2">
        <div className="bg-gradient-to-br from-brand-600 via-violet-600 to-fuchsia-600 p-6 text-white sm:p-8">
          <p className="text-sm font-medium text-white/70">You are buying</p>
          <h2 className="mt-1 text-2xl font-bold">Extracta {plan.name}</h2>
          <p className="mt-4 flex items-baseline gap-1">
            <span className="text-5xl font-bold">${plan.price_usd}</span>
            <span className="text-white/70">USD</span>
          </p>
          <p className="mt-2 flex items-center gap-2 text-sm text-white/80">
            <CalendarClock className="size-4" /> 30 days · no automatic renewal
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
          <p className="text-sm text-slate-600 dark:text-slate-400">
            {sameActivePlan
              ? `You already have ${plan.name} until ${formatDate(user.plan_expires_at)}. Buying again adds 30 more days.`
              : user.plan.id !== "free" && user.plan_expires_at
                ? `This replaces your current ${user.plan.name} plan starting today.`
                : "Pay once with PayPal or a card. Your plan activates immediately."}
          </p>
          <div className="mt-6">
            <PayPalCheckout plan={plan} onPaid={onPaid} />
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
  const checkoutRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (selected && user) checkoutRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
  }, [selected, user]);

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
        subtitle="Start free. Buy a 30-day pass when you need more PDFs per day. No subscription, no automatic charges."
      />

      <div className="mt-14 flex flex-wrap justify-center gap-5 *:w-full sm:*:w-[calc(50%-0.625rem)] lg:*:w-[calc(33.333%-0.834rem)] xl:*:w-[calc(20%-1rem)]">
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
          } else if (user) {
            action = (
              <Button
                variant={plan.highlight ? "primary" : "outline"}
                className="w-full"
                onClick={() => router.replace(`/pricing?plan=${plan.id}`, { scroll: false })}
              >
                {current ? "Add 30 days" : `Choose ${plan.name}`}
              </Button>
            );
          } else {
            action = (
              <ButtonLink href={`/register?next=${encodeURIComponent(`/pricing?plan=${plan.id}`)}`} variant={plan.highlight ? "primary" : "outline"} className="w-full">
                Get {plan.name}
              </ButtonLink>
            );
          }
          return <PlanCard key={plan.id} plan={plan} action={action} current={current} />;
        })}
      </div>

      <div ref={checkoutRef} className="scroll-mt-24">
        {selected && user && <Checkout planId={selected} />}
        {selected && user && (
          <div className="mt-4 text-center">
            <Button variant="ghost" size="sm" onClick={() => router.replace("/pricing", { scroll: false })} icon={<ArrowLeft className="size-4" />}>
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
