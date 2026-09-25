"use client";

import { ArrowLeft, ArrowRight, CalendarClock, Check, Coins, RefreshCw, ShieldCheck } from "lucide-react";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useCallback, useEffect, useRef, useState } from "react";

import { PayPalCheckout, type CheckoutItem } from "@/components/paypal-checkout";
import { DEFAULT_PACK, ModeToggle, PackPicker, PlanCards, type PricingMode } from "@/components/pricing";
import { SiteFooter } from "@/components/site-footer";
import { SiteHeader } from "@/components/site-header";
import { subscriptionIsLive } from "@/components/subscription-panel";
import { useToast } from "@/components/toast";
import { Alert, Button, ButtonLink, Card, SectionTitle } from "@/components/ui";
import { useVerificationRequired, VerifyEmailBanner } from "@/components/verify-email-banner";
import type { PagePack, Plan, User } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { formatDate } from "@/lib/documents";
import { fill, useI18n } from "@/lib/i18n";
import { formatPages, PACKS, planFeatures, PLANS } from "@/lib/plans";

function Checkout({ item }: { item: CheckoutItem }) {
  const { user, setUser } = useAuth();
  const { m, locale } = useI18n();
  const c = m.pricing.checkout;
  const { toast } = useToast();
  const router = useRouter();
  const verificationRequired = useVerificationRequired();

  const onPaid = useCallback(
    (updated: User, activating: boolean) => {
      setUser(updated);
      if (activating) toast("info", c.almost, c.almostText);
      else if (item.kind === "pack")
        toast("success", fill(c.welcomePack, { pages: formatPages(item.pack.pages, locale) }), fill(c.welcomePackText, { balance: formatPages(updated.page_credits, locale) }));
      else toast("success", fill(c.welcomePlan, { plan: updated.plan.name }), fill(c.renewsOn, { date: formatDate(updated.subscription?.next_billing_at ?? null) }));
      router.push("/app");
    },
    [setUser, toast, router, item, c, locale],
  );

  if (!user) return null;
  if (item.kind === "plan" && subscriptionIsLive(user.subscription)) return null;

  let note: string;
  if (item.kind === "pack") note = c.packNote;
  else if (user.plan.id === item.plan.id && user.plan_expires_at) note = fill(c.samePlan, { plan: item.plan.name, date: formatDate(user.plan_expires_at) });
  else if (user.plan.id !== "free" && user.plan_expires_at) note = fill(c.replaces, { current: user.plan.name, plan: item.plan.name });
  else note = fill(c.monthlyNote, { price: item.plan.price_usd });

  const features =
    item.kind === "plan"
      ? planFeatures(item.plan.privileges, m, locale).filter((f) => f.included).map((f) => f.label)
      : m.pricing.packPoints;

  return (
    <Card className="mx-auto mt-12 max-w-3xl overflow-hidden">
      <div className="grid md:grid-cols-2">
        <div className="bg-signature animate-pan p-6 text-white sm:p-8">
          <p className="text-sm font-medium text-white/75">{item.kind === "plan" ? c.subscribing : c.buying}</p>
          <h2 className="mt-1 text-2xl font-bold">
            {item.kind === "plan" ? `Extracta ${item.plan.name}` : fill(c.packName, { pages: formatPages(item.pack.pages, locale) })}
          </h2>
          <p className="mt-4 flex items-baseline gap-1">
            <span className="text-5xl font-bold">${item.kind === "plan" ? item.plan.price_usd : item.pack.price_usd}</span>
            <span className="text-white/75">USD{item.kind === "plan" ? ` ${m.common.perMonth}` : ""}</span>
          </p>
          <p className="mt-2 flex items-center gap-2 text-sm text-white/85">
            {item.kind === "plan" ? (
              <>
                <RefreshCw className="size-4" /> {c.renews}
              </>
            ) : (
              <>
                <Coins className="size-4" /> {c.neverExpire}
              </>
            )}
          </p>
          <ul className="mt-6 space-y-2 text-sm">
            {features.map((label) => (
              <li key={label} className="flex items-center gap-2">
                <Check className="size-4 text-accent" /> {label}
              </li>
            ))}
          </ul>
        </div>
        <div className="p-6 sm:p-8">
          <p className="flex items-start gap-2 text-sm text-slate-600 dark:text-slate-400">
            <CalendarClock className="mt-0.5 size-4 shrink-0" /> {note}
          </p>
          <div className="mt-6">
            {!user.email_verified && verificationRequired ? (
              <VerifyEmailBanner user={user} />
            ) : (
              <PayPalCheckout key={item.kind === "plan" ? item.plan.id : item.pack.id} item={item} onPaid={onPaid} />
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
  const { m, locale } = useI18n();
  const planParam = params.get("plan");
  const packParam = params.get("pack");
  const mode: PricingMode = planParam || params.get("mode") === "subscription" ? "subscription" : "payg";
  const [picked, setPicked] = useState(DEFAULT_PACK.id); // before checkout, the choice lives here
  const selectedPack = PACKS.find((p) => p.id === (packParam ?? picked)) ?? DEFAULT_PACK;
  const selectedPlan = PLANS.find((p) => p.id === planParam && p.id !== "free");
  const checkoutOpen = Boolean(user && (selectedPlan || packParam));
  const checkoutRef = useRef<HTMLDivElement>(null);
  const subscribed = subscriptionIsLive(user?.subscription);

  useEffect(() => {
    if (checkoutOpen) checkoutRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
  }, [checkoutOpen, packParam, planParam]);

  function go(query: Record<string, string>) {
    const search = new URLSearchParams(query);
    router.replace(`/pricing${search.size ? `?${search}` : ""}`, { scroll: false });
  }

  const signUpThen = (next: string) => `/register?next=${encodeURIComponent(next)}`;

  const packAction = (pack: PagePack) =>
    user ? (
      <Button variant="secondary" className="w-full bg-white! text-slate-900! hover:bg-accent!" onClick={() => go({ pack: pack.id })} icon={<ArrowRight className="size-4" />}>
        {fill(m.pricing.buy, { pages: formatPages(pack.pages, locale) })}
      </Button>
    ) : (
      <ButtonLink href={signUpThen(`/pricing?pack=${pack.id}`)} variant="secondary" className="w-full bg-white! text-slate-900! hover:bg-accent!" icon={<ArrowRight className="size-4" />}>
        {fill(m.pricing.buy, { pages: formatPages(pack.pages, locale) })}
      </ButtonLink>
    );

  const planAction = (plan: Plan) => {
    const current = user?.plan.id === plan.id;
    if (plan.id === "free") {
      return user ? (
        <Button variant="outline" className="w-full" disabled>
          {current ? m.pricing.currentPlan : m.pricing.included}
        </Button>
      ) : (
        <ButtonLink href="/register" variant="outline" className="w-full">
          {m.pricing.startFree}
        </ButtonLink>
      );
    }
    if (user && subscribed) {
      return (
        <Button variant="outline" className="w-full" disabled>
          {user.subscription?.plan === plan.id ? m.pricing.yourSubscription : m.pricing.cancelFirst}
        </Button>
      );
    }
    if (user) {
      return (
        <Button variant={plan.highlight ? "primary" : "outline"} className="w-full" onClick={() => go({ plan: plan.id })}>
          {fill(m.pricing.choose, { plan: plan.name })}
        </Button>
      );
    }
    return (
      <ButtonLink href={signUpThen(`/pricing?plan=${plan.id}`)} variant={plan.highlight ? "primary" : "outline"} className="w-full">
        {fill(m.pricing.get, { plan: plan.name })}
      </ButtonLink>
    );
  };

  const item: CheckoutItem | null = selectedPlan
    ? { kind: "plan", plan: selectedPlan }
    : packParam
      ? { kind: "pack", pack: selectedPack }
      : null;

  return (
    <>
      <SectionTitle center title={m.pricing.title} subtitle={m.pricing.subtitle} />

      <div className="mt-10">
        <ModeToggle mode={mode} onChange={(next) => go(next === "subscription" ? { mode: "subscription" } : {})} />
      </div>

      {mode === "subscription" && subscribed && user?.subscription && (
        <div className="mx-auto mt-8 max-w-3xl">
          <Alert
            tone="brand"
            title={fill(m.pricing.subscribedTitle, { plan: PLANS.find((p) => p.id === user.subscription?.plan)?.name ?? "" })}
            action={
              <ButtonLink href="/account" size="sm" variant="outline">
                {m.pricing.manage}
              </ButtonLink>
            }
          >
            {m.pricing.subscribedText}
          </Alert>
        </div>
      )}

      <div className="mt-10">
        {mode === "payg" ? (
          <PackPicker selected={selectedPack.id} onSelect={(id) => {
              setPicked(id);
              if (packParam) go({ pack: id });
            }} action={packAction} />
        ) : (
          <PlanCards action={planAction} currentPlan={user?.plan.id} />
        )}
      </div>

      <div ref={checkoutRef} className="scroll-mt-24">
        {checkoutOpen && item && <Checkout item={item} />}
        {checkoutOpen && (
          <div className="mt-4 text-center">
            <Button variant="ghost" size="sm" onClick={() => go(mode === "subscription" ? { mode: "subscription" } : {})} icon={<ArrowLeft className="size-4" />}>
              {m.common.backToPlans}
            </Button>
          </div>
        )}
      </div>

      <p className="mt-12 flex items-center justify-center gap-2 text-center text-sm text-slate-500">
        <ShieldCheck className="size-4" /> {m.pricing.paypalNote}
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
